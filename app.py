"""Simulacro del Amigo Invisible Doble.
Usa la lógica REAL de app.py (base de datos, sorteo, votos, puntuación y fechas) con jugadores
inventados y una base de datos temporal. No necesita Streamlit instalado ni toca tus datos.
Uso:  python simulacro.py   (con app.py en la misma carpeta)
"""
import os, sys, random, tempfile
from datetime import date
from unittest.mock import MagicMock

AQUI = os.path.dirname(os.path.abspath(__file__))
random.seed(2026)
os.chdir(tempfile.mkdtemp())          # base de datos temporal: nada de lo tuyo se toca
sys.modules["streamlit"] = MagicMock()  # solo probamos la lógica, no la pantalla

src = open(os.path.join(AQUI, "app.py"), encoding="utf-8").read()
corte = src.index("# ---------------------------------------------------------------- SESIÓN / LOGIN")
ns = {"__name__": "simulacro"}
exec(compile(src[:corte], "app.py", "exec"), ns)
q, derangement = ns["q"], ns["derangement"]
ok = lambda m: print("  ✅", m)

# ------------------------------------------------------------ 1. SORTEO
print("\n1) SORTEO")
part = ["Ana", "Luis", "María", "Pedro", "Carmen", "Jorge"]
det = ["Lucía", "Nico"]
parejas = [("Ana", "Luis"), ("María", "Pedro")]
prohibidos = {x for a, b in parejas for x in ((a, b), (b, a))}
regalos = derangement(part, frozenset(prohibidos))
assert regalos, "el sorteo no encontró solución"
pers = ns["PERSONAJES_POR_DEFECTO"][:]
random.shuffle(pers)
pines = {}
for n in part + det:
    pines[n] = ns["nuevo_pin"]()
    q("INSERT INTO jugadores (nombre, rol, personaje, regala_a) VALUES (?,?,?,?)",
      (n, "Participante" if n in part else "Detective", pers.pop(), regalos.get(n, "Ninguno")))
    ns["poner_pin"](n, pines[n])
js = [dict(j) for j in ns["jugadores"]()]
char = {j["nombre"]: j["personaje"] for j in js}
print("  Reparto:", ", ".join(f"{n}→{regalos[n]}" for n in part))
assert all(regalos[n] != n for n in part); ok("nadie se regala a sí mismo")
assert all((a, regalos[a]) not in prohibidos for a in part); ok("las parejas excluidas no se tocan")
assert sorted(regalos.values()) == sorted(part); ok("cada participante regala una vez y recibe una vez")
assert len(set(char.values())) == len(js); ok("cada jugador tiene un personaje distinto")
assert all(j["regala_a"] == "Ninguno" for j in js if j["rol"] == "Detective"); ok("los detectives no tienen amigo invisible")
f = q("SELECT * FROM jugadores WHERE nombre='Ana'", fetch=True)[0]
assert ns["hash_pin"](pines["Ana"], f["salt"]) == f["pin_hash"]
assert ns["hash_pin"]("0000" if pines["Ana"] != "0000" else "1111", f["salt"]) != f["pin_hash"]
ok("el PIN correcto entra y uno incorrecto no")

# ------------------------------------------------------------ 2. CALENDARIO
print("\n2) CALENDARIO (¿qué votación está abierta cada día?)")
esperado = {date(2026, 12, 3): [], date(2026, 12, 4): [], date(2026, 12, 10): [], date(2026, 12, 11): [0],
            date(2026, 12, 17): [0], date(2026, 12, 18): [1], date(2026, 12, 22): [1], date(2026, 12, 23): [2],
            date(2026, 12, 24): [2], date(2026, 12, 25): [3], date(2026, 12, 26): []}
for d, exp in esperado.items():
    ns["hoy"] = lambda d=d: d
    abiertas = [i for i in range(4) if ns["ronda_abierta"](i)]
    assert abiertas == exp, (d, abiertas, exp)
ok("las 4 votaciones se abren y cierran en las fechas pactadas (11, 18, 23 y 25 dic)")

# ------------------------------------------------------------ 3. MURO
print("\n3) MURO")
q("INSERT INTO pistas (semana, personaje, texto, url, imagen, tipo) VALUES (1,?,?,?,?,?)", (char["Ana"], "Ho ho ho", "", "", "pista"))
q("INSERT INTO pistas (semana, personaje, texto, url, imagen, tipo) VALUES (0,?,?,?,?,?)", (char["Luis"], "¡Qué ganas de comer turrón!", "", "", "mensaje"))
q("INSERT INTO comentarios (pista_id, personaje, texto) VALUES (1,?,?)", (char["Pedro"], "Eso suena a alguien que conozco…"))
assert len(q("SELECT * FROM pistas", fetch=True)) == 2
assert q("SELECT tipo FROM pistas WHERE id=2", fetch=True)[0]["tipo"] == "mensaje"
assert len(q("SELECT * FROM comentarios WHERE pista_id=1", fetch=True)) == 1
ok("pista, mensaje libre y comentario se guardan y se leen bien")

assert not ns["revelacion_activa"](); q("INSERT OR REPLACE INTO ajustes VALUES ('revelacion', '1')"); assert ns["revelacion_activa"]()
q("INSERT OR REPLACE INTO ajustes VALUES ('revelacion', '0')"); assert not ns["revelacion_activa"]()
ok("la revelación final está oculta hasta que el organizador la activa")

# ------------------------------------------------------------ 4. LAS 5 VOTACIONES
print("\n4) VOTACIONES (los jugadores van acertando más cada semana)")
prob = [0.15, 0.35, 0.60, 0.85]
esperados = {n: [0] * 4 for n in char}


def votar(v, r):
    otros = [n for n in char if n != v]
    pool = [char[o] for o in otros]
    aciertan = {o for o in otros if random.random() < prob[r]}
    elegido, usados, pts = {}, set(), 0
    for o in otros:
        if o in aciertan:
            elegido[o] = char[o]; usados.add(char[o]); pts += 1
    for o in otros:
        if o not in aciertan:
            libres = [c for c in pool if c != char[o] and c not in usados]
            if libres:
                c = random.choice(libres); elegido[o] = c; usados.add(c)
    amigo = None
    if v in part:
        dador = [g for g in part if regalos[g] == v][0]
        if random.random() < prob[r]:
            amigo = char[dador]; pts += 2
        else:
            amigo = random.choice([char[g] for g in part if g not in (v, dador)])
    q("DELETE FROM votos WHERE ronda=? AND votante=?", (r, v))
    for o, c in elegido.items():
        q("INSERT INTO votos VALUES (?,?,?,?,?)", (r, v, "P", o, c))
    if amigo:
        q("INSERT INTO votos VALUES (?,?,?,?,?)", (r, v, "A", "", amigo))
    return pts


fechas = ["11 dic", "18 dic", "23 dic", "25 dic"]
for r in range(4):
    for v in char:
        if r == 1:
            votar(v, r)                 # primer envío (se cambia después: prueba de "reenviar voto")
        esperados[v][r] = votar(v, r)
    pts = ns["calcular_puntos"]()
    tot = sorted(((sum(p), n) for n, p in pts.items()), reverse=True)
    print(f"  Votación {r + 1} ({fechas[r]}): líder {tot[0][1]} ({tot[0][0]} pts) · último {tot[-1][1]} ({tot[-1][0]} pts)")

pts = ns["calcular_puntos"]()
assert pts == esperados; ok("los puntos de la app coinciden con los esperados en las 4 votaciones")
assert all(len(q("SELECT * FROM votos WHERE ronda=1 AND votante=? AND tipo='P'", (v,), fetch=True)) <= len(char) - 1 for v in char)
ok("reenviar el voto sustituye al anterior (no se duplica)")
assert all(pts[d][r] <= len(char) - 1 for d in det for r in range(4)); ok("un detective nunca pasa de 1 punto por personaje")
maximo_part = 4 * (len(char) - 1 + 2)
assert all(sum(pts[n]) <= maximo_part for n in part); ok(f"nadie supera el máximo teórico ({maximo_part} pts un participante)")

# ------------------------------------------------------------ 5. RESULTADO FINAL
print("\n5) CLASIFICACIÓN FINAL")
print(f"  {'Jugador':<8} {'Rol':<13} {'V1':>3} {'V2':>3} {'V3':>3} {'V4':>3} {'Total':>6}")
for n in sorted(pts, key=lambda x: -sum(pts[x])):
    rol = "Participante" if n in part else "Detective"
    print(f"  {n:<8} {rol:<13} " + " ".join(f"{p:>3}" for p in pts[n]) + f" {sum(pts[n]):>6}")
print("\nSimulacro completado: toda la lógica del juego funciona de principio a fin.")
