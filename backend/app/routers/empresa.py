from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EmpresaEndereco
from ..schemas import EmpresaEnderecoOut, EnderecoBase

router = APIRouter(prefix="/api/empresa", tags=["Empresa"])


@router.get("/endereco", response_model=EmpresaEnderecoOut)
def obter_endereco_empresa(db: Session = Depends(get_db)):
    endereco = db.get(EmpresaEndereco, 1)
    if not endereco:
        raise HTTPException(404, "Endereço da empresa não cadastrado.")
    return endereco


@router.post("/endereco", response_model=EmpresaEnderecoOut)
def salvar_endereco_empresa(
    payload: EnderecoBase,
    db: Session = Depends(get_db),
):
    if payload.latitude is None or payload.longitude is None:
        raise HTTPException(
            400,
            "O endereço da empresa precisa ser localizado antes de salvar.",
        )

    endereco = db.get(EmpresaEndereco, 1)
    if endereco:
        for campo, valor in payload.model_dump().items():
            setattr(endereco, campo, valor)
    else:
        endereco = EmpresaEndereco(id=1, **payload.model_dump())
        db.add(endereco)

    db.commit()
    db.refresh(endereco)
    return endereco