import { useEffect, useState } from "react";
import api from "../api";
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
  const [gerarComissao, setGerarComissao] = useState(false);
  const [funcionarioComissao, setFuncionarioComissao] = useState(null);

  useEffect(() => {
    setVendaAtual((prev) => ({
      ...prev,
      vendedor_funcionario_id: funcionarioComissao?.id || null,
      funcionario_id: gerarComissao ? funcionarioComissao?.id || null : null,
    }));
  }, [funcionarioComissao, gerarComissao, setVendaAtual]);

  const handleToggleVendaComissionada = (checked) => {
    setVendaComissionada(checked);
    if (!checked) {
      setGerarComissao(false);
      setFuncionarioComissao(null);
      setVendaAtual((prev) => ({
        ...prev,
        funcionario_id: null,
        vendedor_funcionario_id: null,
      }));
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
    setVendaAtual((prev) => ({
      ...prev,
      vendedor_funcionario_id: funcionario?.id || null,
      funcionario_id: gerarComissao ? funcionario?.id || null : null,
    }));
    setFuncionariosSugeridos([]);
    setBuscaFuncionario("");
  };

  const handleRemoverFuncionarioComissao = () => {
    setFuncionarioComissao(null);
    setVendaAtual((prev) => ({
      ...prev,
      funcionario_id: null,
      vendedor_funcionario_id: null,
    }));
    setBuscaFuncionario("");
  };

  const limparComissao = () => {
    setVendaComissionada(false);
    setGerarComissao(false);
    setFuncionarioComissao(null);
    setVendaAtual((prev) => ({
      ...prev,
      funcionario_id: null,
      vendedor_funcionario_id: null,
    }));
    setBuscaFuncionario("");
    setFuncionariosSugeridos([]);
  };

  const sincronizarComissaoDaVenda = async (funcionarioId, comissionadoId = null) => {
    debugLog("Venda carregada - vendedor_funcionario_id:", funcionarioId);

    if (!funcionarioId) {
      debugLog("Venda sem funcionario_id - limpando estados de comissao");
      limparComissao();
      return;
    }

    try {
      const funcionarios = await carregarFuncionariosComissao();
      let funcionarioCarregado = funcionarios.find(
        (funcionario) => funcionario.id === funcionarioId,
      );
      if (!funcionarioCarregado) {
        try {
          const response = await api.get(`/funcionarios/${funcionarioId}`);
          funcionarioCarregado = response.data;
        } catch {
          // O cadastro pode ser um parceiro antigo indisponível na lista atual.
        }
      }

      if (funcionarioCarregado) {
        setVendaComissionada(true);
        setGerarComissao(Boolean(comissionadoId));
        setFuncionarioComissao(funcionarioCarregado);
        debugLog("Funcionario comissao carregado:", funcionarioCarregado);
      } else {
        debugWarn("Funcionario ID", funcionarioId, "nao encontrado na lista");
      }
    } catch (error) {
      console.error("Erro ao carregar funcionario de comissao:", error);
    }
  };

  return {
    vendaComissionada,
    gerarComissao,
    setGerarComissao,
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
