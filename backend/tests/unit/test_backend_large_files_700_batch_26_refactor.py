from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]

CHAT_IA_FILES = [
    "app/ia/aba6_chat_ia.py",
    "app/ia/aba6_chat_ia_parts/__init__.py",
    "app/ia/aba6_chat_ia_parts/base.py",
    "app/ia/aba6_chat_ia_parts/contexto.py",
    "app/ia/aba6_chat_ia_parts/conversas.py",
    "app/ia/aba6_chat_ia_parts/facade.py",
    "app/ia/aba6_chat_ia_parts/mensagens.py",
    "app/ia/aba6_chat_ia_parts/metricas.py",
    "app/ia/aba6_chat_ia_parts/periodos.py",
    "app/ia/aba6_chat_ia_parts/respostas.py",
    "app/ia/aba6_chat_ia_parts/service.py",
]


def _non_empty_line_count(relative_path: str) -> int:
    source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
    return sum(1 for line in source.splitlines() if line.strip())


def test_chat_ia_fachada_preserva_api_publica_extraida():
    from app.ia import aba6_chat_ia
    from app.ia import aba6_chat_ia_parts
    from app.ia.aba6_chat_ia_parts import facade

    assert aba6_chat_ia.ChatIAService is aba6_chat_ia_parts.ChatIAService
    assert aba6_chat_ia.criar_conversa_service is facade.criar_conversa_service
    assert aba6_chat_ia.listar_conversas_service is facade.listar_conversas_service
    assert aba6_chat_ia.enviar_mensagem_service is facade.enviar_mensagem_service
    assert aba6_chat_ia.deletar_conversa_service is facade.deletar_conversa_service


def test_chat_ia_fatia_26_fica_abaixo_de_700_linhas_nao_vazias():
    oversized = {
        relative_path: _non_empty_line_count(relative_path)
        for relative_path in CHAT_IA_FILES
        if _non_empty_line_count(relative_path) > 700
    }

    assert oversized == {}
