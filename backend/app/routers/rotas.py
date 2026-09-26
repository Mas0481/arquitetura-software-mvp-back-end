import json
import logging
from sqlalchemy.exc import SQLAlchemyError
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import EmpresaEndereco, Entrega, Rota, RotaParada
from ..schemas import ParadaOut, RotaCalcularRequest, RotaOut, MatrizRequest, MatrizOut, MatrizPontoOut, ErroRoteamentoResponse
from ..services.external_maps import calculate_route, calculate_matrix, routing_error

router = APIRouter(prefix="/api/rotas", tags=["Rotas"])


@router.post("/calcular", response_model=RotaOut,
             responses={status: {"model": ErroRoteamentoResponse, "description": description} for status, description in {
                 422: "Trajeto não encontrado ou pontos inválidos", 500: "Falha ao salvar a rota",
                 502: "Resposta inválida do provedor", 503: "Serviço indisponível ou limitado", 504: "Tempo de espera excedido",
             }.items()})
async def calcular_rota(payload: RotaCalcularRequest, db: Session = Depends(get_db)):
    empresa_endereco = db.get(EmpresaEndereco, 1)
    if not empresa_endereco:
        raise HTTPException(400, "Cadastre o endereço da empresa antes de calcular uma rota.")

    if empresa_endereco.latitude is None or empresa_endereco.longitude is None:
        raise HTTPException(400, "O endereço da empresa precisa ter coordenadas.")

    entregas = (
        db.query(Entrega)
        .options(joinedload(Entrega.cliente), joinedload(Entrega.endereco), joinedload(Entrega.dados_avulsos))
        .filter(Entrega.id.in_(payload.entrega_ids))
        .all()
    )

    por_id = {e.id: e for e in entregas}

    if len(por_id) != len(set(payload.entrega_ids)):
        raise HTTPException(404, "Uma ou mais entregas não foram encontradas.")

    ordenadas = [por_id[i] for i in payload.entrega_ids]

    coordinates = [
        (empresa_endereco.latitude, empresa_endereco.longitude)
    ]
    for entrega in ordenadas:
        if entrega.latitude is None or entrega.longitude is None:
            raise HTTPException(
                400,
                f"Entrega {entrega.id} não possui coordenadas.",
            )
        coordinates.append(
            (entrega.latitude, entrega.longitude)
        )

    resultado = await calculate_route(coordinates)

    rota = Rota(
        data_rota=date.today(),
        distancia_km=resultado["distance_km"],
        duracao_minutos=resultado["duration_minutes"],
        geometria_geojson=json.dumps(resultado["geometry"]),
    )
    try:
        db.add(rota)
        db.flush()
        rota_id = rota.id
    
        paradas_out = []
        for ordem, entrega in enumerate(ordenadas, start=1):
            db.add(
                RotaParada(
                    rota_id=rota.id,
                    entrega_id=entrega.id,
                    ordem=ordem,
                )
            )
            paradas_out.append(
                ParadaOut(
                    ordem=ordem,
                    entrega_id=entrega.id,
                    cliente_nome=entrega.nome_destinatario,
                    latitude=entrega.latitude,
                    longitude=entrega.longitude,
                )
            )
    
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logging.getLogger(__name__).error("Falha ao salvar rota: %s", type(exc).__name__)
        raise routing_error(500, "PersistenceError", "O trajeto foi calculado, mas ocorreu uma falha ao salvar a rota.", "Tente novamente. Se persistir, informe o responsável pelo sistema.", True) from exc

    return RotaOut(
        id=rota_id,
        distancia_km=resultado["distance_km"],
        duracao_minutos=resultado["duration_minutes"],
        geometry=resultado["geometry"],
        paradas=paradas_out,
    )



@router.post("/matriz", response_model=MatrizOut,
             responses={status: {"model": ErroRoteamentoResponse} for status in (422, 502, 503, 504)},
             summary="Comparar distâncias e tempos entre paradas",
             description="Consulta /table/v1/driving do OSRM. A primeira posição é a empresa; as demais seguem entrega_ids. Linhas são origens, colunas são destinos. Valores null indicam ausência de trajeto. Não salva rota nem altera a ordem das entregas. Limite: 24 entregas.")
async def comparar_paradas(payload: MatrizRequest, db: Session = Depends(get_db)):
    if len(payload.entrega_ids) != len(set(payload.entrega_ids)):
        raise HTTPException(400, "Selecione cada entrega apenas uma vez.")
    empresa = db.get(EmpresaEndereco, 1)
    if not empresa or empresa.latitude is None or empresa.longitude is None:
        raise HTTPException(400, "Cadastre a empresa com coordenadas antes de comparar.")
    entregas = (db.query(Entrega)
                .options(joinedload(Entrega.cliente), joinedload(Entrega.endereco), joinedload(Entrega.dados_avulsos))
                .filter(Entrega.id.in_(payload.entrega_ids)).all())
    por_id = {entrega.id: entrega for entrega in entregas}
    if len(por_id) != len(payload.entrega_ids):
        raise HTTPException(404, "Uma ou mais entregas não foram encontradas.")
    pontos = [{"nome": "Empresa", "entrega_id": None,
               "latitude": empresa.latitude, "longitude": empresa.longitude}]
    for entrega_id in payload.entrega_ids:
        entrega = por_id[entrega_id]
        if entrega.latitude is None or entrega.longitude is None:
            raise HTTPException(400, f"Entrega {entrega_id} não possui coordenadas.")
        pontos.append({"nome": entrega.nome_destinatario, "entrega_id": entrega.id,
                       "latitude": entrega.latitude, "longitude": entrega.longitude})
    try:
        pontos = [MatrizPontoOut(**ponto) for ponto in pontos]
    except ValueError as exc:
        raise HTTPException(400, "Existem coordenadas inválidas nos endereços cadastrados.") from exc
    resultado = await calculate_matrix([(p.latitude, p.longitude) for p in pontos])
    return MatrizOut(pontos=pontos, **resultado)
