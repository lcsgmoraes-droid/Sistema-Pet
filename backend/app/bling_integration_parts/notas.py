from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict

import requests
from sqlalchemy.orm import Session

from app.bling_integration_fiscal import (
    _limpar_texto_fiscal,
    _ncm_normalizado,
    _resolver_fiscal_item_nfe,
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
        transmitir: bool | None = None,
    ) -> Dict:
        del venda, tipo_nota, db, transmitir
        raise RuntimeError(
            "A emissão fiscal pelo Bling foi desativada. Use a emissão direta pela IntNFe."
        )

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
                    "endereco": cliente.endereco or "",
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
        centavo = Decimal("0.01")
        valor_produtos = Decimal("0")
        desconto_itens = Decimal("0")
        for idx, item_venda in enumerate(venda.itens, start=1):
            produto = item_venda.produto
            fiscal_item = _resolver_fiscal_item_nfe(db, venda, item_venda)

            valor_unitario = Decimal(str(item_venda.preco_unitario or 0))
            quantidade = Decimal(str(item_venda.quantidade or 0))
            # desconto_item e o desconto da linha inteira, ja rateado pelo PDV.
            desconto = Decimal(str(item_venda.desconto_item or 0)).quantize(
                centavo, rounding=ROUND_HALF_UP
            )
            valor_bruto = (valor_unitario * quantidade).quantize(
                centavo, rounding=ROUND_HALF_UP
            )
            if (
                quantidade <= 0
                or valor_unitario < 0
                or not 0 <= desconto <= valor_bruto
            ):
                raise ValueError(
                    "Item da venda possui quantidade, valor ou desconto invalido."
                )
            valor_produtos += valor_bruto
            desconto_itens += desconto

            item = {
                "numero": idx,
                "codigo": produto.codigo,
                "descricao": produto.nome,
                "quantidade": float(quantidade),
                "unidade": produto.unidade or "UN",
                "valor": float(valor_unitario),
                "classificacaoFiscal": _ncm_normalizado(fiscal_item.get("ncm")) or "",
                "cest": fiscal_item.get("cest") or "",
                "origem": int(fiscal_item.get("origem_mercadoria") or "0"),
                "cfop": fiscal_item.get("cfop") or "5102",
                "icms": {
                    "situacaoTributaria": fiscal_item.get("cst_icms") or "102",
                    "origem": fiscal_item.get("origem_mercadoria") or "0",
                },
            }
            itens.append(item)

        # Totais
        # O desconto geral repete o rateio dos itens nas vendas atuais.
        # Na API Bling o desconto monetario e enviado na raiz da nota.
        desconto_total = (
            desconto_itens
            if desconto_itens > 0
            else Decimal(str(venda.desconto_valor or 0))
        ).quantize(centavo, rounding=ROUND_HALF_UP)
        taxa_entrega = getattr(venda, "taxa_entrega_total", None)
        if taxa_entrega is None:
            taxa_entrega = getattr(venda, "taxa_entrega", 0)
        valor_frete = (
            Decimal(str(taxa_entrega or 0)) if venda.tem_entrega else Decimal("0")
        ).quantize(centavo, rounding=ROUND_HALF_UP)
        valor_total = valor_produtos - desconto_total + valor_frete
        total_venda = getattr(venda, "total", None)
        if total_venda is not None and valor_total != Decimal(
            str(total_venda)
        ).quantize(centavo, rounding=ROUND_HALF_UP):
            raise ValueError(
                "O total fiscal calculado difere do total da venda. "
                "Confira os valores e descontos antes de emitir a nota."
            )

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
            "dataOperacao": (
                venda.data_venda.strftime("%Y-%m-%d")
                if venda.data_venda
                else datetime.now().strftime("%Y-%m-%d")
            ),
            # ✅ RASTREAMENTO: Vincula venda do nosso sistema com nota no Bling
            "numeroPedidoLoja": f"VENDA-{venda.id}",
            # ✅ NATUREZA DE OPERAÇÃO: ID da natureza cadastrada no Bling
            # ID 15103736273 = "Venda de mercadoria - NFC-e" (descoberto automaticamente)
            "naturezaOperacao": {"id": 15103736273},
            "itens": itens,
            "desconto": float(desconto_total),
            "transporte": {"frete": float(valor_frete)},
            "totais": {
                "valorProdutos": float(valor_produtos),
                "valorFrete": float(valor_frete),
                "valorDesconto": float(desconto_total),
                "valorTotal": float(valor_total),
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
            params["dataEmissaoInicial"] = f"{data_inicial[:10]} 00:00:00"
        if data_final:
            params["dataEmissaoFinal"] = f"{data_final[:10]} 23:59:59"
        if situacao:
            params["situacao"] = situacao

        return self._request("GET", "/nfe", data=params)

    def listar_nfces(
        self, data_inicial: str = None, data_final: str = None, situacao: str = None
    ) -> Dict:
        """Lista NFC-es (modelo 65) com filtros"""
        params = {}
        if data_inicial:
            params["dataEmissaoInicial"] = f"{data_inicial[:10]} 00:00:00"
        if data_final:
            params["dataEmissaoFinal"] = f"{data_final[:10]} 23:59:59"
        if situacao:
            params["situacao"] = situacao

        return self._request("GET", "/nfce", data=params)
