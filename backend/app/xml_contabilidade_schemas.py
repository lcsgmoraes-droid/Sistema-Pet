from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class XmlContabilidadeConfigRequest(BaseModel):
    email_contador: EmailStr | None = None
    envio_automatico: bool = False
    envio_mensal: bool = False
    dia_envio_mensal: int = Field(default=1, ge=1, le=31)
    hora_envio_mensal: str = Field(
        default="08:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$"
    )

    @field_validator("email_contador", mode="before")
    @classmethod
    def limpar_email(cls, value):
        return str(value).strip() or None if value is not None else None

    @model_validator(mode="after")
    def exigir_destinatario(self):
        if (self.envio_automatico or self.envio_mensal) and not self.email_contador:
            raise ValueError("Informe o e-mail do contador para ativar os envios.")
        return self


class XmlContabilidadePeriodoRequest(BaseModel):
    data_inicio: date
    data_fim: date

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("A data final deve ser igual ou posterior à data inicial.")
        if (self.data_fim - self.data_inicio).days > 365:
            raise ValueError("Escolha um período de no máximo 366 dias.")
        return self


class XmlContabilidadeEnvioRequest(XmlContabilidadePeriodoRequest):
    agendado_para: datetime | None = None

    @field_validator("agendado_para")
    @classmethod
    def exigir_fuso(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError(
                "Informe o fuso horário no agendamento (horário de Brasília)."
            )
        return value
