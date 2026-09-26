from datetime import date
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field


class EnderecoBase(BaseModel):
    logradouro: str
    numero: str | None = None
    bairro: str | None = None
    cidade: str
    estado: str = Field(min_length=2, max_length=2)
    cep: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ClienteCreate(BaseModel):
    nome: str
    telefone: str | None = None
    endereco: EnderecoBase


class ClienteUpdate(ClienteCreate):
    pass


class EmpresaEnderecoOut(EnderecoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EnderecoOut(EnderecoBase):
    id: int
    cliente_id: int
    model_config = ConfigDict(from_attributes=True)


class ClienteOut(BaseModel):
    id: int
    nome: str
    telefone: str | None
    ativo: bool
    enderecos: list[EnderecoOut] = []
    model_config = ConfigDict(from_attributes=True)


class GeocodeRequest(BaseModel):
    logradouro: str
    numero: str | None = None
    bairro: str | None = None
    cidade: str
    estado: str
    cep: str | None = None


class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    display_name: str


class EntregaCreate(BaseModel):
    cliente_id: int
    endereco_id: int
    data_prevista: date
    observacoes: str | None = None


class EntregaUpdate(EntregaCreate):
    pass


class EntregaOut(BaseModel):
    id: int
    cliente_id: int | None
    endereco_id: int | None
    avulsa: bool = False
    data_prevista: date
    status: str
    observacoes: str | None
    cliente_nome: str
    latitude: float | None
    longitude: float | None
    endereco_resumo: str


class RotaCalcularRequest(BaseModel):
    entrega_ids: list[int] = Field(min_length=1)


class ParadaOut(BaseModel):
    ordem: int
    entrega_id: int
    cliente_nome: str
    latitude: float
    longitude: float


class RotaOut(BaseModel):
    id: int
    distancia_km: float
    duracao_minutos: int
    geometry: dict
    paradas: list[ParadaOut]



class CoordenadasRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class GeocodeReversoResponse(GeocodeResponse):
    address: dict[str, str]


class MatrizRequest(BaseModel):
    entrega_ids: list[int] = Field(min_length=1, max_length=24)


class MatrizPontoOut(CoordenadasRequest):
    nome: str
    entrega_id: int | None = None


class MatrizOut(BaseModel):
    pontos: list[MatrizPontoOut]
    distancias_km: list[list[float | None]]
    duracoes_minutos: list[list[float | None]]


class EntregaAvulsaUpdate(CoordenadasRequest):
    model_config = ConfigDict(str_strip_whitespace=True)
    nome: str = Field(default="Entrega avulsa", min_length=1, max_length=150)
    endereco: str = Field(min_length=1, max_length=500, description="Endereço ou referência conferida pelo usuário; as coordenadas são as do alvo, não as do resultado aproximado da geocodificação.")
    data_prevista: date = Field(default_factory=date.today)
    observacoes: str | None = Field(default=None, max_length=2000)


class EntregaAvulsaCreate(EntregaAvulsaUpdate):
    request_id: UUID = Field(default_factory=uuid4, description="Reutilize este UUID ao repetir a mesma tentativa de cadastro para evitar duplicação.")
    model_config = ConfigDict(str_strip_whitespace=True, json_schema_extra={"example": {
        "latitude": -23.5614, "longitude": -46.6559,
        "nome": "Entrega avulsa", "endereco": "Avenida Paulista, São Paulo, SP",
        "data_prevista": "2026-09-18", "observacoes": "Entregar na recepção",
        "request_id": "7c5ab7c5-6df9-4cf6-b5f1-88b7617b8f50",
    }})


class ErroRoteamentoDetalhe(BaseModel):
    codigo: str
    mensagem: str
    orientacao: str
    tentar_novamente: bool = False


class ErroRoteamentoResponse(BaseModel):
    detail: ErroRoteamentoDetalhe | str | list[dict]
