"""
Integração com API Bling v3 para emissão de NF-e e NFC-e
Documentação: https://developer.bling.com.br/
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
import json
from pathlib import Path
from app.utils.logger import logger

# Configurações da API Bling
BLING_API_BASE_URL = "https://www.bling.com.br/Api/v3"

# Arquivo para controle de expiração do token
TOKEN_CONTROL_FILE = Path("bling_token_control.json")


class BlingAPI:
    """Cliente para integração com Bling API v3"""
    
    def __init__(self):
        self.base_url = BLING_API_BASE_URL
        self.access_token = os.getenv("BLING_ACCESS_TOKEN")
        self.client_id = os.getenv("BLING_CLIENT_ID")
        self.client_secret = os.getenv("BLING_CLIENT_SECRET")
        # Ambiente: 'rascunho', 'homologacao' ou 'producao'
        self.ambiente = os.getenv("BLING_NFE_AMBIENTE", "rascunho")
        
        if not self.access_token:
            raise ValueError("BLING_ACCESS_TOKEN não configurado no .env")
        
        # Verificar se precisa renovar o token automaticamente
        self._verificar_e_renovar_token()
    
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
                
                ultima_renovacao = datetime.fromisoformat(control_data.get('ultima_renovacao', '2020-01-01'))
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
                'renovacoes_automaticas': control_data.get('renovacoes_automaticas', 0) + 1 if TOKEN_CONTROL_FILE.exists() else 1
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
            "Accept": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Faz requisição para API do Bling"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=data)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Método HTTP inválido: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Erro na API Bling: {e}"
            try:
                error_data = e.response.json()
                error_msg = f"{error_msg} - {error_data}"
            except:
                error_msg = f"{error_msg} - {e.response.text}"
            raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"Erro ao comunicar com Bling: {str(e)}")
    
    def validar_conexao(self) -> bool:
        """Testa se a conexão com Bling está funcionando"""
        try:
            # Tenta listar notas (limite 1 para ser rápido)
            self._request("GET", "/nfe", data={"limite": 1})
            return True
        except:
            return False
    
    def emitir_nota_fiscal(self, venda, tipo_nota: str = "nfce", db: Session = None) -> Dict:
        """
        Emite nota fiscal (NF-e ou NFC-e) para uma venda
        
        Args:
            venda: Objeto Venda do banco
            tipo_nota: 'nfe' (modelo 55) ou 'nfce' (modelo 65)
            db: Sessão do banco
            
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
            logger.info(f"Produto: {produto.nome}")
            logger.info(f"  - NCM: {produto.ncm or 'NÃO CADASTRADO'}")
            logger.info(f"  - CEST: {produto.cest or 'NÃO CADASTRADO'}")
            logger.info(f"  - Origem: {produto.origem or 'NÃO CADASTRADO'}")
            
            if not produto.ncm:
                erros_produtos.append(f"{produto.nome}: NCM não cadastrado")
            if not produto.origem:
                erros_produtos.append(f"{produto.nome}: Origem da mercadoria não cadastrada")
        
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
        payload = self._montar_payload(venda, tipo_nota)
        
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
        
        # Se for homologação ou produção, enviar para SEFAZ
        if self.ambiente in ["homologacao", "producao"]:
            nota_id = response.get('data', {}).get('id')
            if nota_id:
                logger.info(f"\n{'⚠️' if self.ambiente == 'homologacao' else '🚨'} Enviando nota #{nota_id} para SEFAZ...")
                try:
                    # Endpoint para enviar nota para SEFAZ (mesmo endpoint base)
                    envio_response = self._request("POST", f"{endpoint}/{nota_id}/enviar")
                    logger.info(f"✅ Nota enviada para SEFAZ!")
                    logger.info(f"Resposta: {envio_response}")
                    
                    # Atualizar response com dados do envio
                    if envio_response.get('data'):
                        response['data'].update(envio_response.get('data', {}))
                except Exception as e:
                    logger.info(f"❌ Erro ao enviar nota para SEFAZ: {e}")
                    # Continuar mesmo se der erro no envio
        
        return response
    
    def _montar_payload(self, venda, tipo_nota: str) -> Dict:
        """Monta payload para emissão de nota"""
        cliente = venda.cliente
        
        # Modelo e série (modelo deve ser número inteiro, não string!)
        modelo = 55 if tipo_nota == "nfe" else 65
        serie = 1 if tipo_nota == "nfe" else 2
        
        # Contato (opcional para NFC-e, obrigatório para NF-e)
        contato = None
        if cliente and (cliente.cpf or cliente.cnpj):
            cpf_cnpj = cliente.cnpj or cliente.cpf
            cpf_cnpj = ''.join(filter(str.isdigit, cpf_cnpj))
            
            # Só adicionar contato se tiver CPF/CNPJ válido (11 ou 14 dígitos)
            if len(cpf_cnpj) >= 11:
                tipo_pessoa = "J" if len(cpf_cnpj) == 14 else "F"
                
                # Para NFC-e, só enviar contato se tiver endereço completo
                # Para NF-e, contato é obrigatório
                tem_endereco_completo = (
                    cliente.endereco and 
                    cliente.cidade and 
                    cliente.estado and 
                    cliente.cep
                )
                
                # Sempre criar contato com CPF/CNPJ
                contato = {
                    "nome": cliente.nome,
                    "numeroDocumento": cpf_cnpj,
                    "tipoPessoa": tipo_pessoa,
                    "email": cliente.email or "",
                    "telefone": cliente.telefone or "",
                }
                
                # Para NFC-e: endereço é opcional
                # Para NF-e: endereço é obrigatório
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
                "ncm": produto.ncm or "00000000",
                "cfop": "5102",
                "icms": {
                    "situacaoTributaria": "102",
                    "origem": "0"
                }
            }
            itens.append(item)
        
        # Totais
        valor_produtos = sum((float(i.preco_unitario or 0) - float(i.desconto_item or 0)) * float(i.quantidade or 1) for i in venda.itens)
        desconto_total = float(venda.desconto_valor or 0)
        valor_frete = float(venda.taxa_entrega_total or 0) if venda.tem_entrega else 0
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
                "informacoesComplementares": f"Venda #{venda.id} - Sistema Pet Shop Pro - Emitida em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
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
        """Lista NF-es com filtros"""
        params = {}
        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final
        if situacao:
            params["situacao"] = situacao
        
        return self._request("GET", "/nfe", data=params)
    
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
    
    def atualizar_estoque_produto(self, produto_id: str, estoque_novo: float, deposito_id: Optional[int] = None) -> Dict:
        """
        Atualiza estoque de um produto no Bling
        
        Args:
            produto_id: ID do produto no Bling
            estoque_novo: Novo saldo de estoque
            deposito_id: ID do depósito (opcional, usa o padrão se não informado)
        """
        payload = {
            "estoque": estoque_novo
        }
        
        if deposito_id:
            payload["deposito"] = {"id": deposito_id}
        
        return self._request("PUT", f"/produtos/{produto_id}/estoque", data=payload)
    
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
        
        refresh = refresh_token or os.getenv("BLING_REFRESH_TOKEN")
        if not refresh:
            raise ValueError("BLING_REFRESH_TOKEN não configurado")
        
        # Basic Auth
        credentials = f'{self.client_id}:{self.client_secret}'
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/x-www-form-urlencoded'
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
            
            # Atualizar .env se possível
            try:
                from pathlib import Path
                env_path = Path('.env')
                if env_path.exists():
                    lines = []
                    for line in env_path.read_text(encoding='utf-8').split('\n'):
                        if line.startswith('BLING_ACCESS_TOKEN='):
                            lines.append(f'BLING_ACCESS_TOKEN={tokens["access_token"]}')
                        elif line.startswith('BLING_REFRESH_TOKEN='):
                            lines.append(f'BLING_REFRESH_TOKEN={tokens["refresh_token"]}')
                        else:
                            lines.append(line)
                    env_path.write_text('\n'.join(lines), encoding='utf-8')
                    logger.info("✅ Tokens atualizados no .env")
            except Exception as e:
                logger.info(f"⚠️ Não foi possível atualizar .env: {e}")
            
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
