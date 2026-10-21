"""Interfaz Streamlit para consultar y exportar datos de perfiles públicos."""

import streamlit as st

from scraper import consultar_perfil, exportar_csv_perfil, exportar_json


st.set_page_config(page_title="Perfiles TikTok", page_icon="🔎", layout="wide")
st.markdown(
    """
    <style>
      .stApp {background: #f6f8fc; color: #1d2840;}
      .block-container {max-width: 1050px; padding-top: 2.4rem;}
      .encabezado {background: #273756; border-radius: 16px; padding: 1.7rem 2rem; margin-bottom: 1.5rem;}
      .encabezado h1 {color: #fff; margin: 0 0 .45rem; font-size: 2.1rem;}
      .encabezado p {color: #e9effb; margin: 0; font-size: 1rem;}
      div[data-testid="stMetric"], div[data-testid="stForm"] {
        background: white; border: 1px solid #e0e5ee; border-radius: 14px; padding: 1rem;
      }
      [data-testid="stMetricLabel"] p, [data-testid="stMetricValue"],
      [data-testid="stMetricValue"] *, [data-testid="stWidgetLabel"] p {
        color: #1d2840 !important; opacity: 1 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="encabezado">
      <h1>🔎 Perfiles TikTok</h1>
      <p>Consulta información pública de una cuenta y guarda los datos obtenidos.
      Proyecto desarrollado con Python, Playwright y Streamlit.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("consulta"):
    usuario = st.text_input("Nombre de usuario", placeholder="Ejemplo: @cuenta_publica")
    buscar = st.form_submit_button("Consultar perfil", type="primary", use_container_width=True)

if "resultado" not in st.session_state:
    st.session_state.resultado = None
if "error" not in st.session_state:
    st.session_state.error = None

if buscar:
    st.session_state.resultado = None
    st.session_state.error = None
    if not usuario.strip():
        st.session_state.error = "Escribe el nombre de usuario de una cuenta."
    else:
        with st.spinner("Revisando la información pública del perfil..."):
            try:
                st.session_state.resultado = consultar_perfil(usuario)
            except Exception as error:
                st.session_state.error = str(error)

if st.session_state.error:
    st.error(st.session_state.error)

datos = st.session_state.resultado
if datos:
    st.divider()
    foto, info = st.columns([1, 5], vertical_alignment="center")
    with foto:
        if datos.get("foto_perfil"):
            st.image(datos["foto_perfil"], width=110)
        else:
            st.caption("Foto no disponible")
    with info:
        st.subheader(datos.get("nombre") or "Nombre no disponible")
        st.caption("@" + datos["usuario"])
        st.link_button("Abrir perfil en TikTok ↗", datos["url"])

    primera, segunda, tercera = st.columns(3)
    primera.metric("Seguidores", datos.get("seguidores") or "No disponible")
    segunda.metric("Seguidos", datos.get("seguidos") or "No disponible")
    tercera.metric("Me gusta", datos.get("me_gusta") or "No disponible")

    st.subheader("Información de la cuenta")
    a, b, c = st.columns(3)
    a.metric("Publicaciones", datos.get("publicaciones") or "No disponible")
    b.metric("Verificación", (
        "Verificada" if datos["verificada"] is True else
        "Sin verificar" if datos["verificada"] is False else "No disponible"
    ))
    c.metric("Privacidad", (
        "Privada" if datos["cuenta_privada"] is True else
        "Pública" if datos["cuenta_privada"] is False else "No disponible"
    ))

    st.markdown("**Biografía**")
    st.write(datos.get("biografia") or "No se encontró una biografía pública.")

    if datos.get("enlace_biografia"):
        st.link_button("Enlace de la biografía ↗", datos["enlace_biografia"])
    st.caption("Consulta realizada: " + datos["fecha_consulta"].replace("T", " ", 1)[:19])
    st.info(
        "La fecha indicada es la de esta consulta, no la fecha de creación de la cuenta. "
        "Los campos no disponibles no se inventan."
    )

    st.subheader("Exportar los resultados")
    boton_json, boton_csv = st.columns(2)
    with boton_json:
        st.download_button(
            "⬇ Descargar JSON",
            data=exportar_json(datos),
            file_name=f"{datos['usuario']}_perfil.json",
            mime="application/json",
            use_container_width=True,
        )
    with boton_csv:
        st.download_button(
            "⬇ Descargar CSV",
            data=exportar_csv_perfil(datos),
            file_name=f"{datos['usuario']}_perfil.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.divider()
st.caption(
    "Se consultan únicamente datos disponibles públicamente. "
    "TikTok puede cambiar su página o limitar el acceso automatizado."
)
