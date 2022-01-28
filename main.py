from bs4 import BeautifulSoup
from selenium import webdriver
import time

# Las siguientes tres las uso para esperar a que Selenium detecte que la página renderizó las peliculas/series
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Objetos
class Elemento:
    def __init__(self, titulo, anio, sinopsis, link) -> None:
        self._titulo = titulo
        self._anio = anio
        self._sinopsis = sinopsis
        self._link = link

class Pelicula(Elemento):
    def __init__(self, titulo, anio, sinopsis, link, duracion) -> None:
        super().__init__(titulo, anio, sinopsis, link)
        self._duracion = duracion

class Serie(Elemento):
    def __init__(self, titulo, anio, sinopsis, link, episodios) -> None:
        super().__init__(titulo, anio, sinopsis, link)
        self._episodios = episodios

# Constantes
WEB_URL = "https://www.starz.com/ar"
PATHS = {
    "peliculas": "/es/movies",
    "series": "/es/series"
}

# Funciones

def obtenerElementos(browser):

    # La defino como una función porque se va a reutilizar dos veces
    def obtenerLargoDocumento(browser):
        # Obtiene el largo del documento, para ello busca el valor de Y en la propiedad transform del elemento scrollable-content
        scrollable = browser.find_element(By.CLASS_NAME,"scrollable-content")
        matrix = scrollable.value_of_css_property("transform") # Devuelve: matrix(a, b, c, d, x, y). Donde nos interesa el valor de y
        height = int(matrix[5:-1].split(',')[-1]) # Obtiene los valores dentro del parentesis, los separa en una lista y toma el último valor, parseandolo como entero.
        return height
    TIEMPO_DE_PAUSA = .2
    set_elementos = set() # Uso un set para evitar que se repitan los elementos
    
    last_height = obtenerLargoDocumento(browser)

    # Itera hasta llegar al final de la página
    while True:
        # Convierte a código fuente para scrapear:
        html_doc = browser.page_source
        soup = BeautifulSoup(html_doc, 'html.parser')
        nuevos_elementos = soup.find_all("a", {"class": "list-link"}) # Busca todos los elementos con la clase "list-link"
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

def scrapPeliculas():
    url = WEB_URL + PATHS["peliculas"]
    peliculas = set() # Set de objetos de clase Pelicula

    # Configuracion de Selenium
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    browser = webdriver.Chrome(options=options, executable_path='./driver/chromedriver.exe')
    browser.get(url)
    # Interactua con la página:
    WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "view-all"))) # Espera al boton "Ver todos"
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "view-all"))).click() # y lo clickea

    WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "icon-stz-list"))) # Espera al boton para cambiar a formato de lista
    WebDriverWait(browser, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "icon-stz-list"))).click() # y lo clickea
    
    WebDriverWait(browser, 20).until(EC.visibility_of_element_located((By.CLASS_NAME, "view-item-text")))# Espera hasta que se renderice el texto de cada pelicula
    set_elementos = obtenerElementos(browser)

    # Convertir el set de elementos en objetos de clase Pelicula
    for elemento in set_elementos:
        link = WEB_URL + '/' + elemento["href"]
        print(link)
        titulo = elemento.find("p", {"class": "title"}).text
        print(titulo)
        info = elemento.find("p", {"class": "text-body"})
        
        duracion, anio = [info.find_all("span")[i].text for i in (0, -1)] # Devuelve una lista de dos elementos, con la cantidad de minutos y el año de salida
        print(duracion)
        print(anio)

        sinopsis = "PENDIENTE" # Para la sinopsis hay que ingresar al link de la pelicula y tomar los datos desde ahí

        pelicula = Pelicula(titulo, anio, sinopsis, link, duracion)
        peliculas.update(pelicula)

    print(f"Cantidad de peliculas encontradas: {len(set_elementos)}")

    browser.quit()

# Ejecucion
if __name__ == "__main__":
    scrapPeliculas()




