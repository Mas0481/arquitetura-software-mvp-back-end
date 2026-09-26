import asyncio
import math
import time
from typing import Any

import httpx
from fastapi import HTTPException

from ..config import settings


# Cache de processo suficiente para o MVP. Em produção, use Redis/banco.
_geocode_cache: dict[tuple, Any] = {}
_last_nominatim_request = 0.0
_nominatim_lock = asyncio.Lock()


def _build_address(data) -> str:
    parts = [
        f"{data.logradouro}, {data.numero}" if data.numero else data.logradouro,
        data.bairro,
        data.cidade,
        data.estado,
        data.cep,
        "Brasil",
    ]
    return ", ".join(str(x).strip() for x in parts if x)


async def _nominatim_get(endpoint: str, params: dict):
    global _last_nominatim_request
    cache_key = (endpoint, tuple(sorted(params.items())))
    async with _nominatim_lock:
        if cache_key in _geocode_cache:
            return _geocode_cache[cache_key]
        elapsed = time.monotonic() - _last_nominatim_request
        if elapsed < 1.05:
            await asyncio.sleep(1.05 - elapsed)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"{settings.nominatim_url.rstrip('/')}/{endpoint}",
                    params=params,
                    headers={"User-Agent": settings.external_api_user_agent,
                             "Accept-Language": "pt-BR,pt;q=0.9"},
                )
                if response.status_code == 404:
                    raise HTTPException(404, "Endereço não localizado.")
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(502, "Falha no serviço externo de endereços.") from exc
        finally:
            _last_nominatim_request = time.monotonic()
        if not data or (isinstance(data, dict) and data.get("error")):
            raise HTTPException(404, "Endereço não localizado.")
        if len(_geocode_cache) >= 500:
            _geocode_cache.pop(next(iter(_geocode_cache)))
        _geocode_cache[cache_key] = data
        return data


async def geocode_address(data):
    items = await _nominatim_get("search", {
        "q": _build_address(data), "format": "jsonv2", "limit": 1, "countrycodes": "br",
    })
    try:
        return {"latitude": float(items[0]["lat"]),
                "longitude": float(items[0]["lon"]),
                "display_name": items[0]["display_name"]}
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(502, "Resposta inválida do serviço de endereços.") from exc


async def reverse_geocode(latitude: float, longitude: float):
    data = await _nominatim_get("reverse", {
        "lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1,
    })
    try:
        return {"latitude": float(data["lat"]), "longitude": float(data["lon"]),
                "display_name": data["display_name"], "address": data.get("address", {})}
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(502, "Resposta inválida do serviço de endereços.") from exc


def routing_error(status, code, message, guidance, retryable=False):
    return HTTPException(status, detail={
        "codigo": code, "mensagem": message, "orientacao": guidance,
        "tentar_novamente": retryable,
    })


_OSRM_ERRORS = {
    "NoRoute": (422, "Não foi encontrado um trajeto de carro entre os pontos selecionados.", "Confira os pontos no mapa e tente retirar uma parada por vez ou ajustar sua localização."),
    "NoSegment": (422, "Um dos pontos não pôde ser associado a uma via disponível para o cálculo.", "Confira a origem e as entregas. Ajuste o ponto para uma rua próxima e tente novamente."),
    "NoTable": (422, "Não foi possível comparar os trajetos entre os pontos selecionados.", "Confira os pontos no mapa e tente comparar menos paradas."),
    "TooBig": (422, "A seleção excede o limite aceito pelo serviço de rotas.", "Selecione menos entregas e divida o planejamento em rotas menores."),
    "InvalidValue": (422, "O serviço de rotas recusou os valores informados.", "Confira as coordenadas da empresa e das entregas."),
    "InvalidOptions": (502, "O serviço de rotas não aceitou as opções da consulta.", "Se o problema persistir, informe o responsável pelo sistema."),
    "InvalidQuery": (502, "O serviço de rotas não conseguiu interpretar a consulta.", "Se o problema persistir, informe o responsável pelo sistema."),
    "InvalidUrl": (502, "O endereço configurado para o serviço de rotas não foi aceito.", "Informe o responsável pelo sistema."),
    "InvalidService": (502, "O serviço de rotas configurado não oferece esta operação.", "Informe o responsável pelo sistema."),
    "InvalidVersion": (502, "A versão configurada do serviço de rotas não foi aceita.", "Informe o responsável pelo sistema."),
    "NotImplemented": (502, "O provedor não oferece esta operação de comparação.", "Informe o responsável pelo sistema para conferir o provedor configurado."),
}


def _coordinate_text(coordinates):
    if len(coordinates) < 2:
        raise routing_error(422, "InsufficientPoints", "São necessários a origem e pelo menos uma entrega.", "Selecione uma entrega antes de calcular.")
    for index, (lat, lon) in enumerate(coordinates):
        if not all(type(value) in (int, float) and math.isfinite(value) for value in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            point = "origem da empresa" if index == 0 else f"parada {index}"
            raise routing_error(422, "InvalidCoordinates", f"As coordenadas da {point} são inválidas.", "Corrija o endereço ou o ponto no mapa antes de tentar novamente.")
    return ";".join(f"{lon},{lat}" for lat, lon in coordinates)


async def _osrm_get(service, coordinates, params):
    coord_text = _coordinate_text(coordinates)
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.get(
                f"{settings.osrm_url.rstrip('/')}/{service}/v1/driving/{coord_text}",
                params=params, headers={"User-Agent": settings.external_api_user_agent},
            )
    except httpx.TimeoutException as exc:
        raise routing_error(504, "Timeout", "O serviço de rotas demorou demais para responder.", "Tente novamente em instantes ou selecione menos entregas.", True) from exc
    except httpx.HTTPError as exc:
        raise routing_error(503, "ConnectionError", "Não foi possível conectar ao serviço de rotas.", "Verifique a conexão do servidor e tente novamente em instantes.", True) from exc
    if response.status_code == 429:
        raise routing_error(503, "RateLimited", "O serviço de rotas recebeu consultas demais e limitou o acesso temporariamente.", "Aguarde um pouco antes de tentar novamente.", True)
    if response.status_code >= 500:
        raise routing_error(503, "Unavailable", "O serviço externo de rotas está indisponível no momento.", "Tente novamente em instantes.", True)
    try:
        data = response.json()
    except ValueError as exc:
        raise routing_error(502, "InvalidResponse", "O serviço de rotas enviou uma resposta que não pôde ser lida.", "Tente novamente. Se persistir, informe o responsável pelo sistema.", True) from exc
    if not isinstance(data, dict):
        raise routing_error(502, "InvalidResponse", "O serviço de rotas enviou uma resposta inválida.", "Tente novamente em instantes.", True)
    code = data.get("code")
    if isinstance(code, str) and code in _OSRM_ERRORS:
        status, message, guidance = _OSRM_ERRORS[code]
        raise routing_error(status, code, message, guidance)
    if not response.is_success or code != "Ok":
        raise routing_error(502, "ProviderError", "O serviço de rotas não conseguiu atender à consulta.", "Tente novamente. Se persistir, informe o responsável pelo sistema.", True)
    return data


async def calculate_route(coordinates: list[tuple[float, float]]):
    data = await _osrm_get("route", coordinates, {"overview": "full", "geometries": "geojson", "steps": "false"})
    try:
        route = data["routes"][0]
        distance, duration, geometry = route["distance"], route["duration"], route["geometry"]
        if not all(type(value) in (int, float) and math.isfinite(value) and value >= 0 for value in (distance, duration)):
            raise ValueError("Invalid route measures")
        if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
            raise ValueError("Invalid geometry")
        points = geometry.get("coordinates")
        if not isinstance(points, list) or len(points) < 2:
            raise ValueError("Missing geometry coordinates")
        for point in points:
            if not isinstance(point, list) or len(point) != 2 or not all(type(v) in (int, float) and math.isfinite(v) for v in point) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                raise ValueError("Invalid geometry coordinate")
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise routing_error(502, "InvalidResponse", "O serviço retornou um trajeto incompleto ou inválido.", "Tente novamente. Se persistir, informe o responsável pelo sistema.", True) from exc
    return {"distance_km": round(distance / 1000, 2), "duration_minutes": round(duration / 60), "geometry": geometry}


async def calculate_matrix(coordinates: list[tuple[float, float]]):
    data = await _osrm_get("table", coordinates, {"annotations": "distance,duration"})

    def convert(name, divisor):
        rows = data.get(name)
        size = len(coordinates)
        if not isinstance(rows, list) or len(rows) != size:
            raise HTTPException(502, "Matriz inválida recebida do serviço externo.")
        result = []
        for row in rows:
            if not isinstance(row, list) or len(row) != size:
                raise HTTPException(502, "Matriz inválida recebida do serviço externo.")
            converted = []
            for value in row:
                if value is None:
                    converted.append(None)
                elif type(value) in (int, float) and math.isfinite(value) and value >= 0:
                    converted.append(round(value / divisor, 2))
                else:
                    raise HTTPException(502, "Valor inválido recebido do serviço externo.")
            result.append(converted)
        return result

    return {"distancias_km": convert("distances", 1000),
            "duracoes_minutos": convert("durations", 60)}
