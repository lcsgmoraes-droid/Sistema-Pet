import { useEffect, useState } from "react";
import { debugLog, debugWarn } from "../utils/debug";

export function usePDVComissaoEstado({
  setVendaAtual,
  modoVisualizacao,
  funcionariosSugeridos,
  setFuncionariosSugeridos,
  buscaFuncionario,
  setBuscaFuncionario,
  carregarFuncionariosComissao,
}) {
  const [vendaComissionada, setVendaComissionada] = useState(false);
  const [funcionarioComissao, setFuncionarioComissao] = useState(null);

  useEffect(() => {
    setVendaAtual((prev) => ({
      ...prev,
      funcionario_id: funcionarioComissao?.id || null,
    }));
  }, [funcionarioComissao, setVendaAtual]);

  const handleToggleVendaComissionada = (checked) => {
    setVendaComissionada(checked);
    if (!checked) {
      setFuncionarioComissao(null);
      setBuscaFuncionario("");
      setFuncionariosSugeridos([]);
    }
  };

  const handleBuscaFuncionarioFocus = async () => {
    if (!modoVisualizacao) {
      await carregarFuncionariosComissao();
    }
  };

  const handleBuscaFuncionarioChange = async (valor) => {
    setBuscaFuncionario(valor);
    await carregarFuncionariosComissao(valor);
  };

  const handleSelecionarFuncionarioComissao = (funcionario) => {
    setFuncionarioComissao(funcionario);
    setFuncionariosSugeridos([]);
    setBuscaFuncionario("");
  };

  const handleRemoverFuncionarioComissao = () => {
    setFuncionarioComissao(null);
    setBuscaFuncionario("");
  };

  const limparComissao = () => {
    setVendaComissionada(false);
    setFuncionarioComissao(null);
    setBuscaFuncionario("");
    setFuncionariosSugeridos([]);
  };

  const sincronizarComissaoDaVenda = async (funcionarioId) => {
    debugLog("Venda carregada - funcionario_id:", funcionarioId);

    if (!funcionarioId) {
      debugLog("Venda sem funcionario_id - limpando estados de comissao");
      limparComissao();
      return;
    }

    try {
      const funcionarios = await carregarFuncionariosComissao();
      const funcionarioCarregado = funcionarios.find(
        (funcionario) => funcionario.id === funcionarioId,
      );

      if (funcionarioCarregado) {
        setVendaComissionada(true);
        setFuncionarioComissao(funcionarioCarregado);
        debugLog("Funcionario comissao carregado:", funcionarioCarregado);
      } else {
        debugWarn(
          "Funcionario ID",
          funcionarioId,
          "nao encontrado na lista",
        );
      }
    } catch (error) {
      console.error("Erro ao carregar funcionario de comissao:", error);
    }
  };

  return {
    vendaComissionada,
    funcionarioComissao,
    funcionariosSugeridos,
    buscaFuncionario,
    sincronizarComissaoDaVenda,
    handleToggleVendaComissionada,
    handleBuscaFuncionarioFocus,
    handleBuscaFuncionarioChange,
    handleSelecionarFuncionarioComissao,
    handleRemoverFuncionarioComissao,
    limparComissao,
  };
}
