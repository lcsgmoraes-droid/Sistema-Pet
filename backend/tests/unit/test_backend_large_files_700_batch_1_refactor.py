from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def line_count(relative_path: str) -> int:
    return len(read(relative_path).splitlines())


def test_backend_large_files_700_batch_1_targets_are_below_limit():
    target_files = [
        "app/relatorio_vendas_builder.py",
        "app/dashboard/ponto_equilibrio.py",
        "app/notas_entrada/processamento_routes.py",
    ]

    for relative_path in target_files:
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_1_extractions_exist_and_stay_small():
    extracted_files = [
        "app/relatorio_vendas_preloads.py",
        "app/dashboard/ponto_equilibrio_margem.py",
        "app/dashboard/ponto_equilibrio_classificacao.py",
        "app/notas_entrada/processamento_precos.py",
    ]

    for relative_path in extracted_files:
        path = ROOT / relative_path
        assert path.exists(), f"Missing extracted backend refactor file: {relative_path}"
        assert line_count(relative_path) <= 700, (
            f"{relative_path} has {line_count(relative_path)} lines; expected <= 700"
        )


def test_backend_large_files_700_batch_1_sources_delegate_to_extractions():
    imports = [
        (
            "app/relatorio_vendas_builder.py",
            ".relatorio_vendas_preloads",
            "relatorio_vendas_builder.py should delegate report preloads",
        ),
        (
            "app/dashboard/ponto_equilibrio.py",
            ".ponto_equilibrio_margem",
            "ponto_equilibrio.py should delegate margin helpers",
        ),
        (
            "app/dashboard/ponto_equilibrio.py",
            ".ponto_equilibrio_classificacao",
            "ponto_equilibrio.py should delegate classification helpers",
        ),
        (
            "app/notas_entrada/processamento_routes.py",
            ".processamento_precos",
            "processamento_routes.py should delegate price processing helpers",
        ),
    ]

    for source_path, import_path, message in imports:
        assert import_path in read(source_path), message
