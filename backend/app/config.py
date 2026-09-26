from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MVP - Sprint: Arquitetura de Software"
    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/windroute"
    database_host: str | None = None
    database_user: str = "windroute"
    database_password: str = ""
    database_name: str = "windroute"
    database_port: int = 3306
    frontend_origin: str = "http://localhost:5173"

    nominatim_url: str = "https://nominatim.openstreetmap.org"
    osrm_url: str = "https://router.project-osrm.org"
    external_api_user_agent: str = "WindRouteMVP/1.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
