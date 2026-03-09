from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

from cryptography.hazmat.primitives.serialization import pkcs12
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

        Observação: integração SOAP real por UF ainda será conectada neste método.
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

        # Integração real SOAP/UF será conectada aqui na próxima etapa.
        raise HTTPException(
            status_code=501,
            detail=(
                "Configuração SEFAZ real validada (certificado OK), mas o conector SOAP por UF "
                "ainda não foi habilitado nesta etapa. Próximo passo: integrar endpoint oficial de consulta/distribuição da SEFAZ-SP."
            ),
        )
