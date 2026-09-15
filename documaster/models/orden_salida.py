from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator


class ClausulaSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    numero: int = Field(gt=0)
    titulo: str = Field(min_length=2, max_length=150)
    contenido: str = Field(min_length=10, max_length=4000)


class OrdenSalidaSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    folio: str = Field(min_length=1, max_length=30)
    fecha_emision: date
    lugar: str = Field(min_length=2, max_length=150)
    arrendador_nombre: str = "NOMBRE DEL ARRENDADOR"
    arrendador_rfc: str = Field(default="XAXX010101000", pattern=r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
    cliente_razon_social: str = Field(min_length=2, max_length=200)
    representante: str = Field(min_length=2, max_length=150)
    domicilio_fiscal: str = Field(min_length=5, max_length=300)
    cliente_rfc: str = Field(pattern=r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")
    producto: str = Field(min_length=2, max_length=300)
    cantidad: int = Field(gt=0)
    precio_unitario: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    tiempo_arrendamiento: Decimal = Field(gt=0, max_digits=8, decimal_places=2)
    fecha_inicio: date
    fecha_fin: date
    tasa_iva: Decimal = Field(default=Decimal("0.16"), ge=0, le=1)
    clausulas: list[ClausulaSchema] = Field(min_length=1)

    @field_validator("arrendador_rfc", "cliente_rfc")
    @classmethod
    def normalizar_rfc(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("La fecha final no puede ser anterior a la fecha inicial.")
        return self

    @staticmethod
    def dinero(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return self.dinero(Decimal(self.cantidad) * self.precio_unitario * self.tiempo_arrendamiento)

    @computed_field
    @property
    def iva(self) -> Decimal:
        return self.dinero(self.subtotal * self.tasa_iva)

    @computed_field
    @property
    def total(self) -> Decimal:
        return self.dinero(self.subtotal + self.iva)
