# GEOREPOSITORIO

Dashboard personal para explorar repositorios detectados por MAGI//ARCHIVE y
organizarlos con una capa propia de curaduria.

## Uso local

```powershell
python scripts/fetch_magi.py
cd docs
python -m http.server 8080
```

Abrir `http://localhost:8080/`.

## Actualizacion

El workflow `.github/workflows/update-magi.yml` actualiza los datos todos los
dias y tambien puede ejecutarse manualmente desde GitHub Actions.

## Fuentes

- MAGI//ARCHIVE: https://tom-doerr.github.io/repo_posts/
- Repositorio fuente: https://github.com/tom-doerr/repo_posts

Este proyecto no copia imagenes ni textos extensos de MAGI//ARCHIVE. Usa
metadatos minimos, enlaces y enriquecimiento desde la API publica de GitHub.
