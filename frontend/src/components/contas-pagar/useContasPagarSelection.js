import { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";

import api from "../../api";
import { safeArray } from "../../utils/safeArray";

export default function useContasPagarSelection({ contas, carregarDados, abrirModalEdicao }) {
  const [contasSelecionadas, setContasSelecionadas] = useState([]);

  const contasVisiveis = useMemo(() => safeArray(contas), [contas]);

  useEffect(() => {
    const idsVisiveis = new Set(contasVisiveis.map((conta) => conta.id));
    setContasSelecionadas((atuais) => atuais.filter((id) => idsVisiveis.has(id)));
  }, [contasVisiveis]);

  const contaTemPagamento = (conta) =>
    Number(conta?.valor_pago || 0) > 0 || ["pago", "parcial"].includes(conta?.status);
  const contaPodePagar = (conta) =>
    !["pago", "cancelado"].includes(conta?.status) &&
    Number(conta?.valor_final || 0) > Number(conta?.valor_pago || 0);
  const contaPodeExcluir = (conta) => !contaTemPagamento(conta);
  const contaPodeCancelar = (conta) => !contaTemPagamento(conta) && conta?.status !== "cancelado";

  const contasSelecionadasObjetos = contasVisiveis.filter((conta) =>
    contasSelecionadas.includes(conta.id),
  );
  const totalSelecionadas = contasSelecionadasObjetos.length;
  const todasVisiveisSelecionadas =
    contasVisiveis.length > 0 &&
    contasVisiveis.every((conta) => contasSelecionadas.includes(conta.id));
  const algumasVisiveisSelecionadas = contasVisiveis.some((conta) =>
    contasSelecionadas.includes(conta.id),
  );
  const haContaPagaSelecionada = contasSelecionadasObjetos.some(contaTemPagamento);
  const haContaPagavelSelecionada = contasSelecionadasObjetos.some(contaPodePagar);
  const haContaCancelavelSelecionada = contasSelecionadasObjetos.some(contaPodeCancelar);
  const haContaExcluivelSelecionada = contasSelecionadasObjetos.some(contaPodeExcluir);

  const alternarSelecaoConta = (contaId) => {
    setContasSelecionadas((atuais) =>
      atuais.includes(contaId) ? atuais.filter((id) => id !== contaId) : [...atuais, contaId],
    );
  };

  const selecionarTodasContasVisiveis = (event) => {
    const selecionar = event.target.checked;
    if (!selecionar) {
      setContasSelecionadas([]);
      return;
    }

    setContasSelecionadas(contasVisiveis.map((conta) => conta.id));
  };

  const limparSelecaoContas = () => {
    setContasSelecionadas([]);
  };

  const editarContaSelecionada = () => {
    if (totalSelecionadas !== 1) {
      toast.error("Selecione apenas um lancamento para editar");
      return;
    }

    abrirModalEdicao(contasSelecionadasObjetos[0]);
  };

  const estornarContasSelecionadas = async () => {
    const contasParaEstornar = contasSelecionadasObjetos.filter(contaTemPagamento);
    if (contasParaEstornar.length === 0) {
      toast.error("Selecione pelo menos uma conta com pagamento para estornar");
      return;
    }

    const motivo = window.prompt("Motivo do estorno (opcional):", "");
    if (motivo === null) return;

    const confirmado = window.confirm(
      `Estornar pagamento de ${contasParaEstornar.length} lancamento(s)? O saldo bancario sera revertido.`,
    );
    if (!confirmado) return;

    try {
      for (const conta of contasParaEstornar) {
        await api.post(`/contas-pagar/${conta.id}/estornar`, { motivo });
      }
      toast.success("Pagamento(s) estornado(s) com sucesso");
      limparSelecaoContas();
      carregarDados();
    } catch (error) {
      console.error("Erro ao estornar pagamentos:", error);
      toast.error(error.response?.data?.detail || "Erro ao estornar pagamento");
    }
  };

  const cancelarContasSelecionadas = async () => {
    const contasParaCancelar = contasSelecionadasObjetos.filter(contaPodeCancelar);
    if (contasParaCancelar.length === 0) {
      toast.error("Selecione pelo menos uma conta sem pagamento para cancelar");
      return;
    }

    const motivo = window.prompt("Motivo do cancelamento (opcional):", "");
    if (motivo === null) return;

    const confirmado = window.confirm(
      `Cancelar ${contasParaCancelar.length} lancamento(s)? O historico sera mantido.`,
    );
    if (!confirmado) return;

    try {
      for (const conta of contasParaCancelar) {
        await api.post(`/contas-pagar/${conta.id}/cancelar`, { motivo });
      }
      toast.success("Lancamento(s) cancelado(s) com sucesso");
      limparSelecaoContas();
      carregarDados();
    } catch (error) {
      console.error("Erro ao cancelar contas:", error);
      toast.error(error.response?.data?.detail || "Erro ao cancelar lancamento");
    }
  };

  const excluirContasSelecionadas = async () => {
    const contasParaExcluir = contasSelecionadasObjetos.filter(contaPodeExcluir);
    if (contasParaExcluir.length === 0) {
      toast.error("Selecione pelo menos uma conta sem pagamento para excluir");
      return;
    }

    const ignoradas = totalSelecionadas - contasParaExcluir.length;
    const avisoIgnoradas =
      ignoradas > 0 ? ` ${ignoradas} lancamento(s) com pagamento serao ignorados.` : "";
    const confirmado = window.confirm(
      `Excluir ${contasParaExcluir.length} lancamento(s) selecionado(s)?${avisoIgnoradas}`,
    );
    if (!confirmado) return;

    try {
      await api.post("/contas-pagar/recorrencias/excluir", {
        ids: contasParaExcluir.map((conta) => conta.id),
      });
      toast.success("Lancamento(s) excluido(s) com sucesso");
      limparSelecaoContas();
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir contas:", error);
      toast.error(error.response?.data?.detail || "Erro ao excluir lancamentos");
    }
  };

  return {
    algumasVisiveisSelecionadas,
    alternarSelecaoConta,
    cancelarContasSelecionadas,
    contaTemPagamento,
    contasSelecionadas,
    contasSelecionadasObjetos,
    contasVisiveis,
    editarContaSelecionada,
    estornarContasSelecionadas,
    excluirContasSelecionadas,
    haContaCancelavelSelecionada,
    haContaExcluivelSelecionada,
    haContaPagavelSelecionada,
    haContaPagaSelecionada,
    limparSelecaoContas,
    selecionarTodasContasVisiveis,
    todasVisiveisSelecionadas,
    totalSelecionadas,
  };
}
