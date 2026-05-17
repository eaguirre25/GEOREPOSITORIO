# GEOREPOSITORIO

Dashboard personal para explorar repositorios detectados en varias fuentes y
organizarlos con una capa propia de curaduria.

## Uso local

```powershell
python scripts/fetch_sources.py
cd docs
python -m http.server 8080
```

Abrir `http://localhost:8080/`.

## Actualizacion

El workflow `.github/workflows/update-magi.yml` actualiza los datos todos los
lunes y tambien puede ejecutarse manualmente desde GitHub Actions.

## Fuentes

- MAGI//ARCHIVE: https://tom-doerr.github.io/repo_posts/
- GitHub topics/search y GitHub Trending
- Hugging Face Spaces
- Papers with Code
- Busquedas GitHub sobre escritura academica, revision bibliografica,
  gestion de citas y analisis cualitativo.

Este proyecto no copia imagenes ni textos extensos de terceros. Usa metadatos
minimos, enlaces y enriquecimiento desde APIs o paginas publicas.
