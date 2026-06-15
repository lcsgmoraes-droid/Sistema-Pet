"""
Integração com API Bling v3 para emissão de NF-e e NFC-e
Documentação: https://developer.bling.com.br/
"""

import os
import requests
import threading
import time
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
import json
from pathlib import Path
from dotenv import dotenv_values
from app.utils.logger import logger
from app.kit_config_fiscal_models import KitConfigFiscal
from app.produto_config_fiscal_models import ProdutoConfigFiscal
from app.produtos_models import Produto

# Configurações da API Bling
BLING_API_BASE_URL = "https://api.bling.com.br/Api/v3"
BLING_NFE_SERIE_PADRAO = 1
BLING_NFCE_SERIE_PADRAO = 3

# Arquivo para controle de expiração do token
TOKEN_CONTROL_FILE = Path("bling_token_control.json")
_BLING_RATE_LOCK = threading.Lock()
_BLING_LAST_REQUEST_AT = 0.0
_BLING_MIN_INTERVAL_SECONDS = 0.42

ENV_PATHS = [
    Path("/opt/petshop/.env"),
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
]


def _get_shared_env_path() -> Optional[Path]:
    for path in ENV_PATHS:
        if path.exists():
            return path
    return None


def _load_bling_runtime_config() -> Dict[str, str]:
    values: Dict[str, str] = {}
    env_path = _get_shared_env_path()

    if env_path:
        try:
            values = {
                key: str(value)
                for key, value in dotenv_values(env_path).items()
                if value is not None
            }
        except Exception as error:
            logger.warning(f"Nao foi possivel reler configuracao compartilhada do Bling em {env_path}: {error}")

    def pick(name: str, default: str = "") -> str:
        return (values.get(name) or os.getenv(name) or default).strip()

    return {
        "access_token": pick("BLING_ACCESS_TOKEN"),
        "refresh_token": pick("BLING_REFRESH_TOKEN"),
        "client_id": pick("BLING_CLIENT_ID"),
        "client_secret": pick("BLING_CLIENT_SECRET"),
        "enable_jwt": pick("BLING_ENABLE_JWT", "1"),
        "ambiente": pick("BLING_NFE_AMBIENTE", "rascunho"),
    }


def _limpar_texto_fiscal(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _primeiro_texto_fiscal(*values) -> Optional[str]:
    for value in values:
        text = _limpar_texto_fiscal(value)
        if text is not None:
            return text
    return None


def _aguardar_slot_bling() -> None:
    global _BLING_LAST_REQUEST_AT

    with _BLING_RATE_LOCK:
        now = time.monotonic()
        wait_for = _BLING_MIN_INTERVAL_SECONDS - (now - _BLING_LAST_REQUEST_AT)
        if wait_for > 0:
            time.sleep(wait_for)
            now = time.monotonic()
        _BLING_LAST_REQUEST_AT = now


def _tempo_espera_rate_limit_bling(response, tentativa: int) -> float:
    retry_after = None
    if response is not None:
        retry_after = getattr(response, "headers", {}).get("Retry-After")

    try:
        if retry_after:
            return min(max(float(retry_after), 1.0), 8.0)
    except (TypeError, ValueError):
        pass

    return min(1.2 + tentativa * 0.8, 5.0)


def _erro_rate_limit_bling(error: requests.exceptions.HTTPError) -> bool:
    response = getattr(error, "response", None)
    if response is not None and response.status_code == 429:
        return True

    mensagem = str(error)
    if response is not None:
        mensagem = f"{mensagem} {getattr(response, 'text', '')}"

    mensagem = mensagem.upper()
    return "TOO_MANY_REQUESTS" in mensagem or "429" in mensagem


def _sku_produto(produto) -> str:
    return (
        _limpar_texto_fiscal(getattr(produto, "codigo", None))
        or _limpar_texto_fiscal(getattr(produto, "codigo_barras", None))
        or f"ID {getattr(produto, 'id', 'sem-id')}"
    )


def _resolver_fiscal_item_nfe(db: Session, venda, item_venda) -> Dict[str, Optional[str]]:
    produto = getattr(item_venda, "produto", None)
    if not produto:
        return {
            "ncm": None,
            "cest": None,
            "origem_mercadoria": None,
            "cfop": None,
            "cst_icms": None,
        }

    tenant_id = getattr(venda, "tenant_id", None) or getattr(produto, "tenant_id", None)
    kit_fiscal = None
    produto_fiscal = None

    if db is not None and tenant_id is not None:
        if getattr(produto, "tipo_produto", None) == "KIT":
            kit_fiscal = (
                db.query(KitConfigFiscal)
                .filter(
                    KitConfigFiscal.tenant_id == tenant_id,
                    KitConfigFiscal.produto_kit_id == produto.id,
                )
                .first()
            )

        produto_fiscal = (
            db.query(ProdutoConfigFiscal)
            .filter(
                ProdutoConfigFiscal.tenant_id == tenant_id,
                ProdutoConfigFiscal.produto_id == produto.id,
            )
            .first()
        )

    return {
        "ncm": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "ncm", None),
            getattr(produto_fiscal, "ncm", None),
            getattr(produto, "ncm", None),
        ),
        "cest": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cest", None),
            getattr(produto_fiscal, "cest", None),
            getattr(produto, "cest", None),
        ),
        "origem_mercadoria": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "origem_mercadoria", None),
            getattr(produto_fiscal, "origem_mercadoria", None),
            getattr(produto, "origem", None),
        ),
        "cfop": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cfop_venda", None),
            getattr(produto_fiscal, "cfop_venda", None),
            getattr(produto, "cfop", None),
            "5102",
        ),
        "cst_icms": _primeiro_texto_fiscal(
            getattr(kit_fiscal, "cst_icms", None),
            getattr(produto_fiscal, "cst_icms", None),
            "102",
        ),
    }


_NCM_SUBSTITUICOES_SEGURAS = {
    "42010000": {
        "valor": "42010090",
        "motivo": "4201.00.00 e um codigo de familia; para guias, coleiras e enforcadores de outros materiais o subitem usual e 4201.00.90.",
    },
}

_NCM_POR_TERMO_PRODUTO = [
    (
        (
            "racao",
            "ração",
            "sache",
            "sachê",
            "petisco",
            "alimento para cao",
            "alimento para caes",
            "alimento para cão",
            "alimento para cães",
            "alimento para gato",
            "alimento para gatos",
        ),
        "23091000",
        "Produto parece alimento para caes ou gatos acondicionado para venda a retalho; confirme com o responsavel fiscal.",
    ),
    (
        ("guia", "coleira", "enforcador", "peitoral", "focinheira"),
        "42010090",
        "Produto parece acessorio para animais; sugestao conservadora para outros materiais.",
    ),
]


def _somente_digitos(value) -> str:
    return "".join(filter(str.isdigit, str(value or "")))


def _ncm_normalizado(value) -> Optional[str]:
    digits = _somente_digitos(value)
    return digits if digits else None


def _ncm_basico_aceitavel(value) -> bool:
    ncm = _ncm_normalizado(value)
    return bool(
        ncm
        and len(ncm) == 8
        and ncm != "00000000"
        and ncm not in _NCM_SUBSTITUICOES_SEGURAS
    )


def _texto_busca_produto(value) -> str:
    texto = str(value or "").lower()
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in normalizado if not unicodedata.combining(ch))


def _sugerir_ncm_por_historico(db: Session, tenant_id, produto) -> Optional[Dict[str, str]]:
    if db is None or tenant_id is None or produto is None:
        return None

    filtros_base = [
        ProdutoConfigFiscal.tenant_id == tenant_id,
        ProdutoConfigFiscal.produto_id != produto.id,
        ProdutoConfigFiscal.ncm.isnot(None),
    ]

    filtros_escopo = []
    if getattr(produto, "categoria_id", None):
        filtros_escopo.append(Produto.categoria_id == produto.categoria_id)
    if getattr(produto, "departamento_id", None):
        filtros_escopo.append(Produto.departamento_id == produto.departamento_id)

    if not filtros_escopo:
        return None

    candidatos = (
        db.query(ProdutoConfigFiscal.ncm)
        .join(Produto, Produto.id == ProdutoConfigFiscal.produto_id)
        .filter(*filtros_base)
        .filter(*filtros_escopo[:1])
        .limit(50)
        .all()
    )
    ncms = [
        _ncm_normalizado(row[0])
        for row in candidatos
        if _ncm_basico_aceitavel(row[0])
    ]
    if not ncms:
        return None

    ncm, ocorrencias = Counter(ncms).most_common(1)[0]
    return {
        "valor": ncm,
        "motivo": f"NCM mais usado em produtos parecidos cadastrados ({ocorrencias} ocorrencia(s)).",
    }


def _sugerir_ncm(produto, fiscal_item: Dict[str, Optional[str]], db: Session, tenant_id) -> Optional[Dict[str, str]]:
    ncm_atual = _ncm_normalizado(fiscal_item.get("ncm"))
    if ncm_atual in _NCM_SUBSTITUICOES_SEGURAS:
        return _NCM_SUBSTITUICOES_SEGURAS[ncm_atual]

    historico = _sugerir_ncm_por_historico(db, tenant_id, produto)
    if historico:
        return historico

    nome = _texto_busca_produto(getattr(produto, "nome", ""))
    for termos, ncm, motivo in _NCM_POR_TERMO_PRODUTO:
        if any(_texto_busca_produto(termo) in nome for termo in termos):
            return {"valor": ncm, "motivo": motivo}

    return None


def prevalidar_fiscal_venda(venda, tipo_nota: str = "nfce", db: Session = None) -> Dict:
    tenant_id = getattr(venda, "tenant_id", None)
    correcoes = []
    bloqueios = []

    if not getattr(venda, "itens", None):
        bloqueios.append({
            "campo": "itens",
            "mensagem": "Venda nao possui itens para emitir nota fiscal.",
        })

    if tipo_nota == "nfe":
        cliente = getattr(venda, "cliente", None)
        cpf_cnpj = _somente_digitos(getattr(cliente, "cnpj", None) or getattr(cliente, "cpf", None))
        if len(cpf_cnpj) != 14:
            bloqueios.append({
                "campo": "cliente.cnpj",
                "mensagem": "NF-e requer cliente empresa com CNPJ cadastrado. Para pessoa fisica use NFC-e.",
            })

    for item in getattr(venda, "itens", []) or []:
        produto = getattr(item, "produto", None)
        if not produto:
            bloqueios.append({
                "campo": "produto",
                "mensagem": f"Item {getattr(item, 'id', '')}: produto nao vinculado.",
            })
            continue

        fiscal_item = _resolver_fiscal_item_nfe(db, venda, item)
        sku = _sku_produto(produto)
        ncm_atual = _ncm_normalizado(fiscal_item.get("ncm"))
        origem_atual = _limpar_texto_fiscal(fiscal_item.get("origem_mercadoria"))

        if not _ncm_basico_aceitavel(ncm_atual):
            sugestao_ncm = _sugerir_ncm(produto, fiscal_item, db, tenant_id)
            if sugestao_ncm:
                correcoes.append({
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "sku": sku,
                    "campo": "ncm",
                    "valor_atual": ncm_atual or "",
                    "valor_sugerido": sugestao_ncm["valor"],
                    "motivo": sugestao_ncm["motivo"],
                })
            else:
                bloqueios.append({
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "sku": sku,
                    "campo": "ncm",
                    "mensagem": "NCM ausente ou invalido e o sistema ainda nao tem sugestao segura.",
                })

        if origem_atual is None:
            correcoes.append({
                "produto_id": produto.id,
                "produto_nome": produto.nome,
                "sku": sku,
                "campo": "origem_mercadoria",
                "valor_atual": "",
                "valor_sugerido": "0",
                "motivo": "Padrao para mercadoria nacional quando a origem nao foi informada.",
            })

    return {
        "success": True,
        "pode_emitir": not bloqueios and not correcoes,
        "requer_autorizacao": bool(correcoes),
        "correcoes": correcoes,
        "bloqueios": bloqueios,
    }


def aplicar_correcoes_fiscais_venda(venda, tipo_nota: str, db: Session, user_id=None) -> Dict:
    validacao = prevalidar_fiscal_venda(venda, tipo_nota, db)
    if validacao["bloqueios"]:
        raise ValueError("Existem pendencias fiscais sem sugestao segura para correcao automatica.")

    tenant_id = getattr(venda, "tenant_id", None)
    por_produto = {}
    for correcao in validacao["correcoes"]:
        por_produto.setdefault(correcao["produto_id"], []).append(correcao)

    for produto_id, correcoes in por_produto.items():
        config = (
            db.query(ProdutoConfigFiscal)
            .filter(
                ProdutoConfigFiscal.tenant_id == tenant_id,
                ProdutoConfigFiscal.produto_id == produto_id,
            )
            .first()
        )
        if not config:
            config = ProdutoConfigFiscal(
                tenant_id=tenant_id,
                produto_id=produto_id,
                herdado_da_empresa=False,
            )
            db.add(config)

        for correcao in correcoes:
            campo = correcao["campo"]
            valor = correcao["valor_sugerido"]
            if campo == "ncm":
                config.ncm = valor
            elif campo == "origem_mercadoria":
                config.origem_mercadoria = valor

        config.observacao_fiscal = (
            f"Correcao fiscal autorizada no PDV em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            + (f" por usuario {user_id}" if user_id else "")
        )

    return validacao


class BlingAPI:
    """Cliente para integração com Bling API v3"""
    
    def __init__(self):
        runtime_config = _load_bling_runtime_config()
        self.base_url = BLING_API_BASE_URL
        self.access_token = runtime_config["access_token"]
        self.refresh_token = runtime_config["refresh_token"]
        self.client_id = runtime_config["client_id"]
        self.client_secret = runtime_config["client_secret"]
        self.enable_jwt = runtime_config["enable_jwt"]
        # Ambiente: 'rascunho', 'homologacao' ou 'producao'
        self.ambiente = runtime_config["ambiente"]
        
        if not self.access_token:
            raise ValueError("BLING_ACCESS_TOKEN não configurado no .env")
        
    
    def _verificar_e_renovar_token(self):
        """
        Verifica se o token está próximo de expirar e renova automaticamente
        Access Token expira em 6 horas
        Refresh Token expira em 60 dias (se não for usado)
        """
        try:
            # Ler arquivo de controle
            if TOKEN_CONTROL_FILE.exists():
                with open(TOKEN_CONTROL_FILE, 'r') as f:
                    control_data = json.load(f)
                
                proxima_renovacao = datetime.fromisoformat(control_data.get('proxima_renovacao', '2020-01-01'))
                
                # Se passou do horário de renovação OU se está perto de expirar (5 horas)
                agora = datetime.now()
                if agora >= proxima_renovacao or (proxima_renovacao - agora).total_seconds() < 3600:
                    logger.info("⏰ Token próximo de expirar. Renovando automaticamente...")
                    self._renovar_token_automatico()
            else:
                # Primeira vez - criar arquivo de controle
                self._salvar_controle_token()
                
        except Exception as e:
            logger.info(f"⚠️ Erro ao verificar expiração do token: {e}")
            # Continua mesmo com erro - não bloqueia a aplicação
    
    def _salvar_controle_token(self):
        """Salva informações de controle do token"""
        try:
            agora = datetime.now()
            # Access token expira em 6 horas
            proxima_renovacao = agora + timedelta(hours=5, minutes=30)  # Renova 30 min antes
            
            control_data = {
                'ultima_renovacao': agora.isoformat(),
                'proxima_renovacao': proxima_renovacao.isoformat(),
                'renovacoes_automaticas': 1
            }
            
            # Ler dados existentes se houver
            if TOKEN_CONTROL_FILE.exists():
                with open(TOKEN_CONTROL_FILE, 'r') as f:
                    existing_data = json.load(f)
                control_data['renovacoes_automaticas'] = existing_data.get('renovacoes_automaticas', 0) + 1
            
            with open(TOKEN_CONTROL_FILE, 'w') as f:
                json.dump(control_data, f, indent=2)
                
            logger.info(f"✅ Controle de token atualizado. Próxima renovação: {proxima_renovacao.strftime('%d/%m/%Y %H:%M')}")
            
        except Exception as e:
            logger.info(f"⚠️ Erro ao salvar controle do token: {e}")
    
    def _renovar_token_automatico(self):
        """Renova o token automaticamente"""
        try:
            tokens = self.renovar_access_token()
            self.access_token = tokens['access_token']
            self._salvar_controle_token()
            logger.info("✅ Token renovado com sucesso automaticamente!")
            return True
        except Exception as e:
            logger.info(f"❌ ERRO ao renovar token automaticamente: {e}")
            logger.warning("⚠️ ATENÇÃO: Token do Bling pode estar expirado!")
            logger.info("💡 Solução: Reautentique no Bling via interface do sistema")
            return False
    
    def _get_headers(self) -> Dict:
        """Retorna headers com autenticação"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "enable-jwt": self.enable_jwt,
        }

    def _deve_renovar_token_apos_erro(self, error: requests.exceptions.HTTPError) -> bool:
        response = getattr(error, "response", None)
        if response is None or response.status_code != 401:
            return False

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        error_data = payload.get("error") if isinstance(payload, dict) else {}
        error_type = str((error_data or {}).get("type") or "").strip().lower()
        mensagem = " ".join(
            str(parte or "").strip().lower()
            for parte in (
                error_type,
                (error_data or {}).get("message"),
                (error_data or {}).get("description"),
                getattr(response, "text", ""),
            )
            if str(parte or "").strip()
        )
        return "invalid_token" in mensagem or "unauthorized" in mensagem
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Faz requisição para API do Bling"""
        url = f"{self.base_url}{endpoint}"
        token_renovado = False

        for tentativa in range(5):
            headers = self._get_headers()

            try:
                _aguardar_slot_bling()

                if method == "GET":
                    response = requests.get(url, headers=headers, params=data, timeout=30)
                elif method == "POST":
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                elif method == "PUT":
                    response = requests.put(url, headers=headers, json=data, timeout=30)
                elif method == "DELETE":
                    response = requests.delete(url, headers=headers, timeout=30)
                else:
                    raise ValueError(f"Método HTTP inválido: {method}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if _erro_rate_limit_bling(e) and tentativa < 4:
                    espera = _tempo_espera_rate_limit_bling(getattr(e, "response", None), tentativa)
                    logger.warning(
                        f"Bling rate limit em {endpoint}. Aguardando {espera:.1f}s antes de repetir ({tentativa + 1}/5).",
                    )
                    time.sleep(espera)
                    continue

                if not token_renovado and self._deve_renovar_token_apos_erro(e):
                    logger.warning(f"Bling retornou token invalido ao consultar {endpoint}. Tentando renovar e repetir.")
                    token_renovado = True
                    if self._renovar_token_automatico():
                        continue

                if _erro_rate_limit_bling(e):
                    raise Exception(
                        "Limite temporario de requisicoes do Bling atingido (HTTP 429). "
                        "Aguarde alguns segundos e tente emitir novamente."
                    )

                error_msg = f"Erro na API Bling: {e}"
                try:
                    error_data = e.response.json()
                    error_msg = f"{error_msg} - {error_data}"
                except Exception:
                    error_msg = f"{error_msg} - {e.response.text}"
                raise Exception(error_msg)
            except Exception as e:
                raise Exception(f"Erro ao comunicar com Bling: {str(e)}")

        raise Exception("Erro ao comunicar com Bling: tentativa de renovacao nao retornou resposta valida")
    
    def validar_conexao(self) -> bool:
        """Testa se a conexão com Bling está funcionando"""
        try:
            # Tenta listar notas (limite 1 para ser rápido)
            self._request("GET", "/nfe", data={"limite": 1})
            return True
        except Exception:
            return False
    
    def emitir_nota_fiscal(self, venda, tipo_nota: str = "nfce", db: Session = None, transmitir: Optional[bool] = None) -> Dict:
        """
        Emite nota fiscal (NF-e ou NFC-e) para uma venda
        
        Args:
            venda: Objeto Venda do banco
            tipo_nota: 'nfe' (modelo 55) ou 'nfce' (modelo 65)
            db: Sessão do banco
            transmitir: quando True, envia a nota para SEFAZ logo apos criar no Bling
            
        Returns:
            Dados da nota emitida
        """
        # Validações básicas
        if not venda.itens or len(venda.itens) == 0:
            raise ValueError("Venda não possui itens")
        
        # Validar dados fiscais dos produtos
        logger.info("\n=== VALIDANDO DADOS FISCAIS ===")
        erros_produtos = []
        for item in venda.itens:
            produto = item.produto
            if not produto:
                erros_produtos.append(f"Item {item.id or ''}: produto nao vinculado")
                continue

            fiscal_item = _resolver_fiscal_item_nfe(db, venda, item)
            sku = _sku_produto(produto)
            logger.info(f"Produto: {produto.nome} (SKU {sku})")
            logger.info(f"  - NCM: {fiscal_item.get('ncm') or 'NAO CADASTRADO'}")
            logger.info(f"  - CEST: {fiscal_item.get('cest') or 'NAO CADASTRADO'}")
            logger.info(f"  - Origem: {fiscal_item.get('origem_mercadoria') or 'NAO CADASTRADO'}")
            
            if not _ncm_basico_aceitavel(fiscal_item.get("ncm")):
                erros_produtos.append(f"{produto.nome} (SKU {sku}): NCM nao cadastrado ou invalido")
            if not fiscal_item.get("origem_mercadoria"):
                erros_produtos.append(f"{produto.nome} (SKU {sku}): Origem da mercadoria nao cadastrada")
        
        if erros_produtos:
            raise ValueError(
                "Produtos sem dados fiscais obrigatórios:\n" + "\n".join(erros_produtos) +
                "\n\nCadastre NCM e Origem nas informações fiscais do produto antes de emitir NF-e."
            )
        
        # Validações por tipo
        if tipo_nota == "nfe":
            if not venda.cliente or not (venda.cliente.cpf or venda.cliente.cnpj):
                raise ValueError("NF-e requer cliente com CPF/CNPJ")
            
            cpf_cnpj = venda.cliente.cnpj or venda.cliente.cpf
            cpf_cnpj = ''.join(filter(str.isdigit, cpf_cnpj))
            if len(cpf_cnpj) == 11:
                raise ValueError("NF-e requer CNPJ (empresa). Para pessoa física use NFC-e")
        
        # Montar payload
        payload = self._montar_payload(venda, tipo_nota, db)
        
        # DEBUG: Mostrar payload completo
        logger.info("\n=== PAYLOAD ENVIADO PARA BLING ===")
        import json
        logger.debug(json.dumps(payload, indent=2, ensure_ascii=False))
        logger.info("=" * 50)
        
        # Definir endpoint correto conforme tipo de nota
        # NF-e: /nfe | NFC-e: /nfce
        endpoint = "/nfce" if tipo_nota == "nfce" else "/nfe"
        logger.info(f"📡 Endpoint: {endpoint}")
        
        # Enviar para Bling
        response = self._request("POST", endpoint, data=payload)
        
        deve_transmitir = transmitir if transmitir is not None else self.ambiente in ["homologacao", "producao"]

        # Quando solicitado, enviar para SEFAZ logo apos criar a nota no Bling.
        if deve_transmitir:
            nota_id = response.get('data', {}).get('id')
            if nota_id:
                logger.info(f"\n{'⚠️' if self.ambiente == 'homologacao' else '🚨'} Enviando nota #{nota_id} para SEFAZ...")
                try:
                    # Endpoint para enviar nota para SEFAZ (mesmo endpoint base)
                    envio_response = self._request("POST", f"{endpoint}/{nota_id}/enviar")
                    logger.info("✅ Nota enviada para SEFAZ!")
                    logger.info(f"Resposta: {envio_response}")
                    response["transmissao"] = {
                        "success": True,
                        "data": envio_response.get("data", envio_response),
                    }
                    
                    # Atualizar response com dados do envio
                    if envio_response.get('data'):
                        response['data'].update(envio_response.get('data', {}))
                except Exception as e:
                    logger.info(f"❌ Erro ao enviar nota para SEFAZ: {e}")
                    response["transmissao"] = {
                        "success": False,
                        "erro": str(e),
                    }
        
        return response
    
    def _montar_payload(self, venda, tipo_nota: str, db: Session = None) -> Dict:
        """Monta payload para emissão de nota"""
        cliente = venda.cliente
        
        # Modelo e série (modelo deve ser número inteiro, não string!)
        modelo = 55 if tipo_nota == "nfe" else 65
        serie = BLING_NFE_SERIE_PADRAO if tipo_nota == "nfe" else BLING_NFCE_SERIE_PADRAO
        
        # Contato: NF-e exige documento; NFC-e pode identificar apenas pelo nome.
        contato = None
        if cliente and _limpar_texto_fiscal(getattr(cliente, "nome", None)):
            cpf_cnpj = cliente.cnpj or cliente.cpf or ""
            cpf_cnpj = ''.join(filter(str.isdigit, cpf_cnpj))
            tem_documento_valido = len(cpf_cnpj) in (11, 14)
            tipo_pessoa = "J" if len(cpf_cnpj) == 14 else "F"

            tem_endereco_completo = (
                cliente.endereco and
                cliente.cidade and
                cliente.estado and
                cliente.cep
            )

            contato = {
                "nome": cliente.nome,
                "tipoPessoa": tipo_pessoa,
                "email": cliente.email or "",
                "telefone": cliente.telefone or "",
            }

            if tem_documento_valido:
                contato["numeroDocumento"] = cpf_cnpj

            if tipo_nota == "nfe" or tem_endereco_completo:
                contato["endereco"] = {
                    "logradouro": cliente.endereco or "",
                    "numero": cliente.numero or "S/N",
                    "complemento": cliente.complemento or "",
                    "bairro": cliente.bairro or "",
                    "cep": ''.join(filter(str.isdigit, cliente.cep or '')),
                    "municipio": cliente.cidade or "",
                    "uf": cliente.estado or "",
                    "pais": "Brasil"
                }
        
        # Itens
        itens = []
        for idx, item_venda in enumerate(venda.itens, start=1):
            produto = item_venda.produto
            fiscal_item = _resolver_fiscal_item_nfe(db, venda, item_venda)
            
            valor_unitario = float(item_venda.preco_unitario or 0)
            desconto = float(item_venda.desconto_item or 0)
            quantidade = float(item_venda.quantidade or 1)
            valor_total = (valor_unitario - desconto) * quantidade
            
            item = {
                "numero": idx,
                "codigo": produto.codigo,
                "descricao": produto.nome,
                "quantidade": quantidade,
                "unidade": produto.unidade or "UN",
                "valor": valor_unitario,
                "desconto": desconto * quantidade,
                "total": valor_total,
                "ncm": _ncm_normalizado(fiscal_item.get("ncm")) or "",
                "cfop": fiscal_item.get("cfop") or "5102",
                "icms": {
                    "situacaoTributaria": fiscal_item.get("cst_icms") or "102",
                    "origem": fiscal_item.get("origem_mercadoria") or "0"
                }
            }
            itens.append(item)
        
        # Totais
        valor_produtos = sum((float(i.preco_unitario or 0) - float(i.desconto_item or 0)) * float(i.quantidade or 1) for i in venda.itens)
        desconto_total = float(venda.desconto_valor or 0)
        taxa_entrega = getattr(venda, "taxa_entrega_total", None)
        if taxa_entrega is None:
            taxa_entrega = getattr(venda, "taxa_entrega", 0)
        valor_frete = float(taxa_entrega or 0) if venda.tem_entrega else 0
        valor_total = valor_produtos - desconto_total + valor_frete
        
        # Definir situação e finalidade conforme ambiente configurado
        situacao = 0  # 0 = Rascunho (pendente)
        finalidade = 1  # 1 = NF-e normal (sempre usar 1, o ambiente é definido no envio)
        
        # Definir tipo correto conforme o modelo
        # tipo: 0 = NF-e (modelo 55), 1 = NFC-e (modelo 65)
        tipo_bling = 1 if modelo == 65 else 0
        
        if self.ambiente == "homologacao":
            logger.warning("⚠️  MODO HOMOLOGAÇÃO: Nota será enviada para SEFAZ de TESTE")
        elif self.ambiente == "producao":
            logger.info("🚨 MODO PRODUÇÃO: Nota será enviada para SEFAZ REAL")
        else:
            logger.info("📝 MODO RASCUNHO: Nota ficará pendente no Bling (não será enviada para SEFAZ)")
        
        # Payload completo
        payload = {
            "tipo": tipo_bling,
            "modelo": modelo,
            "situacao": situacao,
            "finalidade": finalidade,
            "serie": serie,
            # Numero em branco deixa o Bling aplicar a proxima sequencia configurada.
            "numero": None,
            "dataEmissao": datetime.now().strftime("%Y-%m-%d"),
            "dataOperacao": venda.data_venda.strftime("%Y-%m-%d") if venda.data_venda else datetime.now().strftime("%Y-%m-%d"),
            # ✅ RASTREAMENTO: Vincula venda do nosso sistema com nota no Bling
            "numeroPedidoLoja": f"VENDA-{venda.id}",
            # ✅ NATUREZA DE OPERAÇÃO: ID da natureza cadastrada no Bling
            # ID 15103736273 = "Venda de mercadoria - NFC-e" (descoberto automaticamente)
            "naturezaOperacao": {"id": 15103736273},
            "itens": itens,
            "totais": {
                "valorProdutos": valor_produtos,
                "valorFrete": valor_frete,
                "valorDesconto": desconto_total,
                "valorTotal": valor_total
            },
            "informacoesAdicionais": {
                "informacoesComplementares": f"Venda #{venda.id} - CorePet - Emitida em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            }
        }
        
        # Adicionar contato se houver
        if contato:
            payload["contato"] = contato
        
        # NFC-e: indicador de presença (número inteiro!)
        if tipo_nota == "nfce":
            # 1 = Operação presencial (padrão para loja física)
            payload["indicadorPresenca"] = 1
        
        return payload
    
    def consultar_nfe(self, nfe_id: int) -> Dict:
        """Consulta dados de uma NF-e"""
        resultado = self._request("GET", f"/nfe/{nfe_id}")
        # Extrair dados da chave 'data' se existir
        return resultado.get('data', resultado)
    
    def consultar_nfce(self, nfce_id: int) -> Dict:
        """Consulta dados de uma NFC-e"""
        resultado = self._request("GET", f"/nfce/{nfce_id}")
        # Extrair dados da chave 'data' se existir
        return resultado.get('data', resultado)
    
    def baixar_xml(self, nfe_id: int) -> str:
        """Baixa XML da NF-e"""
        response = self._request("GET", f"/nfe/{nfe_id}/xml")
        return response.get("xml", "")
    
    def cancelar_nfe(self, nfe_id: int, justificativa: str) -> Dict:
        """Cancela uma NF-e"""
        if len(justificativa) < 15:
            raise ValueError("Justificativa deve ter no mínimo 15 caracteres")
        
        payload = {"justificativa": justificativa}
        return self._request("POST", f"/nfe/{nfe_id}/cancelar", data=payload)
    
    def carta_correcao(self, nfe_id: int, correcao: str) -> Dict:
        """Emite Carta de Correção Eletrônica (CC-e) para uma NF-e"""
        if len(correcao) < 15:
            raise ValueError("Correção deve ter no mínimo 15 caracteres")
        
        payload = {"correcao": correcao}
        return self._request("POST", f"/nfe/{nfe_id}/carta-correcao", data=payload)
    
    def baixar_danfe(self, nfe_id: int) -> bytes:
        """Baixa PDF da DANFE"""
        url = f"{self.base_url}/nfe/{nfe_id}/danfe"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"Erro ao baixar DANFE: {str(e)}")
    
    def listar_nfes(self, data_inicial: str = None, data_final: str = None, situacao: str = None) -> Dict:
        """Lista NF-es (modelo 55) com filtros"""
        params = {}
        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final
        if situacao:
            params["situacao"] = situacao

        return self._request("GET", "/nfe", data=params)

    def listar_nfces(self, data_inicial: str = None, data_final: str = None, situacao: str = None) -> Dict:
        """Lista NFC-es (modelo 65) com filtros"""
        params = {}
        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final
        if situacao:
            params["situacao"] = situacao

        return self._request("GET", "/nfce", data=params)
    
    # ============================================================================
    # GESTÃO DE PRODUTOS E ESTOQUE
    # ============================================================================
    
    def listar_produtos(self, codigo: str = None, nome: str = None, sku: str = None, pagina: int = 1, limite: int = 100) -> Dict:
        """
        Lista produtos do Bling com filtros
        
        Args:
            codigo: Filtrar por código do produto
            nome: Filtrar por nome (busca parcial)
            sku: Filtrar por SKU
            pagina: Número da página (começa em 1)
            limite: Itens por página (máx 100)
        """
        params = {
            "pagina": pagina,
            "limite": min(limite, 100)
        }
        
        if codigo:
            params["codigo"] = codigo
        if nome:
            params["nome"] = nome
        if sku:
            params["sku"] = sku
        
        return self._request("GET", "/produtos", data=params)
    
    def consultar_produto(self, produto_id: str) -> Dict:
        """
        Consulta dados completos de um produto do Bling
        
        Args:
            produto_id: ID do produto no Bling
        """
        resultado = self._request("GET", f"/produtos/{produto_id}")
        return resultado.get('data', resultado)
    
    def atualizar_estoque_produto(self, produto_id: str, estoque_novo: float, deposito_id: Optional[int] = None, observacao: str = "") -> Dict:
        """
        Atualiza estoque de um produto no Bling via POST /estoques (Balanço absoluto).

        Usa operação "B" (Balanço) para definir o saldo físico exato do produto.
        Endpoint correto para Bling API v3.

        Args:
            produto_id: ID do produto no Bling
            estoque_novo: Novo saldo físico de estoque (valor absoluto)
            deposito_id: ID do depósito (opcional, usa BLING_DEPOSITO_ID do .env se não informado)
            observacao: Observação para o lançamento
        """
        # Deposito: parâmetro > variável de ambiente > sem especificar (Bling usa o padrão)
        _deposito_id = deposito_id or os.getenv("BLING_DEPOSITO_ID")

        payload: Dict = {
            "produto": {"id": int(produto_id)},
            "operacao": "B",  # B = Balanço: define saldo absoluto
            "quantidade": float(estoque_novo),
            "observacoes": observacao or "Sync automatico - CorePet"
        }

        if _deposito_id:
            payload["deposito"] = {"id": int(_deposito_id)}

        return self._request("POST", "/estoques", data=payload)

    def consultar_saldo_estoque(self, produto_id: str, deposito_id: Optional[int] = None) -> Dict:
        """
        Consulta o saldo de estoque de um produto no Bling.

        Retorna saldoFisicoTotal (estoque físico real) e saldoVirtualTotal
        (descontando reservas de pedidos online).

        Args:
            produto_id: ID do produto no Bling
            deposito_id: ID do depósito específico (opcional)

        Returns:
            dict com saldoFisicoTotal, saldoVirtualTotal e lista de depositos
        """
        _deposito_id = deposito_id or os.getenv("BLING_DEPOSITO_ID")

        params: Dict = {"idsProdutos[]": produto_id}

        if _deposito_id:
            endpoint = f"/estoques/saldos/{_deposito_id}"
        else:
            endpoint = "/estoques/saldos"

        resultado = self._request("GET", endpoint, data=params)
        itens = resultado.get("data", [])
        if itens:
            return itens[0]  # Retorna o primeiro (filtrado por produto_id)
        return {}
    
    def consultar_pedido(self, pedido_id: str) -> Dict:
        """
        Busca pedido de VENDA completo pelo ID (incluindo itens).
        Necessário porque o webhook order.created não inclui os itens.
        Endpoint correto: /pedidos/vendas/{id}  (não /pedidos/{id} que é compras)
        """
        resultado = self._request("GET", f"/pedidos/vendas/{pedido_id}")
        return resultado.get("data", resultado)

    def listar_naturezas_operacoes(self) -> Dict:
        """
        Lista todas as naturezas de operação cadastradas no Bling
        Use para descobrir o ID correto da natureza "Venda presencial" ou "Venda de mercadoria"
        
        Returns:
            Dict com lista de naturezas: [{"id": 1, "descricao": "Venda de mercadoria", ...}]
        """
        return self._request("GET", "/naturezas-operacoes")
    
    def renovar_access_token(self, refresh_token: str = None) -> Dict:
        """
        Renova o access token usando o refresh token
        
        Args:
            refresh_token: Token de renovação (se None, usa o do .env)
            
        Returns:
            Dict com novos tokens: {"access_token": "...", "refresh_token": "...", "expires_in": 21600}
        """
        import base64
        
        refresh = (refresh_token or self.refresh_token or _load_bling_runtime_config().get("refresh_token") or "").strip()
        if not refresh:
            raise ValueError("BLING_REFRESH_TOKEN não configurado")
        
        # Basic Auth
        credentials = f'{self.client_id}:{self.client_secret}'
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'enable-jwt': self.enable_jwt,
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh
        }
        
        response = requests.post(
            'https://www.bling.com.br/Api/v3/oauth/token',
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            tokens = response.json()
            
            # Atualizar token na instância
            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            
            # Atualizar .env e variáveis em memória
            try:
                from app.bling_oauth_routes import _salvar_tokens
                _salvar_tokens(tokens["access_token"], tokens["refresh_token"])
            except Exception as e:
                logger.info(f"⚠️ Não foi possível persistir tokens no .env: {e}")
            
            return tokens
        else:
            raise Exception(f"Erro ao renovar token: {response.status_code} - {response.text}")


# Função auxiliar para facilitar uso
def emitir_nfe_venda(venda_id: int, tipo_nota: str, db: Session) -> Dict:
    """Função auxiliar para emitir NF-e de uma venda"""
    from app.vendas_models import Venda
    
    venda = db.query(Venda).filter(Venda.id == venda_id).first()
    if not venda:
        raise ValueError(f"Venda {venda_id} não encontrada")
    
    bling = BlingAPI()
    return bling.emitir_nota_fiscal(venda, tipo_nota, db)
