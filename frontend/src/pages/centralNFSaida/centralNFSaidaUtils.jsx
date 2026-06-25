import { AlertCircle, CheckCircle, FileText, X } from "lucide-react";

export const SITUACOES_NF_SAIDA = [
  { value: "", label: "Todas" },
  { value: "Autorizada", label: "Autorizada" },
  { value: "Emitida DANFE", label: "Emitida DANFE" },
  { value: "Cancelada", label: "Cancelada" },
  { value: "Pendente", label: "Pendente" },
];

export function formatarChave(valor) {
  return valor.replaceAll(/\D/g, "").slice(0, 44);
}

export function tratarColagemChave(event, setChave) {
  event.preventDefault();
  const texto = event.clipboardData?.getData("text") || "";
  setChave(formatarChave(texto));
}

export function formatarDataHora(valor) {
  if (!valor) return "-";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "-";
  return data.toLocaleString("pt-BR");
}

export function soDigitos(valor) {
  return String(valor || "").replaceAll(/\D/g, "");
}

export function getSituacaoCor(status) {
  switch (status?.toLowerCase()) {
    case "autorizada":
    case "emitida danfe":
      return "bg-green-100 text-green-800";
    case "cancelada":
      return "bg-red-100 text-red-800";
    case "pendente":
      return "bg-yellow-100 text-yellow-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

export function getSituacaoIcone(status) {
  switch (status?.toLowerCase()) {
    case "autorizada":
    case "emitida danfe":
      return <CheckCircle className="w-4 h-4" />;
    case "cancelada":
      return <X className="w-4 h-4" />;
    case "pendente":
      return <AlertCircle className="w-4 h-4" />;
    default:
      return <FileText className="w-4 h-4" />;
  }
}

export function formatarDataBR(valor) {
  if (!valor) return "-";
  if (typeof valor === "string" && /^\d{4}-\d{2}-\d{2}$/.test(valor)) {
    const [ano, mes, dia] = valor.split("-");
    return `${dia}/${mes}/${ano}`;
  }
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString("pt-BR");
}

export function formatarValorDetalhe(valor) {
  if (valor === 0) return "0";
  if (valor === false) return "Não";
  if (valor === true) return "Sim";
  if (!valor) return "-";
  if (Array.isArray(valor)) {
    const partes = valor
      .map((item) => formatarValorDetalhe(item))
      .filter((item) => item && item !== "-");
    return partes.length ? partes.join(", ") : "-";
  }
  if (typeof valor === "object") {
    return (
      valor.nome ||
      valor.descricao ||
      valor.label ||
      valor.endereco ||
      valor.logradouro ||
      valor.identificacao ||
      "-"
    );
  }
  return String(valor);
}

export function valorBooleanoLabel(valor) {
  if (valor === true) return "Sim";
  if (valor === false) return "Não";
  return "-";
}

export function montarDetalheFallback(nota) {
  return {
    id: nota.id,
    numero: nota.numero,
    serie: nota.serie,
    modelo: nota.modelo,
    tipo: nota.tipo,
    tipo_label: nota.tipo === "nfce" ? "NFC-e" : "NF-e",
    chave: nota.chave,
    status: nota.status,
    data_emissao: nota.data_emissao,
    cliente: {
      nome: nota.cliente?.nome,
      cpf_cnpj: nota.cliente?.cpf_cnpj,
    },
    totais: {
      valor_total: nota.valor,
    },
    canal: nota.canal,
    canal_label: nota.canal_label,
    loja: nota.loja,
    unidade_negocio: nota.unidade_negocio,
    informacoes_adicionais: {
      numero_pedido_loja: nota.numero_pedido_loja,
      numero_loja_virtual: nota.numero_loja_virtual,
      origem_loja_virtual: nota.origem_loja_virtual,
      origem_canal_venda: nota.origem_canal_venda,
    },
    itens: [],
    pagamento: { parcelas: [] },
    transporte: {},
    endereco_entrega: {},
    intermediador: {},
  };
}
