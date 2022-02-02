# Clases
class Item:
    def __init__(self):
        pass
    
    # Métodos Getters
    def setTitulo(self, titulo) -> None:
        assert(type(titulo) == str)
        self._titulo = titulo
    def setAnio(self, anio) -> None:
        assert(type(anio) == int)
        self._anio = anio
    def setSinopsis(self, sinopsis) -> None:
        assert(type(sinopsis) == str)
        self._sinopsis = sinopsis
    def setLink(self, link) -> None:
        assert(type(link) == str)
        self._link = link
    
    # Getters
    def getTitulo(self) -> str:
        return self._titulo
    def getAnio(self) -> int:
        return self._anio
    def getSinopsis(self) -> str:
        return self._sinopsis    
    def getLink(self) -> str:
        return self._link        


class Pelicula(Item):
    def __init__(self):
        super().__init__()
        pass

    # Setters
    def setDirector(self, director) -> None:
        assert(type(director) == str)
        self._director = director

    def setDuracion(self, duracion) -> None:
        assert(type(duracion) == int)
        self._duracion = duracion
    
    # Getters
    def getDirector(self) -> str:
        return self._director
    
    def getDuracion(self) -> int:
        return self._duracion


class Serie(Item):
    def __init__(self):
        super().__init__()
        pass

    def setAnio(self, anio) -> None: 
    # El atributo año en series es distinto, porque se trata de un diccionario con la estructura:
    # {desde , hasta}
    # por eso reemplazo el comportamiento del método
        assert(type(anio) == dict)
        self._anio = anio

    # Setters
    def setEpisodios(self, episodios) -> None:
        assert(type(episodios) == dict)
        self._episodios = episodios

    # Getters
    def getEpisodios(self) -> dict:
        return self._episodios