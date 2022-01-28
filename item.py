# Clases
class Item:
    def __init__(self, titulo, anio, sinopsis, link) -> None:
        self._titulo = titulo
        self._anio = anio
        self._sinopsis = sinopsis
        self._link = link

class Pelicula(Item):
    def __init__(self, titulo, anio, sinopsis, link, duracion, director) -> None:
        super().__init__(titulo, anio, sinopsis, link)
        self._duracion = duracion
        self._director = director

class Serie(Item):
    def __init__(self, titulo, anio, sinopsis, link, episodios) -> None:
        super().__init__(titulo, anio, sinopsis, link)
        self._episodios = episodios