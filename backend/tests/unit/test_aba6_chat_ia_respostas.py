from types import SimpleNamespace

import pytest

from app.ia.aba6_chat_ia_parts.respostas import ChatIARespostasMixin


class _FakeDb:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.refreshes = []

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, objeto):
        self.refreshes.append(objeto)


class _RespostaBase(ChatIARespostasMixin):
    def __init__(self, falhar=False):
        self.db = _FakeDb()
        self.falhar = falhar
        self.mensagens = []

    def obter_conversa(self, *_args, **_kwargs):
        return SimpleNamespace(id=1)

    def adicionar_mensagem(self, **dados):
        assert dados["commit"] is False
        mensagem = SimpleNamespace(
            id=len(self.mensagens) + 1,
            conteudo=dados["conteudo"],
            criado_em=SimpleNamespace(isoformat=lambda: "2026-09-17T00:00:00"),
        )
        self.mensagens.append(mensagem)
        return mensagem

    def obter_contexto_financeiro(self, *_args, **_kwargs):
        return {}

    def _gerar_resposta_simples(self, *_args, **_kwargs):
        if self.falhar:
            raise RuntimeError("falha simulada")
        return "resposta"


def test_envio_confirma_pergunta_e_resposta_em_um_unico_commit():
    service = _RespostaBase()

    resultado = service.gerar_resposta_ia(1, 1, "pergunta", tenant_id="tenant-1")

    assert resultado["mensagem_ia"]["conteudo"] == "resposta"
    assert service.db.commits == 1
    assert service.db.rollbacks == 0
    assert len(service.db.refreshes) == 2


def test_envio_desfaz_pergunta_quando_geracao_da_resposta_falha():
    service = _RespostaBase(falhar=True)

    with pytest.raises(RuntimeError, match="falha simulada"):
        service.gerar_resposta_ia(1, 1, "pergunta", tenant_id="tenant-1")

    assert service.db.commits == 0
    assert service.db.rollbacks == 1
    assert service.mensagens == []
