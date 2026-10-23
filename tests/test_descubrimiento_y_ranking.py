import unittest

from descubrimiento import candidatos_desde_resultados, usuario_desde_enlace
from seleccion_comercial import afinidad, elegir_cuenta


class DescubrimientoTests(unittest.TestCase):
    def test_extraer_usuarios_de_urls_tiktok(self):
        self.assertEqual(usuario_desde_enlace('https://www.tiktok.com/@tienda_cafe'), 'tienda_cafe')
        self.assertEqual(usuario_desde_enlace('https://www.tiktok.com/@tienda_cafe/video/123'), 'tienda_cafe')
        self.assertIsNone(usuario_desde_enlace('https://falso-tiktok.com/@tienda_cafe'))
        self.assertIsNone(usuario_desde_enlace('http://www.tiktok.com/@tienda_cafe'))
        self.assertIsNone(usuario_desde_enlace('https://www.tiktok.com/login'))
        self.assertEqual(usuario_desde_enlace('https://duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.tiktok.com%2F%40panaderia123'), 'panaderia123')

    def test_candidatos_unicos_sin_invenciones(self):
        datos = [
            {"url": 'https://www.tiktok.com/@pan_fresco', "titulo": "Pan fresco"},
            {"url": 'https://www.tiktok.com/@pan_fresco/video/1', "titulo": "Video"},
            {"url": 'https://www.youtube.com/@cocina', "titulo": "Otro"},
            {"url": 'https://www.tiktok.com/@pasteleria_eco', "titulo": "Pastelería"},
        ]
        seleccion = candidatos_desde_resultados(datos)
        self.assertEqual([c["usuario"] for c in seleccion], ["pan_fresco", "pasteleria_eco"])


class RankingTests(unittest.TestCase):
    def _perfil(self, usuario, bio, seguidores, nombre=None, videos=None):
        return {"usuario": usuario, "nombre": nombre or usuario, "biografia": bio,
                "seguidores": seguidores, "seguidos": "12", "me_gusta": "100K", "publicaciones": "10",
                "verificada": False, "cuenta_privada": False, "fecha_consulta": "2026-10-22T16:00:00-05:00",
                "videos": videos or []}

    def test_relevancia_priorizada_frente_a_seguidores(self):
        pequeno = self._perfil('tartas_eco', 'Repostería artesanal y pasteles', '25K', 'Pasteles de repostería')
        grande = self._perfil('millon', 'Bailes y videos de humor', '2M', 'Bailes')
        resultados = elegir_cuenta('repostería', [grande, pequeno])
        self.assertEqual(resultados[0]['usuario'], 'tartas_eco')
        self.assertGreater(resultados[0]['afinidad_pct'], resultados[1]['afinidad_pct'])
        self.assertEqual(resultados[0]['base_interaccion'], 'No comparable en el lote')

    def test_sin_relevancia_no_aporta_evidencia(self):
        score, evidencia = afinidad('productos de ciclismo', {'nombre': 'Humor', 'biografia': 'Bailes'}, {})
        self.assertEqual(score, 0)
        self.assertEqual(evidencia, [])

    def test_interaccion_solo_si_se_puede_comparar(self):
        a = self._perfil('a', 'ciclismo', '100K', videos=[{'likes': '100', 'vistas': '1000'}])
        b = self._perfil('b', 'ciclismo', '90K')
        resultados = elegir_cuenta('ciclismo', [a, b])
        self.assertTrue(all(r['base_interaccion'] == 'No comparable en el lote' for r in resultados))


if __name__ == '__main__':
    unittest.main()
