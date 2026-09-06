from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from . import database, models
from backend.config import CORS_ORIGINS
import random
import re
import html as html_mod
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Importaciones de los routers
from backend.modulos.auth import router as auth_router
from backend.modulos.usuarios import router as usuarios_router
from backend.modulos.notificaciones import router as notificaciones_router
from backend.modulos.auditoria import router as auditoria_router
from backend.modulos.chat import router as chat_router
from backend.modulos.recursos_humanos import router as rrhh_router
from backend.modulos.patrimonio import router as patrimonio_router
from backend.modulos.sistemas import router as sistemas_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de Routers (API Endpoints)
app.include_router(auth_router.router, tags=["Autenticación"])
app.include_router(usuarios_router.router, tags=["Usuarios y Admin"])
app.include_router(notificaciones_router.router, tags=["Notificaciones"])
app.include_router(auditoria_router.router, tags=["Auditoría"])
app.include_router(chat_router.router, tags=["Chat"])
app.include_router(rrhh_router.router, tags=["Recursos Humanos"])
# Inclusión del nuevo Router de Patrimonio
app.include_router(patrimonio_router.router, tags=["Patrimonio"])
app.include_router(sistemas_router.router, tags=["Sistemas"])


# --------------------------------------------------
# RUTAS DEL FRONTEND (HTML)
# --------------------------------------------------
@app.get("/")
def serve_index(): return FileResponse("frontend/vistas/index.html")

@app.get("/login")
def serve_login(): return FileResponse("frontend/vistas/login.html")

@app.get("/registro")
def serve_registro(): return FileResponse("frontend/vistas/registro.html")

@app.get("/recuperar")
def serve_recuperar(): return FileResponse("frontend/vistas/recuperar.html")

@app.get("/restablecer")
def serve_restablecer(): return FileResponse("frontend/vistas/usuarios/restablecer.html")

@app.get("/favicon.ico", include_in_schema=False)
def favicon(): return Response(content="", media_type="image/x-icon")

@app.get("/usuarios")
def serve_usuarios(): return FileResponse("frontend/vistas/usuarios/usuarios.html")

@app.get("/editor-mapa")
def serve_editor_mapa(): 
    # Asegúrate de que la ruta coincida con donde guardaste el archivo HTML
    return FileResponse("frontend/vistas/usuarios/editor_mapa.html")

@app.get("/sistemas")
async def leer_sistemas():
    return FileResponse("frontend/vistas/sistemas/sistemas.html")

@app.get("/mapa")
def serve_mapa(): 
    return FileResponse("frontend/vistas/usuarios/mapa_vista.html")

@app.get("/auditoria")
def serve_auditoria(): return FileResponse("frontend/vistas/auditoria.html")

@app.get("/perfil")
def serve_perfil(): return FileResponse("frontend/vistas/perfil.html")

@app.get("/notificaciones")
def serve_notificaciones(): return FileResponse("frontend/vistas/notificaciones.html")

@app.get("/control-fichadas")
def serve_control_fichadas(): return FileResponse("frontend/vistas/control_fichadas.html")

# --------------------------------------------------
# RUTAS DEL FRONTEND - MÓDULO PATRIMONIO
# --------------------------------------------------
@app.get("/patrimonio-vista")
def serve_patrimonio(): return FileResponse("frontend/vistas/patrimonio/patrimonio_vista.html")

@app.get("/patrimonio-nuevo")
def serve_patrimonio_nuevo(): return FileResponse("frontend/vistas/patrimonio/patrimonio_nuevo.html")

@app.get("/patrimonio-editar")
def serve_patrimonio_editar(): return FileResponse("frontend/vistas/patrimonio/patrimonio_editar.html")

@app.get("/patrimonio-conceptos")
def serve_patrimonio_conceptos(): return FileResponse("frontend/vistas/patrimonio_conceptos.html")

@app.get("/patrimonio-historial-vista")
def serve_patrimonio_historial(): return FileResponse("frontend/vistas/patrimonio/patrimonio_historial.html")

@app.get("/patrimonio-informatica", include_in_schema=False)
def vista_informatica():
    # Asegúrate de ajustar la ruta si usas otra carpeta
    return FileResponse("frontend/vistas/patrimonio/patrimonio_informatica.html")

@app.get("/patrimonio-imprimir", include_in_schema=False)
def vista_imprimir_etiquetas():
    # Asegúrate de que la ruta apunte a la carpeta correcta donde guardaste el HTML
    # Por ejemplo, si está en una carpeta "frontend" o "templates":
    return FileResponse("frontend/vistas/patrimonio/patrimonio_imprimir.html")

@app.get("/patrimonio-importar")
def serve_patrimonio_importar(): return FileResponse("frontend/vistas/patrimonio/patrimonio_importar.html")

@app.get("/patrimonio-codigos")
def serve_patrimonio_codigos(): return FileResponse("frontend/vistas/patrimonio/atrimonio_codigos.html")

@app.get("/patrimonio-reportes")
def serve_patrimonio_reportes(): return FileResponse("frontend/vistas/patrimonio/patrimonio_reportes.html")

@app.get("/consulta-asignaciones")
def serve_consulta_asignaciones(): return FileResponse("frontend/vistas/patrimonio/consulta_asignaciones.html")


# --------------------------------------------------
# RSS PROXY (noticias con imágenes estilo MSN, fuente random)
# Solo categorías: Mundo, Fútbol y Economía (sin chimentos)
# --------------------------------------------------
RSS_FUENTES = [
    # Mundo
    {"nombre": "Clarín", "categoria": "Mundo", "url": "https://www.clarin.com/rss/mundo/", "imagen": "enclosure"},
    {"nombre": "La Nación", "categoria": "Mundo", "url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/el-mundo/?outputType=xml", "imagen": "media:content"},
    # Fútbol
    {"nombre": "Clarín", "categoria": "Fútbol", "url": "https://www.clarin.com/rss/deportes/futbol/", "imagen": "enclosure"},
    {"nombre": "La Nación", "categoria": "Fútbol", "url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/deportes/futbol/?outputType=xml", "imagen": "media:content"},
    # Economía
    {"nombre": "Clarín", "categoria": "Economía", "url": "https://www.clarin.com/rss/economia/", "imagen": "enclosure"},
    {"nombre": "La Nación", "categoria": "Economía", "url": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml", "imagen": "media:content"},
]

NS = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

# Caché simple en memoria para el proxy RSS (evita golpear las fuentes en cada request)
# Clave: url de la fuente. Valor: (timestamp_almacenado, dict_respuesta)
_RSS_CACHE_TTL = timedelta(minutes=5)
_rss_cache: dict = {}


def limpiar_html(texto):
    """Elimina etiquetas HTML y decodifica entidades."""
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", "", texto)
    return html_mod.unescape(texto).strip()


def extraer_imagen(item, tipo):
    """Extrae la URL de la imagen según el formato de la fuente."""
    if tipo == "enclosure":
        enc = item.find("enclosure")
        if enc is not None and enc.get("url"):
            return enc.get("url")
    else:  # media:content
        mc = item.find("media:content", NS)
        if mc is not None and mc.get("url"):
            return mc.get("url")
    return None


@app.get("/api/rss")
async def proxy_rss():
    fuente = random.choice(RSS_FUENTES)
    rss_url = fuente["url"]

    # Caché: si la fuente ya se pidió hace menos de 5 min, reutilizar
    ahora = datetime.now()
    cacheado = _rss_cache.get(rss_url)
    if cacheado and (ahora - cacheado[0]) < _RSS_CACHE_TTL:
        return cacheado[1]

    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read().decode("utf-8", "ignore")

        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "") or ""
            link = item.findtext("link", "") or ""
            description = item.findtext("description", "") or ""
            image = extraer_imagen(item, fuente["imagen"])
            items.append({
                "title": title,
                "link": link,
                "description": limpiar_html(description)[:180],
                "image": image,
            })
        resultado = {"fuente": fuente["nombre"], "categoria": fuente["categoria"], "items": items[:10]}
        _rss_cache[rss_url] = (ahora, resultado)
        return resultado
    except Exception as e:
        # Si tenemos caché vieja (aunque haya expirado), usarla como respaldo
        if cacheado and cacheado[1].get("items"):
            return cacheado[1]
        return {"fuente": fuente["nombre"], "categoria": fuente["categoria"], "items": [], "error": str(e)}

# Servir archivos estáticos (CSS, JS, Imágenes)
app.mount("/archivos", StaticFiles(directory="frontend"), name="frontend")