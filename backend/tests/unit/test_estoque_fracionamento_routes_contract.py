import os

os.environ["DEBUG"] = "false"

from app.estoque_fracionamento_routes import router


def test_rotas_publicam_conversao_contexto_e_sugestao():
    rotas = {
        (rota.path, ",".join(sorted(rota.methods or []))) for rota in router.routes
    }

    assert ("/estoque/fracionamento-clinico/converter", "POST") in rotas
    assert (
        "/estoque/fracionamento-clinico/origens/{produto_origem_id}",
        "GET",
    ) in rotas
    assert (
        "/estoque/fracionamento-clinico/destinos/{produto_destino_id}/sugestao",
        "GET",
    ) in rotas
