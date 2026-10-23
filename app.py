"""RADAR 5V - Panel de inteligencia comercial con datos públicos de TikTok.

No necesita API ni tokens. Permite importar datos ya obtenidos y consultas por lote
secuenciales de perfiles públicos. No atribuye personalidad ni autoría IA.
"""
import io
from html import escape
import json
import time

import pandas as pd
import streamlit as st
from analisis_negocio import (
    CAMPOS_CALIDAD, exportar_csv_filas, exportar_json, indicadores,
    indicadores_videos, oportunidades, validar_video, videos_tabla,
)
from scraper import limpiar_usuario, consultar_perfil_con_videos
from descubrimiento import buscar_cuentas_por_tema
from seleccion_comercial import elegir_cuenta

st.set_page_config(page_title="RADAR 5V | Selección de cuentas", page_icon="📡", layout="wide")
st.markdown("""
<style>
.stApp {background: #f4f6f8!important; color: #17283d!important;}
.stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li, .stApp h2, .stApp h3 {color:#17283d;}
.stApp [data-testid="stWidgetLabel"] p, .stApp label, .stApp [data-testid="stCaptionContainer"] {color:#33475d!important;opacity:1!important;}
.stApp [data-testid="stVerticalBlockBorderWrapper"] {color:#17283d;}
.stApp [data-testid="stTextArea"] textarea {color:#17283d!important;}
.stApp [data-testid="stNotificationContent"] p {color:#17283d!important;}
.block-container {max-width: 1270px; padding-top: 1.5rem;}
.hero {background:linear-gradient(105deg,#10233f,#243d66 68%,#166b81);
 color:white; padding:25px 32px; border-radius:20px; margin-bottom:16px;}
.hero h1 {font-size:2.2rem; color:white; margin:0 0 5px;}
.hero p {color:#d9e9f2; margin:0;}
[data-testid="stMetric"] {background:white; border:1px solid #e0e7ef; padding:13px 17px;
 border-radius:13px;}
[data-testid="stMetricLabel"] p,[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {color:#162744!important;opacity:1!important;}
[data-testid="stWidgetLabel"] p {color:#1b2b48!important;opacity:1!important;}
.stApp div[data-baseweb="input"] input, .stApp textarea,
.stApp div[data-baseweb="select"] {background-color:#fff!important;color:#15283b!important;}
.stApp input::placeholder, .stApp textarea::placeholder {color:#60758a!important;opacity:1!important;}
.stApp div[data-baseweb="tab-list"] button {color:#274258!important;font-weight:650;}
.stApp [data-testid="stDataFrame"] {background:white;border-radius:10px;}
.stApp .stAlert p {color:#20394f!important;}
.recomendado {background:#e8f5f1;border:1px solid #a0d9cb;border-left:5px solid #168579;
padding:16px 19px;border-radius:12px;color:#153d39;}
.recomendado h3 {color:#123e35;margin:0 0 8px;}
.note {padding:13px 18px;border-left:4px solid #1494a9;border-radius:8px;
 background:#e7f5f8;color:#21445d;margin:7px 0 15px;}
.usuario-carta {background:#fff; color:#17283d!important; border:1px solid #d4dfe8;
 padding:15px 18px; border-radius:12px; margin:8px 0;}
.usuario-carta strong {color:#102f57!important; font-size:1.12rem;}
.usuario-carta small {color:#42566c!important;}
.usuario-carta a {color:#116b76!important; font-weight:650;}
.stApp [data-testid="stDataFrame"] * {opacity:1;}
</style>
""", unsafe_allow_html=True)
st.markdown("""<div class='hero'><h1>📡 RADAR 5V</h1>
<p>Selección de cuentas para colaboraciones comerciales</p></div>""", unsafe_allow_html=True)

for k, value in (("perfiles", {}), ("fallos", {}), ("videos_csv", []), ("comentarios", []),
                 ("candidatas_tema", []), ("tema_actual", ""), ("metadatos_tema", {})):
    if k not in st.session_state:
        st.session_state[k] = value

panel_tema, panel_entrada, panel_analisis, panel_negocio, panel_calidad = st.tabs([
    "Buscar por tema", "Cuentas", "Comparar", "Negocio", "Cinco V"
])

with panel_tema:
    st.subheader("Encontrar cuentas relacionadas")
    tema = st.text_input("Tema o producto", placeholder="Ciclismo, ropa, tecnología...", key="entrada_tema")
    iniciar_busqueda = st.button("Buscar cuentas", type="primary", use_container_width=True)
    if iniciar_busqueda:
        try:
            with st.spinner("Revisando resultados públicos de búsqueda..."):
                lista = buscar_cuentas_por_tema(tema, limite=5)
            st.session_state.candidatas_tema = lista
            st.session_state.metadatos_tema = {x["usuario"].casefold(): x for x in lista}
            st.session_state.tema_actual = tema.strip()
            if not lista:
                st.warning("Los buscadores no devolvieron perfiles. Agrega cuentas conocidas abajo.")
            else:
                st.success(f"Encontradas: {len(lista)} cuentas.")
        except Exception as exc:
            st.session_state.candidatas_tema = []
            st.warning(f"No fue posible buscar: {exc}.")

    st.markdown("#### Cuentas candidatas")
    candidatas = st.session_state.candidatas_tema
    if candidatas:
        for c in candidatas:
            nombre = escape(c["usuario"])
            detalle = escape((c.get("titulo_resultado") or "Perfil público")[:100])
            enlace = escape(c["url"], quote=True)
            st.markdown(f"<div class='usuario-carta'><strong>@{nombre}</strong> "
                        f"<a href='{enlace}' target='_blank'>Ver perfil ↗</a>"
                        f"<div><small>{detalle}</small></div></div>", unsafe_allow_html=True)
    else:
        st.caption("Sin cuentas seleccionadas.")
    manuales = st.text_area("Agregar usuarios (opcional)",
                            placeholder="@cuenta_de_ciclismo\n@tienda_bicicletas", height=80)
    if st.button("Agregar a la lista", use_container_width=True):
        añadidos = list(st.session_state.candidatas_tema)
        vistos = {x["usuario"].casefold() for x in añadidos}
        errores = []
        for fragmento in manuales.replace(",", "\n").splitlines():
            if not fragmento.strip():
                continue
            try:
                u = limpiar_usuario(fragmento)
            except ValueError as exc:
                errores.append(f"{fragmento}: {exc}")
                continue
            if u.casefold() not in vistos and len(añadidos) < 5:
                añ = {"usuario": u, "url": f"https://www.tiktok.com/@{u}",
                       "titulo_resultado": "Cuenta agregada por el usuario", "resumen_resultado": "", "fuente": "Entrada manual"}
                añadidos.append(añ)
                vistos.add(u.casefold())
                st.session_state.metadatos_tema[u.casefold()] = añ
        st.session_state.candidatas_tema = añadidos
        if errores:
            st.warning("Algunos usuarios se descartaron: " + "; ".join(errores))
        st.success(f"Tienes {len(añadidos)} cuenta(s) candidata(s).")

    st.divider()
    if st.button("Consultar perfiles y elegir candidata", type="primary", use_container_width=True,
                 disabled=not st.session_state.candidatas_tema):
        if len(tema.strip()) < 3:
            st.error("Primero escribe el tema para poder evaluar la relación de cada cuenta.")
        else:
            st.session_state.tema_actual = tema.strip()
            seleccion = st.session_state.candidatas_tema[:5]
            progreso = st.progress(0, text="Preparando consultas")
            for i, c in enumerate(seleccion):
                u = c["usuario"]
                progreso.progress(i / len(seleccion), text=f"Consultando @{u} ({i+1}/{len(seleccion)})")
                try:
                    datos = consultar_perfil_con_videos(u, limite=5)
                    st.session_state.perfiles[u.casefold()] = datos
                    st.session_state.fallos.pop(u.casefold(), None)
                except Exception as exc:
                    st.session_state.fallos[u.casefold()] = str(exc)
                if i < len(seleccion)-1:
                    time.sleep(1.5)
            progreso.progress(1.0, text="Consultas finalizadas")

    seleccionados = {x["usuario"].casefold() for x in st.session_state.candidatas_tema}
    comparables = [p for key, p in st.session_state.perfiles.items() if key in seleccionados]
    if comparables and st.session_state.tema_actual:
        st.markdown("#### ¿Cuál conviene revisar primero?")
        ranking = elegir_cuenta(st.session_state.tema_actual, comparables, st.session_state.metadatos_tema)
        ganador = ranking[0]
        if ganador["afinidad_pct"] > 0 and len(ranking) >= 2:
            st.markdown(
                "<div class='recomendado'><h3>Mejor candidata: @" + escape(ganador["usuario"]) +
                "</h3><div>" + escape(ganador["evidencia"]) + "</div></div>", unsafe_allow_html=True
            )
            
        elif ganador["afinidad_pct"] == 0:
            st.warning("Todavía no existe suficiente evidencia textual de relación con el tema. "
                       "No sería responsable declarar una cuenta ganadora solo por seguidores.")
        else:
            st.info("Se analizó una cuenta. Necesitas al menos dos para justificar una comparación.")
        st.dataframe(pd.DataFrame(ranking), hide_index=True, use_container_width=True)
        st.download_button("Descargar ranking y justificaciones (CSV)", exportar_csv_filas(ranking),
                           file_name="ranking_cuentas_por_tema.csv", mime="text/csv", use_container_width=True)
        

    if st.session_state.fallos:
        with st.expander("Consultas que fallaron (no se inventaron datos)"):
            for usuario, error in st.session_state.fallos.items():
                st.write(f"@{usuario}: {error}")

with panel_entrada:
    st.subheader("Consultar perfiles")
    with st.form("lote"):
        entrada = st.text_area("Usuarios de TikTok", placeholder="@cuenta_uno\n@cuenta_dos\n@cuenta_tres", height=105)
        limite = st.select_slider("Intentar detectar hasta N videos por perfil", options=[0, 3, 5, 10], value=10)
        boton = st.form_submit_button("🔍 Analizar lote", type="primary", use_container_width=True)
    if boton:
        usuarios = []
        for fragmento in entrada.replace(",", "\n").splitlines():
            if fragmento.strip():
                try:
                    u = limpiar_usuario(fragmento)
                    if u.casefold() not in {x.casefold() for x in usuarios}:
                        usuarios.append(u)
                except ValueError as exc:
                    st.warning(f"Se descartó «{fragmento}»: {exc}")
        if not usuarios:
            st.warning("Introduce al menos una cuenta válida.")
        elif len(usuarios) > 5:
            st.error("Máximo 5 cuentas por lote. Para más cuentas, realiza otro lote.")
        else:
            avance = st.progress(0, text="Preparando consultas")
            for i, u in enumerate(usuarios):
                avance.progress(i / len(usuarios), text=f"Consultando @{u} ({i+1}/{len(usuarios)})")
                try:
                    datos = consultar_perfil_con_videos(u, limite=max(1, limite))
                    if limite == 0:
                        datos["videos"] = []
                    st.session_state.perfiles[u.casefold()] = datos
                    st.session_state.fallos.pop(u.casefold(), None)
                except Exception as exc:
                    st.session_state.fallos[u.casefold()] = str(exc)
                if i < len(usuarios)-1:
                    time.sleep(1.5)
            avance.progress(1.0, text="Lote finalizado")

    st.markdown("#### ¿Ya tienes archivos del scraper anterior?")
    carga = st.file_uploader("Importar perfiles JSON (uno o varios)", type="json", accept_multiple_files=True)
    if carga and st.button("Agregar JSON al panel", use_container_width=True):
        agregados = 0
        for archivo in carga:
            try:
                contenido = json.load(archivo)
                perfiles = contenido if isinstance(contenido, list) else [contenido]
                for p in perfiles:
                    if isinstance(p, dict) and p.get("usuario"):
                        st.session_state.perfiles[str(p["usuario"]).casefold()] = p
                        agregados += 1
            except (ValueError, UnicodeDecodeError, TypeError) as exc:
                st.warning(f"{archivo.name}: {exc}")
        st.success(f"Se incorporaron {agregados} registros.")

    if st.button("🧪 Cargar el perfil de ejemplo aportado", use_container_width=True):
        try:
            from pathlib import Path
            muestra = json.loads((Path(__file__).parent / "ejemplos" / "perfil_demo_real.json").read_text(encoding="utf-8"))
            st.session_state.perfiles[str(muestra["usuario"]).casefold()] = muestra
            st.success("Ejemplo cargado.")
        except Exception as exc:
            st.error(f"No se pudo cargar el ejemplo: {exc}")

    if st.session_state.fallos:
        with st.expander(f"Consultas que no devolvieron datos ({len(st.session_state.fallos)})"):
            for usuario, error in st.session_state.fallos.items():
                st.error(f"@{usuario}: {error}")
    

perfiles = list(st.session_state.perfiles.values())
resumen = [indicadores(p) for p in perfiles]

with panel_analisis:
    st.subheader("Comparación entre cuentas")
    if not perfiles:
        st.info("Primero consulta un lote o importa tu archivo JSON de TikTok en la pestaña 01.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Cuentas analizadas", len(perfiles))
        c2.metric("Perfiles con seguidores", sum(p["seguidores"] is not None for p in resumen))
        c3.metric("Enlaces de video", sum(len(p.get("videos") or []) for p in perfiles))
        c4.metric("Calidad promedio", f"{sum(x['calidad_porcentaje'] for x in resumen)/len(resumen):.1f}%")
        df = pd.DataFrame(resumen)
        st.dataframe(df, use_container_width=True, hide_index=True)
        grafico = df.dropna(subset=["seguidores"])
        if not grafico.empty:
            st.markdown("#### Audiencia por cuenta")
            st.bar_chart(grafico.set_index("usuario")["seguidores"])
        
        st.download_button("⬇ Exportar comparación CSV", exportar_csv_filas(resumen),
                           file_name="comparacion_perfiles.csv", mime="text/csv", use_container_width=True)
        st.download_button("⬇ Exportar conjunto JSON", exportar_json(perfiles),
                           file_name="perfiles_lote.json", mime="application/json", use_container_width=True)

    st.markdown("#### Últimos videos: detección e importación")
    
    sube_videos = st.file_uploader("Opcional: agregar CSV de estadísticas de videos", type="csv", key="sube_videos")
    if sube_videos and st.button("Incorporar videos del CSV"):
        try:
            origen = pd.read_csv(sube_videos).fillna("").to_dict(orient="records")
            procesados = [validar_video(fila) for fila in origen]
            st.session_state.videos_csv = [v for v in procesados if v]
            st.success(f"Se incorporaron {len(st.session_state.videos_csv)} videos.")
        except Exception as exc:
            st.error(f"CSV no válido: {exc}")
    videos = indicadores_videos(videos_tabla(perfiles, st.session_state.videos_csv))
    if videos:
        st.dataframe(pd.DataFrame(videos), hide_index=True, use_container_width=True)
        st.download_button("⬇ Descargar datos de videos", exportar_csv_filas(videos),
                           file_name="videos_analizados.csv", mime="text/csv")
    else:
        st.warning("No se encontraron videos accesibles. Puedes incorporar un CSV verificado; no se inventarán likes ni comentarios.")

with panel_negocio:
    st.subheader("💡 Radar de demanda: de los comentarios a oportunidades comerciales")
    
    
    sube_comentarios = st.file_uploader("CSV de comentarios", type="csv", key="sube_comentarios")
    if sube_comentarios and st.button("Analizar comentarios"):
        try:
            filas = pd.read_csv(sube_comentarios).fillna("").to_dict(orient="records")
            if "comentario" not in (filas[0].keys() if filas else []):
                st.error("El archivo debe contener una columna llamada comentario.")
            else:
                # Solo conservamos texto, nunca identificadores de personas que comentaron.
                st.session_state.comentarios = [{"comentario": f["comentario"]} for f in filas]
                st.success(f"Se cargaron {len(filas)} comentarios para análisis.")
        except Exception as exc:
            st.error(f"No se pudo abrir el CSV: {exc}")
    reporte = oportunidades(st.session_state.comentarios)
    a, b, c = st.columns(3)
    a.metric("Comentarios evaluados", reporte["comentarios_analizados"])
    b.metric("Necesidades detectadas", len(reporte["prioridades"]))
    c.metric("Textos exactamente repetidos", reporte["duplicados_textuales"])
    if reporte["prioridades"]:
        tabla = pd.DataFrame(reporte["prioridades"])
        st.dataframe(tabla, hide_index=True, use_container_width=True)
        st.bar_chart(tabla.set_index("necesidad")["menciones"])
        st.download_button("⬇ Descargar oportunidades comerciales", exportar_csv_filas(reporte["prioridades"]),
                           file_name="oportunidades_comerciales.csv", mime="text/csv")
        tema = reporte["prioridades"][0]["necesidad"]
        st.success(f"**Primera oportunidad a probar:** {tema}. Grabar contenido que responda esta duda y medir las consultas recibidas.")
    else:
        st.caption("Sin comentarios para analizar.")
    

with panel_calidad:
    st.subheader("Las cinco V del Big Data, aplicadas al proyecto")
    if not perfiles:
        st.info("Importa al menos un perfil para visualizar los indicadores de calidad.")
    else:
        st.write(f"**Volumen:** {len(perfiles)} perfil(es) recopilado(s) y "
                 f"{sum(len(p.get('videos') or []) for p in perfiles)} enlaces de video detectados.")
        fechas = [p.get("fecha_consulta") for p in perfiles if p.get("fecha_consulta")]
        st.write(f"**Velocidad:** {len(fechas)} marcas temporales registradas. "
                 "Con una sola captura de cada cuenta no se calcula crecimiento ni cambios por hora.")
        st.write("**Variedad:** números, texto de biografía, URL, valores booleanos y fechas.")
        st.write("**Veracidad:** indicador de completitud, errores por usuario y datos faltantes diferenciados de cero.")
        st.write("**Valor:** comparaciones, indicadores calculados y recomendaciones comerciales vinculadas a comentarios.")
        st.markdown("#### Pasaporte de calidad de cada cuenta")
        dfc = pd.DataFrame([{
            "usuario": p.get("usuario"),
            "campos_completos": sum(p.get(c) is not None and p.get(c) != "" for c in CAMPOS_CALIDAD),
            "campos_esperados": len(CAMPOS_CALIDAD),
            "completitud_pct": indicadores(p)["calidad_porcentaje"],
        } for p in perfiles])
        st.dataframe(dfc, hide_index=True, use_container_width=True)
        st.bar_chart(dfc.set_index("usuario")["completitud_pct"])
        st.caption("Completitud no es exactitud. 'Verificada' es un campo de la página, no una confirmación independiente de identidad.")
    
