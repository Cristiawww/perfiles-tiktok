"""Análisis local de perfiles, videos y comentarios públicos exportados.

NO infiere personalidad, identidad o autoría de IA a partir del texto.
"""
import csv
import io
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime

CAMPOS_CALIDAD = ("usuario", "nombre", "biografia", "seguidores", "seguidos",
                  "me_gusta", "publicaciones", "verificada", "cuenta_privada", "fecha_consulta")

PREGUNTAS = {
    "Precio y promociones": ("precio", "cuanto cuesta", "cuanto vale", "descuento", "oferta", "promocion"),
    "Disponibilidad": ("disponible", "stock", "tienen", "hay talla", "agotado", "hay en"),
    "Entrega y envíos": ("envio", "delivery", "entrega", "envian", "domicilio"),
    "Ubicación y horarios": ("donde", "ubicacion", "direccion", "horario", "abren", "local"),
    "Características": ("medida", "material", "color", "garantia", "calidad", "tamaño", "funciona"),
}


def numero_compacto(valor):
    """Convierte cantidades como '302.3K' y '1.7M'; no finge exactitud."""
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().upper().replace(" ", "")
    if not texto or texto in {"N/A", "--", "NONE", "NO DISPONIBLE"}:
        return None
    sufijo = texto[-1] if texto[-1] in "KMB" else ""
    cantidad = texto[:-1] if sufijo else texto
    if "," in cantidad and "." in cantidad:
        cantidad = cantidad.replace(",", "")
    elif "," in cantidad:
        cantidad = cantidad.replace(",", ".") if sufijo else cantidad.replace(",", "")
    try:
        n = float(cantidad)
        if n < 0:
            return None
        return n * {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[sufijo]
    except ValueError:
        return None


def calidad(perfil):
    presentes = [k for k in CAMPOS_CALIDAD if perfil.get(k) is not None and perfil.get(k) != ""]
    return round(len(presentes) * 100 / len(CAMPOS_CALIDAD), 1)


def indicadores(perfil):
    seguidores = numero_compacto(perfil.get("seguidores"))
    seguidos = numero_compacto(perfil.get("seguidos"))
    gustos = numero_compacto(perfil.get("me_gusta"))
    publicaciones = numero_compacto(perfil.get("publicaciones"))
    return {
        "usuario": perfil.get("usuario"),
        "nombre": perfil.get("nombre"),
        "seguidores": seguidores,
        "seguidos": seguidos,
        "me_gusta": gustos,
        "publicaciones": publicaciones,
        "seguidores_por_seguido": round(seguidores / seguidos, 2) if seguidores is not None and seguidos and seguidos > 0 else None,
        "me_gusta_por_publicacion": round(gustos / publicaciones, 2) if gustos is not None and publicaciones and publicaciones > 0 else None,
        "calidad_porcentaje": calidad(perfil),
        "videos_detectados": len(perfil.get("videos") or []),
        "fecha_consulta": perfil.get("fecha_consulta"),
    }


def limpiar_texto(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def oportunidades(comentarios):
    """Clasificación EXPLICABLE por palabras clave, no inferencia de autoría."""
    grupos = {tema: [] for tema in PREGUNTAS}
    sin_clasificar = 0
    vistos = Counter()
    for item in comentarios:
        texto = str(item.get("comentario", item.get("texto", ""))).strip()
        if not texto:
            continue
        plano = limpiar_texto(texto)
        vistos[plano] += 1
        encontrado = False
        for tema, palabras in PREGUNTAS.items():
            if any(palabra in plano for palabra in palabras):
                grupos[tema].append(texto)
                encontrado = True
        if not encontrado:
            sin_clasificar += 1
    clasificados = sorted(({
        "necesidad": tema,
        "menciones": len(ejemplos),
        "ejemplo_anonimo": ejemplos[0][:120] if ejemplos else "",
        "accion_sugerida": {
            "Precio y promociones": "Publicar video con precios y condiciones claras.",
            "Disponibilidad": "Mostrar inventario y cómo consultar existencias.",
            "Entrega y envíos": "Explicar tiempos, zonas y costos de entrega.",
            "Ubicación y horarios": "Crear contenido con dirección y horario de atención.",
            "Características": "Grabar una demostración del producto y preguntas frecuentes.",
        }[tema],
    } for tema, ejemplos in grupos.items() if ejemplos), key=lambda x: -x["menciones"])
    return {"prioridades": clasificados, "sin_clasificar": sin_clasificar,
            "duplicados_textuales": sum(n - 1 for n in vistos.values() if n > 1),
            "comentarios_analizados": sum(vistos.values())}


def videos_tabla(perfiles, adjuntos=None):
    todos = []
    for p in perfiles:
        todos.extend(p.get("videos") or [])
    if adjuntos:
        todos.extend(adjuntos)
    return todos


def exportar_csv_filas(filas, campos=None):
    filas = list(filas)
    campos = campos or list(dict.fromkeys(k for fila in filas for k in fila.keys()))
    if not campos:
        campos = ["sin_datos"]
    salida = io.StringIO(newline="")
    writer = csv.DictWriter(salida, fieldnames=campos, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(filas)
    return salida.getvalue().encode("utf-8-sig")


def exportar_json(filas):
    return json.dumps(filas, ensure_ascii=False, indent=2).encode("utf-8")


def validar_video(fila):
    usuario = str(fila.get("usuario", "")).strip().lstrip("@")
    if not usuario:
        return None
    return {
        "usuario": usuario,
        "video_id": str(fila.get("video_id", "")).strip(),
        "url": str(fila.get("url", "")).strip(),
        "descripcion": str(fila.get("descripcion", "")).strip(),
        "vistas": numero_compacto(fila.get("vistas")),
        "likes": numero_compacto(fila.get("likes")),
        "comentarios_cantidad": numero_compacto(fila.get("comentarios_cantidad")),
        "compartidos": numero_compacto(fila.get("compartidos")),
        "fecha_publicacion": str(fila.get("fecha_publicacion", "")).strip(),
        "origen": "CSV aportado",
    }


def indicadores_videos(videos):
    registros = []
    for v in videos:
        vistas = numero_compacto(v.get("vistas"))
        likes = numero_compacto(v.get("likes"))
        comentarios = numero_compacto(v.get("comentarios_cantidad"))
        registros.append({**v, "tasa_like_vistas_pct": round(likes * 100 / vistas, 2)
                          if vistas is not None and vistas > 0 and likes is not None else None,
                          "tasa_comentarios_vistas_pct": round(comentarios * 100 / vistas, 2)
                          if vistas is not None and vistas > 0 and comentarios is not None else None})
    return registros
