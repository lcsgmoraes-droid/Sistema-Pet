from app.ai.intent_classifier import IntentRouter


def test_should_transfer_to_human_for_pedido_novo_phase1():
    assert IntentRouter.should_transfer_to_human("pedido_novo", 0.95) is True


def test_should_transfer_to_human_for_pedido_recompra_phase1():
    assert IntentRouter.should_transfer_to_human("pedido_recompra", 0.90) is True


def test_should_transfer_to_human_for_reclamacao():
    assert IntentRouter.should_transfer_to_human("reclamacao", 0.80) is True


def test_should_transfer_to_human_for_low_confidence():
    assert IntentRouter.should_transfer_to_human("consulta_produto", 0.20) is True


def test_should_not_transfer_for_regular_consulta_with_good_confidence():
    assert IntentRouter.should_transfer_to_human("consulta_produto", 0.85) is False
