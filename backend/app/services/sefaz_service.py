from __future__ import annotations

import base64
import gzip
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple
from xml.etree import ElementTree as ET

import requests
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from fastapi import HTTPException

from app.config import settings


@dataclass
class SefazConfigStatus:
    enabled: bool
    modo: str
    ambiente: str
    uf: str
    cnpj_configurado: bool
    cert_path_configurado: bool
    cert_existe: bool
    cert_senha_configurada: bool
    cert_ok: bool
    mensagem: str


class SefazService:
    """Camada de serviço para validar e preparar integração SEFAZ."""

    SOAP_ACTION_DIST_DFE = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"

    _ENDPOINTS_DISTRIBUICAO = {
        "homologacao": "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
        "producao": "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx",
    }

    _UF_CODIGO = {
        "AC": "12",
        "AL": "27",
        "AP": "16",
        "AM": "13",
        "BA": "29",
        "CE": "23",
        "DF": "53",
        "ES": "32",
        "GO": "52",
        "MA": "21",
        "MT": "51",
        "MS": "50",
        "MG": "31",
        "PA": "15",
        "PB": "25",
        "PR": "41",
        "PE": "26",
        "PI": "22",
        "RJ": "33",
        "RN": "24",
        "RS": "43",
        "RO": "11",
        "RR": "14",
        "SC": "42",
        "SP": "35",
        "SE": "28",
        "TO": "17",
    }

    @staticmethod
    def _read_config(config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        if config:
            return {
                "enabled": bool(config.get("enabled", False)),
                "modo": str(config.get("modo", "mock")).strip().lower(),
                "ambiente": str(config.get("ambiente", "homologacao")).strip().lower(),
                "uf": str(config.get("uf", "")).strip().upper(),
                "cnpj": str(config.get("cnpj", "")).strip(),
                "cert_path": str(config.get("cert_path", "")).strip(),
                "cert_password": str(config.get("cert_password", "")),
            }

        return {
            "enabled": settings.SEFAZ_ENABLED,
            "modo": (settings.SEFAZ_MODO or "mock").strip().lower(),
            "ambiente": (settings.SEFAZ_AMBIENTE or "homologacao").strip().lower(),
            "uf": (settings.SEFAZ_UF or "").strip().upper(),
            "cnpj": (settings.SEFAZ_CNPJ or "").strip(),
            "cert_path": (settings.SEFAZ_CERT_PATH or "").strip(),
            "cert_password": settings.SEFAZ_CERT_PASSWORD or "",
        }

    @staticmethod
    def _validar_modo(modo: str) -> str:
        if modo not in ("mock", "real"):
            raise HTTPException(status_code=422, detail="SEFAZ_MODO inválido. Use 'mock' ou 'real'.")
        return modo

    @staticmethod
    def _validar_ambiente(ambiente: str) -> str:
        if ambiente not in ("homologacao", "producao"):
            raise HTTPException(status_code=422, detail="SEFAZ_AMBIENTE inválido. Use 'homologacao' ou 'producao'.")
        return ambiente

    @staticmethod
    def _validar_certificado(path_cert: str, senha: str) -> Tuple[bool, str]:
        try:
            cert_bytes = Path(path_cert).read_bytes()
            senha_bytes = senha.encode("utf-8") if senha else None
            key, cert, _chain = pkcs12.load_key_and_certificates(cert_bytes, senha_bytes)
            if not key or not cert:
                return False, "Certificado inválido: chave ou certificado não encontrados no .pfx."
            return True, "Certificado A1 válido."
        except FileNotFoundError:
            return False, "Arquivo do certificado não encontrado no caminho informado."
        except Exception as exc:  # noqa: BLE001
            return False, f"Falha ao abrir certificado A1: {exc}"

    @staticmethod
    def _tag_local(tag: str) -> str:
        if "}" in tag:
            return tag.rsplit("}", 1)[1]
        return tag

    @classmethod
    def _find_first(cls, root: ET.Element, tag_name: str) -> Optional[ET.Element]:
        for elem in root.iter():
            if cls._tag_local(elem.tag) == tag_name:
                return elem
        return None

    @classmethod
    def _find_text(cls, root: Optional[ET.Element], tag_name: str) -> str:
        if root is None:
            return ""
        for elem in root.iter():
            if cls._tag_local(elem.tag) == tag_name and elem.text:
                return str(elem.text).strip()
        return ""

    @staticmethod
    def _tp_ambiente(ambiente: str) -> str:
        return "1" if ambiente == "producao" else "2"

    @classmethod
    def _codigo_uf_autor(cls, uf: str) -> str:
        uf_limpa = str(uf or "").strip().upper()
        codigo = cls._UF_CODIGO.get(uf_limpa)
        if not codigo:
            raise HTTPException(status_code=422, detail=f"UF SEFAZ inválida: '{uf_limpa or '-'}'.")
        return codigo

    @classmethod
    def _extrair_cert_key_tempfiles(cls, path_cert: str, senha: str) -> tuple[str, str]:
        cert_bytes = Path(path_cert).read_bytes()
        senha_bytes = senha.encode("utf-8") if senha else None
        key, cert, _chain = pkcs12.load_key_and_certificates(cert_bytes, senha_bytes)
        if not key or not cert:
            raise HTTPException(status_code=422, detail="Certificado inválido: chave ou certificado não encontrados no .pfx.")

        key_pem = key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )
        cert_pem = cert.public_bytes(Encoding.PEM)

        cert_tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
        key_tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".pem", delete=False)
        cert_tmp.write(cert_pem)
        key_tmp.write(key_pem)
        cert_tmp.flush()
        key_tmp.flush()
        cert_tmp.close()
        key_tmp.close()
        return cert_tmp.name, key_tmp.name

    @classmethod
    def _soap_envelope(cls, inner_xml: str) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            "<soap12:Body>"
            f"<nfeDistDFeInteresse xmlns=\"http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe\">{inner_xml}</nfeDistDFeInteresse>"
            "</soap12:Body>"
            "</soap12:Envelope>"
        )

    @classmethod
    def _xml_dist_cons_chave(cls, cfg: dict[str, Any], chave: str) -> str:
        cnpj = cfg["cnpj"]
        tp_amb = cls._tp_ambiente(cfg["ambiente"])
        c_uf_autor = cls._codigo_uf_autor(cfg.get("uf", ""))
        return (
            '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">'
            f'<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">'
            f"<tpAmb>{tp_amb}</tpAmb>"
            f"<cUFAutor>{c_uf_autor}</cUFAutor>"
            f"<CNPJ>{cnpj}</CNPJ>"
            "<consChNFe>"
            f"<chNFe>{chave}</chNFe>"
            "</consChNFe>"
            "</distDFeInt>"
            "</nfeDadosMsg>"
        )

    @classmethod
    def _xml_dist_nsu(cls, cfg: dict[str, Any], ultimo_nsu: str) -> str:
        cnpj = cfg["cnpj"]
        tp_amb = cls._tp_ambiente(cfg["ambiente"])
        c_uf_autor = cls._codigo_uf_autor(cfg.get("uf", ""))
        nsu = str(ultimo_nsu or "0").strip().zfill(15)
        return (
            '<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">'
            f'<distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">'
            f"<tpAmb>{tp_amb}</tpAmb>"
            f"<cUFAutor>{c_uf_autor}</cUFAutor>"
            f"<CNPJ>{cnpj}</CNPJ>"
            "<distNSU>"
            f"<ultNSU>{nsu}</ultNSU>"
            "</distNSU>"
            "</distDFeInt>"
            "</nfeDadosMsg>"
        )

    @classmethod
    def _post_soap_dist_dfe(cls, cfg: dict[str, Any], dados_msg_xml: str) -> str:
        endpoint = cls._ENDPOINTS_DISTRIBUICAO.get(cfg["ambiente"])
        if not endpoint:
            raise HTTPException(status_code=422, detail="Ambiente SEFAZ inválido para consulta.")

        cert_file = None
        key_file = None
        try:
            cert_file, key_file = cls._extrair_cert_key_tempfiles(cfg["cert_path"], cfg["cert_password"])
            payload = cls._soap_envelope(dados_msg_xml)
            headers = {
                "Content-Type": "application/soap+xml; charset=utf-8",
                "SOAPAction": cls.SOAP_ACTION_DIST_DFE,
            }
            timeout = max(10, int(settings.SEFAZ_TIMEOUT_SECONDS or 30))
            response = requests.post(
                endpoint,
                data=payload.encode("utf-8"),
                headers=headers,
                cert=(cert_file, key_file),
                timeout=timeout,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout as exc:
            raise HTTPException(status_code=504, detail=f"Timeout na comunicação com a SEFAZ: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Falha de comunicação com a SEFAZ: {exc}") from exc
        finally:
            if cert_file:
                Path(cert_file).unlink(missing_ok=True)
            if key_file:
                Path(key_file).unlink(missing_ok=True)

    @classmethod
    def _parse_documentos_zipados(cls, ret_dist: ET.Element) -> list[dict[str, Any]]:
        documentos: list[dict[str, Any]] = []
        for elem in ret_dist.iter():
            if cls._tag_local(elem.tag) != "docZip":
                continue

            conteudo_b64 = (elem.text or "").strip()
            if not conteudo_b64:
                continue

            try:
                xml_bruto = gzip.decompress(base64.b64decode(conteudo_b64)).decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue

            documentos.append(
                {
                    "nsu": elem.attrib.get("NSU", ""),
                    "schema": elem.attrib.get("schema", ""),
                    "xml": xml_bruto,
                }
            )

        return documentos

    @classmethod
    def _parse_retorno_dist_dfe(cls, soap_xml: str) -> dict[str, Any]:
        try:
            root = ET.fromstring(soap_xml)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Resposta inválida da SEFAZ (XML malformado): {exc}") from exc

        ret_dist = cls._find_first(root, "retDistDFeInt")
        if ret_dist is None:
            fault_msg = cls._find_text(root, "Text") or cls._find_text(root, "faultstring")
            if fault_msg:
                raise HTTPException(status_code=502, detail=f"SEFAZ retornou falha SOAP: {fault_msg}")
            raise HTTPException(status_code=502, detail="SEFAZ retornou resposta sem retDistDFeInt.")

        c_stat = cls._find_text(ret_dist, "cStat")
        x_motivo = cls._find_text(ret_dist, "xMotivo")
        ult_nsu = cls._find_text(ret_dist, "ultNSU") or "000000000000000"
        max_nsu = cls._find_text(ret_dist, "maxNSU") or ult_nsu
        docs = cls._parse_documentos_zipados(ret_dist)
        return {
            "c_stat": c_stat,
            "x_motivo": x_motivo,
            "ult_nsu": ult_nsu,
            "max_nsu": max_nsu,
            "docs": docs,
        }

    @classmethod
    def _parse_item_det(cls, det: ET.Element) -> dict[str, Any]:
        prod = cls._find_first(det, "prod")
        n_item = det.attrib.get("nItem", "0")
        quantidade = float(cls._find_text(prod, "qCom") or 0)
        valor_unit = float(cls._find_text(prod, "vUnCom") or 0)
        valor_total = float(cls._find_text(prod, "vProd") or 0)
        return {
            "numero_item": int(n_item) if str(n_item).isdigit() else 0,
            "codigo_produto": cls._find_text(prod, "cProd"),
            "descricao": cls._find_text(prod, "xProd"),
            "ncm": cls._find_text(prod, "NCM") or None,
            "cfop": cls._find_text(prod, "CFOP") or None,
            "quantidade": quantidade,
            "unidade": cls._find_text(prod, "uCom") or "UN",
            "valor_unitario": valor_unit,
            "valor_total": valor_total,
        }

    @classmethod
    def _parse_nfe_documento(cls, xml_documento: str) -> Optional[dict[str, Any]]:
        try:
            root = ET.fromstring(xml_documento)
        except Exception:
            return None

        inf_nfe = cls._find_first(root, "infNFe")
        if inf_nfe is not None:
            ide = cls._find_first(inf_nfe, "ide")
            emit = cls._find_first(inf_nfe, "emit")
            dest = cls._find_first(inf_nfe, "dest")
            total = cls._find_first(inf_nfe, "ICMSTot")
            nfe_id = inf_nfe.attrib.get("Id", "")
            chave = nfe_id.replace("NFe", "") if nfe_id.startswith("NFe") else ""

            itens: list[dict[str, Any]] = []
            for elem in inf_nfe.iter():
                if cls._tag_local(elem.tag) == "det":
                    itens.append(cls._parse_item_det(elem))

            return {
                "chave_acesso": chave or cls._find_text(inf_nfe, "chNFe"),
                "numero_nf": cls._find_text(ide, "nNF"),
                "serie": cls._find_text(ide, "serie"),
                "data_emissao": cls._find_text(ide, "dhEmi") or cls._find_text(ide, "dEmi"),
                "emitente_cnpj": cls._find_text(emit, "CNPJ"),
                "emitente_nome": cls._find_text(emit, "xNome"),
                "destinatario_cnpj": cls._find_text(dest, "CNPJ") or cls._find_text(dest, "CPF") or None,
                "destinatario_nome": cls._find_text(dest, "xNome") or None,
                "valor_total_nf": float(cls._find_text(total, "vNF") or 0),
                "itens": itens,
                "tem_xml_completo": True,
            }

        res_nfe = cls._find_first(root, "resNFe")
        if res_nfe is not None:
            return {
                "chave_acesso": cls._find_text(res_nfe, "chNFe"),
                "numero_nf": cls._find_text(res_nfe, "nNF"),
                "serie": cls._find_text(res_nfe, "serie"),
                "data_emissao": cls._find_text(res_nfe, "dhEmi"),
                "emitente_cnpj": cls._find_text(res_nfe, "CNPJ") or cls._find_text(res_nfe, "CNPJCPF"),
                "emitente_nome": cls._find_text(res_nfe, "xNome"),
                "destinatario_cnpj": None,
                "destinatario_nome": None,
                "valor_total_nf": float(cls._find_text(res_nfe, "vNF") or 0),
                "itens": [],
                "tem_xml_completo": False,
            }

        return None

    @classmethod
    def _consultar_por_chave_real(cls, chave: str, cfg: dict[str, Any]) -> dict[str, Any]:
        xml_msg = cls._xml_dist_cons_chave(cfg, chave)
        soap = cls._post_soap_dist_dfe(cfg, xml_msg)
        parsed = cls._parse_retorno_dist_dfe(soap)

        c_stat = parsed["c_stat"]
        if c_stat not in {"138", "139", "137"}:
            raise HTTPException(
                status_code=502,
                detail=f"SEFAZ retornou cStat {c_stat}: {parsed['x_motivo'] or 'sem detalhe'}",
            )

        for doc in parsed["docs"]:
            dados = cls._parse_nfe_documento(doc["xml"])
            if dados and (dados.get("chave_acesso") == chave or not dados.get("chave_acesso")):
                dados["chave_acesso"] = chave
                dados["aviso"] = "Consulta real realizada na SEFAZ via distribuição DF-e."
                if dados.get("tem_xml_completo"):
                    dados["xml_nfe"] = doc["xml"]
                else:
                    dados["xml_nfe"] = None
                return dados

        raise HTTPException(status_code=404, detail="NF-e não localizada para a chave informada na SEFAZ.")

    @classmethod
    def sincronizar_nsu(cls, config: Optional[dict[str, Any]] = None, ultimo_nsu: str = "000000000000000") -> dict[str, Any]:
        cfg = cls._read_config(config)
        cls.garantir_pronto_para_consulta_real(cfg)

        xml_msg = cls._xml_dist_nsu(cfg, ultimo_nsu)
        soap = cls._post_soap_dist_dfe(cfg, xml_msg)
        parsed = cls._parse_retorno_dist_dfe(soap)
        c_stat = parsed["c_stat"]

        if c_stat not in {"137", "138"}:
            raise HTTPException(
                status_code=502,
                detail=f"SEFAZ retornou cStat {c_stat} na sincronização: {parsed['x_motivo'] or 'sem detalhe'}",
            )

        docs = parsed["docs"]
        total_docs = len(docs)
        mensagem = (
            f"Sincronizacao concluida com sucesso. {total_docs} documento(s) retornado(s) pela SEFAZ."
            if total_docs
            else "Sincronizacao concluida. Nenhum documento novo no NSU informado."
        )
        return {
            "status": "ok",
            "mensagem": mensagem,
            "documentos": total_docs,
            "ultimo_nsu": parsed["ult_nsu"],
            "max_nsu": parsed["max_nsu"],
            "c_stat": c_stat,
            "x_motivo": parsed["x_motivo"],
            "docs_list": docs,
        }

    @classmethod
    def _mensagem_e_cert_ok(cls, enabled: bool, modo: str, cert_path: str, cert_pwd: str) -> Tuple[bool, str]:
        if not enabled:
            return False, "SEFAZ desabilitado."
        if modo == "mock":
            return False, "SEFAZ habilitado em modo mock (simulado)."
        if cert_path and cert_pwd:
            return cls._validar_certificado(cert_path, cert_pwd)
        return False, "Preencha caminho e senha do certificado para modo real."

    @classmethod
    def status_configuracao(cls, config: Optional[dict[str, Any]] = None) -> SefazConfigStatus:
        cfg = cls._read_config(config)
        modo = cfg["modo"]
        ambiente = cfg["ambiente"]
        cert_path = cfg["cert_path"]
        cert_pwd = cfg["cert_password"]

        cert_existe = bool(cert_path) and Path(cert_path).exists()
        cert_ok, msg = cls._mensagem_e_cert_ok(cfg["enabled"], modo, cert_path, cert_pwd)

        return SefazConfigStatus(
            enabled=cfg["enabled"],
            modo=modo,
            ambiente=ambiente,
            uf=cfg["uf"],
            cnpj_configurado=bool(cfg["cnpj"]),
            cert_path_configurado=bool(cert_path),
            cert_existe=cert_existe,
            cert_senha_configurada=bool(cert_pwd),
            cert_ok=cert_ok,
            mensagem=msg,
        )

    @classmethod
    def garantir_pronto_para_consulta_real(cls, config: Optional[dict[str, Any]] = None) -> None:
        cfg = cls._read_config(config)

        cls._validar_modo(cfg["modo"])
        cls._validar_ambiente(cfg["ambiente"])

        if not cfg["enabled"]:
            raise HTTPException(status_code=503, detail="SEFAZ está desabilitado. Defina SEFAZ_ENABLED=true.")

        if cfg["modo"] != "real":
            raise HTTPException(status_code=503, detail="SEFAZ está em modo mock. Defina SEFAZ_MODO=real.")

        if not cfg["uf"]:
            raise HTTPException(status_code=422, detail="SEFAZ_UF não configurada.")
        cls._codigo_uf_autor(cfg["uf"])

        cnpj = cfg["cnpj"]
        if not cnpj or not cnpj.isdigit() or len(cnpj) != 14:
            raise HTTPException(status_code=422, detail="SEFAZ_CNPJ deve ter 14 dígitos numéricos.")

        cert_path = cfg["cert_path"]
        cert_pwd = cfg["cert_password"]
        if not cert_path:
            raise HTTPException(status_code=422, detail="SEFAZ_CERT_PATH não configurado.")
        if not cert_pwd:
            raise HTTPException(status_code=422, detail="SEFAZ_CERT_PASSWORD não configurado.")

        ok, msg = cls._validar_certificado(cert_path, cert_pwd)
        if not ok:
            raise HTTPException(status_code=422, detail=msg)

    @classmethod
    def consultar_nfe_por_chave(cls, chave: str, config: Optional[dict[str, Any]] = None) -> dict:
        """
        Ponto único da consulta SEFAZ.
        """
        cfg = cls._read_config(config)
        modo = cls._validar_modo(cfg["modo"])
        if not cfg["enabled"] or modo == "mock":
            return {
                "modo": "mock",
                "chave_acesso": chave,
                "numero_nf": "000123",
                "serie": "001",
                "data_emissao": "2025-01-15",
                "emitente_cnpj": "12.345.678/0001-90",
                "emitente_nome": "Fornecedor Simulado Ltda",
                "destinatario_cnpj": None,
                "destinatario_nome": "Petshop (Destinatário)",
                "valor_total_nf": 1250.00,
                "itens": [
                    {
                        "numero_item": 1,
                        "codigo_produto": "PRD001",
                        "descricao": "Ração Premium Cão Adulto 15kg",
                        "ncm": "23091000",
                        "cfop": "6102",
                        "quantidade": 10.0,
                        "unidade": "UN",
                        "valor_unitario": 89.90,
                        "valor_total": 899.00,
                    },
                    {
                        "numero_item": 2,
                        "codigo_produto": "PRD002",
                        "descricao": "Antipulgas Spot-On Cão 10-25kg",
                        "ncm": "30049099",
                        "cfop": "6102",
                        "quantidade": 5.0,
                        "unidade": "UN",
                        "valor_unitario": 70.20,
                        "valor_total": 351.00,
                    },
                ],
                "aviso": (
                    "Modo mock ativo. Para consulta real configure: SEFAZ_ENABLED=true, "
                    "SEFAZ_MODO=real e certificado A1 no .env."
                ),
            }

        cls.garantir_pronto_para_consulta_real(cfg)
        return cls._consultar_por_chave_real(chave, cfg)
