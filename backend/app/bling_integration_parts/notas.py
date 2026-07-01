from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import requests
from sqlalchemy.orm import Session

from app.bling_integration_fiscal import (
    _limpar_texto_fiscal,
    _ncm_basico_aceitavel,
    _ncm_normalizado,
    _resolver_fiscal_item_nfe,
    _sku_produto,
)
from app.bling_integration_parts.core import (
    BLING_NFCE_SERIE_PADRAO,
    BLING_NFE_SERIE_PADRAO,
    _montar_url_bling,
)
from app.utils.logger import logger


class BlingNotasMixin:
    """Operacoes de NF-e/NFC-e do cliente Bling."""

    def emitir_nota_fiscal(
        self,
        venda,
        tipo_nota: str = "nfce",
        db: Session = None,
        transmitir: Optional[bool] = None,
    ) -> Dict:
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
            logger.info(
                f"  - Origem: {fiscal_item.get('origem_mercadoria') or 'NAO CADASTRADO'}"
            )

            if not _ncm_basico_aceitavel(fiscal_item.get("ncm")):
                erros_produtos.append(
                    f"{produto.nome} (SKU {sku}): NCM nao cadastrado ou invalido"
                )
            if not fiscal_item.get("origem_mercadoria"):
                erros_produtos.append(
                    f"{produto.nome} (SKU {sku}): Origem da mercadoria nao cadastrada"
                )

        if erros_produtos:
            raise ValueError(
                "Produtos sem dados fiscais obrigatórios:\n"
                + "\n".join(erros_produtos)
                + "\n\nCadastre NCM e Origem nas informações fiscais do produto antes de emitir NF-e."
            )

        # Validações por tipo
        if tipo_nota == "nfe":
            if not venda.cliente or not (venda.cliente.cpf or venda.cliente.cnpj):
                raise ValueError("NF-e requer cliente com CPF/CNPJ")

            cpf_cnpj = venda.cliente.cnpj or venda.cliente.cpf
            cpf_cnpj = "".join(filter(str.isdigit, cpf_cnpj))
            if len(cpf_cnpj) == 11:
                raise ValueError(
                    "NF-e requer CNPJ (empresa). Para pessoa física use NFC-e"
                )

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

        deve_transmitir = (
            transmitir
            if transmitir is not None
            else self.ambiente in ["homologacao", "producao"]
        )

        # Quando solicitado, enviar para SEFAZ logo apos criar a nota no Bling.
        if deve_transmitir:
            nota_id = response.get("data", {}).get("id")
            if nota_id:
                logger.info(
                    f"\n{'⚠️' if self.ambiente == 'homologacao' else '🚨'} Enviando nota #{nota_id} para SEFAZ..."
                )
                try:
                    # Endpoint para enviar nota para SEFAZ (mesmo endpoint base)
                    envio_response = self._request(
                        "POST", f"{endpoint}/{nota_id}/enviar"
                    )
                    logger.info("✅ Nota enviada para SEFAZ!")
                    logger.info(f"Resposta: {envio_response}")
                    response["transmissao"] = {
                        "success": True,
                        "data": envio_response.get("data", envio_response),
                    }

                    # Atualizar response com dados do envio
                    if envio_response.get("data"):
                        response["data"].update(envio_response.get("data", {}))
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
        serie = (
            BLING_NFE_SERIE_PADRAO if tipo_nota == "nfe" else BLING_NFCE_SERIE_PADRAO
        )

        # Contato: NF-e exige documento; NFC-e pode identificar apenas pelo nome.
        contato = None
        if cliente and _limpar_texto_fiscal(getattr(cliente, "nome", None)):
            cpf_cnpj = cliente.cnpj or cliente.cpf or ""
            cpf_cnpj = "".join(filter(str.isdigit, cpf_cnpj))
            tem_documento_valido = len(cpf_cnpj) in (11, 14)
            tipo_pessoa = "J" if len(cpf_cnpj) == 14 else "F"

            tem_endereco_completo = (
                cliente.endereco and cliente.cidade and cliente.estado and cliente.cep
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
                    "cep": "".join(filter(str.isdigit, cliente.cep or "")),
                    "municipio": cliente.cidade or "",
                    "uf": cliente.estado or "",
                    "pais": "Brasil",
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
                    "origem": fiscal_item.get("origem_mercadoria") or "0",
                },
            }
            itens.append(item)

        # Totais
        valor_produtos = sum(
            (float(i.preco_unitario or 0) - float(i.desconto_item or 0))
            * float(i.quantidade or 1)
            for i in venda.itens
        )
        desconto_total = float(venda.desconto_valor or 0)
        taxa_entrega = getattr(venda, "taxa_entrega_total", None)
        if taxa_entrega is None:
            taxa_entrega = getattr(venda, "taxa_entrega", 0)
        valor_frete = float(taxa_entrega or 0) if venda.tem_entrega else 0
        valor_total = valor_produtos - desconto_total + valor_frete

        # Definir situação e finalidade conforme ambiente configurado
        situacao = 0  # 0 = Rascunho (pendente)
        finalidade = (
            1  # 1 = NF-e normal (sempre usar 1, o ambiente é definido no envio)
        )

        # Definir tipo correto conforme o modelo
        # tipo: 0 = NF-e (modelo 55), 1 = NFC-e (modelo 65)
        tipo_bling = 1 if modelo == 65 else 0

        if self.ambiente == "homologacao":
            logger.warning("⚠️  MODO HOMOLOGAÇÃO: Nota será enviada para SEFAZ de TESTE")
        elif self.ambiente == "producao":
            logger.info("🚨 MODO PRODUÇÃO: Nota será enviada para SEFAZ REAL")
        else:
            logger.info(
                "📝 MODO RASCUNHO: Nota ficará pendente no Bling (não será enviada para SEFAZ)"
            )

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
            "dataOperacao": venda.data_venda.strftime("%Y-%m-%d")
            if venda.data_venda
            else datetime.now().strftime("%Y-%m-%d"),
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
                "valorTotal": valor_total,
            },
            "informacoesAdicionais": {
                "informacoesComplementares": f"Venda #{venda.id} - CorePet - Emitida em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            },
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
        return resultado.get("data", resultado)

    def consultar_nfce(self, nfce_id: int) -> Dict:
        """Consulta dados de uma NFC-e"""
        resultado = self._request("GET", f"/nfce/{nfce_id}")
        # Extrair dados da chave 'data' se existir
        return resultado.get("data", resultado)

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
        url = _montar_url_bling(self.base_url, f"/nfe/{int(nfe_id)}/danfe")
        headers = self._get_headers()

        try:
            response = (
                requests.get(  # NOSONAR - endpoint validado por _montar_url_bling
                    url, headers=headers, timeout=30
                )
            )
            response.raise_for_status()
            return response.content
        except Exception as e:
            raise Exception(f"Erro ao baixar DANFE: {str(e)}")

    def listar_nfes(
        self, data_inicial: str = None, data_final: str = None, situacao: str = None
    ) -> Dict:
        """Lista NF-es (modelo 55) com filtros"""
        params = {}
        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final
        if situacao:
            params["situacao"] = situacao

        return self._request("GET", "/nfe", data=params)

    def listar_nfces(
        self, data_inicial: str = None, data_final: str = None, situacao: str = None
    ) -> Dict:
        """Lista NFC-es (modelo 65) com filtros"""
        params = {}
        if data_inicial:
            params["dataInicial"] = data_inicial
        if data_final:
            params["dataFinal"] = data_final
        if situacao:
            params["situacao"] = situacao

        return self._request("GET", "/nfce", data=params)
