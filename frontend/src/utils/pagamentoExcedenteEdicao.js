import {
  extrairExcecaoPagamento,
  mensagemExcedentePagamento,
  usarContextoExcedenteServidor,
} from "../components/modalPagamento/modalPagamentoExcedente.js";
import { perguntarCorePet } from "../services/corepetDialog.js";

export async function solicitarJustificativaPagamentoExcedente(composicao) {
  let valorInicial = "";
  let aviso = "";
  for (;;) {
    const resposta = await perguntarCorePet({
      titulo: "Justificar pagamento excedente",
      mensagem: `${aviso}${mensagemExcedentePagamento(composicao)} O recebimento real será preservado, sem gerar troco ou crédito automático.`,
      rotulo: "Justificativa do excedente (10 a 1.000 caracteres)",
      confirmarTexto: "Confirmar exceção",
      cancelarTexto: "Voltar para revisar",
      variante: "warning",
      obrigatorio: true,
      minimoCaracteres: 10,
      multilinha: true,
      valorInicial,
    });
    if (resposta == null) return null;
    valorInicial = String(resposta).trim();
    if (valorInicial.length >= 10 && valorInicial.length <= 1000) return valorInicial;
    aviso = "Informe uma justificativa entre 10 e 1.000 caracteres. ";
  }
}

// Só autoriza a fotografia financeira calculada pelo servidor. Cada 409 novo
// exige outra confirmação, inclusive quando uma baixa ocorre em outra aba.
export async function executarComJustificativaPagamento({
  operacao,
  solicitarJustificativa,
  autorizacaoInicial = {},
}) {
  let autorizacao = autorizacaoInicial;
  for (let tentativa = 0; tentativa < 3; tentativa += 1) {
    try {
      return { resultado: await operacao(autorizacao), autorizacao, cancelada: false };
    } catch (erro) {
      const detalhe = extrairExcecaoPagamento(erro);
      if (!detalhe || !solicitarJustificativa || tentativa === 2) throw erro;
      const composicao = usarContextoExcedenteServidor(
        { chave: "edicao" },
        { base: "edicao", detalhe },
      );
      if (!composicao.contexto) throw erro;
      const resposta = await solicitarJustificativa(composicao);
      if (resposta == null) return { cancelada: true };
      const justificativa = String(resposta).trim();
      if (justificativa.length < 10 || justificativa.length > 1000) {
        throw new Error("Informe uma justificativa entre 10 e 1.000 caracteres.", { cause: erro });
      }
      autorizacao = {
        justificativa_pagamento_excedente: justificativa,
        contexto_pagamento_excedente: composicao.contexto,
      };
    }
  }
}
