# RADAR 5V — De los datos públicos a decisiones comerciales

Proyecto ampliado a partir de `perfiles-tiktok`. La aplicación consulta hasta **cinco perfiles públicos por lote** con Playwright, analiza las cifras recuperadas, permite incorporar estadísticas verificadas de videos y organiza comentarios públicos por preguntas comerciales frecuentes.

**Idea de negocio:** ofrecer a comercios pequeños diagnósticos de contenido basados en preguntas reales de su audiencia. Por ejemplo, si muchos comentarios preguntan por el precio o la entrega, se propone crear un video que responda esas dudas. No es una predicción de ventas.

## Instalación en Windows

Conservar la carpeta `.venv` ya creada. En VS Code, dentro del repositorio:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Uso

1. En **01 · Buscar por tema**, escribe qué vende tu negocio o qué tema necesitas estudiar, por ejemplo `repostería`. La aplicación intenta localizar hasta cinco cuentas públicas en resultados de búsqueda. Puedes completar usuarios manualmente y pulsar **Consultar perfiles y elegir candidata** para obtener un ranking con motivos y exportación CSV.
2. En **02 · Consultar cuentas**, puedes ingresar hasta cinco usuarios concretos por lote, importar JSON exportados por el scraper anterior o cargar el ejemplo que ya proporcionaste.
3. En **03 · Comparar**, visualiza las cuentas, indicadores, gráficos y exporta un CSV. Cuando existan enlaces y estadísticas públicos de videos, se incluyen. También puedes incorporar un CSV verificable de videos con columnas `usuario,video_id,url,descripcion,vistas,likes,comentarios_cantidad,compartidos,fecha_publicacion`.
4. En **04 · Oportunidades**, carga un CSV con una columna `comentario`. La aplicación agrupa dudas sobre precio, ubicación, entrega, disponibilidad y características. Evita incluir nombres de personas que comentan.
5. En **05 · Cinco V**, revisa las cinco V aplicadas al conjunto, incluyendo el porcentaje de completitud.

## Precauciones metodológicas

- No utiliza directamente la API oficial ni cookies copiadas de una sesión. Chromium puede gestionar cookies propias durante la visita.
- Solo usa la información que las páginas públicas muestran; TikTok puede restringir la consulta o cambiar su HTML.
- La página puede mostrar videos fijados antes que recientes. Por eso los primeros diez enlaces detectados **no siempre son cronológicamente los diez últimos**.
- No se inventan likes, vistas o comentarios no disponibles, ni se atribuye autoría humana/IA con certeza.
- `302.3K` se transforma aproximadamente en `302300`, no debe interpretarse como una cifra exacta.
- Un perfil por sí solo no demuestra tendencias de crecimiento ni permite inferir la personalidad de alguien.
- Las oportunidades sugeridas son hipótesis comerciales basadas en palabras clave; deben validarse con más datos y resultados del negocio.

## Archivos

- `app.py`: interfaz con cinco pestañas.
- `scraper.py`: lectura de perfiles HTML/JSON, validación y búsqueda opcional de enlaces de videos.
- `analisis_negocio.py`: indicadores y clasificación transparente de comentarios.
- `descubrimiento.py`: obtención de cuentas candidatas desde resultados públicos de búsqueda web con Playwright.
- `seleccion_comercial.py`: ranking temático y explicación de criterios de comparación.
- `.streamlit/config.toml`: colores y contraste de los controles.
- `requirements.txt`: dependencias.
- `tests/`: pruebas locales sin consultar TikTok.
- `ejemplos/`: un perfil aportado para el análisis y plantillas CSV vacías.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas automáticas no certifican que TikTok permita todas las consultas. La prueba real debe hacerse con cuentas públicas que puedas visitar normalmente.

## Posibles siguientes avances

Comparar capturas de una misma cuenta en dos fechas distintas; evaluar la precisión de la clasificación de comentarios con revisión humana y medir si los videos que responden preguntas comerciales aumentan las consultas de clientes.

## Buscar cuentas por tema y elegir una candidata

En la pestaña **01 · Buscar por tema**, escribe una actividad concreta, por ejemplo
`repostería` o `bicicletas`. El programa intenta encontrar hasta cinco cuentas
públicas a través de resultados web abiertos usando Playwright, Bing y DuckDuckGo;
**no usa una API**. Los motores de búsqueda no indexan todos los perfiles y
pueden rechazar o cambiar las respuestas: por eso el resultado no está garantizado.

Cuando aparezcan las cuentas candidatas, puedes completar la lista con usuarios
públicos reales que conozcas. Pulsa **Consultar perfiles y elegir candidata**.
Se realizará una consulta secuencial a cada cuenta. Las consultas fallidas
se muestran como errores; no se sustituyen con ejemplos ficticios.

El ranking es una **preselección para investigar colaboraciones**, no una
predicción de ventas. Sus criterios son:

- Coincidencia textual de tema con nombre/biografía y, de forma secundaria,
  la descripción en el buscador: **50 %** de peso inicial.
- Tamaño relativo de audiencia (seguidores): **25 %**.
- Disponibilidad/completitud de campos: **10 %**.
- Interacción con publicaciones (likes/vistas): **15 %**, **solo si** todas
  las cuentas tienen datos comparables. De lo contrario se omite este factor
  para todo el lote y los pesos se renormalizan.

Los datos abreviados como `25K` se convierten en cifras aproximadas. Que una
cuenta mencione un tema no demuestra que sea una buena socia comercial;
sería necesario revisar el contenido, la audiencia objetivo y las condiciones
de colaboración. Tampoco se deduce autoría de IA a partir de comentarios.

Para ejecutar pruebas de lógica sin consultar TikTok:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Aspectos que podrían mejorarse

- Incorporar una comprobación humana de los resultados temáticos.
- Evaluar concordancia entre contenido reciente y la temática.
- Medir evolución de una cuenta a partir de consultas repetidas en fechas diferentes.
- Agregar métricas comerciales verificadas (costo de colaboración, conversiones)
  antes de declarar una cuenta como la mejor inversión.

## Ajuste de búsqueda y presentación

La consulta por tema ahora prueba expresiones más abiertas, ampliando vocabulario en ámbitos como ropa/moda, ciclismo/bicicletas y tecnología/dispositivos. Alterna buscadores públicos sin usar API. Las coincidencias temáticas en la descripción del perfil pesan más que las encontradas solo en un resultado del buscador. Si no se recuperan cuentas, se pueden introducir perfiles públicos conocidos; nunca se crean cuentas ficticias. La interfaz usa tarjetas blancas con nombres legibles y menos texto de explicación.
