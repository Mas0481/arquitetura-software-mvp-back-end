"""Small, idempotent migration for existing MySQL installations."""
from sqlalchemy import inspect, text


def ensure_avulsa_schema(engine):
    if engine.dialect.name != "mysql":
        return
    with engine.begin() as connection:
        columns = {column["name"]: column for column in inspect(connection).get_columns("entregas")}
        for name in ("cliente_id", "endereco_id"):
            if not columns[name]["nullable"]:
                # Fixed identifiers only. Existing rows and foreign keys are preserved.
                connection.execute(text(f"ALTER TABLE entregas MODIFY COLUMN {name} INTEGER NULL"))



def ensure_route_geometry_schema(engine):
    """Expand existing geometry storage without changing saved routes."""
    if engine.dialect.name != "mysql":
        return
    from sqlalchemy.dialects.mysql import LONGTEXT
    with engine.begin() as connection:
        columns = {column["name"]: column for column in inspect(connection).get_columns("rotas")}
        if not isinstance(columns["geometria_geojson"]["type"], LONGTEXT):
            connection.execute(text("ALTER TABLE rotas MODIFY COLUMN geometria_geojson LONGTEXT NULL"))
