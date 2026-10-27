// Apresentação do consumo de mensagens de WhatsApp (tela da loja e tela do OPS).

export const ROTULO_DA_CATEGORIA = {
  marketing: "Marketing",
  utility: "Utilidade",
  authentication: "Autenticação",
  authentication_international: "Autenticação internacional",
  service: "Atendimento",
  referral_conversion: "Conversão de indicação",
  sem_categoria: "Sem categoria",
};

export const ROTULO_DA_ORIGEM = {
  ia: "IA",
  atendente: "Atendente",
  sistema: "Avisos do sistema",
  automacao: "Automações",
  tutor: "Tutor",
  desconhecida: "Fora do sistema (ex.: app do celular)",
};

export const ROTULO_DO_ESTADO = {
  enviada: "Enviada",
  entregue: "Entregue",
  lida: "Lida",
  falhou: "Falhou",
  recebida: "Recebida",
};

export function rotulo(tabela, chave) {
  return tabela[chave] || chave;
}

export function formatarReais(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatarQuando(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

/** Mês atual e os anteriores, do mais novo para o mais antigo: [{ value: "AAAA-MM", label }]. */
export function ultimosMeses(quantidade = 12, agora = new Date()) {
  const meses = [];
  for (let passo = 0; passo < quantidade; passo += 1) {
    const data = new Date(agora.getFullYear(), agora.getMonth() - passo, 1);
    const value = `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}`;
    const nome = data.toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
    meses.push({ value, label: nome.charAt(0).toLocaleUpperCase("pt-BR") + nome.slice(1) });
  }
  return meses;
}

/** Texto do alerta quando há mensagens cobráveis sem tarifa ou sem informação de cobrança. */
export function avisosDeCusto(totais) {
  const avisos = [];
  if (totais?.cobraveis_sem_tarifa > 0) {
    avisos.push(
      `${totais.cobraveis_sem_tarifa} mensagem(ns) cobrável(is) sem tarifa cadastrada: o custo estimado está menor que o real.`,
    );
  }
  if (totais?.sem_informacao_de_cobranca > 0) {
    avisos.push(
      `${totais.sem_informacao_de_cobranca} mensagem(ns) ainda sem informação de cobrança da Meta (o aviso pode chegar depois).`,
    );
  }
  return avisos;
}

/** Leitura da divergência entre a fatura real da Meta e o custo estimado. */
export function leituraDaDivergencia(divergencia) {
  if (divergencia === null || divergencia === undefined) {
    return { tom: "neutro", texto: "Fatura da Meta ainda não informada" };
  }
  if (Math.abs(divergencia) < 0.01) return { tom: "ok", texto: "Confere com a fatura" };
  const valor = formatarReais(Math.abs(divergencia));
  return divergencia > 0
    ? { tom: "atencao", texto: `Fatura ${valor} acima do estimado` }
    : { tom: "atencao", texto: `Fatura ${valor} abaixo do estimado` };
}
