from copy import deepcopy
from time import monotonic


_NFE_LIST_CACHE_SECONDS = 45


_NFE_DETAIL_CACHE_SECONDS = 600


_nfe_list_cache: dict[tuple[str, str, str, str], dict] = {}


_nfe_detail_cache: dict[tuple[str, str, str], dict] = {}


def _cache_key_listar_nfes(
    tenant_id, data_inicial: str | None, data_final: str | None, situacao: str | None
) -> tuple[str, str, str, str]:
    return (
        str(tenant_id or ""),
        str(data_inicial or ""),
        str(data_final or ""),
        str((situacao or "")).strip().lower(),
    )


def _cache_key_detalhe_nfe(
    tenant_id, nfe_id: int, modelo: int | None = None
) -> tuple[str, str, str]:
    return (
        str(tenant_id or ""),
        str(nfe_id or ""),
        str(modelo or ""),
    )


def _obter_detalhe_nfe_cache(tenant_id, nfe_id: int, modelo: int | None = None):
    cache_key = _cache_key_detalhe_nfe(tenant_id, nfe_id, modelo)
    cache_atual = _nfe_detail_cache.get(cache_key)
    if not cache_atual:
        return None
    if (monotonic() - cache_atual.get("ts_monotonic", 0)) > _NFE_DETAIL_CACHE_SECONDS:
        _nfe_detail_cache.pop(cache_key, None)
        return None
    return deepcopy(cache_atual.get("payload"))


def _salvar_detalhe_nfe_cache(
    tenant_id, nfe_id: int, modelo: int | None, payload: dict
) -> None:
    _nfe_detail_cache[_cache_key_detalhe_nfe(tenant_id, nfe_id, modelo)] = {
        "ts_monotonic": monotonic(),
        "payload": deepcopy(payload),
    }
