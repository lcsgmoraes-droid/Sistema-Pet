"""Fachada compativel das rotas de funcionarios/RH."""

from app.funcionarios.base_routes import (
    ativar_funcionario,
    atualizar_funcionario,
    criar_funcionario,
    deletar_funcionario,
    listar_funcionarios,
    obter_funcionario,
    obter_remuneracao_funcionario,
)
from app.funcionarios.eventos_routes import (
    api_conceder_ferias,
    api_obter_provisoes_funcionario,
    api_pagar_decimo_terceiro,
)
from app.funcionarios.helpers import (
    _aplicar_app_access_profiles,
    _buscar_cargo_funcionario,
    _cargo_dict,
    _funcionario_app_access_profiles,
    _funcionario_response_dict,
)
from app.funcionarios.routes import router
from app.funcionarios.schemas import (
    CargoSimples,
    ConcederFeriasRequest,
    FuncionarioCreate,
    FuncionarioResponse,
    FuncionarioUpdate,
    PagarDecimoTerceiroRequest,
    ProvisoesResponse,
    RemuneracaoResponse,
)

__all__ = [
    "CargoSimples",
    "ConcederFeriasRequest",
    "FuncionarioCreate",
    "FuncionarioResponse",
    "FuncionarioUpdate",
    "PagarDecimoTerceiroRequest",
    "ProvisoesResponse",
    "RemuneracaoResponse",
    "_aplicar_app_access_profiles",
    "_buscar_cargo_funcionario",
    "_cargo_dict",
    "_funcionario_app_access_profiles",
    "_funcionario_response_dict",
    "api_conceder_ferias",
    "api_obter_provisoes_funcionario",
    "api_pagar_decimo_terceiro",
    "ativar_funcionario",
    "atualizar_funcionario",
    "criar_funcionario",
    "deletar_funcionario",
    "listar_funcionarios",
    "obter_funcionario",
    "obter_remuneracao_funcionario",
    "router",
]
