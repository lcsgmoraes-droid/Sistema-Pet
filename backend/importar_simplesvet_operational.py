"""Carga operacional historica do SimplesVet, sempre pelo plan/apply seguro.

O livro financeiro nao entra nesta carga. Apenas o saldo de vendas em aberto
vira conta a receber, apos conciliacao com a lista de devedores da exportacao.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

import app.db.base  # noqa: F401 - registra todas as tabelas antes dos inserts em lote
from app.dre_plano_contas_models import DRESubcategoria
from app.financeiro_models import CategoriaFinanceira, ContaReceber
from app.models import Cliente
from app.produtos_compras_models import PedidoCompra, PedidoCompraItem
from app.vendas_models import Venda, VendaBaixa, VendaItem, VendaPagamento
from importar_simplesvet_state import ID_MAP, RUNTIME, STATS
from importar_simplesvet_utils import parse_date


CENTAVOS = Decimal("0.01")
LOTE = 750


def _linhas(nome: str):
    caminho = RUNTIME.require_configured().source_dir / nome
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            if linha and any(valor not in (None, "") for valor in linha.values()):
                yield linha


def _valor(texto: str | None) -> Decimal:
    if texto in (None, "", "NULL"):
        return Decimal("0.00")
    return Decimal(str(texto)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _quantidade(texto: str | None) -> Decimal:
    if texto in (None, "", "NULL"):
        return Decimal(0)
    return Decimal(str(texto))


def _data(texto: str | None) -> datetime:
    data = parse_date(texto)
    if data is None:
        raise ValueError(f"Data SimplesVet ausente ou invalida: {texto!r}")
    return data


def _inserir_lote(db: Session, modelo, registros: list[dict]) -> None:
    if registros:
        db.execute(insert(modelo), registros)
        registros.clear()


def _numero_venda(linha: dict) -> str:
    return f"IMP-{_data(linha['ven_dat_data']):%Y%m%d}-{linha['ven_var_chave']}"


def _gravar_vendas_lote(db: Session, lote: list[tuple[str, str, dict]]) -> None:
    numeros = [numero for _, numero, _ in lote]
    existentes = dict(
        db.execute(
            select(Venda.numero_venda, Venda.id).where(
                Venda.tenant_id == RUNTIME.tenant_id,
                Venda.numero_venda.in_(numeros),
            )
        ).all()
    )
    novos = [dados for _, numero, dados in lote if numero not in existentes]
    _inserir_lote(db, Venda, novos)
    identificadores = dict(
        db.execute(
            select(Venda.numero_venda, Venda.id).where(
                Venda.tenant_id == RUNTIME.tenant_id,
                Venda.numero_venda.in_(numeros),
            )
        ).all()
    )
    if len(identificadores) != len(lote):
        raise ValueError("Nem todas as vendas foram vinculadas ao tenant de destino")
    for codigo_antigo, numero, _ in lote:
        ID_MAP["vendas"][codigo_antigo] = identificadores[numero]
    STATS["vendas"]["sucesso"] += len(lote) - len(existentes)
    STATS["vendas"]["duplicado"] += len(existentes)
    lote.clear()


def importar_vendas_em_lote(db: Session) -> None:
    lote: list[tuple[str, str, dict]] = []
    for linha in _linhas("eco_venda.csv"):
        STATS["vendas"]["total"] += 1
        cliente_antigo = linha.get("pes_int_codigo")
        if cliente_antigo not in (None, "", "NULL") and cliente_antigo not in ID_MAP["pessoas"]:
            raise ValueError("Venda referencia cliente que nao foi importado")
        data_venda = _data(linha["ven_dat_data"])
        status = {
            "Baixado": "finalizada",
            "Aberto": "aberta",
            "Baixa parcial": "baixa_parcial",
        }.get(linha.get("ven_var_status"))
        if status is None:
            raise ValueError("Status de venda nao reconhecido na exportacao")
        numero = _numero_venda(linha)
        lote.append(
            (
                linha["ven_int_codigo"],
                numero,
                {
                    "tenant_id": RUNTIME.tenant_id,
                    "user_id": RUNTIME.user_id,
                    "vendedor_id": RUNTIME.user_id,
                    "numero_venda": numero,
                    "cliente_id": ID_MAP["pessoas"].get(cliente_antigo),
                    "subtotal": _valor(linha.get("ven_dec_bruto")),
                    "desconto_valor": _valor(linha.get("ven_dec_descontovalor")),
                    "desconto_percentual": _valor(linha.get("ven_dec_descontopercentual")),
                    "total": _valor(linha.get("ven_dec_liquido")),
                    "observacoes": linha.get("ven_txt_observacao")
                    if linha.get("ven_txt_observacao") not in (None, "", "NULL")
                    else None,
                    "status": status,
                    "data_venda": data_venda,
                    "data_finalizacao": parse_date(linha.get("ven_dat_pagamento"))
                    if status == "finalizada" else None,
                    "created_at": parse_date(linha.get("ven_dti_inclusao")) or data_venda,
                },
            )
        )
        if len(lote) >= LOTE:
            _gravar_vendas_lote(db, lote)
    _gravar_vendas_lote(db, lote)


def importar_itens_venda_em_lote(db: Session) -> None:
    tipos = {
        linha["pro_int_codigo"]: (
            "servico" if linha.get("pro_cha_tipo") == "S" else "produto"
        )
        for linha in _linhas("eco_produto.csv")
    }
    lote: list[dict] = []
    for linha in _linhas("eco_venda_produto.csv"):
        STATS["itens_venda"]["total"] += 1
        venda_id = ID_MAP["vendas"].get(linha.get("ven_int_codigo"))
        produto_id = ID_MAP["produtos"].get(linha.get("pro_int_codigo"))
        if not venda_id or not produto_id:
            raise ValueError("Item de venda sem venda ou produto no tenant de destino")
        quantidade = _quantidade(linha.get("vpr_dec_quantidade"))
        preco = _valor(linha.get("vpr_dec_preco"))
        lote.append(
            {
                "tenant_id": RUNTIME.tenant_id,
                "venda_id": venda_id,
                "produto_id": produto_id,
                "tipo": tipos[linha["pro_int_codigo"]],
                "quantidade": quantidade,
                "preco_unitario": preco,
                "subtotal": (quantidade * preco).quantize(CENTAVOS),
                "desconto_item": Decimal("0.00"),
                "created_at": parse_date(linha.get("vpr_dti_inclusao")),
            }
        )
        if len(lote) >= LOTE:
            tamanho = len(lote)
            _inserir_lote(db, VendaItem, lote)
            STATS["itens_venda"]["sucesso"] += tamanho
    tamanho = len(lote)
    _inserir_lote(db, VendaItem, lote)
    STATS["itens_venda"]["sucesso"] += tamanho


def importar_pagamentos_venda(db: Session) -> None:
    vendas_origem = {
        linha["ven_int_codigo"]: linha for linha in _linhas("eco_venda.csv")
    }
    baixas_origem = {
        linha["vba_int_codigo"]: linha for linha in _linhas("eco_vendabaixa.csv")
    }
    formas_por_baixa: dict[str, set[str]] = defaultdict(set)
    soma_pagamentos: dict[str, Decimal] = defaultdict(Decimal)
    lote: list[dict] = []
    for linha in _linhas("eco_vendabaixa_formapagamento.csv"):
        STATS["pagamentos_venda"]["total"] += 1
        baixa = baixas_origem.get(linha["vba_int_codigo"])
        venda_origem = linha["ven_int_codigo"]
        venda_id = ID_MAP["vendas"].get(venda_origem)
        if baixa is None or not venda_id or baixa["ven_int_codigo"] != venda_origem:
            raise ValueError("Pagamento sem baixa ou venda correspondente")
        forma = (linha.get("fpa_var_nome") or "Outros")[:50]
        valor = _valor(linha.get("vfp_dec_valor"))
        soma_pagamentos[venda_origem] += valor
        formas_por_baixa[linha["vba_int_codigo"]].add(forma)
        lote.append(
            {
                "tenant_id": RUNTIME.tenant_id,
                "venda_id": venda_id,
                "forma_pagamento": forma,
                "valor": valor,
                "status": "aprovado",
                "data_pagamento": _data(baixa.get("vba_dat_baixa")),
            }
        )
        if len(lote) >= LOTE:
            tamanho = len(lote)
            _inserir_lote(db, VendaPagamento, lote)
            STATS["pagamentos_venda"]["sucesso"] += tamanho
    tamanho = len(lote)
    _inserir_lote(db, VendaPagamento, lote)
    STATS["pagamentos_venda"]["sucesso"] += tamanho

    for codigo, linha in vendas_origem.items():
        pago = _valor(linha.get("ven_dec_pago"))
        if pago != soma_pagamentos[codigo]:
            if linha.get("ven_var_status") != "Baixado":
                raise ValueError("Venda aberta tem pagamentos divergentes")
            STATS["pagamentos_venda"]["divergencia"] += 1

    # VendaBaixa preserva a data de cada baixa sem gerar movimentos de caixa.
    saldo_por_venda: dict[str, Decimal] = {}
    lote_baixas: list[dict] = []
    for baixa in sorted(
        baixas_origem.values(),
        key=lambda item: (item.get("vba_dat_baixa") or "", int(item["vba_int_codigo"])),
    ):
        STATS["baixas_venda"]["total"] += 1
        codigo = baixa["ven_int_codigo"]
        venda_id = ID_MAP["vendas"].get(codigo)
        if not venda_id:
            raise ValueError("Baixa sem venda correspondente")
        anterior = saldo_por_venda.setdefault(
            codigo, _valor(vendas_origem[codigo].get("ven_dec_liquido"))
        )
        valor = min(_valor(baixa.get("vba_dec_pago")), anterior)
        restante = max(anterior - valor, Decimal("0.00"))
        saldo_por_venda[codigo] = restante
        formas = formas_por_baixa.get(baixa["vba_int_codigo"], set())
        lote_baixas.append(
            {
                "tenant_id": RUNTIME.tenant_id,
                "venda_id": venda_id,
                "valor_baixa": valor,
                "valor_anterior": anterior,
                "valor_restante": restante,
                "forma_pagamento": next(iter(formas)) if len(formas) == 1 else "Misto",
                "tipo": "baixa_total" if restante == 0 else "baixa_parcial",
                "usuario_id": RUNTIME.user_id,
                "data_baixa": _data(baixa.get("vba_dat_baixa")),
            }
        )
        if len(lote_baixas) >= LOTE:
            tamanho = len(lote_baixas)
            _inserir_lote(db, VendaBaixa, lote_baixas)
            STATS["baixas_venda"]["sucesso"] += tamanho
    tamanho = len(lote_baixas)
    _inserir_lote(db, VendaBaixa, lote_baixas)
    STATS["baixas_venda"]["sucesso"] += tamanho


def importar_saldos_clientes(db: Session) -> None:
    saldos_fonte = {
        linha["pes_int_codigo"]: _valor(linha.get("pes_dec_saldoaberto"))
        for linha in _linhas("glo_pessoadebito.csv")
    }
    soma_por_cliente: dict[str, Decimal] = defaultdict(Decimal)
    contas: list[dict] = []
    categoria = db.execute(
        select(CategoriaFinanceira).where(
            CategoriaFinanceira.tenant_id == RUNTIME.tenant_id,
            CategoriaFinanceira.nome == "Receitas de Vendas",
            CategoriaFinanceira.tipo == "receita",
        )
    ).scalars().first()
    if categoria is None or categoria.dre_subcategoria_id is None:
        raise ValueError("Categoria Receitas de Vendas sem vinculo DRE no tenant")
    subcategoria = db.execute(
        select(DRESubcategoria.id).where(
            DRESubcategoria.tenant_id == RUNTIME.tenant_id,
            DRESubcategoria.id == categoria.dre_subcategoria_id,
        )
    ).scalar_one_or_none()
    if subcategoria is None:
        raise ValueError("Subcategoria DRE da receita nao pertence ao tenant")
    for linha in _linhas("eco_venda.csv"):
        if linha.get("ven_var_status") == "Baixado":
            continue
        saldo = _valor(linha.get("ven_dec_liquido")) - _valor(linha.get("ven_dec_pago"))
        if saldo <= 0:
            continue
        pessoa = linha.get("pes_int_codigo")
        if pessoa in (None, "", "NULL"):
            STATS["contas_receber"]["sem_cliente"] += 1
            continue
        cliente_id = ID_MAP["pessoas"].get(pessoa)
        venda_id = ID_MAP["vendas"].get(linha["ven_int_codigo"])
        if not cliente_id or not venda_id:
            raise ValueError("Saldo em aberto sem cliente ou venda importada")
        soma_por_cliente[pessoa] += saldo
        data_venda = _data(linha["ven_dat_data"]).date()
        contas.append(
            {
                "tenant_id": RUNTIME.tenant_id,
                "user_id": RUNTIME.user_id,
                "descricao": f"Saldo SimplesVet venda {linha['ven_var_chave']}",
                "cliente_id": cliente_id,
                "categoria_id": categoria.id,
                "dre_subcategoria_id": subcategoria,
                "canal": "loja_fisica",
                "valor_original": saldo,
                "valor_recebido": Decimal("0.00"),
                "valor_final": saldo,
                "data_emissao": data_venda,
                "data_vencimento": data_venda,
                "status": "vencido" if data_venda < date.today() else "pendente",
                "venda_id": venda_id,
                "documento": f"SV-{linha['ven_int_codigo']}",
                "observacoes": "Vencimento original indisponivel; usada a data da venda.",
            }
        )
    if saldos_fonte != dict(soma_por_cliente):
        raise ValueError("Saldos por cliente nao conferem com a lista de devedores")
    STATS["contas_receber"]["total"] = len(contas)
    STATS["contas_receber"]["clientes_devedores"] = len(saldos_fonte)
    STATS["contas_receber"]["saldo_centavos"] = int(
        sum(saldos_fonte.values(), Decimal("0.00")) * 100
    )
    for inicio in range(0, len(contas), LOTE):
        db.execute(insert(ContaReceber), contas[inicio:inicio + LOTE])
        STATS["contas_receber"]["sucesso"] += len(contas[inicio:inicio + LOTE])


def importar_fornecedores_e_compras(db: Session) -> None:
    for linha in _linhas("eco_fornecedor.csv"):
        STATS["fornecedores"]["total"] += 1
        codigo = f"FOR-{linha['for_int_codigo']}"
        fornecedor = db.execute(
            select(Cliente).where(
                Cliente.tenant_id == RUNTIME.tenant_id, Cliente.codigo == codigo
            )
        ).scalars().first()
        if fornecedor is None:
            juridica = bool(linha.get("for_var_cnpj") not in (None, "", "NULL"))
            fornecedor = Cliente(
                tenant_id=RUNTIME.tenant_id,
                user_id=RUNTIME.user_id,
                codigo=codigo,
                nome=linha["for_var_nome"],
                tipo_cadastro="fornecedor",
                tipo_pessoa="PJ" if juridica else "PF",
                cnpj=linha.get("for_var_cnpj") if juridica else None,
                cpf=linha.get("for_var_cpf") if not juridica and linha.get("for_var_cpf") not in (None, "", "NULL") else None,
                inscricao_estadual=linha.get("for_var_inscricaoestadual") if linha.get("for_var_inscricaoestadual") not in (None, "", "NULL") else None,
                cep=linha.get("end_var_cep") if linha.get("end_var_cep") not in (None, "", "NULL") else None,
                endereco=linha.get("end_var_endereco") if linha.get("end_var_endereco") not in (None, "", "NULL") else None,
                numero=linha.get("end_var_numero") if linha.get("end_var_numero") not in (None, "", "NULL") else None,
                bairro=linha.get("end_var_bairro") if linha.get("end_var_bairro") not in (None, "", "NULL") else None,
                cidade=linha.get("end_var_municipio") if linha.get("end_var_municipio") not in (None, "", "NULL") else None,
                estado=linha.get("end_var_uf") if linha.get("end_var_uf") not in (None, "", "NULL") else None,
            )
            db.add(fornecedor)
            db.flush()
            STATS["fornecedores"]["sucesso"] += 1
        else:
            STATS["fornecedores"]["duplicado"] += 1
        ID_MAP["fornecedores"][linha["for_int_codigo"]] = fornecedor.id

    for linha in _linhas("eco_compra.csv"):
        STATS["compras"]["total"] += 1
        numero = f"SV-{RUNTIME.tenant_id}-{linha['com_int_codigo']}"
        compra = db.execute(
            select(PedidoCompra).where(
                PedidoCompra.tenant_id == RUNTIME.tenant_id,
                PedidoCompra.numero_pedido == numero,
            )
        ).scalars().first()
        if compra is None:
            fornecedor_id = ID_MAP["fornecedores"].get(linha["for_int_codigo"])
            if not fornecedor_id:
                raise ValueError("Compra sem fornecedor importado")
            data_compra = _data(linha["com_dat_data"])
            compra = PedidoCompra(
                tenant_id=RUNTIME.tenant_id,
                user_id=RUNTIME.user_id,
                numero_pedido=numero,
                fornecedor_id=fornecedor_id,
                status="recebido_total",
                valor_total=float(_valor(linha.get("com_dec_bruto"))),
                valor_desconto=float(_valor(linha.get("com_dec_descontovalor"))),
                valor_final=float(_valor(linha.get("com_dec_liquido"))),
                data_pedido=data_compra,
                data_recebimento=data_compra,
                observacoes=linha.get("com_txt_observacao") if linha.get("com_txt_observacao") not in (None, "", "NULL") else None,
            )
            db.add(compra)
            db.flush()
            STATS["compras"]["sucesso"] += 1
        else:
            STATS["compras"]["duplicado"] += 1
        ID_MAP["compras"][linha["com_int_codigo"]] = compra.id

    lote: list[dict] = []
    for linha in _linhas("eco_compra_produto.csv"):
        STATS["itens_compra"]["total"] += 1
        compra_id = ID_MAP["compras"].get(linha.get("com_int_codigo"))
        produto_id = ID_MAP["produtos"].get(linha.get("pro_int_codigo"))
        if not compra_id or not produto_id:
            raise ValueError("Item de compra sem compra ou produto no tenant")
        quantidade = _quantidade(linha.get("cpr_dec_quantidade"))
        preco = _valor(linha.get("cpr_dec_preco"))
        lote.append(
            {
                "tenant_id": RUNTIME.tenant_id,
                "pedido_compra_id": compra_id,
                "produto_id": produto_id,
                "quantidade_pedida": float(quantidade),
                "quantidade_recebida": float(quantidade),
                "quantidade_total_unidades": float(quantidade),
                "preco_unitario": float(preco),
                "valor_total": float((quantidade * preco).quantize(CENTAVOS)),
                "status": "recebido_total",
            }
        )
        if len(lote) >= LOTE:
            tamanho = len(lote)
            _inserir_lote(db, PedidoCompraItem, lote)
            STATS["itens_compra"]["sucesso"] += tamanho
    tamanho = len(lote)
    _inserir_lote(db, PedidoCompraItem, lote)
    STATS["itens_compra"]["sucesso"] += tamanho
