import { formatMoneyBRL } from "../../../utils/formatters.js";

export const CASHBACK_STATUS = [
  { value: "sem_contato", label: "Ainda não contatado" },
  { value: "conversa_aberta", label: "Conversa aberta" },
  { value: "mensagem_enviada", label: "Mensagem enviada" },
  { value: "aguardando_retorno", label: "Aguardando retorno" },
  { value: "interessado", label: "Interessado" },
  { value: "retornar_depois", label: "Retornar depois" },
  { value: "concluido", label: "Concluído" },
  { value: "sem_interesse", label: "Sem interesse" },
  { value: "nao_contatar", label: "Não contatar" },
];

export const MODELO_CASHBACK =
  "Oi, {nome}! 🐾 Seu pet já tem um motivo extra para ganhar um mimo: você tem {saldo} de cashback disponível com a gente! Que tal aproveitar na próxima visita? 💚 Consulte as regras de uso e as campanhas ativas para também acumular novos benefícios. Vamos escolher algo especial para ele?";

export function mensagemCashback(modelo, cliente) {
  const valores = {
    nome:
      String(cliente?.nome || "cliente")
        .trim()
        .split(/\s+/)[0] || "cliente",
    saldo: formatMoneyBRL(cliente?.saldo_cashback || 0),
  };
  return String(modelo || "").replace(/\{(nome|saldo)\}/g, (_match, chave) => valores[chave]);
}

export function rotuloStatus(status) {
  return CASHBACK_STATUS.find((item) => item.value === status)?.label || status || "—";
}

export function dataCashback(valor, comHora = false) {
  if (!valor) return "—";
  const data = new Date(/^\d{4}-\d{2}-\d{2}$/.test(valor) ? `${valor}T12:00:00` : valor);
  if (Number.isNaN(data.getTime())) return "—";
  return comHora ? data.toLocaleString("pt-BR") : data.toLocaleDateString("pt-BR");
}

// Abre a aba ainda dentro do clique, antes de aguardar a API. Sem o registro persistido,
// a conversa não é aberta; um bloqueio de popup também não cria um contato no histórico.
export async function registrarEAbrirWhatsApp({ abrirAba, registrar }) {
  const aba = abrirAba();
  if (!aba)
    throw new Error(
      "O navegador bloqueou a nova aba do WhatsApp. Libere os pop-ups e tente novamente.",
    );
  aba.opener = null;
  try {
    const resultado = await registrar();
    const url = new URL(resultado.whatsapp_url);
    if (url.protocol !== "https:" || url.hostname !== "wa.me") {
      throw new Error("O link do WhatsApp recebido é inválido.");
    }
    aba.location.replace(url.href);
    return resultado;
  } catch (error) {
    aba.close();
    throw error;
  }
}
