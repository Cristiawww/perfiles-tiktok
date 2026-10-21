"""Pruebas de funciones que no requieren conectarse a TikTok."""
import csv
import io
import json
import unittest

from scraper import (
    buscar_diccionario_usuario,
    exportar_csv_perfil,
    exportar_json,
    limpiar_usuario,
    paquete_de_usuario,
    url_publica,
)


class PruebasScraper(unittest.TestCase):
    def test_usuario_con_arroba(self):
        self.assertEqual(limpiar_usuario(" @ejemplo "), "ejemplo")

    def test_rechazar_url_completa(self):
        with self.assertRaises(ValueError):
            limpiar_usuario("https://www.tiktok.com/@ejemplo")

    def test_buscar_usuario_correcto(self):
        datos = {"otro": {"uniqueId": "otra"}, "perfil": {"uniqueId": "EJEMPLO"}}
        self.assertEqual(buscar_diccionario_usuario(datos, "ejemplo")["uniqueId"], "EJEMPLO")

    def test_extraer_paquete(self):
        estructura = {"__DEFAULT_SCOPE__": {"webapp.user-detail": {"userInfo": {
            "user": {"uniqueId": "ejemplo", "nickname": "Mi perfil"},
            "stats": {"followerCount": 21},
        }}}}
        cuenta, stats = paquete_de_usuario(estructura, "ejemplo")
        self.assertEqual(cuenta["nickname"], "Mi perfil")
        self.assertEqual(stats["followerCount"], 21)

    def test_no_acepta_javascript_url(self):
        self.assertIsNone(url_publica("javascript:alert(1)"))

    def test_exportaciones(self):
        datos = {"usuario": "ejemplo", "nombre": "Prueba", "seguidores": "10"}
        self.assertEqual(json.loads(exportar_json(datos))["nombre"], "Prueba")
        csv_texto = exportar_csv_perfil(datos).decode("utf-8-sig")
        filas = list(csv.DictReader(io.StringIO(csv_texto)))
        self.assertEqual(filas[0]["usuario"], "ejemplo")
        self.assertEqual(filas[0]["seguidores"], "10")


if __name__ == "__main__":
    unittest.main()
