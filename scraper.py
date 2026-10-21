
import json
import re

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def leer_texto(pagina, selector):
    """Busca un elemento y devuelve su texto si está disponible."""
    try:
        elemento = pagina.locator(selector).first
        return elemento.inner_text(timeout=3000).strip()
    except PlaywrightTimeoutError:
        return None


def consultar_perfil(usuario):
    """Consulta los datos visibles de un perfil público de TikTok."""

    usuario = usuario.strip().lstrip("@")

    if not re.fullmatch(r"[A-Za-z0-9._]{1,24}", usuario):
        raise ValueError("El nombre de usuario contiene caracteres no válidos.")

    enlace = f"https://www.tiktok.com/@{usuario}"

    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=False)

        try:
            pagina = navegador.new_page(
                viewport={"width": 1280, "height": 800},
                locale="es-ES"
            )

            pagina.goto(
                enlace,
                wait_until="domcontentloaded",
                timeout=45000
            )

            try:
                pagina.locator(
                    '[data-e2e="user-title"], [data-e2e="followers-count"]'
                ).first.wait_for(timeout=15000)
            except PlaywrightTimeoutError:
                pass

            datos = {
                "usuario": usuario,
                "nombre": leer_texto(pagina, '[data-e2e="user-subtitle"]'),
                "seguidores": leer_texto(pagina, '[data-e2e="followers-count"]'),
                "seguidos": leer_texto(pagina, '[data-e2e="following-count"]'),
                "me_gusta": leer_texto(pagina, '[data-e2e="likes-count"]'),
                "url": pagina.url
            }

            if not datos["nombre"] and not datos["seguidores"]:
                raise RuntimeError(
                    "No se pudo leer el perfil. Puede ser privado, "
                    "no existir o estar restringido por TikTok."
                )

            return datos

        finally:
            navegador.close()


if __name__ == "__main__":
    nombre_usuario = input("Ingrese el usuario de TikTok: ")

    try:
        resultado = consultar_perfil(nombre_usuario)
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
    except Exception as error:
        print(f"Error durante la consulta: {error}")
