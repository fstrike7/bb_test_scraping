from importlib.resources import path
from bson.json_util import dumps
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import time, os

# Para multiprocesamiento
from multiprocessing import Pool

# Para guardar la informacion
import json
from pymongo import MongoClient

# Las siguientes tres las uso para esperar a que Selenium detecte que la página renderizó las peliculas/series
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service

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
        self.options.add_argument('log-level=2')
        """
        log-level: 
        Establece el nivel de log mínimo.
        Los valores válidos son de 0 a 3: 
            INFO = 0, 
            WARNING = 1, 
            LOG_ERROR = 2, 
            LOG_FATAL = 3.
        """

    # Funciones
    def configurarMongo(self):
        # Opciones de Mongo
        try:
            client = MongoClient("localhost", 27017)
            db = client["starz"]
            return db
        except Exception as e:
            print("Ocurrió un error conectandose a la base de datos en MongoDB: ")
            print(e.args)
            os.exit()

    def configurarSelenium(self) -> webdriver:
        # Configuracion de Selenium
        try:
            s=Service(ChromeDriverManager().install())
            browser = webdriver.Chrome(service=s, options=self.options)
            return browser
        except Exception as e:
            if e.__class__.__name__ == "SessionNotCreatedException":
                # Este error se da cuando la sesión no se puede crear porque la versión del navegador con la del driver son incompatibles
                # para solucionarlo usamos un driver propio que se encuentra en la carpeta driver.
                s=Service("./driver/chromedriver.exe")
                browser = webdriver.Chrome(service=s, options=self.options)
                return browser
            print("Ocurrió un error configurando Selenium:")
            print(e.args)
            os.exit()


    def obtenerElementos(self, browser, path) -> set:
        # Al tener ambas páginas (movies y series) la misma estructura, se repite el proceso de renderizar, moverse y tomar los elementos.
        url = self.WEB_URL + self.PATHS[path]
        print(f"Obteniendo elementos desde {url}")
        browser.get(url)
        WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "view-all"))) # Espera al boton "Ver todos"
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "view-all"))).click() # y lo clickea

        WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "icon-stz-list"))) # Espera al boton para cambiar a formato de lista
        WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "icon-stz-list"))).click() # y lo clickea
        
        WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "view-item-text")))# Espera hasta que se renderice el texto de cada pelicula
        
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

        print(f"{len(set_elementos)} elementos encontrados para la coleccion {path}")
        
        return set_elementos

    def scrapPeliculas(self) -> None:

        peliculas = [] # Lista de objetos de clase Pelicula
        browser = self.configurarSelenium() # Devuelve un driver de Selenium
        db = self.configurarMongo() # Devuelve una instancia de la base de datos "starz"
        set_elementos = self.obtenerElementos(browser, "peliculas") # Reune todos los elementos del listado de la página

        # Por elemento, tomar la información importante e instanciarlo en un objeto Pelicula
        for elemento in set_elementos:
            link = self.WEB_URL + '/' + elemento["href"] # link puede ser tomado como id porque es único por elemento
            # Para evitar escribir el mismo documento dos veces, comprueba si existe en la DB
            if self.existeEnDB(link, db): continue # Si existe, saltea a la siguiente iteración
            print(f"Scrapeando: {link}")

            titulo = elemento.find("p", {"class": "title"}).text
            info = elemento.find("p", {"class": "text-body"})
            # <info> devuelve un array con tres etiquetas span.
            duracion, anio = [info.find_all("span")[i].text for i in (0, -1)]
            # <duracion> y <anio> toman el primer y último valor que corresponden a la duración en minutos y el año de salida.
            duracion = int(duracion)
            anio = int(anio)

            browser.get(link) # Redirecciona al link de la pelicula para tener más información, como la sinopsis y el director.
            WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "movie-details-page"))) # Espera a los detalles de la pelicula
            try:
                # Si la sinopsis está parcialmente oculta, espera al botón para expandir la info:
                WebDriverWait(browser, 10).until(EC.element_to_be_clickable(browser.find_element(By.XPATH, "//button[@class='more-link more-button show']"))).click()
            except Exception as e:
                # No encontró un botón "...MÁS"
                pass # Continua

            html_doc = browser.page_source
            soup = BeautifulSoup(html_doc, 'html.parser')

            sinopsis = soup.find("div", {"class": "logline"}).find("p").text
            director = soup.find("div", {"class": "directors"}).find("span").text

            # Instanciar objeto Pelicula
            pelicula = Pelicula()
            pelicula.setTitulo(titulo)
            pelicula.setAnio(anio)
            pelicula.setSinopsis(sinopsis)
            pelicula.setLink(link)
            pelicula.setDirector(director)
            try:
                self.guardarEnDB(pelicula, db) # Lo guarda en la BD
                print(f"Pelicula: {titulo} guardada en la base de datos")
            except Exception as e:
                print(f"Hubo un error y no se pudo guardar la pelicula {titulo} en la base de datos.")
                print(e.args)
            peliculas.append(pelicula.__dict__) # Convierte todos los atributos del objeto a un diccionario y lo guarda en la lista de peliculas
        browser.close()

        # Una vez que se iteró todos los elementos y la colección contiene todos los documentos, se exporta como archivo .json
        self.exportarJSON("peliculas", db)

    def scrapSeries(self) -> None:
        series = [] # Set de objetos de clase Serie
        browser = self.configurarSelenium()
        db = self.configurarMongo()
        set_elementos = self.obtenerElementos(browser, "series") # Reune todos los elementos de la lista

        # Por cada elemento, tomar la información e instanciarlo en un objeto Serie
        for elemento in set_elementos:
            link = self.WEB_URL + '/' + elemento["href"]
            if self.existeEnDB(link, db): continue
            print(f"Scrapeando: {link}")

            titulo = elemento.find("p", {"class": "title"}).text
            info = elemento.find("p", {"class": "text-body"})
            # <info> devuelve una lista de 4 elementos span, donde la 3ra corresponde a los episodios y la 4ta al año
            anio = info.find_all("span")[-1].text.split("-") # Si la serie finalizó, se divide en una lista [desde, hasta], sino [desde]
            if len(anio) == 2:
                anio = {
                    "desde": int(anio[0]),
                    "hasta": int(anio[1])
                }
            else: anio = {"desde": int(anio[0])}
            cantidad_episodios = int(info.find_all("span")[2].find_all("span")[0].text)

            # Redirecciona al link de la serie para tener más información, como la sinopsis y los episodios.
            browser.get(link)
            WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "series-details-page"))) # Espera a los detalles de la serie
            html_doc = browser.page_source
            soup = BeautifulSoup(html_doc, 'html.parser')
            
            sinopsis = soup.find("div", {"class": "logline"}).find("p").text
            
            elem_temporadas = soup.find_all("div", {"class": "season-number"}) # elemento del DOM que contiene la cantidad de temporadas
            elem_temporadas = [ self.WEB_URL + '/' + temporada.find("a")["href"][4:] for temporada in elem_temporadas ] # Mapear cada elemento para extraer el link de esa temporada
            detalle_episodios = [] # Una lista donde por cada episodio se guarda información como nombre, sinopsis, duración y año de estreno.
            def scrapTemporada(temporada):
                browser.get(temporada)
                WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "episodes-container")))
                
                # Por cada episodio, si la sinopsis está parcialmente oculta, toca el botón "...MÁS":
                try:
                    WebDriverWait(browser, 10).until(EC.element_to_be_clickable(browser.find_element(By.XPATH, "//button[@class='more-link more-button show']")))
                    for element in browser.find_elements(By.XPATH, "//button[@class='more-link more-button show']"): element.click()
                except Exception as e:
                    # No encontró botones
                    pass

                html_doc = browser.page_source
                season = BeautifulSoup(html_doc, 'html.parser')

                lista_episodios = season.find("div", {"class": "episodes-container"}).find_all("div", {"class": "episode-container"})
                for episodio in lista_episodios:
                    ep_titulo = episodio.find("h6", {"class": "title"}).text
                    ep_sinopsis = episodio.find("div", {"class": "logline"}).find("p").text
                    if ep_titulo == "Tráiler oficial": break # Ignora el trailer
                    metadata = episodio.find("ul", {"class": "meta-list"}).find_all("li")
                    informacion = {
                        "nombre": ep_titulo,
                        "sinopsis" : ep_sinopsis,
                        "duracion" : metadata[1].text + " minutos",
                        "anio": metadata[2].text
                    }
                    detalle_episodios.append(informacion)
            for temporada in elem_temporadas: scrapTemporada(temporada)
            episodios = {
                "cantidad": cantidad_episodios,
                "temporadas": len(elem_temporadas),
                "detalles": detalle_episodios
            }
            
            # Instanciar serie
            print("Instanciando")
            serie = Serie()
            serie.setTitulo(titulo)
            serie.setAnio(anio)
            serie.setSinopsis(sinopsis)
            serie.setLink(link)
            serie.setEpisodios(episodios)
            
            try:
                self.guardarEnDB(serie, db) # Lo guarda en la BD
                print(f"Serie: {titulo} guardada en la base de datos")
            except Exception as e:
                print(f"Hubo un error y no se pudo guardar la serie {titulo} en la base de datos:")
                print(e.args)

            series.append(serie.__dict__) # Lo agrega a la lista como diccionario

        browser.close()
        self.exportarJSON("series", db)

    def existeEnDB(self, link, db) -> bool:
        coleccion = db["series"] if link.split("/")[4] == "series" else db["peliculas"]
        cantidad_documentos = 0
        try:
            cantidad_documentos = coleccion.count_documents({"_link": link})
        except Exception as e:
            print(e.__class__.__name__)
            print(e.args)
            # La primera vez no va a encontrar la coleccion y entra aca, pero no hace falta notificarlo
            pass
        return cantidad_documentos > 0

    def guardarEnDB(self, elem, db):
        coleccion = db["series"] if type(elem) == Serie else db["peliculas"]
        coleccion.insert_one(elem.__dict__)
        print(f"{coleccion.count_documents({})} elementos guardados en la coleccion {coleccion.name}.")
    
    def exportarJSON(self, coleccion, db): # Toma la colección directamente de la base de datos y la exporta como .json
        coleccion = db[coleccion] 

        cursor = coleccion.find({})
        archivo = f"{coleccion.name}.json"
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(json.loads(dumps(cursor)), f, ensure_ascii=False, indent=4)
        print(f"Archivo {archivo} generado")

    def run(self):
        resultados = [] # Lista de funciones
        with Pool() as pool:
            # Agrega a la lista
            resultados.append(pool.apply_async(self.scrapPeliculas))
            resultados.append(pool.apply_async(self.scrapSeries))

            for r in resultados:
                r.wait() # Espera a que finalicen ambos procesos



# Ejecucion
if __name__ == "__main__":
    app = Main()
    app.run()
    print("Finalizado")

