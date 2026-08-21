from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_SOURCE_ROOTS = (
    "backend/app",
    "frontend/src",
    "app-mobile/src",
)

REQUIRED_ENTRYPOINTS = (
    "backend/app/main.py",
    "frontend/src/main.jsx",
    "app-mobile/App.tsx",
    "backend/alembic/versions",
    "scripts/deploy_producao_remoto.ps1",
    "scripts/deploy_producao_seguro.sh",
)

REQUIRED_GUIDES = (
    "README.md",
    "CONTRIBUTING.md",
    "docs/MAPA_CODIGO_FONTE.md",
    "docs/ARQUITETURA.md",
    "docs/INDICE_OPERACIONAL.md",
    "docs/ATALHOS_OPERACIONAIS.md",
)

README_REFERENCES = (
    "docs/MAPA_CODIGO_FONTE.md",
    "docs/ARQUITETURA.md",
    "CONTRIBUTING.md",
)

KNOWN_LEGACY_SOURCE: frozenset[str] = frozenset()

BASH_DEPLOY_ALIASES = (
    "deploy.sh",
    "deploy-producao.sh",
    "deploy_completo_producao.sh",
    "CORRIGIR_PRODUCAO.sh",
    "EXECUTAR_NO_SERVIDOR.sh",
)

POWERSHELL_DEPLOY_ALIASES = ("deploy-prod-auto.ps1",)

BLOCKED_LEGACY_ENTRYPOINTS = ("setup-server.sh",)

FORBIDDEN_ROOT_OPERATION_SNIPPETS = (
    "git push origin main",
    "git reset --hard",
    "drop table if exists alembic_version",
    "rm -f *merge*.py",
    "docker restart petshop-prod-backend",
    "docker cp ",
    "server_ip=",
)

FORBIDDEN_TRACKED_PREFIXES = (
    "frontend/dist/",
    "frontend/node_modules/",
    "app-mobile/node_modules/",
    "node_modules/",
    "runtime/",
    ".venv/",
)

SOURCE_SUFFIXES = frozenset({".py", ".js", ".jsx", ".ts", ".tsx", ".mjs"})


def _normalize(path: str) -> str:
    return path.strip().replace("\\", "/").lstrip("./")


def tracked_files(root: Path = ROOT) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    decoded = {
        _normalize(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item
    }
    return {path for path in decoded if (root / path).exists()}


def legacy_source_files_on_disk(root: Path = ROOT) -> set[str]:
    found: set[str] = set()
    for legacy_root in (root / "app", root / "src"):
        if not legacy_root.exists():
            continue
        for path in legacy_root.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in SOURCE_SUFFIXES
                and "__pycache__" not in path.parts
            ):
                found.add(_normalize(path.relative_to(root).as_posix()))
    return found


def unexpected_legacy_source(paths: Iterable[str]) -> list[str]:
    normalized = {_normalize(path) for path in paths}
    legacy = {
        path
        for path in normalized
        if path.startswith("app/") or path.startswith("src/")
    }
    return sorted(legacy - KNOWN_LEGACY_SOURCE)


def forbidden_generated_artifacts(paths: Iterable[str]) -> list[str]:
    normalized = {_normalize(path) for path in paths}
    return sorted(
        path
        for path in normalized
        if any(path.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES)
    )


def forbidden_operational_snippets(content: str) -> list[str]:
    normalized = content.casefold()
    return sorted(
        snippet
        for snippet in FORBIDDEN_ROOT_OPERATION_SNIPPETS
        if snippet in normalized
    )


def operational_entrypoint_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    for relative_path in BASH_DEPLOY_ALIASES:
        path = root / relative_path
        if not path.exists():
            errors.append(f"Atalho de compatibilidade ausente: {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        if "COMPATIBILITY_ALIAS" not in content:
            errors.append(
                f"Atalho sem identificacao de compatibilidade: {relative_path}"
            )
        if "scripts/deploy_producao_seguro.sh" not in content:
            errors.append(f"Atalho fora do deploy seguro oficial: {relative_path}")
        forbidden = forbidden_operational_snippets(content)
        if forbidden:
            errors.append(
                f"Operacao perigosa voltou ao atalho {relative_path}: "
                + ", ".join(forbidden)
            )

    for relative_path in POWERSHELL_DEPLOY_ALIASES:
        path = root / relative_path
        if not path.exists():
            errors.append(f"Atalho de compatibilidade ausente: {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        if "COMPATIBILITY_ALIAS" not in content:
            errors.append(
                f"Atalho sem identificacao de compatibilidade: {relative_path}"
            )
        if r"scripts\deploy_producao_remoto.ps1" not in content:
            errors.append(f"Atalho fora do launcher remoto oficial: {relative_path}")
        forbidden = forbidden_operational_snippets(content)
        if forbidden:
            errors.append(
                f"Operacao perigosa voltou ao atalho {relative_path}: "
                + ", ".join(forbidden)
            )

    for relative_path in BLOCKED_LEGACY_ENTRYPOINTS:
        path = root / relative_path
        if not path.exists():
            errors.append(f"Bloqueio de compatibilidade ausente: {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        if "LEGACY_BLOCKED" not in content or "exit 1" not in content:
            errors.append(f"Entrada legada deixou de estar bloqueada: {relative_path}")
        forbidden = forbidden_operational_snippets(content)
        if forbidden:
            errors.append(
                f"Operacao perigosa voltou a entrada bloqueada {relative_path}: "
                + ", ".join(forbidden)
            )

    return errors


def validate_repository_structure(
    root: Path = ROOT,
    paths: Iterable[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    tracked = set(paths) if paths is not None else tracked_files(root)
    current_source_paths = tracked | legacy_source_files_on_disk(root)

    for relative_path in (
        *ACTIVE_SOURCE_ROOTS,
        *REQUIRED_ENTRYPOINTS,
        *REQUIRED_GUIDES,
    ):
        if not (root / relative_path).exists():
            errors.append(f"Caminho oficial ausente: {relative_path}")

    readme_path = root / "README.md"
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        for reference in README_REFERENCES:
            if reference not in readme:
                errors.append(f"README sem referencia oficial: {reference}")

    unexpected = unexpected_legacy_source(current_source_paths)
    if unexpected:
        errors.append("Codigo novo encontrado em raiz legada: " + ", ".join(unexpected))

    generated = forbidden_generated_artifacts(tracked)
    if generated:
        errors.append(
            "Artefato gerado ou dependencia rastreada no Git: " + ", ".join(generated)
        )

    errors.extend(operational_entrypoint_errors(root))

    return errors


def main() -> int:
    errors = validate_repository_structure()
    if errors:
        print("Estrutura do repositorio: FALHOU")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Estrutura do repositorio: OK")
    print("Fontes oficiais: backend/app, frontend/src, app-mobile/src")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
