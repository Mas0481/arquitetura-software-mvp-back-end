from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(30))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    enderecos: Mapped[list["Endereco"]] = relationship(
        back_populates="cliente",
        cascade="all, delete-orphan",
    )
    entregas: Mapped[list["Entrega"]] = relationship(back_populates="cliente")


class Endereco(Base):
    __tablename__ = "enderecos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)

    logradouro: Mapped[str] = mapped_column(String(150), nullable=False)
    numero: Mapped[str | None] = mapped_column(String(20))
    bairro: Mapped[str | None] = mapped_column(String(100))
    cidade: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    cep: Mapped[str | None] = mapped_column(String(10))

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    cliente: Mapped["Cliente"] = relationship(back_populates="enderecos")


class EmpresaEndereco(Base):
    __tablename__ = "empresa_endereco"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    logradouro: Mapped[str] = mapped_column(String(150), nullable=False)
    numero: Mapped[str | None] = mapped_column(String(20))
    bairro: Mapped[str | None] = mapped_column(String(100))
    cidade: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    cep: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)


class Entrega(Base):
    __tablename__ = "entregas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[int | None] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    endereco_id: Mapped[int | None] = mapped_column(ForeignKey("enderecos.id"), nullable=True)

    data_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDENTE", nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text)

    cliente: Mapped["Cliente | None"] = relationship(back_populates="entregas")
    endereco: Mapped["Endereco | None"] = relationship()


    dados_avulsos: Mapped["EntregaAvulsa | None"] = relationship(
        back_populates="entrega", cascade="all, delete-orphan", uselist=False,
    )

    @property
    def avulsa(self):
        return self.dados_avulsos is not None

    @property
    def nome_destinatario(self):
        return self.dados_avulsos.nome if self.avulsa else self.cliente.nome

    @property
    def latitude(self):
        return self.dados_avulsos.latitude if self.avulsa else self.endereco.latitude

    @property
    def longitude(self):
        return self.dados_avulsos.longitude if self.avulsa else self.endereco.longitude

    @property
    def endereco_resumo(self):
        if self.avulsa:
            return self.dados_avulsos.endereco
        end = self.endereco
        return ", ".join(x for x in [end.logradouro + (f", {end.numero}" if end.numero else ""), end.cidade, end.estado] if x)


class EntregaAvulsa(Base):
    __tablename__ = "entregas_avulsas"

    entrega_id: Mapped[int] = mapped_column(ForeignKey("entregas.id"), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    endereco: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    entrega: Mapped["Entrega"] = relationship(back_populates="dados_avulsos")


class Rota(Base):
    __tablename__ = "rotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_rota: Mapped[date] = mapped_column(Date, nullable=False)
    distancia_km: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    duracao_minutos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    geometria_geojson: Mapped[str | None] = mapped_column(Text().with_variant(LONGTEXT(), "mysql"))
    status: Mapped[str] = mapped_column(String(30), default="PLANEJADA", nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    paradas: Mapped[list["RotaParada"]] = relationship(
        back_populates="rota",
        cascade="all, delete-orphan",
        order_by="RotaParada.ordem",
    )


class RotaParada(Base):
    __tablename__ = "rota_paradas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rota_id: Mapped[int] = mapped_column(ForeignKey("rotas.id"), nullable=False)
    entrega_id: Mapped[int] = mapped_column(ForeignKey("entregas.id"), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    rota: Mapped["Rota"] = relationship(back_populates="paradas")
    entrega: Mapped["Entrega"] = relationship()
