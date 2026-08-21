"""Estado isolado de uma execucao do importador SimplesVet.

O importador legado usava ``user_id=1`` e descobria o tenant implicitamente.
Agora o alvo e os diretorios precisam ser configurados pelo fluxo seguro antes
de qualquer leitura ou gravacao.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass
class ImportRuntime:
    tenant_id: UUID | None = None
    user_id: int | None = None
    source_dir: Path | None = None
    report_dir: Path | None = None
    dry_run: bool = True

    def configure(
        self,
        *,
        tenant_id: UUID,
        user_id: int,
        source_dir: Path,
        report_dir: Path,
        dry_run: bool,
    ) -> None:
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.source_dir = source_dir.resolve()
        self.report_dir = report_dir.resolve()
        self.dry_run = dry_run

    def require_configured(self) -> "ImportRuntime":
        if (
            self.tenant_id is None
            or self.user_id is None
            or self.source_dir is None
            or self.report_dir is None
        ):
            raise RuntimeError(
                "Importador sem contexto seguro. Use importar_simplesvet_cli.py plan/apply."
            )
        return self

    def clear(self) -> None:
        """Remove todo o alvo da memoria ao encerrar uma execucao."""

        self.tenant_id = None
        self.user_id = None
        self.source_dir = None
        self.report_dir = None
        self.dry_run = True


RUNTIME = ImportRuntime()

# Mapeamento de IDs antigos -> novos para preservar relacionamentos.
ID_MAP = {
    "pessoas": {},
    "animais": {},
    "produtos": {},
    "vendas": {},
    "especies": {},
    "racas": {},
    "marcas": {},
}

STATS = {
    "especies": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "racas": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "clientes": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "marcas": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "produtos": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0, "sem_sku": 0},
    "pets": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "vendas": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
    "itens_venda": {"total": 0, "sucesso": 0, "erro": 0, "duplicado": 0},
}

NAO_IMPORTADOS = {
    "produtos": [],
    "clientes": [],
    "pets": [],
    "vendas": [],
}


def reset_import_state() -> None:
    """Limpa mapas e contadores para uma nova execucao no mesmo processo."""

    for mapping in ID_MAP.values():
        mapping.clear()

    for counters in STATS.values():
        for key in counters:
            counters[key] = 0

    for rejected in NAO_IMPORTADOS.values():
        rejected.clear()
