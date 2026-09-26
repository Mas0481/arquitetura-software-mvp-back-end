from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Cliente, Endereco, Entrega, EntregaAvulsa, Rota, RotaParada
from ..schemas import EntregaCreate, EntregaOut, EntregaUpdate, EntregaAvulsaCreate, EntregaAvulsaUpdate

router = APIRouter(prefix="/api/entregas", tags=["Entregas"])


def serialize_entrega(e: Entrega):
    return EntregaOut(
        id=e.id,
        cliente_id=e.cliente_id,
        endereco_id=e.endereco_id,
        data_prevista=e.data_prevista,
        status=e.status,
        observacoes=e.observacoes,
        cliente_nome=e.nome_destinatario,
        latitude=e.latitude,
        longitude=e.longitude,
        endereco_resumo=e.endereco_resumo,
        avulsa=e.avulsa,
    )


@router.get("", response_model=list[EntregaOut])
def listar_entregas(
    data_prevista: date | None = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Entrega)
        .options(joinedload(Entrega.cliente), joinedload(Entrega.endereco), joinedload(Entrega.dados_avulsos))
    )

    if data_prevista:
        query = query.filter(Entrega.data_prevista == data_prevista)

    entregas = query.order_by(Entrega.data_prevista, Entrega.id).all()
    return [serialize_entrega(e) for e in entregas]


@router.post("", response_model=EntregaOut, status_code=201)
def criar_entrega(payload: EntregaCreate, db: Session = Depends(get_db)):
    cliente = db.get(Cliente, payload.cliente_id)
    endereco = db.get(Endereco, payload.endereco_id)

    if not cliente:
        raise HTTPException(404, "Cliente não encontrado.")

    if not endereco or endereco.cliente_id != cliente.id:
        raise HTTPException(400, "Endereço inválido para o cliente.")

    if endereco.latitude is None or endereco.longitude is None:
        raise HTTPException(
            400,
            "O endereço precisa ter latitude e longitude antes de criar a entrega.",
        )

    entrega = Entrega(**payload.model_dump())
    db.add(entrega)
    db.commit()

    entrega = (
        db.query(Entrega)
        .options(joinedload(Entrega.cliente), joinedload(Entrega.endereco), joinedload(Entrega.dados_avulsos))
        .filter(Entrega.id == entrega.id)
        .one()
    )
    return serialize_entrega(entrega)


def validar_entrega(payload: EntregaCreate, db: Session):
    cliente = db.get(Cliente, payload.cliente_id)
    endereco = db.get(Endereco, payload.endereco_id)

    if not cliente:
        raise HTTPException(404, "Cliente não encontrado.")
    if not endereco or endereco.cliente_id != cliente.id:
        raise HTTPException(400, "Endereço inválido para o cliente.")
    if endereco.latitude is None or endereco.longitude is None:
        raise HTTPException(400, "O endereço precisa ter latitude e longitude antes de criar a entrega.")


@router.put("/{entrega_id}", response_model=EntregaOut)
def editar_entrega(
    entrega_id: int,
    payload: EntregaUpdate,
    db: Session = Depends(get_db),
):
    entrega = db.get(Entrega, entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega não encontrada.")
    if entrega.avulsa:
        raise HTTPException(400, "Use o endpoint de edição de entregas avulsas.")
    validar_entrega(payload, db)
    for campo, valor in payload.model_dump().items():
        setattr(entrega, campo, valor)
    db.commit()
    entrega = (
        db.query(Entrega)
        .options(joinedload(Entrega.cliente), joinedload(Entrega.endereco), joinedload(Entrega.dados_avulsos))
        .filter(Entrega.id == entrega.id)
        .one()
    )
    return serialize_entrega(entrega)


@router.delete("/{entrega_id}", status_code=204)
def excluir_entrega(entrega_id: int, db: Session = Depends(get_db)):
    entrega = db.get(Entrega, entrega_id)
    if not entrega:
        raise HTTPException(404, "Entrega não encontrada.")

    rotas = (
        db.query(Rota)
        .join(RotaParada, RotaParada.rota_id == Rota.id)
        .filter(RotaParada.entrega_id == entrega_id)
        .all()
    )
    for rota in rotas:
        db.delete(rota)

    db.delete(entrega)
    db.commit()



def _same_avulsa_request(existing, payload):
    return (existing.nome == payload.nome and existing.endereco == payload.endereco
            and existing.latitude == payload.latitude and existing.longitude == payload.longitude
            and existing.entrega.data_prevista == payload.data_prevista
            and existing.entrega.observacoes == payload.observacoes)


@router.post("/avulsas", response_model=EntregaOut, status_code=201,
             summary="Inserir entrega avulsa pelo mapa",
             description="Cria uma entrega sem cliente cadastrado, preservando o ponto exato selecionado. Endereço pode ser revisado ou informado manualmente. A entrega aparece na listagem e pode ser incluída em rotas e matrizes. Repetir o mesmo request_id com o mesmo conteúdo retorna a entrega existente; conteúdo diferente retorna 409.",
             responses={409: {"description": "request_id já utilizado com outros dados"}})
async def criar_entrega_avulsa(payload: EntregaAvulsaCreate, db: Session = Depends(get_db)):
    existing = db.query(EntregaAvulsa).filter_by(request_id=str(payload.request_id)).first()
    if existing:
        if not _same_avulsa_request(existing, payload):
            raise HTTPException(409, "Esta tentativa já foi salva com outros dados. Atualize a entrega existente.")
        return serialize_entrega(existing.entrega)
    entrega = Entrega(data_prevista=payload.data_prevista, observacoes=payload.observacoes)
    entrega.dados_avulsos = EntregaAvulsa(
        request_id=str(payload.request_id), nome=payload.nome, endereco=payload.endereco,
        latitude=payload.latitude, longitude=payload.longitude,
    )
    db.add(entrega)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(EntregaAvulsa).filter_by(request_id=str(payload.request_id)).first()
        if existing and _same_avulsa_request(existing, payload):
            return serialize_entrega(existing.entrega)
        raise HTTPException(409, "Não foi possível salvar esta tentativa. Verifique se a entrega já existe.")
    return serialize_entrega(entrega)


@router.put("/avulsas/{entrega_id}", response_model=EntregaOut,
            summary="Editar uma entrega avulsa",
            description="Atualiza destinatário, referência, coordenadas, data e observações. Rotas anteriores que contêm a entrega são removidas para não manter trajetos desatualizados.")
def editar_entrega_avulsa(entrega_id: int, payload: EntregaAvulsaUpdate, db: Session = Depends(get_db)):
    entrega = db.get(Entrega, entrega_id)
    if not entrega or not entrega.avulsa:
        raise HTTPException(404, "Entrega avulsa não encontrada.")
    for rota in db.query(Rota).join(RotaParada).filter(RotaParada.entrega_id == entrega_id).all():
        db.delete(rota)
    entrega.data_prevista = payload.data_prevista
    entrega.observacoes = payload.observacoes
    for field in ("nome", "endereco", "latitude", "longitude"):
        setattr(entrega.dados_avulsos, field, getattr(payload, field))
    db.commit()
    return serialize_entrega(entrega)
