import streamlit as st
import sqlite3
import random
import hashlib
import secrets
import os
import uuid
import html
from contextlib import closing
from datetime import date, timedelta

st.set_page_config(page_title="Amigo Invisible: Liga de Impostores 2026", page_icon="🎄", layout="centered")

# ---------------------------------------------------------------- ESTILO
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Mountains+of+Christmas:wght@400;700&display=swap');
.stApp { background-color: #0B2515; color: #F4EBE1; }
[data-testid="stSidebar"] { background-color: #06190E; }
/* Barra superior y menú de Streamlit con los colores de la web */
header[data-testid="stHeader"], [data-testid="stHeader"], [data-testid="stToolbar"] { background-color: #0B2515 !important; }
[data-testid="stDecoration"] { background: #0B2515 !important; background-image: none !important; }
[data-testid="stHeader"] button, [data-testid="stHeader"] svg, [data-testid="stToolbar"] svg,
[data-testid="stToolbar"] button, [data-testid="stMainMenu"] svg { color: #F4EBE1 !important; fill: #F4EBE1 !important; }
[data-testid="stHeader"] button:hover, [data-testid="stToolbar"] button:hover { background-color: #143F24 !important; }
div[data-baseweb="popover"][data-testid="stMainMenuPopover"],
div[data-baseweb="popover"][data-testid="stMainMenuPopover"] ul,
div[data-baseweb="popover"][data-testid="stMainMenuPopover"] li,
div[data-baseweb="popover"][data-testid="stMainMenuPopover"] div { background-color: #143F24 !important; }
div[data-baseweb="popover"][data-testid="stMainMenuPopover"] *,
div[data-baseweb="popover"][data-testid="stMainMenuPopover"] svg { color: #F4EBE1 !important; fill: #F4EBE1 !important; }
div[data-baseweb="popover"][data-testid="stMainMenuPopover"] li:hover,
div[data-baseweb="popover"][data-testid="stMainMenuPopover"] li:hover div { background-color: #721C24 !important; }
[data-testid="main-menu-divider"], div[data-baseweb="popover"][data-testid="stMainMenuPopover"] hr { border-color: #721C24 !important; background-color: #721C24 !important; }
div[role="dialog"] { background-color: #0B2515 !important; color: #F4EBE1 !important; border: 1px solid #721C24; }
/* Desplegable del organizador: mismo color que el fondo del menú */
[data-testid="stExpander"], [data-testid="stExpander"] details, [data-testid="stExpander"] summary,
[data-testid="stExpander"] details > div { background-color: #06190E !important; color: #F4EBE1 !important; }
[data-testid="stExpander"] details { border: 1px solid #721C24 !important; border-radius: 8px; }
[data-testid="stExpander"] summary:hover { background-color: #0B2515 !important; }
[data-testid="stExpander"] summary * { color: #F4EBE1 !important; }
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
/* Casillas blancas con letra negra */
div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"], div[data-baseweb="base-input"] {
    background-color: #FFFFFF !important; border: 1px solid #721C24 !important; }
input, select, textarea,
div[data-baseweb="input"] *, div[data-baseweb="select"] *, div[data-baseweb="textarea"] * {
    color: #000000 !important; -webkit-text-fill-color: #000000 !important; }
::placeholder { color: #6B6B6B !important; -webkit-text-fill-color: #6B6B6B !important; opacity: 1; }
/* Menús desplegables */
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li, ul[role="listbox"] { background-color: #FFFFFF !important; }
div[data-baseweb="popover"] *, ul[role="listbox"] * { color: #000000 !important; }
/* Zona de subir fotos y bloques de código */
[data-testid="stFileUploaderDropzone"] *, pre, pre *, code, code * { color: #000000 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- CONFIGURACIÓN
DB_FILE = "juego_navidad.db"
IMG_DIR = "imagenes"
AVATAR_DIR = "avatares"
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)

# (inicio de pistas, día de votación) de cada semana
RONDAS = [
    (date(2026, 12, 4), date(2026, 12, 11)),    # primera pista: viernes 4 de diciembre
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
    # Convierte los parámetros a tipos simples (texto, número, None) para evitar errores de enlace en SQLite
    args = tuple(a if a is None or isinstance(a, (int, float, bytes)) else str(a) for a in args)
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
    try:  # bases de datos antiguas: añade el tipo de publicación (pista o mensaje libre)
        q("ALTER TABLE pistas ADD COLUMN tipo TEXT DEFAULT 'pista'")
    except sqlite3.OperationalError:
        pass
    q("""CREATE TABLE IF NOT EXISTS comentarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pista_id INTEGER, personaje TEXT, texto TEXT)""")
    q("CREATE TABLE IF NOT EXISTS avatares (personaje TEXT PRIMARY KEY, ruta TEXT)")
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


def normalizar_url(url):
    """Convierte enlaces de página de Giphy en el enlace directo del GIF."""
    url = url.strip()
    base = url.split("?")[0].rstrip("/")
    if any(x in base for x in ("giphy.com/gifs/", "giphy.com/stickers/", "giphy.com/embed/")):
        gid = base.split("/")[-1].split("-")[-1]
        return f"https://media.giphy.com/media/{gid}/giphy.gif"
    return url


def mostrar_enlace(url):
    """Pinta la imagen con una etiqueta <img> (más tolerante que st.image) y deja un enlace de respaldo."""
    u = normalizar_url(url)
    st.markdown(f'<img src="{html.escape(u, quote=True)}" style="width:100%;border-radius:8px" '
                f'referrerpolicy="no-referrer" alt="pista">', unsafe_allow_html=True)
    st.caption(f"[🔗 ¿No se ve? Abrir enlace]({u})")


def todos_los_avatares():
    return {r["personaje"]: r["ruta"] for r in q("SELECT * FROM avatares", fetch=True) if os.path.exists(r["ruta"])}


def cabecera(avatar, texto):
    """Foto de perfil del personaje (o una máscara si no tiene) junto al texto."""
    c1, c2 = st.columns([1, 5])
    with c1:
        if avatar:
            st.image(avatar, width=64)
        else:
            st.markdown("<div style='font-size:44px;line-height:1.2'>🎭</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(texto)


def derangement(items, prohibidos=frozenset()):
    """Sorteo sin que nadie se toque a sí mismo ni caiga en una pareja prohibida.
    Devuelve None si no hay forma de cumplir todas las exclusiones."""
    for _ in range(20000):
        p = items[:]
        random.shuffle(p)
        if all(a != b and (a, b) not in prohibidos for a, b in zip(items, p)):
            return dict(zip(items, p))
    return None


def revelacion_activa():
    r = q("SELECT valor FROM ajustes WHERE clave='revelacion'", fetch=True)
    return bool(r) and r[0]["valor"] == "1"


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
            fila = []
            if n and n != "—":
                try:
                    fila = q("SELECT * FROM jugadores WHERE nombre=?", (n,), fetch=True)
                except Exception as e:  # muestra el error real (Streamlit lo oculta por defecto)
                    st.sidebar.error(f"Error técnico: {type(e).__name__}: {e}")
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


def requiere_login(permitir_admin=False):
    if usuario is None:
        if permitir_admin and st.session_state.get("admin"):
            return None
        st.info("Entra con tu nombre y tu PIN en el menú de la izquierda.")
        st.stop()
    return q("SELECT * FROM jugadores WHERE nombre=?", (usuario,), fetch=True)[0]


# ---------------------------------------------------------------- MI PERFIL
if pagina == "🎁 Mi perfil":
    yo = requiere_login()
    st.header("🎄 Tu perfil secreto")
    av = todos_los_avatares().get(yo["personaje"])
    if av:
        st.image(av, width=140)
    st.info(f"🎭 Tu personaje es: **{yo['personaje']}**")
    if yo["rol"] == "Participante":
        st.info(f"🎁 Le haces el regalo a: **{yo['regala_a']}**")
        st.caption("Alguien te lo hará a ti: ¡descubre quién es!")
    else:
        st.info("🕵️‍♂️ Juegas como **Detective Externo** (sin intercambio de regalos).")
    st.caption("Solo tú ves esta pantalla. No se la enseñes a nadie.")

# ---------------------------------------------------------------- MURO DE PISTAS
elif pagina == "🕵️‍♂️ Muro de pistas":
    yo = requiere_login(permitir_admin=True)
    st.header("🕵️‍♂️ El Muro de los Impostores")
    semanas = list(range(1, len(RONDAS) + 1)) if modo_prueba() else semanas_empezadas()
    if yo is None:
        st.info("Modo organizador: puedes moderar el muro. Para publicar, entra con tu nombre y tu PIN.")
    else:
        st.markdown(f"### 📤 Escribir en el muro como **{yo['personaje']}**")
        tipo_msg = st.radio("¿Qué quieres publicar?", ["💬 Mensaje libre", "🎭 Pista de la semana"], horizontal=True)
        es_pista = tipo_msg.startswith("🎭")
        if es_pista and not semanas:
            st.caption("Las pistas empiezan el viernes 4 de diciembre. Mientras tanto puedes escribir mensajes libres.")
        with st.form("pista", clear_on_submit=True):
            semana = st.selectbox("Semana de la pista", semanas, index=len(semanas) - 1) if (es_pista and semanas) else 0
            texto = st.text_area("1. Escribe lo que quieras (habla como tu personaje):")
            tipo = st.radio("2. Archivo visual (opcional)", ["Ninguno", "Enlace (GIF o imagen)", "Subir foto"])
            url = st.text_input("Enlace del GIF o imagen (solo si eliges enlace). Mejor un enlace de Giphy o uno directo que acabe en .gif, .jpg o .png:")
            foto = st.file_uploader("Foto (solo si eliges subir foto):", type=["png", "jpg", "jpeg", "gif"])
            if st.form_submit_button("Publicar"):
                ruta = ""
                if tipo == "Subir foto" and foto is not None:
                    ext = foto.name.rsplit(".", 1)[-1].lower()
                    ruta = os.path.join(IMG_DIR, f"{uuid.uuid4().hex}.{ext}")
                    with open(ruta, "wb") as f:
                        f.write(foto.getvalue())
                url_ok = url.strip() if tipo == "Enlace (GIF o imagen)" else ""
                if es_pista and not semanas:
                    st.error("Las pistas aún no han empezado. Elige «Mensaje libre».")
                elif url_ok and not url_ok.lower().startswith(("http://", "https://")):
                    st.error("El enlace debe empezar por http:// o https://")
                elif texto.strip() or url_ok or ruta:
                    q("INSERT INTO pistas (semana, personaje, texto, url, imagen, tipo) VALUES (?,?,?,?,?,?)",
                      (semana, yo["personaje"], texto.strip(), url_ok, ruta, "pista" if es_pista else "mensaje"))
                    st.success("¡Publicado en el muro!")
                else:
                    st.error("La publicación no puede estar vacía.")
    st.markdown("---")
    st.markdown("### 📜 Historial del muro")
    avatares = todos_los_avatares()
    for p in q("SELECT * FROM pistas ORDER BY id DESC", fetch=True):
        if (p["tipo"] or "pista") == "mensaje":
            sub = f"💬 **{p['personaje']}** dice:"
        else:
            sub = f"🎅 **{p['personaje']}** (Pista Semana {p['semana']})"
        cabecera(avatares.get(p["personaje"]), sub)
        if p["texto"]:
            st.info(p["texto"])
        if p["url"]:
            mostrar_enlace(p["url"])
        if p["imagen"] and os.path.exists(p["imagen"]):
            show_img(p["imagen"])
        coms = q("SELECT * FROM comentarios WHERE pista_id=? ORDER BY id", (p["id"],), fetch=True)
        for c in coms:
            ca, cb = st.columns([1, 9])
            with ca:
                if avatares.get(c["personaje"]):
                    st.image(avatares[c["personaje"]], width=40)
                else:
                    st.markdown("<div style='font-size:28px'>🎭</div>", unsafe_allow_html=True)
            with cb:
                st.markdown(f"**{c['personaje']}:** {c['texto']}")
            if st.session_state.get("admin"):
                if st.button("🗑️ Quitar comentario", key=f"delc_{c['id']}"):
                    q("DELETE FROM comentarios WHERE id=?", (c["id"],))
                    st.rerun()
        if yo is not None:
            with st.form(f"com_{p['id']}", clear_on_submit=True):
                t = st.text_input("💬 Comenta como tu personaje", key=f"t_{p['id']}", max_chars=300)
                if st.form_submit_button("Comentar") and t.strip():
                    q("INSERT INTO comentarios (pista_id, personaje, texto) VALUES (?,?,?)",
                      (p["id"], yo["personaje"], t.strip()))
                    st.rerun()
        if st.session_state.get("admin"):
            if st.button("🗑️ Eliminar esta publicación", key=f"del_{p['id']}"):
                q("DELETE FROM pistas WHERE id=?", (p["id"],))
                q("DELETE FROM comentarios WHERE pista_id=?", (p["id"],))
                if p["imagen"] and os.path.exists(p["imagen"]):
                    os.remove(p["imagen"])
                st.rerun()

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

    # Sin formulario: cada cambio recarga la página para ir quitando de las listas los personajes ya asignados.
    base = f"v_{ronda}_{usuario}_"
    amigo = None
    if yo["rol"] == "Participante":
        st.markdown("### 🧠 Tu apuesta principal (doble punto)")
        ops = ["—"] + [j["personaje"] for j in otros if j["rol"] == "Participante"]
        ka = base + "amigo"
        if ka not in st.session_state:
            pr = previos.get(("A", ""), "—")
            st.session_state[ka] = pr if pr in ops else "—"
        amigo = st.selectbox("¿Qué personaje crees que es TU amigo invisible (el que te hace el regalo)?", ops, key=ka)

    st.markdown("### 🕵️‍♂️ Quiniela de compañeros")
    st.caption("Los personajes que ya has asignado a alguien desaparecen de la lista de los demás. "
               "Para liberar uno, pon «—» en la persona a la que se lo habías asignado.")
    claves = {j["nombre"]: f"{base}q_{j['nombre']}" for j in otros}
    for j in otros:  # valores iniciales: tu voto anterior, si lo hay
        k = claves[j["nombre"]]
        if k not in st.session_state:
            pr = previos.get(("P", j["nombre"]), "—")
            st.session_state[k] = pr if pr in opciones else "—"
    elegidos = {}
    h1, h2 = st.columns([1, 2])
    h1.markdown("**Participante**")
    h2.markdown("**Personaje**")
    for j in otros:
        k = claves[j["nombre"]]
        usados_otros = {st.session_state.get(claves[o["nombre"]]) for o in otros if o["nombre"] != j["nombre"]} - {"—", None}
        ops = ["—"] + [c for c in opciones if c not in usados_otros]
        if st.session_state.get(k) not in ops:
            st.session_state[k] = "—"
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"<div style='padding-top:8px;font-size:1.05rem'>👤 <b>{html.escape(j['nombre'])}</b></div>", unsafe_allow_html=True)
        with c2:
            elegidos[j["nombre"]] = st.selectbox(f"Personaje de {j['nombre']}", ops, key=k, label_visibility="collapsed")

    if st.button("Enviar voto", key=base + "enviar"):
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

        if revelacion_activa():
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
                q("DELETE FROM jugadores"); q("DELETE FROM pistas"); q("DELETE FROM votos"); q("DELETE FROM comentarios")
                q("INSERT OR REPLACE INTO ajustes VALUES ('personajes', ?)", ("\n".join(pers),))
                q("INSERT OR REPLACE INTO ajustes VALUES ('revelacion', '0')")
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

    st.subheader("5. Fotos de perfil de los personajes")
    lista = [x.strip() for x in pool_txt.splitlines() if x.strip()]
    avs = todos_los_avatares()
    with st.form("avatar", clear_on_submit=True):
        pers_sel = st.selectbox("Personaje", lista)
        foto_av = st.file_uploader("Foto de perfil (png, jpg, gif o webp)", type=["png", "jpg", "jpeg", "gif", "webp"])
        c_a, c_b = st.columns(2)
        guardar = c_a.form_submit_button("Guardar foto")
        quitar = c_b.form_submit_button("Quitar foto")
        if guardar:
            if foto_av is None:
                st.error("Elige primero una imagen.")
            else:
                ext = foto_av.name.rsplit(".", 1)[-1].lower()
                ruta = os.path.join(AVATAR_DIR, f"{uuid.uuid4().hex}.{ext}")
                with open(ruta, "wb") as f:
                    f.write(foto_av.getvalue())
                vieja = avs.get(pers_sel)
                q("INSERT OR REPLACE INTO avatares VALUES (?,?)", (pers_sel, ruta))
                if vieja and os.path.exists(vieja):
                    os.remove(vieja)
                st.success(f"Foto de «{pers_sel}» guardada.")
                st.rerun()
        if quitar:
            vieja = avs.get(pers_sel)
            q("DELETE FROM avatares WHERE personaje=?", (pers_sel,))
            if vieja and os.path.exists(vieja):
                os.remove(vieja)
            st.rerun()
    if avs:
        cols = st.columns(4)
        for k, (n, r) in enumerate(avs.items()):
            with cols[k % 4]:
                st.image(r, width=70, caption=n)

    st.subheader("6. Revelación final")
    st.caption("Mientras esté desactivada, nadie ve los personajes ni los amigos invisibles en el ranking. Actívala el 25 de diciembre.")
    activa = revelacion_activa()
    nueva = st.checkbox("🎭 Mostrar la revelación final a todos los jugadores", value=activa, key="chk_revelacion")
    if nueva != activa:
        q("INSERT OR REPLACE INTO ajustes VALUES ('revelacion', ?)", ("1" if nueva else "0",))
        st.rerun()
