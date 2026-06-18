from datetime import datetime
import hashlib

from app.ia.extrato_parser import ExtratoParser


def test_gerar_hash_transacao_usa_sha256_deterministico():
    data = datetime(2026, 6, 18, 10, 30)
    descricao = "PIX CLIENTE"
    valor = 123.45
    conteudo = f"{data.isoformat()}{descricao}{valor}"

    assert (
        ExtratoParser.gerar_hash_transacao(data, descricao, valor)
        == hashlib.sha256(conteudo.encode()).hexdigest()
    )
