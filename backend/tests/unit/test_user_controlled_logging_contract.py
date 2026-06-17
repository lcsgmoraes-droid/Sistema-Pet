from __future__ import annotations

import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


FORBIDDEN_USER_CONTROLLED_LOG_PATTERNS = [
    (
        "app/analise_racoes_routes.py",
        r"logger\.info\(f\".*\{tenant_id\}",
        "tenant id in opcoes filtros log",
    ),
    (
        "app/bling_sync_routes.py",
        r"logger\.warning\(\"Falha ao ler snapshot compartilhado %s do tenant %s: %s\"",
        "shared snapshot read log with tenant/error args",
    ),
    (
        "app/bling_sync_routes.py",
        r"logger\.warning\(\"Falha ao gravar snapshot compartilhado %s do tenant %s: %s\"",
        "shared snapshot write log with tenant/error args",
    ),
    (
        "app/bling_sync_routes.py",
        r"logger\.info\(f\".*Produto \{produto_id\}, Origem: \{origem\}",
        "manual stock reconciliation product/origin log",
    ),
    (
        "app/calculadora_racao.py",
        r"logger\.info\(f\".*\{req\.peso_pet_kg\}.*\{req\.idade_meses\}.*\{req\.nivel_atividade\}",
        "ration calculator request payload log",
    ),
    (
        "app/calculadora_racao.py",
        r"logger\.info\(f\".*\{tabela_consumo\[:200\]\}",
        "ration calculator consumption table log",
    ),
    (
        "app/clientes_routes.py",
        r"logger\.info\(f\"\[DEBUG update_cliente\].*\{cliente_id\}.*\{tenant_id\}",
        "client update debug identity log",
    ),
    (
        "app/clientes_routes.py",
        r"logger\.info\(f\"\[DEBUG\] entregador_padrao=.*\{cliente_data\.",
        "client update payload log",
    ),
    (
        "app/clientes_routes.py",
        r"logger\.info\(f\".*vendas-em-aberto: cliente_id=\{cliente_id\}, user_id=\{current_user\.id\}",
        "open sales client/user log",
    ),
    (
        "app/comissoes_diagnostico_routes.py",
        r"logger\.info\(f\".*tenant \{tenant_id\}",
        "commission diagnosis tenant log",
    ),
    (
        "app/conciliacao_services.py",
        r"logger\.info\(f\"\[Upload\] Iniciando processamento: \{nome_arquivo\}",
        "conciliation upload filename log",
    ),
    (
        "app/dashboard_routes.py",
        r"logger\.info\(f\"\[contas-vencidas\].*tenant \{tenant_id\}",
        "overdue accounts tenant log",
    ),
    (
        "app/estoque_movimentacoes_edicao_routes.py",
        r"logger\.info\(\"Movimentacao %s excluida por %s\"",
        "stock movement delete user log",
    ),
    (
        "app/estoque_movimentacoes_edicao_routes.py",
        r"logger\.info\(\"Movimentacao %s editada por %s\"",
        "stock movement edit user log",
    ),
    (
        "app/notas_entrada_routes.py",
        r"logger\.info\(f\".*Upload de XML - Arquivo: \{file\.filename\}",
        "xml upload filename log",
    ),
    (
        "app/notas_entrada_routes.py",
        r"logger\.info\(f\".*Content-type: \{file\.content_type\}",
        "xml upload content-type log",
    ),
    (
        "app/notas_entrada_routes.py",
        r"logger\.info\(f\".*\{current_user\.email\} \(ID: \{current_user\.id\}\)",
        "xml upload user identity log",
    ),
    (
        "app/notas_entrada_routes.py",
        r"logger\.error\(f\".*Arquivo.*\{file\.filename\}",
        "invalid xml filename log",
    ),
    (
        "app/notas_entrada_routes.py",
        r"logger\.info\(f\"Upload de PDF de entrada - Arquivo: \{filename\}",
        "pdf upload filename log",
    ),
    (
        "app/notas_entrada_routes.py",
        r"logger\.info\(f\".*Usuario: \{current_user\.email\} \(ID: \{current_user\.id\}\)",
        "pdf upload user identity log",
    ),
    (
        "app/notas_entrada_routes.py",
        r"logger\.info\(f\".*Usu.*rio: \{current_user\.email\}",
        "batch upload user email log",
    ),
    (
        "app/pedidos_compra_routes.py",
        r"logger\.info\(f\".*Usu.*rio: \{current_user\.nome\}",
        "purchase orders user name log",
    ),
    (
        "app/pedidos_compra_routes.py",
        r"logger\.info\(\s*f\".*fornecedor \{fornecedor_id\}.*tenant \{tenant_id\}\"",
        "purchase draft supplier/tenant log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\".*User: \{current_user\.email\}",
        "product create user email log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\".*Dados recebidos: \{produto\.model_dump\(\)\}",
        "product create payload log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\".*GET /produtos/.*\{total\}.*\{tenant_id\}",
        "product list tenant log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.error\(f\"\[UPLOAD\] Produto \{produto_id\}.*\{current_user\.email\}",
        "product image missing product user log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.error\(f\"\[UPLOAD\] Tipo.*\{file\.content_type\}",
        "product image content-type log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\".*Imagem \{nova_imagem\.id\}.*\{produto_id\}.*\{current_user\.email\}",
        "product image upload user log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\"Imagem \{imagem_id\} atualizada por \{user\.email\}",
        "product image update user log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\"Imagem \{imagem_id\} deletada por \{current_user\.email\}",
        "product image delete user log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\"V.*nculo fornecedor \{vinculo_id\} atualizado por \{current_user\.email\}",
        "supplier link update user log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\"Fornecedor desvinculado \(id \{vinculo_id\}\) por \{current_user\.email\}",
        "supplier unlink user log",
    ),
    (
        "app/produtos_routes.py",
        r"logger\.info\(f\"\[racao/alertas\].*\{tenant_id\}.*\{especie\}",
        "ration alerts tenant/species log",
    ),
    (
        "app/relatorio_vendas_routes.py",
        r"logger\.info\(f\"Gerando PDF de vendas.*\{data_inicio\}.*\{data_fim\}",
        "sales report date range log",
    ),
    (
        "app/routes/sefaz_routes.py",
        r"logger\.info\(f\"\[SEFAZ\].*tenant \{tenant_id\} user \{current_user\.id\}",
        "sefaz manual sync tenant/user log",
    ),
    (
        "app/vendas_routes.py",
        r"logger\.info\(\s*\"Cancelando venda por rota DELETE preservando auditoria: venda_id=%s user_id=%s tenant_id=%s\"",
        "sale delete audit user/tenant log",
    ),
    (
        "app/vendas_routes.py",
        r"logger\.info\(f\".*Dados recebidos: \{dados\}",
        "sale cancel payload log",
    ),
    (
        "app/vendas_routes.py",
        r"logger\.info\(f\".*Usu.*rio: \{current_user\.nome\} \(ID: \{current_user\.id\}\)",
        "sale cancel user identity log",
    ),
    (
        "app/vendas_routes.py",
        r"logger\.info\(f\".*Tenant ID: \{tenant_id\}",
        "sale cancel tenant log",
    ),
]


def test_known_user_controlled_log_patterns_are_removed():
    matches: list[str] = []

    for relative_path, pattern, label in FORBIDDEN_USER_CONTROLLED_LOG_PATTERNS:
        source = (BACKEND_ROOT / relative_path).read_text(encoding="utf-8")
        if re.search(pattern, source, flags=re.DOTALL):
            matches.append(f"{relative_path}: {label}")

    assert matches == []
