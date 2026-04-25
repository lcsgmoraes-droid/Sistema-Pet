import io
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ["DEBUG"] = "false"

from app import veterinario_exames_arquivos as arquivos


def _upload(filename: str, content: bytes):
    return SimpleNamespace(filename=filename, file=io.BytesIO(content))


def test_salvar_arquivo_exame_upload_persiste_e_atualiza_status(tmp_path, monkeypatch):
    monkeypatch.setattr(arquivos, "UPLOADS_DIR", tmp_path)
    exame = SimpleNamespace(
        id=12,
        arquivo_nome=None,
        arquivo_url=None,
        data_resultado=None,
        status="solicitado",
    )

    nome_original = arquivos.salvar_arquivo_exame_upload(
        exame,
        "tenant-a",
        _upload("Laudo Clinico.pdf", b"%PDF-1.4"),
    )

    caminho_salvo = tmp_path / "tenant-a" / Path(exame.arquivo_url).name
    assert nome_original == "Laudo Clinico.pdf"
    assert exame.arquivo_nome == "Laudo Clinico.pdf"
    assert exame.arquivo_url.startswith("/uploads/veterinario/exames/tenant-a/exame_12_")
    assert exame.status == "disponivel"
    assert exame.data_resultado is not None
    assert caminho_salvo.read_bytes() == b"%PDF-1.4"


def test_salvar_arquivo_exame_upload_rejeita_extensao_invalida(tmp_path, monkeypatch):
    monkeypatch.setattr(arquivos, "UPLOADS_DIR", tmp_path)
    exame = SimpleNamespace(id=12, data_resultado=None, status="solicitado")

    with pytest.raises(HTTPException) as exc:
        arquivos.salvar_arquivo_exame_upload(exame, "tenant-a", _upload("laudo.exe", b"abc"))

    assert exc.value.status_code == 400
    assert "Formato inválido" in exc.value.detail
