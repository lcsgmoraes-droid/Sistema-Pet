import { useEffect, useState } from "react";
import api from "../api";
import { debugLog, debugWarn } from "../utils/debug";

export function usePDVComissao(setVendaAtual, modoVisualizacao) {
  const [vendaComissionada, setVendaComissionada] = useState(false);
  const [funcionarioComissao, setFuncionarioComissao] = useState(null);
  const [funcionariosSugeridos, setFuncionariosSugeridos] = useState([]);
  const [buscaFuncionario, setBuscaFuncionario] = useState("");

  useEffect(() => {
    setVendaAtual((prev) => ({
      ...prev,
      funcionario_id: funcionarioComissao?.id || null,
    }));
  }, [funcionarioComissao, setVendaAtual]);

  const carregarFuncionariosComissao = async (busca = "") => {
    try {
      const response = await api.get("/comissoes/configuracoes/funcionarios");
      const funcionarios = response.data.data || [];
      const termo = String(busca || "").trim().toLowerCase();
      const filtrados = termo
        ? funcionarios.filter((funcionario) =>
            funcionario.nome.toLowerCase().includes(termo),
          )
        : funcionarios;

      setFuncionariosSugeridos(filtrados);
      return filtrados;
    } catch (error) {
      console.error("Erro ao buscar funcionários:", error);
      setFuncionariosSugeridos([]);
      return [];
    }
  };

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
    debugLog("🔍 Venda carregada - funcionario_id:", funcionarioId);

    if (!funcionarioId) {
      debugLog("ℹ️ Venda sem funcionario_id - limpando estados de comissão");
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
        debugLog(
          "✅ Funcionário comissão carregado:",
          funcionarioCarregado,
        );
      } else {
        debugWarn(
          "⚠️ Funcionário ID",
          funcionarioId,
          "não encontrado na lista",
        );
      }
    } catch (error) {
      console.error("Erro ao carregar funcionário de comissão:", error);
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
