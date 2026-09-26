from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware



from .config import settings

from .database import Base, engine

from .routers import clientes, empresa, entregas, rotas



from .migrations import ensure_avulsa_schema, ensure_route_geometry_schema



Base.metadata.create_all(bind=engine)

ensure_avulsa_schema(engine)
ensure_route_geometry_schema(engine)



app = FastAPI(

    title=settings.app_name,

    description=(

        "API do MVP - Sprint: Arquitetura de Software. Integra dados internos com "

        "serviços externos baseados em OpenStreetMap."

    ),

    version="1.0.0",

)



app.add_middleware(

    CORSMiddleware,

    allow_origins=[settings.frontend_origin],

    allow_origin_regex=r"https?://localhost(?::\d+)?$",

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)



app.include_router(clientes.router)

app.include_router(empresa.router)

app.include_router(entregas.router)

app.include_router(rotas.router)





@app.get("/api/health", tags=["Sistema"])

def health():

    return {

        "status": "ok",

        "app": settings.app_name,

        "external_maps": "OpenStreetMap / Nominatim / OSRM",

    }

