from pydantic import BaseModel, Field, field_validator


class GrupoComercialCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=150)

    @field_validator("nome")
    @classmethod
    def limpar_nome(cls, value: str) -> str:
        nome = " ".join(value.split())
        if len(nome) < 2:
            raise ValueError("Informe um nome para o grupo.")
        return nome


class GrupoComercialGestorConceder(BaseModel):
    user_id: int = Field(gt=0)


class GrupoComercialLojaAdicionar(BaseModel):
    """Provisiona uma loja nova e a anexa direto neste grupo, como membro —
    sem convite/código, porque é o mesmo dono legal adicionando outra loja
    própria (ver GrupoComercialService.adicionar_loja)."""

    nome_loja: str = Field(min_length=2, max_length=150)
    nome_acesso: str | None = Field(default=None, max_length=150)
    plan: str | None = None
    organization_type: str | None = None

    @field_validator("nome_loja")
    @classmethod
    def limpar_nome_loja(cls, value: str) -> str:
        nome = " ".join(value.split())
        if len(nome) < 2:
            raise ValueError("Informe um nome para a loja.")
        return nome


class GrupoComercialProdutoReferencia(BaseModel):
    empresa_id: str = Field(min_length=36, max_length=36)
    produto_id: int = Field(gt=0)


class GrupoComercialProdutoVincular(BaseModel):
    produto_a: GrupoComercialProdutoReferencia
    produto_b: GrupoComercialProdutoReferencia

    @field_validator("produto_b")
    @classmethod
    def validar_empresas_distintas(
        cls,
        value: GrupoComercialProdutoReferencia,
        info,
    ) -> GrupoComercialProdutoReferencia:
        produto_a = info.data.get("produto_a")
        if produto_a and produto_a.empresa_id == value.empresa_id:
            raise ValueError("Escolha produtos de empresas diferentes.")
        return value


class GrupoComercialEstoqueCompartilhar(BaseModel):
    empresa_consumidora_id: str = Field(min_length=36, max_length=36)
    produto_ids: list[int] = Field(min_length=1, max_length=200)
    acesso_catalogo_completo: bool = False

    @field_validator("produto_ids")
    @classmethod
    def validar_produtos(cls, value: list[int]) -> list[int]:
        ids = sorted({int(produto_id) for produto_id in value if int(produto_id) > 0})
        if not ids:
            raise ValueError("Selecione ao menos um produto.")
        return ids


class GrupoComercialEstoqueAcessoCatalogoAtualizar(BaseModel):
    acesso_catalogo_completo: bool
