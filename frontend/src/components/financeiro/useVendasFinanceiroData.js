import { useEffect, useState } from "react";
import api from "../../api";
import {
  calcularAnaliseInteligenteVendas,
  calcularPeriodoComparacao,
} from "./vendasFinanceiroUtils";

const RESUMO_VENDAS_INICIAL = {
  venda_bruta: 0,
  taxa_entrega: 0,
  desconto: 0,
  venda_liquida: 0,
  valor_recebido: 0,
  em_aberto: 0,
  quantidade_vendas: 0,
};

export default function useVendasFinanceiroData({
  abaAtiva,
  dataFim,
  dataInicio,
  modoComparacao,
  periodoComparacao,
  podeVerFinanceiroCompleto,
}) {
  const [loading, setLoading] = useState(false);
  const [resumo, setResumo] = useState(RESUMO_VENDAS_INICIAL);
  const [resumoComparacao, setResumoComparacao] = useState(RESUMO_VENDAS_INICIAL);
  const [vendasPorData, setVendasPorData] = useState([]);
  const [formasRecebimento, setFormasRecebimento] = useState([]);
  const [vendasPorFuncionario, setVendasPorFuncionario] = useState([]);
  const [vendasPorTipo, setVendasPorTipo] = useState([]);
  const [vendasPorGrupo, setVendasPorGrupo] = useState([]);
  const [produtosDetalhados, setProdutosDetalhados] = useState([]);
  const [listaVendas, setListaVendas] = useState([]);
  const [formasRecebimentoComparacao, setFormasRecebimentoComparacao] = useState([]);
  const [vendasPorGrupoComparacao, setVendasPorGrupoComparacao] = useState([]);
  const [vendasPorFuncionarioComparacao, setVendasPorFuncionarioComparacao] = useState([]);
  const [produtosAnalise, setProdutosAnalise] = useState([]);
  const [produtosMaisLucrativos, setProdutosMaisLucrativos] = useState([]);
  const [produtosPorCategoria, setProdutosPorCategoria] = useState({});
  const [alertasInteligentesVendas, setAlertasInteligentesVendas] = useState([]);
  const [previsaoProximos7Dias, setPrevisaoProximos7Dias] = useState(0);

  useEffect(() => {
    if (!podeVerFinanceiroCompleto) return;
    if (!dataInicio || !dataFim) return;

    const carregarDados = async () => {
      setLoading(true);

      try {
        const response = await api.get("/relatorios/vendas/relatorio", {
          params: { data_inicio: dataInicio, data_fim: dataFim },
        });
        const data = response.data;

        setResumo(data.resumo || {});
        setVendasPorData(data.vendas_por_data || []);
        setFormasRecebimento(data.formas_recebimento || []);
        setVendasPorFuncionario(data.vendas_por_funcionario || []);
        setVendasPorTipo(data.vendas_por_tipo || []);
        setVendasPorGrupo(data.vendas_por_grupo || []);
        setProdutosDetalhados(data.produtos_detalhados || []);
        setProdutosAnalise(data.produtos_analise || []);
        setListaVendas(data.lista_vendas || []);

        if (modoComparacao || abaAtiva === "comparacao") {
          const periodoComp = calcularPeriodoComparacao({
            dataInicio,
            dataFim,
            periodoComparacao,
          });
          const responseComp = await api.get("/relatorios/vendas/relatorio", {
            params: periodoComp,
          });
          setResumoComparacao(responseComp.data.resumo || {});
          setFormasRecebimentoComparacao(responseComp.data.formas_recebimento || []);
          setVendasPorGrupoComparacao(responseComp.data.vendas_por_grupo || []);
          setVendasPorFuncionarioComparacao(
            responseComp.data.vendas_por_funcionario || [],
          );
        } else {
          setResumoComparacao(RESUMO_VENDAS_INICIAL);
        }
      } catch (error) {
        console.error("Erro ao carregar relatório:", error);
      } finally {
        setLoading(false);
      }
    };

    carregarDados();
  }, [
    abaAtiva,
    dataFim,
    dataInicio,
    modoComparacao,
    periodoComparacao,
    podeVerFinanceiroCompleto,
  ]);

  useEffect(() => {
    if (abaAtiva !== "analise") return;

    const resultado = calcularAnaliseInteligenteVendas({
      produtosAnalise,
      resumo,
      resumoComparacao,
      vendasPorData,
    });

    setProdutosMaisLucrativos(resultado.produtosMaisLucrativos);
    setProdutosPorCategoria(resultado.produtosPorCategoria);
    setAlertasInteligentesVendas(resultado.alertasInteligentesVendas);
    setPrevisaoProximos7Dias(resultado.previsaoProximos7Dias);
  }, [abaAtiva, produtosAnalise, resumo, resumoComparacao, vendasPorData]);

  return {
    alertasInteligentesVendas,
    formasRecebimento,
    formasRecebimentoComparacao,
    listaVendas,
    loading,
    previsaoProximos7Dias,
    produtosDetalhados,
    produtosMaisLucrativos,
    produtosPorCategoria,
    resumo,
    resumoComparacao,
    vendasPorData,
    vendasPorFuncionario,
    vendasPorFuncionarioComparacao,
    vendasPorGrupo,
    vendasPorGrupoComparacao,
    vendasPorTipo,
  };
}
