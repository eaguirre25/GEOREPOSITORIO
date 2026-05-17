#!/usr/bin/env python3
"""Build GEOREPOSITORIO as a multi-source repository radar."""
from __future__ import annotations

import csv
import html
import json
import os
import re
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"
OUT_JSON = DATA / "georepositorio.json"
OUT_CSV = DATA / "georepositorio.csv"
MAGI_JSON = DATA / "magi_repos.json"
MAGI_CSV = DATA / "magi_repos.csv"
WATCHLIST_JSON = DATA / "source_watchlist.json"

MAGI_INDEX_URL = "https://tom-doerr.github.io/repo_posts/assets/search-index.json"
GITHUB_API = "https://api.github.com"
HF_SPACES_API = "https://huggingface.co/api/spaces"
PWC_REPOS_API = "https://paperswithcode.com/api/v1/repositories/"

WATCH_SOURCES = [
    {
        "name": "DeepTechTR",
        "url": "https://x.com/DeepTechTR",
        "kind": "X / Twitter",
        "focus": "Deep tech, IA, investigación aplicada y repositorios emergentes.",
    },
    {
        "name": "R Markdown",
        "url": "https://x.com/rmarkdown",
        "kind": "X / Twitter",
        "focus": "Escritura académica reproducible con R Markdown, Quarto y documentos técnicos.",
    },
    {
        "name": "Estación R",
        "url": "https://x.com/estacion_erre",
        "kind": "X / Twitter",
        "focus": "R en español, análisis de datos, visualización y materiales de aprendizaje.",
    },
    {
        "name": "Google Maps Platform",
        "url": "https://x.com/GMapsPlatform",
        "kind": "X / Twitter",
        "focus": "APIs, herramientas y novedades para mapas, rutas y datos geoespaciales.",
    },
    {
        "name": "MappingGIS",
        "url": "https://x.com/MappingGIS",
        "kind": "X / Twitter",
        "focus": "GIS, cartografía, QGIS, teledetección y formación geoespacial.",
    },
    {
        "name": "Google Earth",
        "url": "https://x.com/googleearth",
        "kind": "X / Twitter",
        "focus": "Google Earth, exploración territorial, imágenes satelitales y recursos geográficos.",
    },
]

CURATED_PROFILE_REPOS = [
    # DeepTechTR difunde proyectos emergentes de IA/deep tech. Estos repos
    # se detectaron en menciones indexadas de su perfil y quedan como semilla
    # curada para que el radar los trate como una fuente propia.
    ("DeepTechTR", "microsoft", "TRELLIS", "Modelo abierto de Microsoft para generación 3D a partir de texto o imagen.", "LLM / GenAI", ["3d-generation", "computer-vision", "ai"]),
    ("DeepTechTR", "taracodlabs", "aiden", "Sistema local-first para operar herramientas de IA en Windows.", "AI agents", ["local-first", "ai-agents", "windows"]),
    # R Markdown / Posit: herramientas centrales de escritura reproducible.
    ("R Markdown", "rstudio", "rmarkdown", "Paquete R para crear documentos dinámicos y reproducibles.", "Academic writing", ["r", "rmarkdown", "reproducible-research"]),
    ("R Markdown", "yihui", "knitr", "Motor R para integrar código, resultados y texto en documentos reproducibles.", "Academic writing", ["r", "markdown", "latex"]),
    ("R Markdown", "rstudio", "bookdown", "Herramientas para escribir libros, tesis y documentos largos con R Markdown.", "Academic writing", ["r", "book", "writing"]),
    ("R Markdown", "rstudio", "blogdown", "Publicación de sitios y blogs reproducibles desde R Markdown.", "Academic writing", ["r", "blog", "hugo"]),
    ("R Markdown", "rstudio", "flexdashboard", "Creación de dashboards con R Markdown.", "Dashboard / UI", ["r", "dashboard", "rmarkdown"]),
    ("R Markdown", "quarto-dev", "quarto-cli", "Sistema de publicación científica y técnica para documentos, libros, sitios y presentaciones.", "Academic writing", ["quarto", "markdown", "publishing"]),
    # Estacion R comparte recursos en español para aprender y trabajar con R.
    ("Estación R", "jfulponi", "istatR", "Paquete R para consultar datos abiertos del instituto estadístico italiano ISTAT.", "Data / ETL", ["r", "open-data", "statistics"]),
    # Google Maps Platform: librerias y muestras oficiales.
    ("Google Maps Platform", "googlemaps", "google-maps-services-python", "Cliente Python para servicios web de Google Maps Platform.", "Geospatial", ["google-maps", "python", "geocoding"]),
    ("Google Maps Platform", "googlemaps", "google-maps-services-js", "Cliente Node.js/TypeScript para servicios web de Google Maps Platform.", "Geospatial", ["google-maps", "typescript", "geocoding"]),
    ("Google Maps Platform", "googlemaps", "android-maps-compose", "Componentes Jetpack Compose para integrar Google Maps en Android.", "Geospatial", ["android", "maps", "compose"]),
    ("Google Maps Platform", "googlemaps", "js-api-loader", "Carga dinámica de la API JavaScript de Google Maps.", "Geospatial", ["javascript", "google-maps", "loader"]),
    ("Google Maps Platform", "googlemaps", "js-markerclusterer", "Agrupamiento de marcadores para mapas con muchos puntos.", "Geospatial", ["javascript", "marker-clustering", "maps"]),
    ("Google Maps Platform", "googlemaps", "extended-component-library", "Web Components para construir experiencias con Google Maps Platform.", "Geospatial", ["web-components", "google-maps", "places"]),
    ("Google Maps Platform", "googlemaps-samples", "js-samples", "Muestras oficiales para la API JavaScript de Google Maps.", "Geospatial", ["samples", "javascript", "maps"]),
    # MappingGIS suele curar herramientas QGIS/GIS abiertas.
    ("MappingGIS", "qgis", "QGIS", "Sistema de información geográfica libre y multiplataforma.", "Geospatial", ["qgis", "gis", "maps"]),
    ("MappingGIS", "qgis", "QGIS-Documentation", "Documentación oficial de QGIS.", "Geospatial", ["qgis", "documentation", "gis"]),
    ("MappingGIS", "qgis", "qwc2", "Cliente web para publicar proyectos QGIS en la web.", "Geospatial", ["qgis", "web-map", "gis"]),
    ("MappingGIS", "nextgis", "quickmapservices", "Plugin QGIS para agregar capas base de servicios como Google, ESRI y OpenStreetMap.", "Geospatial", ["qgis", "plugin", "basemaps"]),
    # Google Earth / Earth Engine.
    ("Google Earth", "google", "earthengine-api", "Biblioteca cliente en Python y JavaScript para usar Google Earth Engine.", "Geospatial", ["earth-engine", "remote-sensing", "python"]),
    ("Google Earth", "gee-community", "geemap", "Herramienta Python para análisis interactivo con Google Earth Engine.", "Geospatial", ["earth-engine", "python", "mapping"]),
    ("Google Earth", "opengeos", "Awesome-GEE", "Lista curada de recursos para Google Earth Engine.", "Geospatial", ["earth-engine", "awesome-list", "remote-sensing"]),
]

X_HANDLES = {
    "DeepTechTR": "DeepTechTR",
    "R Markdown": "rmarkdown",
    "Estación R": "estacion_erre",
    "Google Maps Platform": "GMapsPlatform",
    "MappingGIS": "MappingGIS",
    "Google Earth": "googleearth",
}

TOPIC_QUERIES = [
    "geospatial", "gis", "remote-sensing", "qgis", "leaflet", "deckgl",
    "dashboard", "data-visualization", "open-data", "scraper",
    "llm", "rag", "ai-agents", "mcp", "vector-database",
    "academic-research", "bibliometrics",
    "academic-writing", "scientific-writing", "research-writing",
    "literature-review", "citation-management", "zotero", "latex",
    "markdown", "qualitative-analysis", "qualitative-research",
    "text-analysis", "coding", "qda", "discourse-analysis",
]

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Academic writing", ["academic writing", "scientific writing", "research writing", "citation", "zotero", "latex", "literature review", "paper writing", "manuscript", "markdown"]),
    ("Qualitative analysis", ["qualitative", "qda", "text analysis", "discourse", "coding", "thematic analysis", "interview", "transcription", "annotation"]),
    ("AI agents", ["agent", "agents", "autonomous", "multi-agent", "mcp", "tool-use"]),
    ("LLM / GenAI", ["llm", "gpt", "rag", "embedding", "diffusion", "whisper", "transformer", "prompt"]),
    ("Geospatial", ["geo", "gis", "map", "maps", "satellite", "lidar", "drone", "terrain", "qgis", "leaflet", "deckgl"]),
    ("Data / ETL", ["data", "database", "warehouse", "etl", "pipeline", "postgres", "vector", "scraper", "crawler"]),
    ("Research", ["research", "paper", "academic", "benchmark", "modeling", "simulation", "bibliometric"]),
    ("Security", ["security", "forensic", "pentest", "vulnerability", "malware", "audit"]),
    ("Dashboard / UI", ["dashboard", "visualiz", "viewer", "web ui", "interface", "frontend", "chart"]),
    ("Dev tools", ["cli", "editor", "developer", "code", "git", "terminal", "server"]),
]

SPANISH_PATTERNS: list[tuple[str, str]] = [
    (r"\bopen[- ]source\b", "herramienta de código abierto"),
    (r"\bdashboard\b", "panel de control"),
    (r"\bvisualization\b|\bvisualisation\b", "visualización de datos"),
    (r"\bdata\b", "datos"),
    (r"\bscraper\b|\bcrawler\b", "recolección automatizada"),
    (r"\bllm\b|\bgpt\b|\brag\b", "modelos de lenguaje e IA generativa"),
    (r"\bagent\b|\bagents\b", "agentes de IA"),
    (r"\bgeospatial\b|\bgis\b|\bmap\b|\bmaps\b", "información geoespacial y mapas"),
    (r"\bacademic writing\b|\bscientific writing\b|\bresearch writing\b", "escritura académica"),
    (r"\bliterature review\b", "revisión bibliográfica"),
    (r"\bcitation\b|\bzotero\b|\bbibtex\b", "gestión de citas y bibliografía"),
    (r"\bqualitative\b|\bqda\b|\bthematic analysis\b", "análisis cualitativo"),
    (r"\btext analysis\b|\bdiscourse\b", "análisis de textos y discurso"),
    (r"\btranscription\b|\binterview\b", "trabajo con entrevistas y transcripciones"),
]

SPECIFIC_SPANISH_RULES: list[tuple[str, str]] = [
    (r"photo.*video|video.*photo|google photos", "Gestiona fotos y videos en un servidor propio o en una app especializada."),
    (r"documentation sites?.*markdown|markdown.*documentation", "Genera sitios de documentación a partir de archivos Markdown."),
    (r"dynamic documents?|r markdown", "Crea documentos dinámicos y reproducibles combinando texto, código y resultados."),
    (r"book|thesis|manuscript", "Ayuda a escribir y publicar libros, tesis o documentos académicos extensos."),
    (r"citation|citations|bibliography|zotero|bibtex", "Ayuda a gestionar citas, bibliografía y escritura académica reproducible."),
    (r"literature review", "Apoya revisiones bibliográficas y organización de literatura académica."),
    (r"qualitative|qda|thematic analysis|interview|transcription", "Sirve para organizar, codificar o analizar materiales cualitativos."),
    (r"geospatial analysis|gis|qgis|spatial data", "Permite visualizar, gestionar o analizar datos geoespaciales."),
    (r"google maps|maps sdk|marker cluster|geocoding|routes?", "Facilita integrar mapas, geocodificación, rutas o marcadores con Google Maps."),
    (r"earth engine|satellite|remote sensing", "Permite trabajar con Google Earth Engine, imágenes satelitales o análisis territorial."),
    (r"dashboard|leaderboard", "Construye o muestra paneles de control para comparar resultados, métricas o modelos."),
    (r"llm|large language model|rag|embedding|prompt", "Trabaja con modelos de lenguaje, recuperación aumentada o flujos de IA generativa."),
    (r"agent|agents|autonomous", "Permite crear o ejecutar agentes de IA con herramientas y flujos automatizados."),
    (r"scraper|crawler|extract", "Extrae datos de sitios o fuentes públicas mediante recolección automatizada."),
    (r"api client|client library|bindings", "Ofrece una biblioteca cliente para conectarse a una API desde código."),
    (r"web components?", "Ofrece componentes web reutilizables para construir interfaces."),
    (r"command line|cli|terminal", "Agrega herramientas de línea de comandos para automatizar tareas de desarrollo."),
    (r"database|postgres|redis|vector search|indexing", "Gestiona, indexa o consulta datos en bases de datos y motores de búsqueda."),
    (r"visualization|visualisation|chart|plot", "Crea visualizaciones para explorar datos y comunicar resultados."),
    (r"open data|dataset|statistics", "Facilita acceder, descargar o procesar datos abiertos y estadísticos."),
    (r"3d|three|gaussian|mesh", "Genera, procesa o visualiza recursos 3D."),
]

CATEGORY_FALLBACKS = {
    "Academic writing": "Ayuda a producir, organizar o publicar escritura académica reproducible.",
    "Qualitative analysis": "Ayuda a organizar, codificar o analizar materiales cualitativos.",
    "AI agents": "Permite crear o ejecutar agentes de IA con herramientas conectadas.",
    "LLM / GenAI": "Trabaja con modelos de lenguaje, prompts, embeddings o generación de contenido.",
    "Geospatial": "Permite trabajar con mapas, GIS, datos espaciales o análisis territorial.",
    "Data / ETL": "Ayuda a extraer, transformar, consultar o organizar datos.",
    "Research": "Apoya investigación, experimentación, evaluación o revisión de literatura.",
    "Security": "Sirve para auditoría, análisis o protección de sistemas.",
    "Dashboard / UI": "Permite construir interfaces o paneles para explorar información.",
    "Dev tools": "Agrega herramientas para programar, automatizar o mantener proyectos.",
}


def insecure_ssl() -> bool:
    return os.getenv("GEOREPOSITORIO_INSECURE_SSL", "").strip().lower() in {"1", "true", "yes", "si"}


def request_text(url: str, token: str = "", accept: str = "*/*") -> str:
    headers = {"User-Agent": "georepositorio/1.0", "Accept": accept}
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    context = ssl._create_unverified_context() if insecure_ssl() else None
    with urlopen(Request(url, headers=headers), timeout=35, context=context) as resp:
        return resp.read().decode("utf-8", errors="replace")


def request_json(url: str, token: str = "") -> Any:
    return json.loads(request_text(url, token=token, accept="application/json"))


def clean_title(value: str) -> str:
    return re.sub(r"^\[([^\]]+)\]\([^)]+\)$", r"\1", value or "").strip()


def extract_repo(value: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/\]\)]+)/([^/\]\)#\s]+)", value or "", re.I)
    if match:
        return match.group(1), match.group(2).replace(".git", "")
    plain = clean_title(value)
    if "/" in plain and not plain.startswith("20"):
        owner, repo = plain.split("/", 1)
        return owner.strip(), repo.strip()
    return "", ""


def classify(row: dict[str, Any]) -> str:
    haystack = " ".join([
        str(row.get("repo", "")),
        str(row.get("description", "")),
        str(row.get("language", "")),
        " ".join(row.get("topics") or []),
    ]).casefold()
    for category, terms in CATEGORY_RULES:
        if any(term in haystack for term in terms):
            return category
    return "Other"


def looks_spanish(value: str) -> bool:
    text = value.casefold()
    markers = [" para ", " con ", " datos ", " herramienta ", " permite ", " sistema ", " análisis ", " código "]
    return any(marker in text for marker in markers) or any(ch in text for ch in "áéíóúñ")


def polish_sentence(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip(" .")
    if not text:
        return ""
    return text[0].upper() + text[1:] + "."


def spanish_brief(row: dict[str, Any]) -> str:
    description = str(row.get("description") or "").strip()
    if description and looks_spanish(description):
        return polish_sentence(description)

    text = " ".join([
        str(row.get("repo", "")),
        description,
        str(row.get("category", "")),
        " ".join(row.get("topics") or []),
    ]).casefold()

    for pattern, sentence in SPECIFIC_SPANISH_RULES:
        if re.search(pattern, text):
            return sentence

    hits: list[str] = []
    for pattern, phrase in SPANISH_PATTERNS:
        if re.search(pattern, text) and phrase not in hits:
            hits.append(phrase)
    if hits:
        return "Sirve para trabajar con " + ", ".join(hits[:3]) + "."

    category = str(row.get("category") or "Other")
    if category in CATEGORY_FALLBACKS:
        return CATEGORY_FALLBACKS[category]
    if description:
        return "Repositorio para revisar: " + polish_sentence(description).lower()
    return "Repositorio para explorar y clasificar manualmente."


def github_repo(owner: str, repo: str, token: str) -> dict[str, Any]:
    if not owner or not repo:
        return {}
    try:
        data = request_json(f"{GITHUB_API}/repos/{owner}/{repo}", token=token)
        time.sleep(0.08 if token else 0.5)
        return data if isinstance(data, dict) else {}
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {}


def row_from_github(gh: dict[str, Any], source: str, discovered_at: str = "", source_url: str = "") -> dict[str, Any]:
    owner = gh.get("owner") if isinstance(gh.get("owner"), dict) else {}
    license_info = gh.get("license") if isinstance(gh.get("license"), dict) else {}
    row = {
        "id": f"github:{gh.get('full_name') or gh.get('html_url')}",
        "source": source,
        "repo": gh.get("full_name") or "",
        "owner": owner.get("login") or "",
        "name": gh.get("name") or "",
        "description": gh.get("description") or "",
        "category": "",
        "language": gh.get("language") or "",
        "stars": int(gh.get("stargazers_count") or 0),
        "forks": int(gh.get("forks_count") or 0),
        "open_issues": int(gh.get("open_issues_count") or 0),
        "license": license_info.get("spdx_id") or "",
        "topics": gh.get("topics") or [],
        "created_at": gh.get("created_at") or "",
        "updated_at": gh.get("updated_at") or "",
        "pushed_at": gh.get("pushed_at") or "",
        "discovered_at": discovered_at,
        "source_url": source_url,
        "github_url": gh.get("html_url") or "",
        "avatar_url": owner.get("avatar_url") or "",
    }
    row["category"] = classify(row)
    row["descripcion_es"] = spanish_brief(row)
    row["score"] = int(row["stars"]) + int(row["forks"]) * 3
    return row


def fetch_magi(token: str, limit: int) -> list[dict[str, Any]]:
    raw = request_json(MAGI_INDEX_URL)
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw[-limit:][::-1]:
        owner, repo = extract_repo(str(item.get("title", "")))
        key = f"{owner}/{repo}".casefold() if owner and repo else str(item.get("u", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        gh = github_repo(owner, repo, token)
        if gh:
            row = row_from_github(
                gh,
                source="MAGI//ARCHIVE",
                discovered_at=str(item.get("d") or ""),
                source_url="https://tom-doerr.github.io/repo_posts" + str(item.get("u") or ""),
            )
        else:
            repo_full = f"{owner}/{repo}" if owner and repo else clean_title(str(item.get("title", "")))
            row = {
                "id": f"magi:{repo_full}",
                "source": "MAGI//ARCHIVE",
                "repo": repo_full,
                "owner": owner,
                "name": repo,
                "description": str(item.get("s") or ""),
                "category": "Other",
                "language": "",
                "stars": 0,
                "forks": 0,
                "open_issues": 0,
                "license": "",
                "topics": [],
                "created_at": "",
                "updated_at": "",
                "pushed_at": "",
                "discovered_at": str(item.get("d") or ""),
                "source_url": "https://tom-doerr.github.io/repo_posts" + str(item.get("u") or ""),
                "github_url": f"https://github.com/{repo_full}" if "/" in repo_full else "",
                "avatar_url": "",
                "score": 0,
            }
            row["category"] = classify(row)
            row["descripcion_es"] = spanish_brief(row)
        rows.append(row)
    return rows


def fetch_github_topics(token: str, per_topic: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for topic in TOPIC_QUERIES:
        query = f"topic:{topic} stars:>20 archived:false"
        params = urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": str(per_topic)})
        try:
            data = request_json(f"{GITHUB_API}/search/repositories?{params}", token=token)
            for item in data.get("items", []) if isinstance(data, dict) else []:
                if isinstance(item, dict):
                    rows.append(row_from_github(item, source=f"GitHub topic:{topic}", source_url=f"https://github.com/topics/{topic}"))
            time.sleep(0.2 if token else 1.0)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            continue
    return rows


def fallback_curated_row(profile: str, owner: str, repo: str, description: str, category: str, topics: list[str]) -> dict[str, Any]:
    full = f"{owner}/{repo}"
    row = {
        "id": f"x-curated:{full}",
        "source": f"X curado:{profile}",
        "repo": full,
        "owner": owner,
        "name": repo,
        "description": description,
        "category": category,
        "language": "",
        "stars": 0,
        "forks": 0,
        "open_issues": 0,
        "license": "",
        "topics": topics,
        "created_at": "",
        "updated_at": "",
        "pushed_at": "",
        "discovered_at": datetime.now(timezone.utc).date().isoformat(),
        "source_url": f"https://x.com/{X_HANDLES.get(profile, profile.replace(' ', ''))}",
        "github_url": f"https://github.com/{full}",
        "avatar_url": "",
        "score": 0,
    }
    row["descripcion_es"] = spanish_brief(row)
    return row


def fetch_curated_profile_repos(token: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile, owner, repo, description, category, topics in CURATED_PROFILE_REPOS:
        gh = github_repo(owner, repo, token)
        if gh:
            row = row_from_github(
                gh,
                source=f"X curado:{profile}",
                source_url=f"https://github.com/{owner}/{repo}",
            )
            github_description = str(row.get("description") or "").strip().casefold()
            weak_description = not github_description or len(github_description) < 24 or github_description in {repo.casefold(), f"{owner}/{repo}".casefold()}
            if weak_description:
                row["description"] = description
                row["category"] = category
                row["topics"] = list(dict.fromkeys(topics + (row.get("topics") or [])))[:16]
                row["descripcion_es"] = spanish_brief(row)
            rows.append(row)
        else:
            rows.append(fallback_curated_row(profile, owner, repo, description, category, topics))
    return rows


def fetch_github_trending() -> list[dict[str, Any]]:
    url = "https://github.com/trending?since=weekly"
    text = request_text(url, accept="text/html")
    rows: list[dict[str, Any]] = []
    for owner, repo in re.findall(r'href="/([^/\s"]+)/([^/\s"]+)"\s+data-hydro-click', text):
        if owner in {"features", "topics", "collections", "events"}:
            continue
        full = f"{html.unescape(owner)}/{html.unescape(repo)}"
        rows.append({
            "id": f"trending:{full}",
            "source": "GitHub Trending",
            "repo": full,
            "owner": owner,
            "name": repo,
            "description": "",
            "category": "Other",
            "language": "",
            "stars": 0,
            "forks": 0,
            "open_issues": 0,
            "license": "",
            "topics": [],
            "created_at": "",
            "updated_at": "",
            "pushed_at": "",
            "discovered_at": datetime.now(timezone.utc).date().isoformat(),
            "source_url": url,
            "github_url": f"https://github.com/{full}",
            "avatar_url": "",
            "score": 0,
        })
    return rows[:50]


def fetch_hf_spaces(limit: int) -> list[dict[str, Any]]:
    params = urlencode({"sort": "likes", "direction": "-1", "limit": str(limit), "full": "true"})
    data = request_json(f"{HF_SPACES_API}?{params}")
    rows: list[dict[str, Any]] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        repo = item.get("id") or item.get("name") or ""
        likes = int(item.get("likes") or 0)
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        row = {
            "id": f"hf:{repo}",
            "source": "Hugging Face Spaces",
            "repo": repo,
            "owner": str(repo).split("/")[0] if "/" in str(repo) else "",
            "name": str(repo).split("/")[-1],
            "description": item.get("cardData", {}).get("title") if isinstance(item.get("cardData"), dict) else "",
            "category": "",
            "language": item.get("sdk") or "",
            "stars": likes,
            "forks": 0,
            "open_issues": 0,
            "license": item.get("license") or "",
            "topics": tags[:12],
            "created_at": item.get("createdAt") or "",
            "updated_at": item.get("lastModified") or "",
            "pushed_at": item.get("lastModified") or "",
            "discovered_at": datetime.now(timezone.utc).date().isoformat(),
            "source_url": "https://huggingface.co/spaces",
            "github_url": f"https://huggingface.co/spaces/{repo}",
            "avatar_url": "",
            "score": likes,
        }
        row["category"] = classify(row)
        row["descripcion_es"] = spanish_brief(row)
        rows.append(row)
    return rows


def fetch_paperswithcode(limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    url = f"{PWC_REPOS_API}?page=1"
    data = request_json(url)
    for item in data.get("results", [])[:limit] if isinstance(data, dict) else []:
        if not isinstance(item, dict):
            continue
        repo_url = item.get("url") or ""
        owner, repo = extract_repo(repo_url)
        full = f"{owner}/{repo}" if owner and repo else repo_url
        row = {
            "id": f"pwc:{full}",
            "source": "Papers with Code",
            "repo": full,
            "owner": owner,
            "name": repo,
            "description": item.get("description") or item.get("name") or "",
            "descripcion_es": "",
            "category": "Research",
            "language": "",
            "stars": int(item.get("stars") or 0),
            "forks": 0,
            "open_issues": 0,
            "license": "",
            "topics": ["papers-with-code"],
            "created_at": "",
            "updated_at": item.get("updated") or "",
            "pushed_at": "",
            "discovered_at": datetime.now(timezone.utc).date().isoformat(),
            "source_url": "https://paperswithcode.com/",
            "github_url": repo_url,
            "avatar_url": "",
            "score": int(item.get("stars") or 0),
        }
        row["descripcion_es"] = spanish_brief(row)
        rows.append(row)
    return rows


def merge_rows(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for rows in groups:
        for row in rows:
            key = str(row.get("github_url") or row.get("repo") or row.get("id")).casefold()
            if key not in merged:
                row["sources"] = [row.get("source", "")]
                merged[key] = row
                continue
            current = merged[key]
            src = row.get("source", "")
            if src and src not in current["sources"]:
                current["sources"].append(src)
            for field in ["description", "language", "license", "avatar_url", "created_at", "updated_at", "pushed_at"]:
                if not current.get(field) and row.get(field):
                    current[field] = row[field]
            current["stars"] = max(int(current.get("stars") or 0), int(row.get("stars") or 0))
            current["forks"] = max(int(current.get("forks") or 0), int(row.get("forks") or 0))
            current["score"] = max(int(current.get("score") or 0), int(row.get("score") or 0))
            topics = list(dict.fromkeys((current.get("topics") or []) + (row.get("topics") or [])))
            current["topics"] = topics[:16]
            current["source"] = " + ".join(current["sources"])
            current["category"] = classify(current)
            current["descripcion_es"] = spanish_brief(current)
    rows = list(merged.values())
    rows.sort(key=lambda r: (int(r.get("score") or 0), str(r.get("updated_at") or r.get("discovered_at") or "")), reverse=True)
    return rows


def write_outputs(rows: list[dict[str, Any]], source_counts: dict[str, int], errors: dict[str, str]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "source_counts": source_counts,
        "source_errors": errors,
        "watch_sources": WATCH_SOURCES,
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    MAGI_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    WATCHLIST_JSON.write_text(json.dumps({
        "generated_at": payload["generated_at"],
        "count": len(WATCH_SOURCES),
        "sources": WATCH_SOURCES,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = [
        "repo", "source", "description", "category", "language", "stars", "forks",
        "descripcion_es",
        "open_issues", "license", "topics", "created_at", "updated_at", "pushed_at",
        "discovered_at", "source_url", "github_url", "score",
    ]
    for path in [OUT_CSV, MAGI_CSV]:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                out = dict(row)
                out["topics"] = "; ".join(out.get("topics") or [])
                writer.writerow({field: out.get(field, "") for field in fields})


def guarded(name: str, fn, errors: dict[str, str]) -> list[dict[str, Any]]:
    try:
        rows = fn()
        print(f"{name}: {len(rows)}")
        return rows
    except Exception as exc:
        errors[name] = str(exc)
        print(f"{name}: ERROR {exc}")
        return []


def main() -> None:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    magi_limit = int(os.getenv("MAGI_LIMIT", "250"))
    topic_limit = int(os.getenv("GITHUB_TOPIC_LIMIT", "12"))
    hf_limit = int(os.getenv("HF_SPACES_LIMIT", "80"))
    pwc_limit = int(os.getenv("PWC_LIMIT", "60"))
    errors: dict[str, str] = {}
    groups = [
        guarded("MAGI//ARCHIVE", lambda: fetch_magi(token, magi_limit), errors),
        guarded("GitHub topics", lambda: fetch_github_topics(token, topic_limit), errors),
        guarded("X curated profile repos", lambda: fetch_curated_profile_repos(token), errors),
        guarded("GitHub Trending", fetch_github_trending, errors),
        guarded("Hugging Face Spaces", lambda: fetch_hf_spaces(hf_limit), errors),
        guarded("Papers with Code", lambda: fetch_paperswithcode(pwc_limit), errors),
    ]
    source_counts = {
        "MAGI//ARCHIVE": len(groups[0]),
        "GitHub topics": len(groups[1]),
        "X curated profile repos": len(groups[2]),
        "GitHub Trending": len(groups[3]),
        "Hugging Face Spaces": len(groups[4]),
        "Papers with Code": len(groups[5]),
    }
    rows = merge_rows(groups)
    write_outputs(rows, source_counts, errors)
    print(f"Wrote {OUT_JSON} with {len(rows)} repositories")


if __name__ == "__main__":
    main()
