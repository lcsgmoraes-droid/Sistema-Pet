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


class EmpresaGrupoProdutoReferencia(BaseModel):
    empresa_id: str = Field(min_length=36, max_length=36)
    produto_id: int = Field(gt=0)


class EmpresaGrupoProdutoVincular(BaseModel):
    produto_a: EmpresaGrupoProdutoReferencia
    produto_b: EmpresaGrupoProdutoReferencia

    @field_validator("produto_b")
    @classmethod
    def validar_empresas_distintas(
        cls,
        value: EmpresaGrupoProdutoReferencia,
        info,
    ) -> EmpresaGrupoProdutoReferencia:
        produto_a = info.data.get("produto_a")
        if produto_a and produto_a.empresa_id == value.empresa_id:
            raise ValueError("Escolha produtos de empresas diferentes.")
        return value


class EmpresaGrupoEstoqueCompartilhar(BaseModel):
    empresa_consumidora_id: str = Field(min_length=36, max_length=36)
    produto_ids: list[int] = Field(min_length=1, max_length=200)

    @field_validator("produto_ids")
    @classmethod
    def validar_produtos(cls, value: list[int]) -> list[int]:
        ids = sorted({int(produto_id) for produto_id in value if int(produto_id) > 0})
        if not ids:
            raise ValueError("Selecione ao menos um produto.")
        return ids
