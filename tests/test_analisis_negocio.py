import unittest
from analisis_negocio import numero_compacto, indicadores, oportunidades, calidad, validar_video

class PruebasAnalisis(unittest.TestCase):
    def test_convertir_abreviaturas(self):
        self.assertEqual(numero_compacto('302.3K'), 302300)
        self.assertEqual(numero_compacto('1.7M'), 1700000)
        self.assertEqual(numero_compacto('0'), 0)
        self.assertIsNone(numero_compacto('No disponible'))

    def test_indicadores(self):
        p = {"usuario":"prueba","seguidores":"100","seguidos":"20",
             "me_gusta":"600","publicaciones":"3"}
        r = indicadores(p)
        self.assertEqual(r['seguidores_por_seguido'], 5)
        self.assertEqual(r['me_gusta_por_publicacion'], 200)

    def test_cero_es_dato_valido(self):
        p = {"usuario": "x", "seguidores": "0", "verificada": False}
        self.assertEqual(calidad(p), 30.0)

    def test_demanda_y_duplicados(self):
        r = oportunidades([{"comentario":"¿Cuánto cuesta?"},
                           {"comentario":"¿Cuánto cuesta?"},
                           {"comentario":"¿Hacen envíos?"}])
        self.assertEqual(r['duplicados_textuales'], 1)
        self.assertEqual(r['prioridades'][0]['necesidad'], 'Precio y promociones')

    def test_videos_sin_metricas(self):
        v = validar_video({"usuario":"prueba", "url":"https://ejemplo.com"})
        self.assertIsNone(v['likes'])

if __name__ == '__main__':
    unittest.main()

from scraper import _item_stats

class PruebasMetricasVideo(unittest.TestCase):
    def test_item_module_video(self):
        salida = _item_stats({"ItemModule": {"123": {"id": "123", "stats": {
            "playCount": 250, "diggCount": 20, "commentCount": 7}}}})
        self.assertEqual(salida["123"]["vistas"], 250)
        self.assertEqual(salida["123"]["comentarios_cantidad"], 7)
