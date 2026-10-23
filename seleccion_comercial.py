"""Selecciona candidatas con criterios visibles y sin inventar engagement.

La recomendación no es una certificación de calidad o rendimiento comercial.
"""
import math
import re
import unicodedata

from analisis_negocio import calidad, numero_compacto
from descubrimiento import TEMAS_RELACIONADOS, normalizar

VACIAS = {"y", "de", "del", "para", "una", "uno", "los", "las", "con", "por", "que", "el", "la", "en", "un", "a", "e", "o", "sobre", "mi", "mejor", "quiero"}


def tokens(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).casefold()
    return {x for x in re.findall(r"[a-z0-9]+", texto) if len(x) >= 3 and x not in VACIAS}


def afinidad(tema, perfil, busqueda=None):
    """Combina evidencia del perfil y búsqueda con vocabulario relacionado."""
    terminos = tokens(tema)
    if not terminos:
        return 0.0, []
    nombre = tokens(perfil.get("nombre")) | tokens(perfil.get("usuario"))
    bio = tokens(perfil.get("biografia"))
    externo = tokens((busqueda or {}).get("titulo_resultado")) | tokens((busqueda or {}).get("resumen_resultado"))
    valores = []
    motivos = []
    for termino in terminos:
        sinonimos = set(tokens(" ".join(TEMAS_RELACIONADOS.get(normalizar(termino), []))))
        relacionados = {termino} | sinonimos
        if relacionados & (nombre | bio):
            encontrado = sorted(relacionados & (nombre | bio))[0]
            valores.append(1.0 if encontrado == termino else 0.8)
            motivos.append("perfil: " + encontrado)
        elif relacionados & externo:
            encontrado = sorted(relacionados & externo)[0]
            valores.append(0.45 if encontrado == termino else 0.35)
            motivos.append("búsqueda: " + encontrado)
        else:
            valores.append(0.0)
    return round(100 * sum(valores) / len(valores), 1), motivos


def tasa_interaccion_publica(perfil):
    """Likes/vistas de videos individuales; no likes históricos del perfil."""
    muestras = []
    for v in perfil.get("videos") or []:
        vistas = numero_compacto(v.get("vistas"))
        likes = numero_compacto(v.get("likes"))
        if vistas is not None and vistas > 0 and likes is not None:
            muestras.append(min(100.0, 100.0 * likes / vistas))
    return round(sum(muestras) / len(muestras), 2) if muestras else None


def elegir_cuenta(tema, perfiles, metadatos=None):
    """Ordena perfiles usando criterios comparables en todo el lote.

    Pesos con información suficiente:
      afinidad 50%, audiencia relativa 25%, interacción por video 15%,
      completitud 10%. Si falta interacción en alguna cuenta se excluye
      del ranking de TODAS las cuentas para evitar injusticias.
    """
    perfiles = list(perfiles)
    metadatos = metadatos or {}
    if not perfiles:
        return []
    max_seguidores = max((numero_compacto(p.get("seguidores")) or 0 for p in perfiles), default=0)
    interacciones = {str(p.get("usuario", "")).casefold(): tasa_interaccion_publica(p) for p in perfiles}
    incluye_interaccion = all(x is not None for x in interacciones.values())
    max_interaccion = max((x or 0 for x in interacciones.values()), default=0)
    resultados = []
    for perfil in perfiles:
        usuario = str(perfil.get("usuario", ""))
        seg = numero_compacto(perfil.get("seguidores"))
        rele, pruebas = afinidad(tema, perfil, metadatos.get(usuario.casefold(), {}))
        audiencia = (round(100 * math.log1p(seg) / math.log1p(max_seguidores), 1)
                     if seg is not None and max_seguidores > 0 else None)
        completitud = calidad(perfil)
        valores = {"afinidad": rele, "audiencia": audiencia, "completitud": completitud}
        pesos = {"afinidad": 0.50, "audiencia": 0.25, "completitud": 0.10}
        if incluye_interaccion:
            tasa = interacciones.get(usuario.casefold())
            valores["interaccion"] = round(100 * tasa / max_interaccion, 1) if max_interaccion > 0 else 0.0
            pesos["interaccion"] = 0.15
        # No dar puntos a datos no recuperados: excluir de la media y reportarlo.
        disponibles = {k: w for k, w in pesos.items() if valores.get(k) is not None}
        ponderacion = sum(disponibles.values())
        puntaje = round(sum(valores[k] * w for k, w in disponibles.items()) / ponderacion, 1) if ponderacion else 0.0
        prueba = "; ".join(pruebas) if pruebas else "No hay coincidencias textuales comprobadas con el tema"
        conclusiones = [prueba]
        if seg is not None:
            conclusiones.append(f"{seg:,.0f} seguidores (aproximado si venía abreviado)")
        else:
            conclusiones.append("seguidores no disponibles")
        conclusiones.append(f"{completitud:.1f}% de campos informados")
        resultados.append({
            "usuario": usuario,
            "nombre": perfil.get("nombre") or "Sin nombre visible",
            "afinidad_pct": rele,
            "seguidores": seg,
            "audiencia_relativa_pct": audiencia,
            "interaccion_videos_pct": interacciones.get(usuario.casefold()),
            "completitud_pct": completitud,
            "puntaje_comparativo": puntaje,
            "evidencia": " · ".join(conclusiones),
            "base_interaccion": "Incluida" if incluye_interaccion else "No comparable en el lote",
        })
    return sorted(resultados, key=lambda r: (-r["puntaje_comparativo"], -r["afinidad_pct"], r["usuario"].casefold()))
