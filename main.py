from importlib.resources import path
from bs4 import BeautifulSoup
from selenium import webdriver
import time

# Para guardar la informacion
import json
from pymongo import MongoClient

# Las siguientes tres las uso para esperar a que Selenium detecte que la página renderizó las peliculas/series
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Importamos clases
from item import Pelicula, Serie

# Clase Main
class Main:
    def __init__(self) -> None:
        
        # Constantes
        self.WEB_URL = "https://www.starz.com/ar"
        self.PATHS = {
            "peliculas": "/es/movies",
            "series": "/es/series"
        }

        # Opciones de Selenium
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')

        # Opciones de Mongo
        CONNECTION_STRING = "mongodb://localhost:27020/BBTestScraping"
        self.client = MongoClient(CONNECTION_STRING)

    # Funciones

    def configurarSelenium(self) -> webdriver:
        # Configuracion de Selenium
        browser = webdriver.Chrome(options=self.options, executable_path='./driver/chromedriver.exe')
        return browser


    def obtenerElementos(self, browser, path) -> set:
        # Al tener ambas páginas (movies y series) la misma estructura, se repite el proceso de renderizar, moverse y tomar los elementos.
        url = self.WEB_URL + self.PATHS[path]
        browser.get(url)
        WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "view-all"))) # Espera al boton "Ver todos"
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "view-all"))).click() # y lo clickea

        WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "icon-stz-list"))) # Espera al boton para cambiar a formato de lista
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "icon-stz-list"))).click() # y lo clickea
        
        WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "view-item-text")))# Espera hasta que se renderice el texto de cada pelicula
        
        # Ya una vez en el listado de peliculas/series, se reunen todos los elementos y se devuelven en un set
        def obtenerLargoDocumento(browser):
            # Obtiene el largo del documento, para ello busca el valor de Y en la propiedad transform del elemento scrollable-content
            scrollable = browser.find_element(By.CLASS_NAME,"scrollable-content")
            matrix = scrollable.value_of_css_property("transform") # Devuelve: matrix(a, b, c, d, x, y). Donde nos interesa el valor de y
            height = int(matrix[5:-1].split(',')[-1]) # Obtiene los valores dentro del parentesis, los separa en una lista y toma el último valor, parseandolo como entero.
            return height
        TIEMPO_DE_PAUSA = .2
        set_elementos = set() # Uso un set para evitar que se repitan los elementos
        
        last_height = obtenerLargoDocumento(browser)

        # Loopea hasta llegar al final de la página
        while True:
            # Convierte a código fuente para scrapear:
            html_doc = browser.page_source
            soup = BeautifulSoup(html_doc, 'html.parser')
            nuevos_elementos = soup.find_all("a", {"class": "list-link"}) # Junta todos los elementos con la clase "list-link"
            set_elementos.update(nuevos_elementos) # y actualiza el set con los nuevos elementos

            # Una vez agregados al set, scrollea al ultimo elemento
            browser.execute_script("arguments[0].scrollIntoView();", browser.find_elements(By.CLASS_NAME,"list-link")[-1])
            # Espera a que la página cargue los elementos
            time.sleep(TIEMPO_DE_PAUSA)

            # Obtiene el nuevo largo del documento y lo compara con el largo anterior
            new_height = obtenerLargoDocumento(browser)
            if new_height == last_height: break
            last_height = new_height
        
        return set_elementos

    def scrapPeliculas(self):

        peliculas = set() # Set de objetos de clase Pelicula
        browser = self.configurarSelenium()
        set_elementos = self.obtenerElementos(browser, "peliculas") # Reune todos los elementos de la lista
        browser.quit()

        # De un elemento, tomar la información importante e instanciarlo en un objeto Pelicula
        def instanciarPelicula(elemento):

            link = self.WEB_URL + '/' + elemento["href"]
            titulo = elemento.find("p", {"class": "title"}).text
            info = elemento.find("p", {"class": "text-body"})
            # <info> devuelve un array con tres etiquetas span.
            duracion, anio = [info.find_all("span")[i].text for i in (0, -1)]
            # <duracion> y <anio> toman el primer y último valor que corresponden a la duración en minutos y el año de salida.
            duracion = int(duracion)

            # Redirecciona al link de la pelicula para tener más información, como la sinopsis y el director.
            browser.get(link)
            WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "movie-details-page"))) # Espera a los detalles de la pelicula
            html_doc = browser.page_source
            soup = BeautifulSoup(html_doc, 'html.parser')

            sinopsis = soup.find("div", {"class": "logline"}).find("p").text
            director = soup.find("div", {"class": "directors"}).find("span").text

            pelicula = Pelicula(titulo, anio, sinopsis, link, duracion, director)
            self.guardarEnDB(pelicula)
            peliculas.add(pelicula.__dict__)
        
        for elem in set_elementos: instanciarPelicula(elem)

        print(f"Cantidad de peliculas encontradas: {len(peliculas)}")
        browser.quit()
        return peliculas

    def scrapSeries(self) -> set:
        series = set() # Set de objetos de clase Serie
        browser = self.configurarSelenium()
        set_elementos = self.obtenerElementos(browser, "series") # Reune todos los elementos de la lista

        # Por cada elemento, tomar la información e instanciarlo en un objeto Serie
        def instanciarSerie(elemento):
            link = self.WEB_URL + '/' + elemento["href"]
            titulo = elemento.find("p", {"class": "title"}).text
            info = elemento.find("p", {"class": "text-body"})
            # <info> devuelve una lista de 4 elementos span, donde la 3ra corresponde a los episodios y la 4ta al año
            anio = info.find_all("span")[-1].text.split(",") # Si la serie terminó, se divide en una lista [desde, hasta], sino [desde]
            if len(anio) == 2:
                anio = {
                    "desde": anio[0],
                    "hasta": anio[1]
                }
            else: anio = anio[0]
            cantidad_episodios = int(info.find_all("span")[2].find_all("span")[0].text)

            # Redirecciona al link de la serie para tener más información, como la sinopsis y los episodios.
            browser.get(link)
            WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "series-details-page"))) # Espera a los detalles de la serie
            html_doc = browser.page_source
            soup = BeautifulSoup(html_doc, 'html.parser')
            
            sinopsis = soup.find("div", {"class": "logline"}).find("p").text
            
            detalle_episodios = [] # Una lista donde por cada episodio se guarda información como nombre, sinopsis, duración y año de estreno.

            lista_episodios = soup.find("div", {"class": "episodes-container"}).find_all("div", {"class": "episode-container"})
            for episodio in lista_episodios:
                metadata = episodio.find("ul", {"class": "meta-list"}).find_all("li")
                informacion = {
                    "nombre": episodio.find("h6", {"class": "title"}).text,
                    "sinopsis" : soup.find("div", {"class": "logline"}).find("p").text,
                    "duracion" : metadata[1].text,
                    "anio": metadata[2].text
                }
                detalle_episodios.append(informacion)
            episodios = {
                "cantidad": cantidad_episodios,
                "listado": detalle_episodios
            }

            serie = Serie(titulo, anio, sinopsis, link, episodios)
            
            self.guardarEnDB(serie) # Lo guarda en la BD
            series.add(serie.__dict__) # Lo agrega al set como diccionario

        for elem in set_elementos: instanciarSerie(elem)
        browser.quit()
        return series

    def guardarEnDB(self, elem):
        db = self.client["starz"]
        collection = db["series"] if type(elem) == Serie else db["peliculas"]
        collection.insert_one(elem.__dict__)
    
    def guardarSetsEnJSON(peliculas: set, series: set):
        with open('peliculas.json', 'w', encoding='utf-8') as f:
            json.dump(peliculas, f, ensure_ascii=False, indent=4)
        
        with open('series.json', 'w', encoding='utf-8') as f:
            json.dump(series, f, ensure_ascii=False, indent=4)



# Ejecucion
if __name__ == "__main__":
    main = Main()
    set_series = main.scrapSeries()
    set_peliculas = main.scrapPeliculas()
    main.guardarSetsEnJSON(peliculas=set_peliculas, series=set_series)




