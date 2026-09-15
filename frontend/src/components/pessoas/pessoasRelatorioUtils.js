import { resolveMediaUrl } from "../../utils/mediaUrl.js";

export const TIPOS_RELATORIO_PESSOAS = [
  { value: "todos", label: "Todos os cadastros", singular: "Pessoas" },
  { value: "cliente", label: "Somente clientes", singular: "Clientes" },
  { value: "fornecedor", label: "Somente fornecedores", singular: "Fornecedores" },
  { value: "veterinario", label: "Somente veterinarios", singular: "Veterinarios" },
  { value: "funcionario", label: "Somente funcionarios", singular: "Funcionarios" },
];

const ROTULOS_TIPO_CADASTRO = {
  cliente: "Cliente",
  fornecedor: "Fornecedor",
  veterinario: "Veterinario",
  funcionario: "Funcionario",
};

const formatarData = (valor) => {
  if (!valor) return "";
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? String(valor) : data.toLocaleDateString("pt-BR");
};

const somenteDigitos = (valor) => String(valor || "").replace(/\D/g, "");

const formatarCpf = (valor) => {
  const digitos = somenteDigitos(valor);
  if (digitos.length !== 11) return String(valor || "");
  return digitos.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
};

const formatarCnpj = (valor) => {
  const digitos = somenteDigitos(valor);
  if (digitos.length !== 14) return String(valor || "");
  return digitos.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
};

export const COLUNAS_RELATORIO_PESSOAS = [
  { key: "codigo", label: "Codigo", width: 12, value: (pessoa) => pessoa.codigo || "" },
  { key: "nome", label: "Nome", width: 32, value: (pessoa) => pessoa.nome || "" },
  {
    key: "tipo_cadastro",
    label: "Tipo de cadastro",
    width: 18,
    value: (pessoa) => ROTULOS_TIPO_CADASTRO[pessoa.tipo_cadastro] || pessoa.tipo_cadastro || "",
  },
  {
    key: "tipo_pessoa",
    label: "Pessoa fisica/juridica",
    width: 22,
    value: (pessoa) => (pessoa.tipo_pessoa === "PJ" ? "Pessoa juridica" : "Pessoa fisica"),
  },
  {
    key: "documento",
    label: "CPF/CNPJ",
    width: 20,
    value: (pessoa) =>
      pessoa.tipo_pessoa === "PJ" ? formatarCnpj(pessoa.cnpj) : formatarCpf(pessoa.cpf),
  },
  {
    key: "telefone",
    label: "Telefone",
    width: 18,
    value: (pessoa) => pessoa.telefone || pessoa.celular || "",
  },
  { key: "celular", label: "Celular", width: 18, value: (pessoa) => pessoa.celular || "" },
  { key: "email", label: "E-mail", width: 30, value: (pessoa) => pessoa.email || "" },
  { key: "cep", label: "CEP", width: 14, value: (pessoa) => pessoa.cep || "" },
  {
    key: "endereco",
    label: "Rua / endereco",
    width: 32,
    value: (pessoa) => pessoa.endereco || "",
  },
  { key: "numero", label: "Numero", width: 12, value: (pessoa) => pessoa.numero || "" },
  {
    key: "complemento",
    label: "Complemento",
    width: 20,
    value: (pessoa) => pessoa.complemento || "",
  },
  { key: "bairro", label: "Bairro", width: 24, value: (pessoa) => pessoa.bairro || "" },
  { key: "cidade", label: "Cidade", width: 24, value: (pessoa) => pessoa.cidade || "" },
  { key: "estado", label: "Estado/UF", width: 12, value: (pessoa) => pessoa.estado || "" },
  {
    key: "data_nascimento",
    label: "Nascimento",
    width: 16,
    value: (pessoa) => formatarData(pessoa.data_nascimento),
  },
  {
    key: "razao_social",
    label: "Razao social",
    width: 30,
    value: (pessoa) => pessoa.razao_social || "",
  },
  {
    key: "nome_fantasia",
    label: "Nome fantasia",
    width: 28,
    value: (pessoa) => pessoa.nome_fantasia || "",
  },
  {
    key: "inscricao_estadual",
    label: "Inscricao estadual",
    width: 20,
    value: (pessoa) => pessoa.inscricao_estadual || "",
  },
  {
    key: "responsavel",
    label: "Responsavel",
    width: 28,
    value: (pessoa) => pessoa.responsavel || "",
  },
  { key: "crmv", label: "CRMV", width: 16, value: (pessoa) => pessoa.crmv || "" },
  {
    key: "origem_cliente",
    label: "Origem",
    width: 20,
    value: (pessoa) => pessoa.origem_cliente || "",
  },
  {
    key: "created_at",
    label: "Data do cadastro",
    width: 18,
    value: (pessoa) => formatarData(pessoa.created_at),
  },
  {
    key: "observacoes",
    label: "Observacoes",
    width: 38,
    value: (pessoa) => pessoa.observacoes || "",
  },
];

export const COLUNAS_PADRAO_RELATORIO_PESSOAS = ["nome", "telefone"];

export const PRESETS_RELATORIO_PESSOAS = {
  basico: ["nome", "telefone"],
  endereco: ["nome", "telefone", "cep", "endereco", "numero", "bairro", "cidade", "estado"],
};

export const ORDENACOES_RELATORIO_PESSOAS = [
  { value: "nome_asc", label: "Nome (A a Z)" },
  { value: "nome_desc", label: "Nome (Z a A)" },
  { value: "codigo_asc", label: "Codigo (menor para maior)" },
  { value: "codigo_desc", label: "Codigo (maior para menor)" },
  { value: "cidade_asc", label: "Cidade (A a Z)" },
  { value: "cadastro_desc", label: "Cadastro mais recente primeiro" },
  { value: "cadastro_asc", label: "Cadastro mais antigo primeiro" },
];

const collator = new Intl.Collator("pt-BR", { numeric: true, sensitivity: "base" });

export function obterNomeEmpresaRelatorio(empresa = {}) {
  return String(empresa.nome || empresa.nome_fantasia || empresa.slug || "Empresa").trim();
}

export function ordenarPessoasRelatorio(pessoas, ordenacao = "nome_asc") {
  const [campo, direcao] = ordenacao.includes("cadastro_")
    ? ["created_at", ordenacao.endsWith("_desc") ? "desc" : "asc"]
    : [ordenacao.replace(/_(asc|desc)$/, ""), ordenacao.endsWith("_desc") ? "desc" : "asc"];
  const multiplicador = direcao === "desc" ? -1 : 1;

  return [...(pessoas || [])].sort((a, b) => {
    if (campo === "created_at") {
      const dataA = a?.created_at ? new Date(a.created_at).getTime() : 0;
      const dataB = b?.created_at ? new Date(b.created_at).getTime() : 0;
      if (dataA !== dataB) return (dataA - dataB) * multiplicador;
    }

    const comparacao = collator.compare(String(a?.[campo] || ""), String(b?.[campo] || ""));
    if (comparacao !== 0) return comparacao * multiplicador;
    return collator.compare(String(a?.nome || ""), String(b?.nome || ""));
  });
}

export function obterColunasRelatorio(chaves) {
  const colunasPorChave = new Map(COLUNAS_RELATORIO_PESSOAS.map((coluna) => [coluna.key, coluna]));
  return (chaves || []).map((chave) => colunasPorChave.get(chave)).filter(Boolean);
}

export function montarLinhasRelatorioPessoas(pessoas, chavesColunas) {
  const colunas = obterColunasRelatorio(chavesColunas);
  return [
    colunas.map((coluna) => coluna.label),
    ...(pessoas || []).map((pessoa) => colunas.map((coluna) => String(coluna.value(pessoa) ?? ""))),
  ];
}

function nomeBaseArquivo(tipo) {
  const tipoEncontrado = TIPOS_RELATORIO_PESSOAS.find((item) => item.value === tipo);
  const escopo = (tipoEncontrado?.singular || "Pessoas").toLowerCase();
  return `relatorio_${escopo}_${new Date().toLocaleDateString("sv-SE")}`;
}

const criarLinhaMescladaExcel = (valor, totalColunas, estilo = {}) => [
  { value: valor, columnSpan: totalColunas, ...estilo },
  ...Array.from({ length: Math.max(totalColunas - 1, 0) }, () => null),
];

export async function exportarPessoasExcel({ pessoas, colunas, tipo, busca = "", empresa = {} }) {
  const linhas = montarLinhasRelatorioPessoas(pessoas, colunas);
  const colunasAtivas = obterColunasRelatorio(colunas);
  const totalColunas = Math.max(colunasAtivas.length, 1);
  const nomeEmpresa = obterNomeEmpresaRelatorio(empresa);
  const tipoLabel = TIPOS_RELATORIO_PESSOAS.find((item) => item.value === tipo)?.label || "Pessoas";
  const dadosTabela = linhas.map((linha, indiceLinha) =>
    linha.map((valor) => ({
      value: valor,
      ...(indiceLinha === 0
        ? { fontWeight: "bold", backgroundColor: "#D1FAE5", color: "#065F46" }
        : {}),
    })),
  );
  const dados = [
    criarLinhaMescladaExcel(nomeEmpresa, totalColunas, {
      fontSize: 14,
      fontWeight: "bold",
      color: "#0F172A",
    }),
    criarLinhaMescladaExcel("Relatorio de Pessoas", totalColunas, {
      fontSize: 12,
      fontWeight: "bold",
      color: "#0F172A",
    }),
    criarLinhaMescladaExcel(`${tipoLabel} | ${pessoas.length} registro(s)`, totalColunas, {
      color: "#475569",
    }),
    criarLinhaMescladaExcel(
      `${busca ? `Busca: ${busca} | ` : ""}Gerado em ${new Date().toLocaleString("pt-BR")}`,
      totalColunas,
      { color: "#64748B" },
    ),
    ...dadosTabela,
  ];
  const { default: writeExcelFile } = await import("write-excel-file/browser");

  await writeExcelFile(dados, {
    sheet: "Pessoas",
    stickyRowsCount: 5,
    columns: colunasAtivas.map((coluna) => ({ width: coluna.width })),
  }).toFile(`${nomeBaseArquivo(tipo)}.xlsx`);
}

async function carregarLogoEmpresaPdf(logoUrl) {
  const url = resolveMediaUrl(logoUrl);
  if (!url) return null;

  try {
    const response = await fetch(url, { credentials: "include" });
    if (!response.ok) return null;

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    try {
      const imagem = await new Promise((resolve, reject) => {
        const elemento = new Image();
        elemento.onload = () => resolve(elemento);
        elemento.onerror = reject;
        elemento.src = objectUrl;
      });
      const maiorLado = Math.max(imagem.naturalWidth, imagem.naturalHeight);
      const escala = maiorLado > 1000 ? 1000 / maiorLado : 1;
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(Math.round(imagem.naturalWidth * escala), 1);
      canvas.height = Math.max(Math.round(imagem.naturalHeight * escala), 1);
      canvas.getContext("2d").drawImage(imagem, 0, 0, canvas.width, canvas.height);
      return {
        dataUrl: canvas.toDataURL("image/png"),
        width: canvas.width,
        height: canvas.height,
      };
    } finally {
      URL.revokeObjectURL(objectUrl);
    }
  } catch (error) {
    console.warn("Nao foi possivel incluir o logo da empresa no relatorio:", error);
    return null;
  }
}

export function desenharCabecalhoTabelaPdf(
  doc,
  { colunasAtivas, larguras, margem, y, altura = 7, tamanhoFonte },
) {
  const larguraTotal = larguras.reduce((total, largura) => total + largura, 0);
  doc.setFillColor(5, 150, 105);
  doc.rect(margem, y, larguraTotal, altura, "F");
  doc.setDrawColor(4, 120, 87);
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(tamanhoFonte);

  let x = margem;
  colunasAtivas.forEach((coluna, indice) => {
    doc.rect(x, y, larguras[indice], altura, "S");
    const texto = doc.splitTextToSize(coluna.label, Math.max(larguras[indice] - 2, 2))[0];
    doc.text(texto || coluna.label, x + 1, y + 4.5);
    x += larguras[indice];
  });
}

export async function exportarPessoasPdf({ pessoas, colunas, tipo, busca = "", empresa = {} }) {
  const colunasAtivas = obterColunasRelatorio(colunas);
  const linhas = montarLinhasRelatorioPessoas(pessoas, colunas).slice(1);
  const orientation = colunasAtivas.length > 4 ? "landscape" : "portrait";
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ orientation, unit: "mm", format: "a4" });
  const logo = await carregarLogoEmpresaPdf(empresa.logo_url);
  const nomeEmpresa = obterNomeEmpresaRelatorio(empresa);
  const margem = 10;
  const topoCabecalhoTabela = 34;
  const alturaCabecalhoTabela = 7;
  const rodape = 10;
  const larguraPagina = doc.internal.pageSize.getWidth();
  const alturaPagina = doc.internal.pageSize.getHeight();
  const larguraDisponivel = larguraPagina - margem * 2;
  const somaPesos = colunasAtivas.reduce((total, coluna) => total + coluna.width, 0);
  const larguras = colunasAtivas.map((coluna) => (coluna.width / somaPesos) * larguraDisponivel);
  const tamanhoFonte = colunasAtivas.length > 7 ? 6.2 : colunasAtivas.length > 4 ? 7 : 8;
  const alturaLinhaTexto = tamanhoFonte * 0.42;
  const tipoLabel = TIPOS_RELATORIO_PESSOAS.find((item) => item.value === tipo)?.label || "Pessoas";
  let y = topoCabecalhoTabela + alturaCabecalhoTabela;

  const desenharCabecalhoPagina = () => {
    let textoX = margem;
    if (logo) {
      const escalaLogo = Math.min(30 / logo.width, 17 / logo.height);
      const larguraLogo = logo.width * escalaLogo;
      const alturaLogo = logo.height * escalaLogo;
      doc.addImage(logo.dataUrl, "PNG", margem, 7, larguraLogo, alturaLogo);
      textoX += larguraLogo + 4;
    }

    const larguraTexto = Math.max(larguraPagina - margem - textoX, 30);
    doc.setTextColor(15, 23, 42);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text(doc.splitTextToSize(nomeEmpresa, larguraTexto)[0] || nomeEmpresa, textoX, 10);
    doc.setFontSize(15);
    doc.text("Relatorio de Pessoas", textoX, 16.5);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.text(`${tipoLabel} | ${pessoas.length} registro(s)`, textoX, 22);
    doc.text(
      `${busca ? `Busca: ${busca} | ` : ""}Gerado em ${new Date().toLocaleString("pt-BR")}`,
      textoX,
      27,
    );

    desenharCabecalhoTabelaPdf(doc, {
      colunasAtivas,
      larguras,
      margem,
      y: topoCabecalhoTabela,
      altura: alturaCabecalhoTabela,
      tamanhoFonte,
    });
    y = topoCabecalhoTabela + alturaCabecalhoTabela;
  };

  desenharCabecalhoPagina();
  linhas.forEach((linha, indiceLinha) => {
    const textos = linha.map((valor, indiceColuna) =>
      doc.splitTextToSize(String(valor || "-"), Math.max(larguras[indiceColuna] - 2, 2)),
    );
    const totalLinhas = Math.max(...textos.map((texto) => texto.length), 1);
    const altura = Math.max(6, totalLinhas * alturaLinhaTexto + 2);

    if (y + altura > alturaPagina - rodape) {
      doc.addPage();
      desenharCabecalhoPagina();
    }

    let x = margem;
    if (indiceLinha % 2 === 1) {
      doc.setFillColor(241, 245, 249);
      doc.rect(margem, y, larguraDisponivel, altura, "F");
    }
    doc.setDrawColor(203, 213, 225);
    doc.setTextColor(51, 65, 85);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(tamanhoFonte);
    textos.forEach((texto, indiceColuna) => {
      doc.rect(x, y, larguras[indiceColuna], altura);
      doc.text(texto, x + 1, y + alturaLinhaTexto + 0.8);
      x += larguras[indiceColuna];
    });
    y += altura;
  });

  const paginas = doc.getNumberOfPages();
  for (let pagina = 1; pagina <= paginas; pagina += 1) {
    doc.setPage(pagina);
    doc.setTextColor(100, 116, 139);
    doc.setFontSize(7);
    doc.text(`Pagina ${pagina} de ${paginas}`, larguraPagina - margem, alturaPagina - 4, {
      align: "right",
    });
  }

  doc.save(`${nomeBaseArquivo(tipo)}.pdf`);
}
