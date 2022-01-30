# Test Scraping - BB

El objetivo del script es tomar el listado de peliculas y series de la plataforma Starz, extraer la información importante y guardarla en un archivo JSON.

## Ejecucion
Para correr el script es necesario instalar las librerías dictadas en el archivo `requirements.txt`, el proceso se puede automatizar usando el siguiente comando: <br>
`pip3 install -r requirements.txt`<br>
Luego se ejecuta el archivo main.py:<br>
`python3 main.py`<br>
Como resultado, va a generar una base de datos "starz" en MongoDB con dos colecciones: "series" y "peliculas", ademas de dos archivos .json (series.json, peliculas.json) en la carpeta raíz.

## Funcionamiento
Se parte de dos rutas:
- `https://www.starz.com/ar/es/movies` para las peliculas
- `https://www.starz.com/ar/es/series` para las series

Usando la librería de Selenium se interactua con la página hasta obtener el listado de todas las series/peliculas, luego con Beautiful Soup se obtiene información como título, año, duración, además de la ruta especifica de cada pelicula/serie para obtener más metadatos como sinopsis, director, episodios, etc.

Para agilizar su ejecución, el script corre las funciones en dos procesos distintos usando la librería multiprocessing.