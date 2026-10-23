"""Consulta información que TikTok muestra públicamente, sin utilizar su API.

Los campos pueden faltar si la página cambia o limita la navegación automatizada.
Nunca se infieren fechas de creación ni datos de perfiles privados.
"""

import csv
import io
import json
import re
from datetime import datetime
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


SELECTORES = {
    "nombre": '[data-e2e="user-title"]',
    "seguidores": '[data-e2e="followers-count"]',
    "seguidos": '[data-e2e="following-count"]',
    "me_gusta": '[data-e2e="likes-count"]',
    "biografia": '[data-e2e="user-bio"]',
}


def limpiar_usuario(valor):
    """Acepta usuarios con o sin @; evita enlaces y caracteres inesperados."""
    if not isinstance(valor, str):
        raise ValueError("Introduce un nombre de usuario válido.")
    usuario = valor.strip().removeprefix("@").strip()
    if not re.fullmatch(r"[A-Za-z0-9._]{1,24}", usuario):
        raise ValueError("Escribe solo el usuario, por ejemplo @cuenta_publica.")
    return usuario


def leer_texto(pagina, selector, espera=1200):
    try:
        texto = pagina.locator(selector).first.inner_text(timeout=espera).strip()
        return texto or None
    except PlaywrightTimeoutError:
        return None


def leer_atributo(pagina, selector, atributo, espera=1000):
    try:
        valor = pagina.locator(selector).first.get_attribute(atributo, timeout=espera)
        return valor.strip() if valor else None
    except PlaywrightTimeoutError:
        return None


def url_publica(valor):
    """Solo admite enlaces web normales; nunca enlaces javascript: o locales."""
    if not isinstance(valor, str):
        return None
    valor = valor.strip()
    partes = urlparse(valor)
    return valor if partes.scheme in ("https", "http") and partes.netloc else None


def buscar_diccionario_usuario(estructura, usuario):
    """Encuentra un objeto de usuario si su uniqueId coincide exactamente."""
    pendientes = [estructura]
    while pendientes:
        actual = pendientes.pop()
        if isinstance(actual, dict):
            if str(actual.get("uniqueId", "")).casefold() == usuario.casefold():
                return actual
            pendientes.extend(actual.values())
        elif isinstance(actual, list):
            pendientes.extend(actual)
    return None


def datos_incrustados(pagina):
    """Lee únicamente JSON incluido en los scripts de la página visitada."""
    estados = []
    for nombre in ("__UNIVERSAL_DATA_FOR_REHYDRATION__", "SIGI_STATE"):
        try:
            texto = pagina.locator(f'script[id="{nombre}"]').first.text_content(timeout=1200)
            if texto:
                estado = json.loads(texto)
                if isinstance(estado, dict):
                    estados.append(estado)
        except (PlaywrightTimeoutError, ValueError, TypeError):
            pass
    return estados


def paquete_de_usuario(estado, usuario):
    """Localiza usuario y estadísticas solo si el @ corresponde a la consulta."""
    scope = estado.get("__DEFAULT_SCOPE__", {})
    detalle = scope.get("webapp.user-detail", {}) if isinstance(scope, dict) else {}
    info = detalle.get("userInfo", {}) if isinstance(detalle, dict) else {}
    if isinstance(info, dict):
        obj = info.get("user", {})
        if isinstance(obj, dict) and str(obj.get("uniqueId", "")).casefold() == usuario.casefold():
            return obj, info.get("stats") or info.get("statsV2") or {}

    modulo = estado.get("UserModule", {})
    if isinstance(modulo, dict):
        usuarios = modulo.get("users", {})
        estadisticas = modulo.get("stats", {})
        if isinstance(usuarios, dict):
            for clave, obj in usuarios.items():
                if isinstance(obj, dict) and str(obj.get("uniqueId", "")).casefold() == usuario.casefold():
                    stats = estadisticas.get(clave, {}) if isinstance(estadisticas, dict) else {}
                    return obj, stats

    # Alternativa para cambios menores de estructura, manteniendo validación de usuario.
    obj = buscar_diccionario_usuario(estado, usuario)
    if obj:
        pendientes = [estado]
        while pendientes:
            actual = pendientes.pop()
            if isinstance(actual, dict):
                candidato = actual.get("user")
                if (isinstance(candidato, dict)
                        and str(candidato.get("uniqueId", "")).casefold() == usuario.casefold()):
                    stats = actual.get("stats") or actual.get("statsV2") or {}
                    return candidato, stats
                pendientes.extend(actual.values())
            elif isinstance(actual, list):
                pendientes.extend(actual)
        return obj, {}
    return {}, {}


def valor_numero(valor):
    if valor is None or isinstance(valor, bool):
        return None
    return str(valor)


def valor_booleano(valor):
    return valor if type(valor) is bool else None


def nombre_de_titulo(pagina, usuario):
    texto = leer_atributo(pagina, 'meta[property="og:title"]', "content")
    if not texto:
        try:
            texto = pagina.title(timeout=1200)
        except PlaywrightTimeoutError:
            return None
    patron = rf"^(.+?)\s*\(@{re.escape(usuario)}\)(?:\s*[-|·].*)?$"
    encontrado = re.search(patron, texto, flags=re.IGNORECASE)
    if encontrado:
        nombre = encontrado.group(1).strip()
        if nombre.lstrip("@").casefold() != usuario.casefold():
            return nombre
    return None


def consultar_perfil(entrada):
    """Devuelve un diccionario con datos visibles o None si faltan."""
    usuario = limpiar_usuario(entrada)
    url = f"https://www.tiktok.com/@{usuario}"
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=False)
        try:
            pagina = navegador.new_page(viewport={"width": 1366, "height": 900}, locale="es-ES")
            pagina.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                pagina.locator(
                    f'{SELECTORES["nombre"]}, {SELECTORES["seguidores"]}'
                ).first.wait_for(timeout=12000)
            except PlaywrightTimeoutError:
                pass

            nombre = leer_texto(pagina, SELECTORES["nombre"])
            if nombre and nombre.lstrip("@").casefold() == usuario.casefold():
                nombre = None
            datos = {
                "usuario": usuario,
                "nombre": nombre,
                "biografia": leer_texto(pagina, SELECTORES["biografia"]),
                "seguidores": leer_texto(pagina, SELECTORES["seguidores"]),
                "seguidos": leer_texto(pagina, SELECTORES["seguidos"]),
                "me_gusta": leer_texto(pagina, SELECTORES["me_gusta"]),
                "publicaciones": None,
                "verificada": None,
                "cuenta_privada": None,
                "foto_perfil": None,
                "enlace_biografia": None,
                "url": pagina.url,
                "fecha_consulta": datetime.now().astimezone().isoformat(timespec="seconds"),
            }

            for estado in datos_incrustados(pagina):
                cuenta, stats = paquete_de_usuario(estado, usuario)
                if not cuenta:
                    continue
                datos["nombre"] = cuenta.get("nickname") or datos["nombre"]
                datos["biografia"] = cuenta.get("signature") or datos["biografia"]
                datos["seguidores"] = datos["seguidores"] or valor_numero(stats.get("followerCount"))
                datos["seguidos"] = datos["seguidos"] or valor_numero(stats.get("followingCount"))
                datos["me_gusta"] = datos["me_gusta"] or valor_numero(stats.get("heartCount"))
                datos["publicaciones"] = datos["publicaciones"] or valor_numero(stats.get("videoCount"))
                datos["verificada"] = valor_booleano(cuenta.get("verified"))
                datos["cuenta_privada"] = valor_booleano(cuenta.get("privateAccount"))
                datos["foto_perfil"] = url_publica(
                    cuenta.get("avatarLarger") or cuenta.get("avatarMedium") or cuenta.get("avatarThumb")
                ) or datos["foto_perfil"]
                enlace = cuenta.get("bioLink")
                if isinstance(enlace, dict):
                    enlace = enlace.get("link")
                datos["enlace_biografia"] = url_publica(enlace) or datos["enlace_biografia"]

            datos["nombre"] = datos["nombre"] or nombre_de_titulo(pagina, usuario)
            datos["foto_perfil"] = datos["foto_perfil"] or url_publica(
                leer_atributo(pagina, 'meta[property="og:image"]', "content")
            )
            datos["enlace_biografia"] = datos["enlace_biografia"] or url_publica(
                leer_atributo(pagina, '[data-e2e="user-link"] a[href]', "href")
            )

            if not any((datos["nombre"], datos["seguidores"], datos["seguidos"], datos["me_gusta"], datos["biografia"])):
                raise RuntimeError(
                    "TikTok no mostró suficientes datos públicos de este perfil. "
                    "Comprueba el nombre de usuario y abre el perfil en el navegador. "
                    "También puede deberse a restricciones o cambios en la página."
                )
            return datos
        finally:
            navegador.close()


def exportar_json(datos):
    """Genera los bytes del JSON para descargar."""
    return json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8")


def exportar_csv_perfil(datos):
    """Genera una fila CSV con los campos del perfil, incluso si faltan datos."""
    campos = [
        "usuario", "nombre", "biografia", "seguidores", "seguidos", "me_gusta",
        "publicaciones", "verificada", "cuenta_privada", "enlace_biografia",
        "foto_perfil", "url", "fecha_consulta",
    ]
    salida = io.StringIO(newline="")
    escritor = csv.DictWriter(salida, fieldnames=campos)
    escritor.writeheader()
    escritor.writerow({campo: datos.get(campo) for campo in campos})
    return salida.getvalue().encode("utf-8-sig")


if __name__ == "__main__":
    entrada = input("Nombre de usuario de TikTok: ")
    try:
        print(exportar_json(consultar_perfil(entrada)).decode("utf-8"))
    except (ValueError, RuntimeError, PlaywrightTimeoutError) as error:
        print(f"No se pudo completar la consulta: {error}")


def _item_stats(estado):
    """Lee métricas de publicaciones únicamente si están incrustadas en el HTML.

    No consulta endpoints de API ni intenta recuperar información privada.
    """
    resultados = {}
    if not isinstance(estado, dict):
        return resultados
    modulo = estado.get("ItemModule")
    if isinstance(modulo, dict):
        for identificador, item in modulo.items():
            if not isinstance(item, dict):
                continue
            estadisticas = item.get("stats") or item.get("statsV2") or {}
            if not isinstance(estadisticas, dict):
                estadisticas = {}
            resultados[str(item.get("id", identificador))] = {
                "descripcion": item.get("desc"),
                "vistas": estadisticas.get("playCount"),
                "likes": estadisticas.get("diggCount"),
                "comentarios_cantidad": estadisticas.get("commentCount"),
                "compartidos": estadisticas.get("shareCount"),
                "fecha_publicacion": item.get("createTime"),
            }
    return resultados


def extraer_videos_publicos(pagina, usuario, limite=10, estados=None):
    """Intenta reconocer videos enlazados en el perfil público. No garantiza 10.

    No obtiene ni clasifica automáticamente autores de comentarios como IA/humanos.
    """
    limite = max(1, min(int(limite), 10))
    usuario = limpiar_usuario(usuario)
    patron = re.compile(r"^https?://(?:www\.)?tiktok\.com/@([^/?#]+)/video/(\d+)")
    for _ in range(2):
        try:
            pagina.evaluate("window.scrollBy(0, window.innerHeight)")
            pagina.wait_for_timeout(650)
        except Exception:
            break
    mapa_stats = {}
    for estado in estados or []:
        mapa_stats.update(_item_stats(estado))
    enlaces = []
    try:
        # Se capturan solo enlaces que pertenecen a la cuenta solicitada.
        enlaces = pagina.locator('a[href*="/video/"]').evaluate_all(
            "els => els.map(e => ({url:e.href, texto:(e.innerText || '').trim()}))"
        )
    except Exception:
        return []
    videos, vistos = [], set()
    for enlace in enlaces:
        url = enlace.get("url", "")
        hallazgo = patron.match(url)
        if not hallazgo or hallazgo.group(1).casefold() != usuario.casefold():
            continue
        identificador = hallazgo.group(2)
        if identificador in vistos:
            continue
        vistos.add(identificador)
        stats = mapa_stats.get(identificador, {})
        videos.append({
            "usuario": usuario,
            "video_id": identificador,
            "url": f"https://www.tiktok.com/@{usuario}/video/{identificador}",
            "descripcion": stats.get("descripcion"),
            "vistas": stats.get("vistas"),
            "likes": stats.get("likes"),
            "comentarios_cantidad": stats.get("comentarios_cantidad"),
            "compartidos": stats.get("compartidos"),
            "fecha_publicacion": stats.get("fecha_publicacion"),
            "origen": "enlace público; métricas HTML incrustado si disponibles",
        })
        if len(videos) >= limite:
            break
    # El orden es el que muestra la página, NO necesariamente cronológico.
    return videos


def consultar_perfil_con_videos(entrada, limite=10):
    """Extrae perfil y enlaces de publicaciones en la MISMA navegación.

    Es una versión ampliada de consultar_perfil, preservando su comportamiento.
    """
    usuario = limpiar_usuario(entrada)
    url = f"https://www.tiktok.com/@{usuario}"
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)
        try:
            contexto = navegador.new_context(viewport={"width": 1366, "height": 900}, locale="es-ES")
            pagina = contexto.new_page()
            pagina.goto(url, wait_until="domcontentloaded", timeout=40000)
            try:
                pagina.locator(
                    f'{SELECTORES["nombre"]}, {SELECTORES["seguidores"]}'
                ).first.wait_for(timeout=10000)
            except PlaywrightTimeoutError:
                pass
            nombre = leer_texto(pagina, SELECTORES["nombre"])
            if nombre and nombre.lstrip("@").casefold() == usuario.casefold():
                nombre = None
            datos = {
                "usuario": usuario,
                "nombre": nombre,
                "biografia": leer_texto(pagina, SELECTORES["biografia"]),
                "seguidores": leer_texto(pagina, SELECTORES["seguidores"]),
                "seguidos": leer_texto(pagina, SELECTORES["seguidos"]),
                "me_gusta": leer_texto(pagina, SELECTORES["me_gusta"]),
                "publicaciones": None,
                "verificada": None,
                "cuenta_privada": None,
                "foto_perfil": None,
                "enlace_biografia": None,
                "url": pagina.url,
                "fecha_consulta": datetime.now().astimezone().isoformat(timespec="seconds"),
            }
            estados = datos_incrustados(pagina)
            for estado in estados:
                cuenta, stats = paquete_de_usuario(estado, usuario)
                if not cuenta:
                    continue
                datos["nombre"] = cuenta.get("nickname") or datos["nombre"]
                datos["biografia"] = cuenta.get("signature") or datos["biografia"]
                for campo, clave in (("seguidores", "followerCount"), ("seguidos", "followingCount"),
                                     ("me_gusta", "heartCount"), ("publicaciones", "videoCount")):
                    if datos[campo] is None:
                        datos[campo] = valor_numero(stats.get(clave))
                datos["verificada"] = valor_booleano(cuenta.get("verified"))
                datos["cuenta_privada"] = valor_booleano(cuenta.get("privateAccount"))
                datos["foto_perfil"] = url_publica(
                    cuenta.get("avatarLarger") or cuenta.get("avatarMedium") or cuenta.get("avatarThumb")
                ) or datos["foto_perfil"]
                enl = cuenta.get("bioLink")
                datos["enlace_biografia"] = url_publica(enl.get("link") if isinstance(enl, dict) else enl) or datos["enlace_biografia"]
            datos["nombre"] = datos["nombre"] or nombre_de_titulo(pagina, usuario)
            datos["foto_perfil"] = datos["foto_perfil"] or url_publica(leer_atributo(pagina, 'meta[property="og:image"]', "content"))
            datos["enlace_biografia"] = datos["enlace_biografia"] or url_publica(
                leer_atributo(pagina, '[data-e2e="user-link"] a[href]', "href")
            )
            if not any(datos.get(c) is not None for c in ("nombre", "seguidores", "seguidos", "me_gusta", "biografia")):
                raise RuntimeError("El perfil no proporcionó datos públicos suficientes en esta visita.")
            datos["videos"] = extraer_videos_publicos(pagina, usuario, limite, estados)
            datos["videos_detectados"] = len(datos["videos"])
            return datos
        finally:
            navegador.close()
