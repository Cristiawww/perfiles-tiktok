"""Descubre candidatas con enlaces públicos: sin API ni credenciales."""
import re
import unicodedata
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from playwright.sync_api import sync_playwright

PATRON_USUARIO = re.compile(r"^/@([A-Za-z0-9._]{1,24})(?:/|$)")

# Expansión sencilla de vocabulario: no es una predicción ni inventa perfiles.
TEMAS_RELACIONADOS = {
    "ropa": ["moda", "outfits", "fashion", "vestimenta", "tienda ropa"],
    "moda": ["ropa", "outfits", "fashion", "estilo"],
    "ciclismo": ["bicicleta", "bicicletas", "ciclista", "bike", "mtb"],
    "bicicleta": ["ciclismo", "bicis", "mtb", "bike"],
    "bicicletas": ["ciclismo", "bike", "mtb"],
    "tecnologia": ["tech", "gadgets", "celulares", "informatica", "computacion"],
    "celulares": ["tecnologia", "smartphones", "moviles"],
    "reposteria": ["pasteles", "postres", "tortas", "pasteleria"],
    "maquillaje": ["makeup", "cosmeticos", "belleza"],
    "comida": ["recetas", "gastronomia", "cocina"],
    "deportes": ["fitness", "entrenamiento", "deporte"],
}


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto or "")).casefold()
    return "".join(c for c in t if not unicodedata.combining(c))


def variantes(tema):
    palabras = normalizar(tema).split()
    alternativas = []
    for palabra in palabras:
        alternativas.extend(TEMAS_RELACIONADOS.get(palabra, []))
    return list(dict.fromkeys(alternativas))[:4]


def usuario_desde_enlace(enlace):
    """Acepta perfiles o publicaciones enlazadas realmente a TikTok."""
    if not isinstance(enlace, str):
        return None
    parsed = urlparse(enlace)
    if (parsed.hostname or "").lower().endswith("duckduckgo.com"):
        redirected = parse_qs(parsed.query).get("uddg", [])
        if not redirected:
            return None
        parsed = urlparse(unquote(redirected[0]))
    if parsed.scheme != "https" or parsed.hostname not in {"www.tiktok.com", "tiktok.com", "m.tiktok.com"}:
        return None
    coincidencia = PATRON_USUARIO.match(parsed.path)
    return coincidencia.group(1) if coincidencia else None


def candidatos_desde_resultados(resultados, limite=5):
    encontrados, vistos = [], set()
    for r in resultados:
        usuario = usuario_desde_enlace(r.get("url", ""))
        if not usuario or usuario.casefold() in vistos:
            continue
        vistos.add(usuario.casefold())
        encontrados.append({
            "usuario": usuario,
            "url": f"https://www.tiktok.com/@{usuario}",
            "titulo_resultado": str(r.get("titulo") or "")[:160],
            "resumen_resultado": str(r.get("resumen") or "")[:300],
            "fuente": "Resultado web público",
        })
        if len(encontrados) >= limite:
            break
    return encontrados


def _leer_resultados(pagina):
    """Lee enlaces de cualquier plantilla pública del buscador, no una clase CSS única."""
    return pagina.locator("a[href]").evaluate_all('''enlaces => enlaces.map(a => ({
        url: a.href || '',
        titulo: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0,160),
        resumen: (a.closest('article, .result, .b_algo, .MjjYud, li')?.innerText ||
                 a.parentElement?.parentElement?.innerText || '').trim().slice(0,300)
    }))''')


def buscar_cuentas_por_tema(tema, limite=5):
    """Prueba búsquedas amplias en distintos buscadores públicos; no inventa cuentas."""
    tema = str(tema or "").strip()
    if not 2 <= len(tema) <= 80:
        raise ValueError("Escribe un tema entre 2 y 80 caracteres.")
    limite = max(1, min(int(limite), 5))
    alternativos = variantes(tema)
    relacionado = " ".join(alternativos[:2]) if alternativos else "creadores"
    consultas = [
        f"site:tiktok.com/@ {tema}",
        f"TikTok {tema} {relacionado}",
        f"site:tiktok.com/@ {relacionado}"
    ]
    urls = [
        "https://www.bing.com/search?q=" + quote_plus(consultas[0]),
        "https://html.duckduckgo.com/html/?q=" + quote_plus(consultas[1]),
        "https://www.bing.com/search?q=" + quote_plus(consultas[2]),
        "https://html.duckduckgo.com/html/?q=" + quote_plus(consultas[0]),
    ]
    encontrados, vistos = [], set()
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=True)
        try:
            pagina = navegador.new_page(locale="es-ES")
            for url in urls:
                if len(encontrados) >= limite:
                    break
                try:
                    pagina.goto(url, wait_until="domcontentloaded", timeout=14000)
                    pagina.wait_for_timeout(600)
                    resultados = _leer_resultados(pagina)
                    for c in candidatos_desde_resultados(resultados, limite=40):
                        if c["usuario"].casefold() not in vistos:
                            vistos.add(c["usuario"].casefold())
                            encontrados.append(c)
                            if len(encontrados) >= limite:
                                break
                except Exception:
                    # Un buscador puede fallar sin impedir probar el otro.
                    continue
        finally:
            navegador.close()
    return encontrados[:limite]
