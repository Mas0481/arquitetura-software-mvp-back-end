from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Cliente, Endereco
from ..schemas import (
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    CoordenadasRequest,
    GeocodeReversoResponse,
    GeocodeRequest,
    GeocodeResponse,
)
from ..services.external_maps import geocode_address, reverse_geocode

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).order_by(Cliente.nome).all()


@router.post("", response_model=ClienteOut, status_code=201)
def criar_cliente(payload: ClienteCreate, db: Session = Depends(get_db)):
    cliente = Cliente(nome=payload.nome, telefone=payload.telefone)
    db.add(cliente)
    db.flush()

    endereco = Endereco(
        cliente_id=cliente.id,
        **payload.endereco.model_dump(),
    )
    db.add(endereco)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
def editar_cliente(
    cliente_id: int,
    payload: ClienteUpdate,
    db: Session = Depends(get_db),
):
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado.")

    cliente.nome = payload.nome
    cliente.telefone = payload.telefone
    endereco = cliente.enderecos[0] if cliente.enderecos else Endereco(cliente_id=cliente.id)
    for campo, valor in payload.endereco.model_dump().items():
        setattr(endereco, campo, valor)
    if not endereco in cliente.enderecos:
        cliente.enderecos.append(endereco)

    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=204)
def excluir_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado.")
    if cliente.entregas:
        raise HTTPException(409, "Não é possível excluir um cliente com entregas cadastradas.")

    db.delete(cliente)
    db.commit()


@router.post("/geocodificar", response_model=GeocodeResponse)
async def geocodificar(payload: GeocodeRequest):
    return await geocode_address(payload)



@router.post("/geocodificar-reverso", response_model=GeocodeReversoResponse,
             summary="Consultar endereço pelas coordenadas",
             description="Consulta o endpoint /reverse do Nominatim. Retorna o endereço próximo encontrado, que pode diferir do ponto informado.")
async def geocodificar_reverso(payload: CoordenadasRequest):
    return await reverse_geocode(payload.latitude, payload.longitude)
