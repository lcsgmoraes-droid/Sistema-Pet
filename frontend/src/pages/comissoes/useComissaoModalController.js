import { useEffect, useState } from "react";
import api from "../../api";
import { DEFAULT_COMMISSION_RULES } from "./comissoesConstants";
import {
  buildBatchPayload,
  buildExistingRulesPayload,
  buildPendingConfiguration,
  buildRulesFromConfig,
  buildSelectedItemPayload,
  createSelectedCommissionItem,
  getCommissionItemKey,
  hasRuleChanges,
  isSameCommissionTarget,
  mapConfiguracoesPorItem,
  parseCommissionInteger,
} from "./comissoesUtils";

export function useComissaoModalController({ funcionarioId, configuracoes, onSave }) {
  const [funcionarios, setFuncionarios] = useState([]);
  const [funcionarioSel, setFuncionarioSel] = useState(funcionarioId || "");
  const [dataFechamento, setDataFechamento] = useState("");
  const [regras, setRegras] = useState(DEFAULT_COMMISSION_RULES);
  const [categoriasExpanded, setCategoriasExpanded] = useState({});
  const [configuracao, setConfiguracao] = useState({});
  const [itemSelecionado, setItemSelecionado] = useState(null);
  const [configuracoesParaSalvar, setConfiguracoesParaSalvar] = useState([]);
  const [salvando, setSalvando] = useState(false);
  const [progressoSalvamento, setProgressoSalvamento] = useState({ atual: 0, total: 0 });
  const [regrasOriginais, setRegrasOriginais] = useState(null);

  const carregarFuncionarios = async () => {
    try {
      const response = await api.get("/comissoes/funcionarios");
      if (response.data.success) {
        setFuncionarios(response.data.data);

        if (funcionarioId) {
          const funcionario = response.data.data.find(
            (item) => item.id === parseInt(funcionarioId, 10),
          );
          if (funcionario?.data_fechamento_comissao) {
            setDataFechamento(String(funcionario.data_fechamento_comissao));
          }
        }
      }
    } catch (err) {
      console.error("Erro ao carregar parceiros:", err);
    }
  };

  useEffect(() => {
    carregarFuncionarios();
  }, []);

  useEffect(() => {
    setConfiguracao(mapConfiguracoesPorItem(configuracoes));

    if (configuracoes.length > 0) {
      const regrasCarregadas = buildRulesFromConfig(configuracoes[0]);
      setRegras(regrasCarregadas);
      setRegrasOriginais(regrasCarregadas);
    }
  }, [configuracoes]);

  const setRegra = (campo, valor) => {
    setRegras((prev) => ({ ...prev, [campo]: valor }));
  };

  const toggleCategoria = (catId) => {
    setCategoriasExpanded((prev) => ({
      ...prev,
      [catId]: !prev[catId],
    }));
  };

  const getConfiguracao = (tipo, id) => configuracao[getCommissionItemKey(tipo, id)];
  const temConfiguracao = (tipo, id) => Boolean(getConfiguracao(tipo, id));
  const itemJaAdicionado = (tipo, id) =>
    configuracoesParaSalvar.some((config) => config.tipo === tipo && config.referencia_id === id);

  const selecionarItem = (tipo, id, nome) => {
    setItemSelecionado(createSelectedCommissionItem(tipo, id, nome, getConfiguracao(tipo, id)));
  };

  const adicionarConfiguracao = () => {
    if (!funcionarioSel) {
      alert("Selecione um parceiro");
      return;
    }

    if (!itemSelecionado) {
      alert("Selecione um item para configurar");
      return;
    }

    if (configuracoesParaSalvar.some((config) => isSameCommissionTarget(config, itemSelecionado))) {
      alert("Este item já foi adicionado à lista!");
      return;
    }

    if (
      itemSelecionado.tipo === "geral" &&
      (configuracoesParaSalvar.length > 0 || Object.keys(configuracao).length > 0)
    ) {
      const confirma = confirm(
        "A regra geral vale para todos os produtos e categorias deste parceiro.\n\n" +
          "Regras especificas de produto, subcategoria ou categoria continuam com prioridade.\n\nDeseja adicionar mesmo assim?",
      );
      if (!confirma) return;
    }

    if (itemSelecionado.tipo === "categoria") {
      const temProdutosOuSubs = configuracoesParaSalvar.some(
        (config) =>
          (config.tipo === "subcategoria" || config.tipo === "produto") &&
          config.nome.includes(itemSelecionado.nome),
      );
      if (temProdutosOuSubs) {
        const confirma = confirm(
          `ATENÇÃO: Você já configurou produtos/subcategorias desta categoria.\n\n` +
            `HIERARQUIA: Produto > Subcategoria > Categoria\n\n` +
            `A configuração mais específica tem prioridade.\n\nDeseja adicionar mesmo assim?`,
        );
        if (!confirma) return;
      }
    }

    setConfiguracoesParaSalvar((prev) => [...prev, buildPendingConfiguration(itemSelecionado)]);
    setItemSelecionado(null);
    alert('Configuração adicionada! Configure mais itens ou clique em "Salvar Todas"');
  };

  const removerConfiguracao = (index) => {
    setConfiguracoesParaSalvar((prev) => prev.filter((_, itemIndex) => itemIndex !== index));
  };

  const recarregarConfiguracoes = async () => {
    if (!funcionarioSel) return;

    try {
      const configResponse = await api.get(
        `/comissoes/configuracoes/funcionario/${funcionarioSel}`,
      );
      if (configResponse.data.success) {
        setConfiguracao(mapConfiguracoesPorItem(configResponse.data.data));
      }
    } catch (err) {
      console.error("Erro ao recarregar configurações:", err);
    }
  };

  const salvarDataFechamento = async () => {
    try {
      await api.put(`/clientes/${funcionarioSel}`, {
        data_fechamento_comissao: dataFechamento ? parseCommissionInteger(dataFechamento) : null,
      });
      alert("Data de fechamento salva com sucesso!");
    } catch (err) {
      console.error("Erro ao salvar data:", err);
      alert("Erro ao salvar data de fechamento");
    }
  };

  const salvarTodasConfiguracoes = async () => {
    if (!funcionarioSel) {
      alert("Selecione um parceiro");
      return;
    }

    if (configuracoesParaSalvar.length === 0) {
      alert("Adicione pelo menos uma configuração");
      return;
    }

    setSalvando(true);

    try {
      if (dataFechamento) {
        await api.put(`/clientes/${funcionarioSel}`, {
          data_fechamento_comissao: parseCommissionInteger(dataFechamento),
        });
      }

      const payload = buildBatchPayload(configuracoesParaSalvar, funcionarioSel, regras);
      const response = await api.post("/comissoes/configuracoes/batch", { configuracoes: payload });

      if (response.data.success) {
        alert(`${response.data.total} configurações salvas com sucesso!`);
        setConfiguracoesParaSalvar([]);
        await recarregarConfiguracoes();
        onSave();
      }
    } catch (err) {
      console.error("Erro ao salvar configurações:", err);
      console.error("Resposta do servidor:", err.response?.data);
      const mensagemErro = err.response?.data?.detail || err.message || "Erro desconhecido";
      alert(`Erro ao salvar configurações:\n\n${mensagemErro}`);
    } finally {
      setSalvando(false);
      setProgressoSalvamento({ atual: 0, total: 0 });
    }
  };

  const salvarItem = async () => {
    if (!funcionarioSel) {
      alert("Selecione um parceiro");
      return;
    }

    if (!itemSelecionado) {
      if (Object.keys(configuracao).length === 0) {
        alert("Nenhuma configuração encontrada para atualizar as regras.");
        return;
      }

      if (!hasRuleChanges(regras, regrasOriginais)) {
        alert("Nenhuma alteração detectada nas regras.");
        return;
      }

      if (
        !confirm("Deseja atualizar as regras de cálculo em TODAS as configurações deste parceiro?")
      ) {
        return;
      }

      try {
        for (const config of Object.values(configuracao)) {
          await api.post(
            "/comissoes/configuracoes",
            buildExistingRulesPayload(config, funcionarioSel, regras),
          );
        }
        alert("Regras atualizadas com sucesso em todas as configurações!");
        setRegrasOriginais(regras);
      } catch (err) {
        console.error("Erro ao atualizar regras:", err);
        alert("Erro ao atualizar regras");
      }
      return;
    }

    try {
      const dados = buildSelectedItemPayload(itemSelecionado, funcionarioSel, regras);
      const response = await api.post("/comissoes/configuracoes", dados);

      if (response.data.success) {
        alert("Configuração salva com sucesso!");
        const key = getCommissionItemKey(itemSelecionado.tipo, itemSelecionado.id);
        setConfiguracao((prev) => ({
          ...prev,
          [key]: { ...dados, id: response.data.config_id, nome_item: itemSelecionado.nome },
        }));
        setItemSelecionado(null);
      }
    } catch (err) {
      console.error("Erro ao salvar configuração:", err);
      alert("Erro ao salvar configuração");
    }
  };

  const removerConfiguracaoExistente = async (key, config) => {
    if (!confirm(`Deseja remover a configuração de "${config.nome_item || "Item"}"?`)) return;

    try {
      await api.delete(`/comissoes/configuracoes/${config.id}`);
      alert("Configuração removida com sucesso!");
      setConfiguracao((prev) => {
        const novoConfig = { ...prev };
        delete novoConfig[key];
        return novoConfig;
      });
    } catch (err) {
      console.error("Erro ao remover:", err);
      alert("Erro ao remover configuração");
    }
  };

  return {
    adicionarConfiguracao,
    categoriasExpanded,
    configuracao,
    configuracoesParaSalvar,
    dataFechamento,
    funcionarioSel,
    funcionarios,
    itemJaAdicionado,
    itemSelecionado,
    progressoSalvamento,
    regras,
    regrasAlteradas: hasRuleChanges(regras, regrasOriginais),
    regrasOriginais,
    removerConfiguracao,
    removerConfiguracaoExistente,
    salvarDataFechamento,
    salvarItem,
    salvarTodasConfiguracoes,
    salvando,
    selecionarItem,
    setDataFechamento,
    setFuncionarioSel,
    setItemSelecionado,
    setRegra,
    temConfiguracao,
    toggleCategoria,
  };
}
