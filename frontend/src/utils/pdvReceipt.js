import { formatMoneyBRL } from "./formatters.js";

export const RECEIPT_WIDTH = 42;

function texto(valor) {
  return String(valor || "").trim();
}

function toAscii(valor) {
  return texto(valor)
    .normalize("NFD")
    .replaceAll(/[\u0300-\u036f]/g, "")
    .replaceAll(/[^\x20-\x7E]/g, " ")
    .replaceAll(/\s+/g, " ")
    .trim();
}

function clip(valor, max = RECEIPT_WIDTH) {
  const limpo = toAscii(valor);
  return limpo.length > max ? `${limpo.slice(0, max - 3)}...` : limpo;
}

function center(valor, width = RECEIPT_WIDTH) {
  const limpo = clip(valor, width);
  const total = Math.max(0, width - limpo.length);
  const left = Math.floor(total / 2);
  const right = total - left;
  return `${" ".repeat(left)}${limpo}${" ".repeat(right)}`;
}

function linePair(label, valor, width = RECEIPT_WIDTH) {
  const right = clip(valor, Math.max(8, Math.floor(width / 2)));
  const maxLeft = Math.max(0, width - right.length - 1);
  const left = clip(label, maxLeft);
  return `${left}${" ".repeat(Math.max(1, width - left.length - right.length))}${right}`;
}

function wrap(valor, width = RECEIPT_WIDTH) {
  const palavras = toAscii(valor).split(" ");
  const linhas = [];
  let atual = "";

  for (const palavra of palavras) {
    if (!palavra) continue;
    const proposta = atual ? `${atual} ${palavra}` : palavra;
    if (proposta.length <= width) {
      atual = proposta;
      continue;
    }
    if (atual) linhas.push(atual);
    if (palavra.length <= width) {
      atual = palavra;
      continue;
    }
    for (let index = 0; index < palavra.length; index += width) {
      linhas.push(palavra.slice(index, index + width));
    }
    atual = "";
  }

  if (atual) linhas.push(atual);
  return linhas.length ? linhas : [""];
}

function wrapMultiline(valor, width = RECEIPT_WIDTH) {
  return String(valor || "")
    .split(/\r?\n/)
    .flatMap((linha) => wrap(linha, width));
}

function textosIguais(primeiro, segundo) {
  return (
    toAscii(primeiro).toLocaleLowerCase("pt-BR") === toAscii(segundo).toLocaleLowerCase("pt-BR")
  );
}

function montarEnderecoEmpresa(empresa = {}) {
  const cidadeUf = [texto(empresa.cidade), texto(empresa.uf)].filter(Boolean).join("/");
  return [
    texto(empresa.endereco || empresa.logradouro),
    texto(empresa.numero),
    texto(empresa.complemento),
    texto(empresa.bairro),
    cidadeUf,
    texto(empresa.cep) ? `CEP ${texto(empresa.cep)}` : "",
  ]
    .filter(Boolean)
    .join(", ");
}

function montarCabecalhoEmpresa(empresa = {}) {
  const cabecalhoPersonalizado = texto(empresa.cupom_cabecalho);
  const nomeFantasia = texto(empresa.nome_fantasia || empresa.name);
  const razaoSocial = texto(empresa.razao_social);
  const nomePrincipal = nomeFantasia || razaoSocial || "SISTEMA PET";
  const endereco = montarEnderecoEmpresa(empresa);
  const linhas = [];

  if (cabecalhoPersonalizado) {
    linhas.push(...wrapMultiline(cabecalhoPersonalizado).map((linha) => center(linha)));
  } else {
    linhas.push(center(nomePrincipal));
  }

  if (cabecalhoPersonalizado && !textosIguais(cabecalhoPersonalizado, nomePrincipal)) {
    linhas.push(...wrap(nomePrincipal).map((linha) => center(linha)));
  }

  if (razaoSocial && !textosIguais(razaoSocial, nomePrincipal)) {
    linhas.push(...wrap(razaoSocial).map((linha) => center(linha)));
  }

  if (texto(empresa.cnpj)) {
    linhas.push(center(`CNPJ: ${texto(empresa.cnpj)}`));
  }

  if (endereco) {
    linhas.push(...wrap(endereco).map((linha) => center(linha)));
  }

  if (texto(empresa.telefone)) {
    linhas.push(center(`Contato: ${texto(empresa.telefone)}`));
  }
  if (texto(empresa.email)) {
    linhas.push(...wrap(texto(empresa.email)).map((linha) => center(linha)));
  }

  return linhas;
}

function montarRodapeEmpresa(empresa = {}) {
  const mensagem = texto(empresa.cupom_mensagem_final);
  if (mensagem) {
    return wrapMultiline(mensagem).map((linha) => center(linha));
  }
  return [center("Obrigado pela preferencia!"), center("Volte sempre!")];
}

function renderItens(itens = []) {
  const linhas = [];
  for (const item of itens) {
    const nome = item?.produto_nome || item?.descricao || item?.servico_descricao || "Item";
    linhas.push(...wrap(nome, RECEIPT_WIDTH));

    const qtd = Number(item?.quantidade || 0);
    const unit = formatMoneyBRL(Number(item?.preco_unitario || item?.preco_venda || 0));
    const subtotal = formatMoneyBRL(Number(item?.subtotal || 0));
    linhas.push(linePair(`${qtd} x ${unit}`, subtotal));

    const desconto = Number(item?.desconto_valor || item?.desconto_item || 0);
    if (desconto > 0) {
      linhas.push(linePair("Desconto item", `-${formatMoneyBRL(desconto)}`));
    }
    linhas.push("");
  }
  return linhas;
}

function montarDadosCliente(venda = {}) {
  const telefoneCliente =
    venda?.cliente?.celular ||
    venda?.cliente?.telefone ||
    venda?.cliente?.celular_whatsapp ||
    venda?.telefone_cliente ||
    "";
  const enderecoCliente = [
    venda?.cliente?.endereco,
    venda?.cliente?.numero,
    venda?.cliente?.bairro,
    venda?.cliente?.cidade,
    venda?.cliente?.estado || venda?.cliente?.uf,
  ]
    .filter(Boolean)
    .join(", ");

  return {
    nome: venda?.cliente?.nome || venda?.cliente_nome || venda?.nome_cliente || "",
    telefone: telefoneCliente,
    endereco: enderecoCliente,
  };
}

function formatarDataHoraVenda(valor) {
  const data = valor ? new Date(valor) : new Date();
  return Number.isNaN(data.getTime()) ? String(valor || "-") : data.toLocaleString("pt-BR");
}

function pagamentoEhCrediario(pagamento = {}) {
  const tipo = toAscii(pagamento.forma_pagamento_tipo || pagamento.tipo).toLowerCase();
  const nome = toAscii(pagamento.forma_pagamento || pagamento.nome).toLowerCase();
  return tipo === "crediario" || nome.includes("crediario");
}

export function ehVendaCrediario(venda = {}) {
  return Boolean(venda.eh_crediario) || (venda.pagamentos || []).some(pagamentoEhCrediario);
}

function obterPagamentosCrediario(venda = {}) {
  const pagamentos = Array.isArray(venda.pagamentos) ? venda.pagamentos : [];
  const encontrados = pagamentos.filter(pagamentoEhCrediario);
  if (encontrados.length) return encontrados;
  return venda.eh_crediario ? pagamentos : [];
}

function gerarParcelasCrediario(pagamento = {}) {
  const quantidade = Math.max(
    1,
    Math.trunc(Number(pagamento.numero_parcelas || pagamento.parcelas || 1)),
  );
  const correspondencia = String(pagamento.data_recebimento_prevista || "").match(
    /^(\d{4})-(\d{2})-(\d{2})/,
  );
  const totalCentavos = Math.round(Number(pagamento.valor || 0) * 100);
  const valorBaseCentavos = Math.round(totalCentavos / quantidade);

  if (!correspondencia) {
    return Array.from({ length: quantidade }, (_, indice) => ({
      numero: indice + 1,
      total_parcelas: quantidade,
      valor:
        (indice === quantidade - 1
          ? totalCentavos - valorBaseCentavos * (quantidade - 1)
          : valorBaseCentavos) / 100,
      data_vencimento: "Conforme combinado",
    }));
  }

  const [, anoTexto, mesTexto, diaTexto] = correspondencia;
  const ano = Number(anoTexto);
  const mes = Number(mesTexto);
  const dia = Number(diaTexto);
  const intervalo = pagamento.intervalo_crediario || "mensal";

  return Array.from({ length: quantidade }, (_, indice) => {
    let vencimento;
    if (intervalo === "7_dias" || intervalo === "15_dias") {
      vencimento = new Date(ano, mes - 1, dia, 12);
      vencimento.setDate(vencimento.getDate() + (intervalo === "7_dias" ? 7 : 15) * indice);
    } else {
      const indiceMes = ano * 12 + (mes - 1) + indice;
      const anoParcela = Math.floor(indiceMes / 12);
      const mesParcela = indiceMes % 12;
      const ultimoDia = new Date(anoParcela, mesParcela + 1, 0, 12).getDate();
      vencimento = new Date(anoParcela, mesParcela, Math.min(dia, ultimoDia), 12);
    }

    const valorCentavos =
      indice === quantidade - 1
        ? totalCentavos - valorBaseCentavos * (quantidade - 1)
        : valorBaseCentavos;

    return {
      numero: indice + 1,
      total_parcelas: quantidade,
      valor: valorCentavos / 100,
      data_vencimento: `${String(vencimento.getDate()).padStart(2, "0")}/${String(
        vencimento.getMonth() + 1,
      ).padStart(2, "0")}/${vencimento.getFullYear()}`,
    };
  });
}

function montarResumoVenda(venda = {}) {
  const subtotal = Number(venda.subtotal || 0);
  const descontoTotal = Number(venda.desconto_valor || 0);
  const totalBruto = subtotal + descontoTotal;
  const taxaEntrega = Number(venda?.entrega?.taxa_entrega_total || venda.taxa_entrega || 0);
  const linhas = [
    "-".repeat(RECEIPT_WIDTH),
    "ITENS",
    "-".repeat(RECEIPT_WIDTH),
    ...renderItens(venda.itens || []),
    "-".repeat(RECEIPT_WIDTH),
    linePair("Total bruto:", formatMoneyBRL(totalBruto)),
  ];

  if (descontoTotal > 0) {
    linhas.push(linePair("Desconto:", `-${formatMoneyBRL(descontoTotal)}`));
  }
  if (venda.tem_entrega) {
    linhas.push(linePair("Taxa entrega:", formatMoneyBRL(taxaEntrega)));
  }
  linhas.push(
    "-".repeat(RECEIPT_WIDTH),
    linePair("TOTAL:", formatMoneyBRL(Number(venda.total || 0))),
    "-".repeat(RECEIPT_WIDTH),
  );

  return linhas;
}

export function montarCupomVenda(venda = {}, empresa = {}) {
  const dataVenda = formatarDataHoraVenda(venda.data_venda);
  const numeroVenda = venda.numero_venda || venda.id || "-";
  const cliente = montarDadosCliente(venda);
  const enderecoEntrega = venda?.entrega?.endereco_completo || venda.endereco_entrega || "";
  const observacoesEntrega = venda?.entrega?.observacoes_entrega || venda.observacoes_entrega || "";
  const linhas = [
    ...montarCabecalhoEmpresa(empresa),
    "-".repeat(RECEIPT_WIDTH),
    center("RECIBO DO PDV"),
    center("DOCUMENTO NAO FISCAL"),
    "-".repeat(RECEIPT_WIDTH),
    clip(`VENDA #${numeroVenda}`),
    clip(`Data: ${dataVenda}`),
  ];

  if (cliente.nome) linhas.push(...wrap(`Cliente: ${cliente.nome}`));
  if (cliente.telefone) linhas.push(...wrap(`Telefone: ${cliente.telefone}`));
  if (cliente.endereco) linhas.push(...wrap(`Endereco: ${cliente.endereco}`));
  if (venda?.pet?.nome) linhas.push(...wrap(`Pet: ${venda.pet.nome}`));

  linhas.push(...montarResumoVenda(venda));

  if (Array.isArray(venda.pagamentos) && venda.pagamentos.length > 0) {
    linhas.push("PAGAMENTOS");
    for (const pagamento of venda.pagamentos) {
      linhas.push(
        linePair(
          pagamento?.forma_pagamento || pagamento?.nome || "Pagamento",
          formatMoneyBRL(Number(pagamento?.valor || 0)),
        ),
      );
    }
    linhas.push("-".repeat(RECEIPT_WIDTH));
  }

  if (venda.tem_entrega && (enderecoEntrega || observacoesEntrega)) {
    linhas.push("ENTREGA:");
    if (enderecoEntrega) linhas.push(...wrap(enderecoEntrega));
    if (observacoesEntrega) linhas.push(...wrap(`Obs: ${observacoesEntrega}`));
    linhas.push("-".repeat(RECEIPT_WIDTH));
  }

  if (venda.observacoes) {
    linhas.push("OBSERVACOES:", ...wrap(venda.observacoes), "-".repeat(RECEIPT_WIDTH));
  }

  linhas.push(...montarRodapeEmpresa(empresa));
  return linhas.join("\n");
}

function montarViaCrediario(venda = {}, empresa = {}, via) {
  const numeroVenda = venda.numero_venda || venda.id || "-";
  const cliente = montarDadosCliente(venda);
  const pagamentosCrediario = obterPagamentosCrediario(venda);
  const linhas = [
    ...montarCabecalhoEmpresa(empresa),
    "-".repeat(RECEIPT_WIDTH),
    center("COMPROVANTE DE CREDIARIO"),
    center(via),
    center("DOCUMENTO NAO FISCAL"),
    "-".repeat(RECEIPT_WIDTH),
    clip(`VENDA #${numeroVenda}`),
    clip(`Data: ${formatarDataHoraVenda(venda.data_venda)}`),
  ];

  if (cliente.nome) linhas.push(...wrap(`Cliente: ${cliente.nome}`));
  if (cliente.telefone) linhas.push(...wrap(`Telefone: ${cliente.telefone}`));
  if (cliente.endereco) linhas.push(...wrap(`Endereco: ${cliente.endereco}`));

  linhas.push(...montarResumoVenda(venda), "PARCELAS DO CREDIARIO");

  if (pagamentosCrediario.length === 0) {
    linhas.push("Vencimentos: conforme combinado");
  } else {
    pagamentosCrediario.forEach((pagamento, indicePagamento) => {
      if (pagamentosCrediario.length > 1) {
        linhas.push(`Plano ${indicePagamento + 1}:`);
      }
      for (const parcela of gerarParcelasCrediario(pagamento)) {
        linhas.push(
          linePair(
            `${parcela.numero}/${parcela.total_parcelas} ${parcela.data_vencimento}`,
            formatMoneyBRL(parcela.valor),
          ),
        );
      }
    });
  }

  linhas.push(
    "-".repeat(RECEIPT_WIDTH),
    ...wrap("Declaro que reconheco a compra e os vencimentos descritos neste comprovante."),
    "",
    "",
    "_".repeat(RECEIPT_WIDTH),
    center("ASSINATURA DO CLIENTE"),
    ...(cliente.nome
      ? wrap(`Nome: ${cliente.nome}`)
      : ["Nome: ____________________________________"]),
    "Documento: _____________________________",
    "-".repeat(RECEIPT_WIDTH),
    ...montarRodapeEmpresa(empresa),
  );

  return linhas.join("\n");
}

export function montarCupomCrediario(venda = {}, empresa = {}) {
  const separador = ["", center("CORTE AQUI"), "- ".repeat(RECEIPT_WIDTH / 2), ""].join("\n");
  return [
    montarViaCrediario(venda, empresa, "VIA DO ESTABELECIMENTO"),
    montarViaCrediario(venda, empresa, "VIA DO CLIENTE"),
  ].join(separador);
}

export function montarConteudoCupom(venda = {}, empresa = {}) {
  return ehVendaCrediario(venda)
    ? montarCupomCrediario(venda, empresa)
    : montarCupomVenda(venda, empresa);
}
