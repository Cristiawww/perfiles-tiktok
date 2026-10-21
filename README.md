# Perfiles TikTok


## Qué hace el programa

Permite consultar el nombre visible, el usuario, los seguidores, los seguidos y los Me gusta. También intenta recuperar la biografía, la foto, el enlace de la biografía, el estado de verificación, si la cuenta es privada y la cantidad de publicaciones. Algunos de estos datos pueden no aparecer en todas las consultas.

Además, muestra la fecha y hora en que se realizó la consulta y permite guardar el resultado en formatos JSON y CSV.

**Importante:** la fecha de consulta no es la fecha de creación de la cuenta. TikTok no muestra de forma habitual una fecha de creación verificable en los perfiles públicos, por lo que no se incluye ese dato.

## Herramientas utilizadas

- **Python 3.12:** lenguaje principal.
- **Playwright:** abre el perfil en Chromium y busca información que aparece en la página. No utilizo la API oficial de TikTok.
- **Streamlit:** presenta el formulario, los resultados y los botones de descarga.
- **Git y GitHub:** permiten guardar versiones del proyecto y registrar los cambios.

## Cómo ejecutarlo

Desde la carpeta del proyecto, en Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m streamlit run app.py
```

La interfaz se abre normalmente en `http://localhost:8501`. Se escribe un usuario con o sin `@` y se selecciona **Consultar perfil**.

Para ejecutar solo la consulta desde la terminal:

```powershell
.\.venv\Scripts\python.exe scraper.py
```

## Archivos principales

- `scraper.py`: valida el usuario, abre la página, busca los datos y prepara las exportaciones.
- `app.py`: contiene la interfaz web.
- `requirements.txt`: enumera las bibliotecas necesarias.
- `.gitignore`: evita subir el entorno virtual y archivos temporales.

## Limitaciones y pruebas

Los resultados dependen de lo que TikTok muestre públicamente en el momento de la consulta. Algunos elementos pueden cambiar o no cargar, y el programa no accede a datos privados. Tampoco inventa valores cuando un campo no está disponible.

**Completar con las pruebas realizadas antes de entregar:**

- Perfil público probado: ____________________
- ¿Mostró el nombre, seguidores y seguidos?: ____________________
- ¿Apareció la biografía?: ____________________
- ¿Se detectó la verificación y el número de publicaciones?: ____________________
- ¿Se descargó correctamente el JSON?: ____________________
- ¿Se descargó correctamente el CSV?: ____________________
- Dificultades encontradas: ____________________

## Comentario final

También comprobé que un scraper necesita pruebas, porque una página web puede cambiar y no siempre entrega la misma información. Por eso es importante distinguir entre un dato obtenido realmente y uno que simplemente no está disponible.
