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
    "scripts/diagnosticar_producao_publica.py",
    "scripts/diagnosticar_autenticacao_dev.ps1",
    "scripts/executar_testes_e2e.ps1",
    "scripts/iniciar_frontend_dev.ps1",
    "scripts/iniciar_app_mobile.ps1",
    "scripts/manutencao_banco_dev.ps1",
)

REQUIRED_GUIDES = (
    "README.md",
    "CONTRIBUTING.md",
    "docs/MAPA_CODIGO_FONTE.md",
    "docs/ARQUITETURA.md",
    "docs/CATALOGO_DADOS_CRITICOS_LGPD.md",
    "docs/CATALOGO_INTEGRACOES.md",
    "docs/GESTAO_INCIDENTES_SUSTENTACAO.md",
    "docs/INDICE_OPERACIONAL.md",
    "docs/ATALHOS_OPERACIONAIS.md",
    "docs/CLASSIFICACAO_RACOES.md",
)

README_REFERENCES = (
    "docs/MAPA_CODIGO_FONTE.md",
    "docs/ARQUITETURA.md",
    "CONTRIBUTING.md",
)

KNOWN_LEGACY_SOURCE: frozenset[str] = frozenset()

COMPATIBILITY_ENTRYPOINTS = {
    "deploy.sh": "scripts/deploy_producao_seguro.sh",
    "deploy-producao.sh": "scripts/deploy_producao_seguro.sh",
    "deploy_completo_producao.sh": "scripts/deploy_producao_seguro.sh",
    "CORRIGIR_PRODUCAO.sh": "scripts/deploy_producao_seguro.sh",
    "EXECUTAR_NO_SERVIDOR.sh": "scripts/deploy_producao_seguro.sh",
    "deploy-prod-auto.ps1": "scripts/deploy_producao_remoto.ps1",
    "CORRIGIR_LEMBRETES_404_SIMPLES.ps1": "scripts/diagnosticar_producao_publica.py",
    "CORRIGIR_LEMBRETES_404.ps1": "scripts/diagnosticar_producao_publica.py",
    "DIAGNOSTICAR_404.ps1": "scripts/diagnosticar_producao_publica.py",
    "DIAGNOSTICAR_E_CORRIGIR_404.sh": "scripts/diagnosticar_producao_publica.py",
    "INICIAR_APP.bat": "scripts/iniciar_app_mobile.ps1",
    "INICIAR_BACKEND_LOCAL.bat": "FLUXO_UNICO.bat",
    "INICIAR_DEV.bat": "FLUXO_UNICO.bat",
    "INICIAR_FRONTEND.bat": "scripts/iniciar_frontend_dev.ps1",
    "INICIAR_TUDO.bat": "FLUXO_UNICO.bat",
    "PARAR_TUDO.bat": "FLUXO_UNICO.bat",
    "CORRIGIR_PERMISSOES_ADMIN.bat": "scripts/manutencao_banco_dev.ps1",
    "EXECUTAR_TESTES_E2E.bat": "scripts/executar_testes_e2e.ps1",
    "FRONTEND_DEV.bat": "scripts/iniciar_frontend_dev.ps1",
    "PILOTO_WHATSAPP.bat": "scripts/whatsapp_pilot.ps1",
    "RESETAR_SEQUENCES.bat": "scripts/manutencao_banco_dev.ps1",
    "TESTAR_AUTENTICACAO.bat": "scripts/diagnosticar_autenticacao_dev.ps1",
    "IMPORTAR_SIMPLESVET_TESTE.bat": "scripts/importar_simplesvet_seguro.ps1",
}

COMPATIBILITY_REQUIRED_ACTIONS = {
    "INICIAR_BACKEND_LOCAL.bat": "dev-up",
    "INICIAR_DEV.bat": "dev-up",
    "INICIAR_TUDO.bat": "dev-up",
    "PARAR_TUDO.bat": "dev-down",
    "CORRIGIR_PERMISSOES_ADMIN.bat": "corrigir-permissoes-admin",
    "RESETAR_SEQUENCES.bat": "resetar-sequences",
}

BLOCKED_LEGACY_ENTRYPOINTS = (
    "setup-server.sh",
    "INICIAR_BANCO_PRODUCAO.bat",
    "INICIAR_PRODUCAO_LOCAL.bat",
    "INICIAR_PRODUCAO.bat",
    "ASSISTENTE_RELEASE.bat",
    "ASSISTENTE_RELEASE_EXECUTAR.bat",
    "FRONTEND_PILOTO.bat",
)

OFFICIAL_ROOT_OPERATIONAL_ENTRYPOINTS = frozenset({"FLUXO_UNICO.bat"})
ROOT_OPERATIONAL_SUFFIXES = frozenset({".bat", ".ps1", ".sh"})
ALLOWED_ROOT_OPERATIONAL_ENTRYPOINTS = frozenset(
    set(OFFICIAL_ROOT_OPERATIONAL_ENTRYPOINTS)
    | set(COMPATIBILITY_ENTRYPOINTS)
    | set(BLOCKED_LEGACY_ENTRYPOINTS)
)

LEGACY_DOCUMENT_REDIRECTS = {
    "DEPLOY_QUICKSTART.md": "docs/PRODUCAO_DEPLOY_SSH.md",
    "GUIA_COMPLETO_AMBIENTES.md": "docs/ATALHOS_OPERACIONAIS.md",
}
MAX_LEGACY_DOCUMENT_REDIRECT_LINES = 40

ALLOWED_ROOT_MARKDOWN = frozenset(
    {
        "AGENTS.md",
        "CONTRIBUTING.md",
        "DEPLOY_QUICKSTART.md",
        "GUIA_COMPLETO_AMBIENTES.md",
        "README.md",
    }
)

FORBIDDEN_ROOT_OPERATION_SNIPPETS = (
    "git push origin main",
    "git reset --hard",
    "drop table if exists alembic_version",
    "rm -f *merge*.py",
    "docker restart petshop-prod-backend",
    "docker cp ",
    "server_ip=",
    "git pull",
    "docker compose",
    "docker-compose",
    "npm run build",
    "frontend/.env.production",
    "root@mlprohub.com.br",
    "192.168.15.138",
    "admin123",
    "copy /y .env.development .env",
    "docker-compose.production-local.yml",
    "docker-compose.production.yml",
    "python -m uvicorn",
    "npm install",
    "prod-up",
    "docker exec",
    "c:/users/",
    "copy /y .env",
    "docker-compose.development.yml",
)

FORBIDDEN_TRACKED_PREFIXES = (
    "frontend/dist/",
    "frontend/node_modules/",
    "app-mobile/node_modules/",
    "node_modules/",
    "runtime/",
    ".venv/",
    "backend/logs_importacao/",
    "backend/resultado_importacao.txt",
    "simplesvet/",
    "backend/simplesvet/",
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


def unexpected_root_markdown(paths: Iterable[str]) -> list[str]:
    normalized = {_normalize(path) for path in paths}
    return sorted(
        path
        for path in normalized
        if "/" not in path
        and path.casefold().endswith(".md")
        and path not in ALLOWED_ROOT_MARKDOWN
    )


def unexpected_root_operational_entrypoints(paths: Iterable[str]) -> list[str]:
    normalized = {_normalize(path) for path in paths}
    return sorted(
        path
        for path in normalized
        if "/" not in path
        and Path(path).suffix.casefold() in ROOT_OPERATIONAL_SUFFIXES
        and path not in ALLOWED_ROOT_OPERATIONAL_ENTRYPOINTS
    )


def forbidden_operational_snippets(content: str) -> list[str]:
    normalized = content.casefold().replace("\\", "/")
    return sorted(
        snippet
        for snippet in FORBIDDEN_ROOT_OPERATION_SNIPPETS
        if snippet in normalized
    )


def has_blocking_exit(relative_path: str, content: str) -> bool:
    normalized = content.casefold()
    if Path(relative_path).suffix.casefold() == ".bat":
        return "exit /b 1" in normalized
    return "exit 1" in normalized


def operational_entrypoint_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    for relative_path, official_target in COMPATIBILITY_ENTRYPOINTS.items():
        path = root / relative_path
        if not path.exists():
            errors.append(f"Atalho de compatibilidade ausente: {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        if "COMPATIBILITY_ALIAS" not in content:
            errors.append(
                f"Atalho sem identificacao de compatibilidade: {relative_path}"
            )
        normalized_content = content.replace("\\", "/")
        if official_target not in normalized_content:
            errors.append(
                f"Atalho fora da implementacao oficial {official_target}: {relative_path}"
            )
        required_action = COMPATIBILITY_REQUIRED_ACTIONS.get(relative_path)
        if required_action and required_action not in content.casefold():
            errors.append(f"Atalho sem acao oficial {required_action}: {relative_path}")
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
        if "LEGACY_BLOCKED" not in content or not has_blocking_exit(
            relative_path, content
        ):
            errors.append(f"Entrada legada deixou de estar bloqueada: {relative_path}")
        forbidden = forbidden_operational_snippets(content)
        if forbidden:
            errors.append(
                f"Operacao perigosa voltou a entrada bloqueada {relative_path}: "
                + ", ".join(forbidden)
            )

    return errors


def legacy_document_redirect_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative_path, official_target in LEGACY_DOCUMENT_REDIRECTS.items():
        path = root / relative_path
        if not path.exists():
            errors.append(f"Redirecionamento de documento ausente: {relative_path}")
            continue
        content = path.read_text(encoding="utf-8")
        if "LEGACY_DOCUMENT_REDIRECT" not in content:
            errors.append(
                f"Documento historico voltou a ter instrucoes: {relative_path}"
            )
        if official_target not in content:
            errors.append(
                f"Documento historico sem destino oficial {official_target}: {relative_path}"
            )
        if len(content.splitlines()) > MAX_LEGACY_DOCUMENT_REDIRECT_LINES:
            errors.append(
                f"Redirecionamento historico voltou a ser guia: {relative_path}"
            )
        forbidden = forbidden_operational_snippets(content)
        if forbidden:
            errors.append(
                f"Instrucao operacional voltou ao documento {relative_path}: "
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

    unexpected_docs = unexpected_root_markdown(tracked)
    if unexpected_docs:
        errors.append("Documento solto fora de docs/: " + ", ".join(unexpected_docs))

    unexpected_operations = unexpected_root_operational_entrypoints(tracked)
    if unexpected_operations:
        errors.append(
            "Atalho operacional novo e nao classificado na raiz: "
            + ", ".join(unexpected_operations)
        )

    errors.extend(operational_entrypoint_errors(root))
    errors.extend(legacy_document_redirect_errors(root))

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
