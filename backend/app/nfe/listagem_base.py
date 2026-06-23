import re
from datetime import datetime, timedelta

from app.vendas_models import Venda


_STATUS_EMITIDA_DANFE = "Emitida DANFE"


_STATUS_MAP = {
    0: "Pendente",
    1: "Pendente",
    2: _STATUS_EMITIDA_DANFE,
    4: "Cancelada",
    5: "Autorizada",
    6: "Rejeitada",
    9: "Autorizada",
}


_LOJA_ID_CANAL_MAP = {
    "204647675": "mercado_livre",
    "205367939": "shopee",
    "205639810": "amazon",
}


_REGIME_TRIBUTARIO_MAP = {
    "1": "Simples Nacional",
    "2": "Simples Nacional - excesso de sublimite",
    "3": "Regime Normal",
}


_FINALIDADE_MAP = {
    "1": "NF-e normal",
    "2": "NF-e complementar",
    "3": "NF-e de ajuste",
    "4": "Devolucao / Retorno",
}


_INDICADOR_PRESENCA_MAP = {
    "0": "0 - Nao se aplica",
    "1": "1 - Operacao presencial",
    "2": "2 - Operacao nao presencial, internet",
    "3": "3 - Operacao nao presencial, teleatendimento",
    "4": "4 - NFC-e em operacao com entrega em domicilio",
    "5": "5 - Operacao presencial, fora do estabelecimento",
    "9": "9 - Operacao nao presencial, outros",
}


_XML_NS = {"nfe": "http" + "://www.portalfiscal.inf.br/nfe"}


_NFE_SYNC_CACHE_TTL_SECONDS = 300


_NFE_SYNC_DEFAULT_LOOKBACK_DAYS = 7


_NFE_SYNC_SAFETY_LOOKBACK_DAYS = 2


def _coerce_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sort_key_nota_por_numero_desc(nota: dict) -> tuple[int, str, int]:
    numero_texto = str(nota.get("numero") or "").strip()
    numero_digits = re.sub(r"\D", "", numero_texto)
    numero_int = _coerce_int(numero_digits, default=-1) if numero_digits else -1
    data_emissao = str(nota.get("data_emissao") or "").strip()
    nota_id = _coerce_int(nota.get("id"), default=-1)
    return (numero_int, data_emissao, nota_id)


def _coerce_float(value, default: float | None = 0.0) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _texto(value) -> str | None:
    if value is None:
        return None
    texto = str(value).strip()
    return texto or None


def _texto_relacionado(value, *keys: str, fallback_to_id: bool = True) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        chaves = keys or (
            "nome",
            "descricao",
            "descricaoPadrao",
            "fantasia",
            "apelido",
            "label",
            "sigla",
            "tipo",
            "endereco",
            "logradouro",
        )
        for chave in chaves:
            texto = _texto(value.get(chave))
            if texto:
                return texto
        identificador = _texto(value.get("id"))
        if fallback_to_id and identificador and identificador != "0":
            return f"ID {identificador}"
        return None
    if isinstance(value, list):
        partes = [_texto_relacionado(item, *keys) for item in value]
        partes = [parte for parte in partes if parte]
        return ", ".join(partes) or None
    return _texto(value)


def _primeiro_preenchido(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _canal_slug(value) -> str:
    texto = str(value or "").strip().lower()
    if not texto:
        return ""

    if (
        any(
            chave in texto
            for chave in ("mercado livre", "mercadolivre", "mercado_livre")
        )
        or texto == "ml"
    ):
        return "mercado_livre"
    if "shopee" in texto:
        return "shopee"
    if "amazon" in texto:
        return "amazon"
    if any(
        chave in texto for chave in ("loja virtual", "ecommerce", "e-commerce", "site")
    ):
        return "site"
    if any(chave in texto for chave in ("app", "aplicativo")):
        return "app"
    if "whatsapp" in texto:
        return "whatsapp"
    if "bling" in texto:
        return "bling"
    return texto.replace(" ", "_")


def _canal_label(slug: str, fallback: str | None = None) -> str | None:
    mapa = {
        "mercado_livre": "Mercado Livre",
        "shopee": "Shopee",
        "amazon": "Amazon",
        "site": "Site",
        "app": "App",
        "whatsapp": "WhatsApp",
        "bling": "Bling",
        "loja_fisica": "Loja fisica",
    }
    return mapa.get(slug) or _texto(fallback) or None


def _digitos(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _extrair_campo_texto(texto: str | None, *padroes: str) -> str | None:
    conteudo = _texto(texto)
    if not conteudo:
        return None
    for padrao in padroes:
        match = re.search(padrao, conteudo, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return _texto(match.group(1))
    return None


def _inferir_canal_por_numero(numero) -> str | None:
    texto = _texto(numero)
    if not texto:
        return None
    if re.fullmatch(r"\d{3}-\d{7}-\d{7}", texto):
        return "amazon"
    if texto.isdigit() and len(texto) >= 14:
        return "mercado_livre"
    if re.search(r"[A-Za-z]", texto) and re.search(r"\d", texto):
        return "shopee"
    return None


def _inferir_canal_por_loja_id(loja_id) -> str | None:
    return _LOJA_ID_CANAL_MAP.get(_texto(loja_id) or "")


def _formatar_endereco(value) -> str | None:
    if isinstance(value, dict):
        logradouro = _texto(
            _primeiro_preenchido(
                value.get("endereco"),
                value.get("logradouro"),
                value.get("descricao"),
                value.get("nome"),
            )
        )
        numero = _texto(value.get("numero"))
        bairro = _texto(value.get("bairro"))
        complemento = _texto(value.get("complemento"))
        municipio = _texto(
            _primeiro_preenchido(value.get("municipio"), value.get("cidade"))
        )
        uf = _texto(_primeiro_preenchido(value.get("uf"), value.get("estado")))

        linha_principal = logradouro or None
        if linha_principal and numero:
            linha_principal = f"{linha_principal}, {numero}"

        linha_secundaria = (
            ", ".join([parte for parte in (bairro, municipio, uf) if parte]) or None
        )
        partes = [
            parte for parte in (linha_principal, complemento, linha_secundaria) if parte
        ]
        return " - ".join(partes) or None

    return _texto(value)


def _texto_generico_baixo_valor(value) -> bool:
    texto = _texto(value)
    if not texto:
        return True
    texto_norm = texto.strip().lower()
    return texto_norm in {
        "outros",
        "outro",
        "online",
        "marketplace",
        "loja virtual",
        "e-commerce",
        "ecommerce",
        "id",
    } or texto_norm.startswith("id ")


def _formatar_data_iso(valor) -> str | None:
    texto = _texto(valor)
    if not texto:
        return None
    texto = texto.replace(" ", "T")
    try:
        return datetime.fromisoformat(texto).isoformat()
    except ValueError:
        return texto


def _detalhe_nota_valido(item: dict | None) -> bool:
    return (
        isinstance(item, dict)
        and bool(item)
        and bool(
            _primeiro_preenchido(
                item.get("id"),
                item.get("numero"),
                item.get("chaveAcesso"),
                item.get("contato"),
                item.get("itens"),
            )
        )
    )


def _tipo_pessoa_label(value, cpf_cnpj: str | None = None) -> str | None:
    texto = _texto(value)
    if texto:
        mapa = {
            "F": "Fisica",
            "J": "Juridica",
            "1": "Fisica",
            "2": "Juridica",
        }
        return mapa.get(texto.upper()) or texto

    numero_documento = _digitos(cpf_cnpj)
    if len(numero_documento) == 11:
        return "Fisica"
    if len(numero_documento) == 14:
        return "Juridica"
    return None


def _separar_data_hora(valor) -> tuple[str | None, str | None]:
    texto = _texto(valor)
    if not texto:
        return None, None

    texto_normalizado = texto
    if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", texto):
        texto_normalizado = texto.replace(" ", "T", 1)

    try:
        dt = datetime.fromisoformat(texto_normalizado)
        return dt.date().isoformat(), dt.strftime("%H:%M:%S")
    except ValueError:
        pass

    match = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})", texto)
    if match:
        return match.group(1), match.group(2)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        return texto, None
    if re.fullmatch(r"\d{2}:\d{2}:\d{2}", texto):
        return None, texto
    return _formatar_data_iso(texto), None


def _label_codigo(mapa: dict[str, str], valor) -> str | None:
    texto = _texto_relacionado(
        valor, "descricao", "nome", "label", fallback_to_id=False
    )
    if texto:
        return texto
    codigo = _texto(
        _primeiro_preenchido(
            _dict(valor).get("valor") if isinstance(valor, dict) else None, valor
        )
    )
    if not codigo:
        return None
    return mapa.get(codigo, codigo)


def _tipo_nota_label(modelo: int | str | None) -> str:
    return "NFC-e" if str(modelo or "") == "65" else "NF-e"


def _situacao_num(val) -> int:
    """Extrai o código real da situação retornada pelo Bling."""
    if isinstance(val, dict):
        if "valor" in val:
            return _coerce_int(val.get("valor"), 0)
        if "id" in val:
            return _coerce_int(val.get("id"), 0)
        return 0
    return _coerce_int(val, 0)


def _texto_situacao(val) -> str:
    if not isinstance(val, dict):
        return ""

    for chave in ("descricao", "descricaoSituacao", "nome", "label"):
        texto = str(val.get(chave) or "").strip()
        if texto:
            return texto.lower()
    return ""


def _status_nota_bling(item: dict) -> str:
    situacao = item.get("situacao")
    situacao_txt = _texto_situacao(situacao)
    chave = str(item.get("chaveAcesso") or item.get("chave") or "").strip()
    sit_num = _situacao_num(situacao)

    status_textual = _status_nota_por_texto(situacao_txt, chave=chave)
    if status_textual:
        return status_textual

    status_codigo = _status_nota_por_codigo(sit_num, chave=chave)
    if status_codigo:
        return status_codigo

    return _STATUS_MAP.get(sit_num, "Pendente")


def _status_nota_por_texto(situacao_txt: str, *, chave: str) -> str | None:
    for trecho, status in (
        ("cancel", "Cancelada"),
        ("rejeit", "Rejeitada"),
        ("deneg", "Denegada"),
        ("inutil", "Inutilizada"),
        ("autoriz", "Autorizada"),
        ("pend", "Pendente"),
    ):
        if trecho in situacao_txt:
            return status

    if "emit" in situacao_txt and not chave:
        return _STATUS_EMITIDA_DANFE
    return None


def _status_nota_por_codigo(sit_num: int, *, chave: str) -> str | None:
    if sit_num == 2 and not chave:
        return _STATUS_EMITIDA_DANFE
    if sit_num in {2, 5, 9} or (sit_num == 1 and chave):
        return "Autorizada"
    if sit_num == 4:
        return "Cancelada"
    if sit_num == 6:
        return "Rejeitada"
    return None


def _nota_autorizada_bling(item: dict) -> bool:
    return _status_nota_bling(item) == "Autorizada"


def _nota_cancelada_bling(item: dict) -> bool:
    return _status_nota_bling(item) == "Cancelada"


def _venda_usa_nfce(venda: Venda) -> bool:
    tipo = str(getattr(venda, "nfe_tipo", "") or "").strip().lower()
    modelo = str(getattr(venda, "nfe_modelo", "") or "").strip()
    return tipo in {"nfce", "1"} or modelo == "65"


def _extrair_valor_nota(item: dict) -> float:
    totais = item.get("totais") or {}
    pagamento = _dict(item.get("pagamento"))
    valor_direto = _primeiro_float(
        item.get("valorNota"),
        item.get("valorNotaNf"),
        item.get("valorTotalNf"),
        item.get("valorTotal"),
        item.get("valor_total"),
        item.get("total"),
        item.get("valor"),
        totais.get("valorTotal"),
        totais.get("valor_total"),
        totais.get("total"),
    )
    if valor_direto is not None:
        return valor_direto

    total_parcelas = _somar_parcelas_nota(pagamento, item)
    if total_parcelas is not None:
        return total_parcelas

    return _calcular_total_componentes_nota(totais, item)


def _primeiro_float(*candidatos) -> float | None:
    for valor in candidatos:
        try:
            if valor is None or valor == "":
                continue
            return float(valor)
        except (TypeError, ValueError):
            continue
    return None


def _somar_parcelas_nota(pagamento: dict, item: dict) -> float | None:
    parcelas = _list(
        _primeiro_preenchido(pagamento.get("parcelas"), item.get("parcelas"))
    )
    valores = [
        _coerce_float(
            _primeiro_preenchido(
                _dict(parcela).get("valor"),
                _dict(parcela).get("valorParcela"),
            ),
            None,
        )
        for parcela in parcelas
    ]
    valores_validos = [valor for valor in valores if valor is not None]
    return sum(valores_validos) if valores_validos else None


def _calcular_total_componentes_nota(totais: dict, item: dict) -> float:
    valor_produtos = _coerce_float(
        _primeiro_preenchido(totais.get("valorProdutos"), item.get("valorProdutos")),
        None,
    )
    if valor_produtos is None:
        return 0.0

    valor_frete = _coerce_float(
        _primeiro_preenchido(totais.get("valorFrete"), item.get("valorFrete")), 0.0
    )
    valor_seguro = _coerce_float(
        _primeiro_preenchido(totais.get("valorSeguro"), item.get("valorSeguro")), 0.0
    )
    outras_despesas = _coerce_float(
        _primeiro_preenchido(totais.get("outrasDespesas"), item.get("outrasDespesas")),
        0.0,
    )
    valor_desconto = _coerce_float(
        _primeiro_preenchido(totais.get("valorDesconto"), item.get("valorDesconto")),
        0.0,
    )
    return max(
        valor_produtos
        + (valor_frete or 0.0)
        + (valor_seguro or 0.0)
        + (outras_despesas or 0.0)
        - (valor_desconto or 0.0),
        0.0,
    )


def _parse_data_referencia(value) -> datetime | None:
    texto = _texto(value)
    if not texto:
        return None

    candidatos = [
        texto,
        texto.replace("Z", "+00:00"),
        texto.split("T")[0],
    ]
    for candidato in candidatos:
        try:
            return datetime.fromisoformat(candidato)
        except ValueError:
            continue

    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto[:10], formato)
        except ValueError:
            continue
    return None


def _formatar_data_param_bling(value) -> str | None:
    data_ref = _parse_data_referencia(value)
    return data_ref.date().isoformat() if data_ref else None


def _planejar_sincronizacao_bling_nfes(
    *,
    force_refresh: bool,
    data_inicial: str | None,
    data_final: str | None,
    cache_total: int,
    cache_intervalo_tem_dados: bool,
    ultimo_sync: datetime | None,
    ultima_data_emissao: datetime | None,
    agora: datetime | None = None,
) -> tuple[bool, str | None, str | None, str]:
    agora_ref = agora or datetime.now()
    data_final_sync = (
        _formatar_data_param_bling(data_final) or agora_ref.date().isoformat()
    )
    data_inicial_sync = _formatar_data_param_bling(data_inicial)
    cache_stale = (
        force_refresh
        or not ultimo_sync
        or (agora_ref - ultimo_sync).total_seconds() > _NFE_SYNC_CACHE_TTL_SECONDS
    )

    if data_inicial or data_final:
        if force_refresh or not cache_intervalo_tem_dados or cache_stale:
            return True, data_inicial_sync, data_final_sync, "intervalo_especifico"
        return False, None, None, "cache_intervalo_recente"

    if cache_total <= 0:
        return (
            True,
            (agora_ref - timedelta(days=_NFE_SYNC_DEFAULT_LOOKBACK_DAYS))
            .date()
            .isoformat(),
            data_final_sync,
            "bootstrap_cache_vazio",
        )

    if not cache_stale:
        return False, None, None, "cache_global_recente"

    base_data = ultima_data_emissao or agora_ref
    janela_inicial = max(
        (base_data - timedelta(days=_NFE_SYNC_SAFETY_LOOKBACK_DAYS)).date(),
        (agora_ref - timedelta(days=_NFE_SYNC_DEFAULT_LOOKBACK_DAYS)).date(),
    )
    return (
        True,
        janela_inicial.isoformat(),
        data_final_sync,
        "janela_incremental_recente",
    )


def _status_local_ultima_nf(ultima_nf: dict) -> str:
    situacao_textual = _texto(
        _primeiro_preenchido(ultima_nf.get("situacao"), ultima_nf.get("status"))
    )
    if situacao_textual:
        if situacao_textual.isdigit():
            return _STATUS_MAP.get(_coerce_int(situacao_textual, 0), situacao_textual)
        return situacao_textual

    situacao_codigo = _coerce_int(ultima_nf.get("situacao_codigo"), 0)
    return _STATUS_MAP.get(situacao_codigo, "Pendente")
