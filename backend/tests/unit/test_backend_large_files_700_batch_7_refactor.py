from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read(relative_path).splitlines())


def test_backend_large_files_700_batch_7_compras_pendencias_modules_stay_below_limit():
    target_files = [
        "app/compras_pendencias_routes.py",
        "app/compras_pendencias_constants.py",
        "app/compras_pendencias_schemas.py",
        "app/compras_pendencias_utils.py",
        "app/compras_pendencias_notas.py",
        "app/compras_pendencias_serializacao.py",
        "app/compras_pendencias_documentos.py",
        "app/compras_pendencias_criacao_routes.py",
        "app/compras_pendencias_consulta_routes.py",
        "app/compras_pendencias_email_routes.py",
    ]

    for relative_path in target_files:
        path = ROOT / relative_path
        assert path.exists(), (
            f"Missing extracted backend refactor file: {relative_path}"
        )
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_7_compras_pendencias_routes_is_facade():
    source = read("app/compras_pendencias_routes.py")

    assert "router.include_router(consulta_router)" in source
    assert "router.include_router(criacao_router)" in source
    assert "router.include_router(email_router)" in source
    assert "from .compras_pendencias_consulta_routes import" in source
    assert "from .compras_pendencias_criacao_routes import" in source
    assert "from .compras_pendencias_email_routes import" in source
    assert "def criar_pendencia_por_nota(" not in source
    assert "def enviar_email_pendencia(" not in source
    assert line_count("app/compras_pendencias_routes.py") <= 120


def test_backend_large_files_700_batch_7_preserves_public_compras_paths():
    from app.compras_pendencias_routes import router

    route_methods = {
        (route.path, method)
        for route in router.routes
        for method in getattr(route, "methods", set())
    }

    expected_methods = {
        ("/compras-pendencias/", "GET"),
        ("/compras-pendencias/notas/{nota_id}", "POST"),
        ("/compras-pendencias/envio/status", "GET"),
        ("/compras-pendencias/{pendencia_id}", "GET"),
        ("/compras-pendencias/{pendencia_id}", "PATCH"),
        ("/compras-pendencias/{pendencia_id}/registrar-email", "POST"),
        ("/compras-pendencias/{pendencia_id}/enviar-email", "POST"),
        ("/compras-pendencias/{pendencia_id}/email-texto", "GET"),
        ("/compras-pendencias/{pendencia_id}/pdf", "GET"),
    }

    assert expected_methods <= route_methods


def test_backend_large_files_700_batch_7_keeps_public_exports():
    from app.compras_pendencias_consulta_routes import (
        listar_pendencias as extracted_listar,
    )
    from app.compras_pendencias_criacao_routes import (
        criar_pendencia_por_nota as extracted_criar,
    )
    from app.compras_pendencias_email_routes import (
        enviar_email_pendencia as extracted_enviar,
    )
    from app.compras_pendencias_routes import (
        CriarPendenciaNotaPayload,
        RegistrarEmailPayload,
        criar_pendencia_por_nota,
        enviar_email_pendencia,
        listar_pendencias,
    )
    from app.compras_pendencias_schemas import (
        CriarPendenciaNotaPayload as ExtractedCriarPayload,
        RegistrarEmailPayload as ExtractedEmailPayload,
    )

    assert CriarPendenciaNotaPayload is ExtractedCriarPayload
    assert RegistrarEmailPayload is ExtractedEmailPayload
    assert criar_pendencia_por_nota is extracted_criar
    assert listar_pendencias is extracted_listar
    assert enviar_email_pendencia is extracted_enviar
