import streamlit as st
import sqlite3
import random
import hashlib
import secrets
import os
import uuid
from contextlib import closing
from datetime import date, timedelta

st.set_page_config(page_title="Amigo Invisible: Liga de Impostores 2026", page_icon="🎄", layout="centered")

# ---------------------------------------------------------------- ESTILO
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Mountains+of+Christmas:wght@400;700&display=swap');
.stApp { background-color: #0B2515; color: #F4EBE1; }
[data-testid="stSidebar"] { background-color: #06190E; }
h1, h2, h3, p, span, label { color: #F4EBE1 !important; }
p, label { font-family: 'Georgia', serif; }
h1, h2, h3 { font-family: 'Mountains of Christmas', 'Georgia', cursive !important; font-weight: 700 !important; letter-spacing: 0.5px; }
h1 { font-size: 3rem !important; color: #E8C46A !important; text-shadow: 2px 2px 0 #721C24; }
h2, h3 { color: #F4EBE1 !important; }
div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button {
    background-color: #721C24; color: #F4EBE1; border: 2px solid #A93226;
    border-radius: 8px; font-weight: bold; transition: all 0.3s ease; }
div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover {
    background-color: #A93226; color: #FFFFFF; border-color: #C0392B; }
.stAlert { background-color: #143F24 !important; border-left: 5px solid #721C24 !important; border-radius: 8px; }
div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {
    background-color: #143F24 !important; border: 1px solid #721C24 !important; }
input, select, textarea { color: #F4EBE1 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- CONFIGURACIÓN
DB_FILE = "juego_navidad.db"
IMG_DIR = "imagenes"
os.makedirs(IMG_DIR, exist_ok=True)

# (inicio de pistas, día de votación) de cada semana
RONDAS = [
    (date(2026, 11, 28), date(2026, 12, 4)),
    (date(2026, 12, 5), date(2026, 12, 11)),
    (date(2026, 12, 12), date(2026, 12, 18)),
    (date(2026, 12, 19), date(2026, 12, 23)),   # votación adelantada
    (date(2026, 12, 24), date(2026, 12, 25)),   # pistas dobles + votación final
]
FIN_JUEGO = date(2026, 12, 25)
PUNTOS_PERSONAJE = 1
PUNTOS_AMIGO = 2

PERSONAJES_POR_DEFECTO = [
    "El Grinch", "Darth Vader", "Harry Potter", "Miércoles Addams", "Jack Sparrow", "Santa Claus",
    "Shrek", "Sherlock Holmes", "Batman", "Barbie", "Spiderman", "Super Mario",
    "El Genio de Aladín", "Pato Donald", "Indiana Jones", "Homer Simpson",
]

try:
    ADMIN_PIN = st.secrets["ADMIN_PIN"]
except Exception:
    ADMIN_PIN = os.environ.get("ADMIN_PIN", "admin1234")


# ---------------------------------------------------------------- BASE DE DATOS (SQLite compartida)
def q(sql, args=(), fetch=False):
    """Ejecuta una consulta. SQLite gestiona la concurrencia, así nadie pisa los datos de otro."""
    with closing(sqlite3.connect(DB_FILE, timeout=15)) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, args)
        rows = cur.fetchall() if fetch else None
        con.commit()
        return rows


def init_db():
    q("""CREATE TABLE IF NOT EXISTS jugadores (
        nombre TEXT PRIMARY KEY, rol TEXT, salt TEXT, pin_hash TEXT,
        personaje TEXT, regala_a TEXT)""")
    q("""CREATE TABLE IF NOT EXISTS pistas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, semana INTEGER, personaje TEXT,
        texto TEXT, url TEXT, imagen TEXT)""")
    q("""CREATE TABLE IF NOT EXISTS votos (
        ronda INTEGER, votante TEXT, tipo TEXT, objetivo TEXT, personaje TEXT,
        PRIMARY KEY (ronda, votante, tipo, objetivo))""")
    q("CREATE TABLE IF NOT EXISTS ajustes (clave TEXT PRIMARY KEY, valor TEXT)")


init_db()


# ---------------------------------------------------------------- UTILIDADES
def hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 100_000).hex()


def nuevo_pin():
    return f"{secrets.randbelow(10000):04d}"


def poner_pin(nombre, pin):
    salt = secrets.token_hex(8)
    q("UPDATE jugadores SET salt=?, pin_hash=? WHERE nombre=?", (salt, hash_pin(pin, salt), nombre))


def jugadores():
    return q("SELECT * FROM jugadores ORDER BY nombre", fetch=True)


def show_img(src):
    try:
        st.image(src, width="stretch")
    except Exception:
        st.image(src, use_container_width=True)


def derangement(items, prohibidos=frozenset()):
    """Sorteo sin que nadie se toque a sí mismo ni caiga en una pareja prohibida.
    Devuelve None si no hay forma de cumplir todas las exclusiones."""
    for _ in range(20000):
        p = items[:]
        random.shuffle(p)
        if all(a != b and (a, b) not in prohibidos for a, b in zip(items, p)):
            return dict(zip(items, p))
    return None


def modo_prueba():
    return st.session_state.get("admin") and st.session_state.get("prueba", False)


def hoy():
    return date.today()


def ronda_abierta(i):
    """Cada votación se puede enviar/cambiar desde su día hasta el día de la siguiente."""
    inicio = RONDAS[i][1]
    fin = RONDAS[i + 1][1] - timedelta(days=1) if i < len(RONDAS) - 1 else FIN_JUEGO
    return inicio <= hoy() <= fin


def semanas_empezadas():
    return [i + 1 for i, r in enumerate(RONDAS) if r[0] <= hoy()]


# ---------------------------------------------------------------- PUNTUACIÓN (calculada desde los votos)
def calcular_puntos():
    js = jugadores()
    char_de = {j["nombre"]: j["personaje"] for j in js}
    dueno = {j["personaje"]: j["nombre"] for j in js}
    regala = {j["nombre"]: j["regala_a"] for j in js}
    pts = {j["nombre"]: [0] * len(RONDAS) for j in js}
    for v in q("SELECT * FROM votos", fetch=True):
        if v["votante"] not in pts:
            continue
        if v["tipo"] == "P" and char_de.get(v["objetivo"]) == v["personaje"]:
            pts[v["votante"]][v["ronda"]] += PUNTOS_PERSONAJE
        elif v["tipo"] == "A":
            d = dueno.get(v["personaje"])
            if d and regala.get(d) == v["votante"]:
                pts[v["votante"]][v["ronda"]] += PUNTOS_AMIGO
    return pts


# ---------------------------------------------------------------- SESIÓN / LOGIN
st.sidebar.title("🎄 Menú")

if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    nombres = [j["nombre"] for j in jugadores()]
    with st.sidebar.form("login"):
        n = st.selectbox("Tu nombre", ["—"] + nombres)
        p = st.text_input("Tu PIN", type="password", max_chars=4)
        if st.form_submit_button("Entrar"):
            fila = q("SELECT * FROM jugadores WHERE nombre=?", (n,), fetch=True)
            if fila and fila[0]["pin_hash"] and secrets.compare_digest(hash_pin(p, fila[0]["salt"]), fila[0]["pin_hash"]):
                st.session_state.usuario = n
                st.rerun()
            else:
                st.sidebar.error("Nombre o PIN incorrectos.")
else:
    st.sidebar.success(f"Hola, {st.session_state.usuario}")
    if st.sidebar.button("Salir"):
        st.session_state.usuario = None
        st.rerun()

with st.sidebar.expander("👑 Organizador"):
    if not st.session_state.get("admin"):
        ap = st.text_input("PIN de organizador", type="password", key="ap")
        if st.button("Entrar como organizador"):
            if ap == ADMIN_PIN:
                st.session_state.admin = True
                st.rerun()
            else:
                st.error("PIN incorrecto.")
    else:
        st.session_state.prueba = st.checkbox("Modo prueba (ignora las fechas)", value=st.session_state.get("prueba", False))
        if st.button("Salir de organizador"):
            st.session_state.admin = False
            st.rerun()

menu = ["🎁 Mi perfil", "🕵️‍♂️ Muro de pistas", "🗳️ Votaciones", "🏆 Ranking"]
if st.session_state.get("admin"):
    menu.append("⚙️ Organizador")
pagina = st.sidebar.selectbox("Ir a:", menu)
usuario = st.session_state.usuario

st.title("🎅 El Banquete de los Impostores Navideños")


def requiere_login():
    if usuario is None:
        st.info("Entra con tu nombre y tu PIN en el menú de la izquierda.")
        st.stop()
    return q("SELECT * FROM jugadores WHERE nombre=?", (usuario,), fetch=True)[0]


# ---------------------------------------------------------------- MI PERFIL
if pagina == "🎁 Mi perfil":
    yo = requiere_login()
    st.header("🎄 Tu perfil secreto")
    st.info(f"🎭 Tu personaje es: **{yo['personaje']}**")
    if yo["rol"] == "Participante":
        st.info(f"🎁 Le haces el regalo a: **{yo['regala_a']}**")
        st.caption("Alguien te lo hará a ti: ¡descubre quién es!")
    else:
        st.info("🕵️‍♂️ Juegas como **Detective Externo** (sin intercambio de regalos).")
    st.caption("Solo tú ves esta pantalla. No se la enseñes a nadie.")

# ---------------------------------------------------------------- MURO DE PISTAS
elif pagina == "🕵️‍♂️ Muro de pistas":
    yo = requiere_login()
    st.header("🕵️‍♂️ El Muro de los Impostores")
    semanas = list(range(1, len(RONDAS) + 1)) if modo_prueba() else semanas_empezadas()
    if not semanas:
        st.warning("El juego empieza el sábado 28 de noviembre.")
    else:
        st.markdown(f"### 📤 Publicar pista como **{yo['personaje']}**")
        with st.form("pista", clear_on_submit=True):
            semana = st.selectbox("Semana de la pista", semanas, index=len(semanas) - 1)
            texto = st.text_area("1. Escribe tu pista (habla como tu personaje):")
            tipo = st.radio("2. Archivo visual (opcional)", ["Ninguno", "Enlace (GIF o imagen)", "Subir foto"])
            url = st.text_input("Enlace del GIF o imagen (solo si eliges enlace):")
            foto = st.file_uploader("Foto (solo si eliges subir foto):", type=["png", "jpg", "jpeg", "gif"])
            if st.form_submit_button("Publicar"):
                ruta = ""
                if tipo == "Subir foto" and foto is not None:
                    ext = foto.name.rsplit(".", 1)[-1].lower()
                    ruta = os.path.join(IMG_DIR, f"{uuid.uuid4().hex}.{ext}")
                    with open(ruta, "wb") as f:
                        f.write(foto.getvalue())
                url_ok = url.strip() if tipo == "Enlace (GIF o imagen)" else ""
                if texto.strip() or url_ok or ruta:
                    q("INSERT INTO pistas (semana, personaje, texto, url, imagen) VALUES (?,?,?,?,?)",
                      (semana, yo["personaje"], texto.strip(), url_ok, ruta))
                    st.success("¡Pista publicada!")
                else:
                    st.error("La pista no puede estar vacía.")
    st.markdown("---")
    st.markdown("### 📜 Historial del muro")
    for p in q("SELECT * FROM pistas ORDER BY id DESC", fetch=True):
        st.markdown(f"🎅 **{p['personaje']}** (Semana {p['semana']})")
        if p["texto"]:
            st.info(p["texto"])
        if p["url"]:
            show_img(p["url"])
        if p["imagen"] and os.path.exists(p["imagen"]):
            show_img(p["imagen"])

# ---------------------------------------------------------------- VOTACIONES
elif pagina == "🗳️ Votaciones":
    yo = requiere_login()
    st.header("🗳️ Urna de votación secreta")
    abiertas = [i for i in range(len(RONDAS)) if modo_prueba() or ronda_abierta(i)]
    if not abiertas:
        proximas = [r[1] for r in RONDAS if r[1] > hoy()]
        st.warning("No hay ninguna votación abierta." + (f" La próxima es el {proximas[0].strftime('%d/%m/%Y')}." if proximas else ""))
        st.stop()
    ronda = st.selectbox("Votación", abiertas, format_func=lambda i: f"Votación {i + 1} ({RONDAS[i][1].strftime('%d/%m')})", index=len(abiertas) - 1)

    otros = [j for j in jugadores() if j["nombre"] != usuario]
    opciones = sorted(j["personaje"] for j in otros)
    previos = {(v["tipo"], v["objetivo"]): v["personaje"] for v in
               q("SELECT * FROM votos WHERE ronda=? AND votante=?", (ronda, usuario), fetch=True)}
    st.caption("Puedes cambiar tu voto y reenviarlo mientras la votación esté abierta. "
               f"{PUNTOS_PERSONAJE} punto por personaje acertado y {PUNTOS_AMIGO} por acertar tu amigo invisible.")

    with st.form("votos"):
        amigo = None
        if yo["rol"] == "Participante":
            st.markdown("### 🧠 Tu apuesta principal (doble punto)")
            ops = ["—"] + [j["personaje"] for j in otros if j["rol"] == "Participante"]
            pr = previos.get(("A", ""), "—")
            amigo = st.selectbox("¿Qué personaje crees que es TU amigo invisible (el que te hace el regalo)?",
                                 ops, index=ops.index(pr) if pr in ops else 0)
        st.markdown("### 🕵️‍♂️ Quiniela de compañeros")
        elegidos = {}
        for j in otros:
            ops = ["—"] + opciones
            pr = previos.get(("P", j["nombre"]), "—")
            elegidos[j["nombre"]] = st.selectbox(f"¿Qué personaje es {j['nombre']}?", ops,
                                                 index=ops.index(pr) if pr in ops else 0, key=f"q_{ronda}_{j['nombre']}")
        if st.form_submit_button("Enviar voto"):
            usados = [v for v in elegidos.values() if v != "—"]
            if len(usados) != len(set(usados)):
                st.error("Has puesto el mismo personaje a dos personas. Cada personaje es de una sola persona.")
            else:
                q("DELETE FROM votos WHERE ronda=? AND votante=?", (ronda, usuario))
                for nombre, pers in elegidos.items():
                    if pers != "—":
                        q("INSERT INTO votos VALUES (?,?,?,?,?)", (ronda, usuario, "P", nombre, pers))
                if amigo and amigo != "—":
                    q("INSERT INTO votos VALUES (?,?,?,?,?)", (ronda, usuario, "A", "", amigo))
                st.success("¡Voto guardado! Los puntos se calculan al cerrar y aparecen en el ranking.")

# ---------------------------------------------------------------- RANKING
elif pagina == "🏆 Ranking":
    st.header("🏆 Ranking global")
    pts = calcular_puntos()
    if not pts:
        st.info("Aún no hay jugadores.")
    else:
        orden = sorted(pts, key=lambda n: -sum(pts[n]))
        filas = []
        for n in orden:
            f = {"Jugador": n}
            for i, v in enumerate(pts[n]):
                f[f"V{i + 1}"] = v
            f["Total"] = sum(pts[n])
            filas.append(f)
        st.dataframe(filas, hide_index=True, use_container_width=True)

        medallas = ["🥇", "🥈", "🥉"]
        txt = f"🎄 *Clasificación Amigo Invisible Doble* 🎅\n{hoy().strftime('%d/%m/%Y')}\n\n"
        for k, n in enumerate(orden):
            partes = ", ".join(f"V{i + 1}: {v}" for i, v in enumerate(pts[n]) if v)
            txt += f"{medallas[k] if k < 3 else str(k + 1) + '.'} *{n}* – {sum(pts[n])} pts" + (f" ({partes})" if partes else "") + "\n"
        txt += f"\n{PUNTOS_PERSONAJE} punto por personaje y {PUNTOS_AMIGO} por tu amigo invisible. ¡Se acumulan! 🏆"
        st.markdown("### 📲 Informe para WhatsApp")
        st.code(txt, language=None)

        if hoy() >= FIN_JUEGO or modo_prueba():
            st.markdown("### 🎭 Revelación final")
            st.dataframe([{"Jugador": j["nombre"], "Personaje": j["personaje"], "Regala a": j["regala_a"]} for j in jugadores()],
                         hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- ORGANIZADOR
elif pagina == "⚙️ Organizador":
    st.header("⚙️ Panel del organizador")
    st.subheader("1. Crear jugadores y hacer el sorteo")
    pool_guardado = q("SELECT valor FROM ajustes WHERE clave='personajes'", fetch=True)
    pool_txt = pool_guardado[0]["valor"] if pool_guardado else "\n".join(PERSONAJES_POR_DEFECTO)
    with st.form("sorteo"):
        part_txt = st.text_area("Participantes del amigo invisible (uno por línea)")
        det_txt = st.text_area("Detectives externos: solo juegan a los personajes (uno por línea)")
        excl_txt = st.text_area(
            "Exclusiones del amigo invisible (opcional, una por línea).\n"
            "«Ana > Luis» = Ana no le hace el regalo a Luis. «Ana = Luis» = no se tocan entre ellos (parejas).",
            placeholder="Ana > Luis\nMaría = Pedro")
        pers_txt = st.text_area("Personajes (uno por línea, al menos tantos como jugadores)", value=pool_txt, height=200)
        ok = st.checkbox("Entiendo que esto borra jugadores, pistas y votos anteriores")
        if st.form_submit_button("🎲 Hacer sorteo"):
            part = list(dict.fromkeys(x.strip() for x in part_txt.splitlines() if x.strip()))
            det = [x.strip() for x in det_txt.splitlines() if x.strip() and x.strip() not in part]
            pers = list(dict.fromkeys(x.strip() for x in pers_txt.splitlines() if x.strip()))
            todos = part + det
            prohibidos, err_excl = set(), []
            for linea in excl_txt.splitlines():
                if not linea.strip():
                    continue
                sep = "=" if "=" in linea else ">" if ">" in linea else None
                if not sep:
                    err_excl.append(f"Formato no válido: «{linea.strip()}»")
                    continue
                a, b = (x.strip() for x in linea.split(sep, 1))
                if a not in part or b not in part:
                    err_excl.append(f"«{linea.strip()}»: ambos nombres deben estar en la lista de participantes.")
                    continue
                prohibidos.add((a, b))
                if sep == "=":
                    prohibidos.add((b, a))
            regalos = derangement(part, frozenset(prohibidos)) if len(part) >= 3 and not err_excl else None
            if not ok:
                st.error("Marca la casilla de confirmación.")
            elif len(part) < 3:
                st.error("Hacen falta al menos 3 participantes.")
            elif err_excl:
                st.error("\n\n".join(err_excl))
            elif regalos is None:
                st.error("Con esas exclusiones no es posible hacer el sorteo. Quita alguna e inténtalo de nuevo.")
            elif len(pers) < len(todos):
                st.error(f"Hay {len(todos)} jugadores y solo {len(pers)} personajes.")
            else:
                q("DELETE FROM jugadores"); q("DELETE FROM pistas"); q("DELETE FROM votos")
                q("INSERT OR REPLACE INTO ajustes VALUES ('personajes', ?)", ("\n".join(pers),))
                random.shuffle(pers)
                pines = {}
                for n in todos:
                    pin = nuevo_pin()
                    pines[n] = pin
                    q("INSERT INTO jugadores (nombre, rol, personaje, regala_a) VALUES (?,?,?,?)",
                      (n, "Participante" if n in part else "Detective", pers.pop(), regalos.get(n, "Ninguno")))
                    poner_pin(n, pin)
                st.session_state.pines = pines
                st.success("¡Sorteo hecho! Envía a cada persona su PIN por WhatsApp.")

    if st.session_state.get("pines"):
        st.subheader("2. PIN de cada jugador (envíaselo en privado)")
        for n, pin in st.session_state.pines.items():
            st.code(f"🎄 Amigo Invisible Doble\nEntra con tu nombre ({n}) y este PIN: {pin}\nTu personaje y tu amigo invisible los verás dentro. ¡Secreto!", language=None)

    st.subheader("3. Regenerar el PIN de alguien")
    js = [j["nombre"] for j in jugadores()]
    if js:
        quien = st.selectbox("Jugador", js)
        if st.button("Generar PIN nuevo"):
            pin = nuevo_pin()
            poner_pin(quien, pin)
            st.success(f"Nuevo PIN de {quien}: **{pin}**")

    st.subheader("4. Asignaciones (solo para el organizador)")
    if st.checkbox("Mostrar asignaciones (¡spoilers!)"):
        st.dataframe([{"Jugador": j["nombre"], "Rol": j["rol"], "Personaje": j["personaje"], "Regala a": j["regala_a"]}
                      for j in jugadores()], hide_index=True, use_container_width=True)
