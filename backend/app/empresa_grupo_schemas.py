from pydantic import BaseModel, Field, field_validator


class EmpresaGrupoCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=150)

    @field_validator("nome")
    @classmethod
    def limpar_nome(cls, value: str) -> str:
        nome = " ".join(value.split())
        if len(nome) < 2:
            raise ValueError("Informe um nome para o grupo.")
        return nome


class EmpresaGrupoConvidar(BaseModel):
    codigo_empresa: str = Field(min_length=12, max_length=20)
