import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle, Copy, Edit, PackageX, RefreshCw } from "lucide-react";
import { toast } from "react-hot-toast";
import api from "../api";
import SugestoesInteligentesRacoesPanels from "./racoes/SugestoesInteligentesRacoesPanels";

/**
 * Painel de Sugestões Inteligentes - Fase 6
 *
 * Features:
 * - Detecção de duplicatas
 * - Sugestões de padronização de nomes
 * - Gaps de estoque em segmentos importantes
 * - Score de saúde do cadastro
 *
 * @version 1.0.0 (2026-02-14)
 */
const SugestoesInteligentesRacoes = () => {
  // ============================================================================
  // STATES
  // ============================================================================

  const [loading, setLoading] = useState(true);
  const [relatorioCompleto, setRelatorioCompleto] = useState(null);
  const [duplicatas, setDuplicatas] = useState([]);
  const [padronizacoes, setPadronizacoes] = useState([]);
  const [gapsEstoque, setGapsEstoque] = useState([]);
  const [abaAtiva, setAbaAtiva] = useState("resumo");

  // Filtros
  const [filtroThreshold, setFiltroThreshold] = useState(0.8);
  const [filtroTipoSegmento, setFiltroTipoSegmento] = useState("porte");

  // Seleção de produto para mesclar (índice da duplicata -> 'produto_1' ou 'produto_2')
  const [produtosSelecionados, setProdutosSelecionados] = useState({});

  // Edição de nomes sugeridos (produto_id -> {editando: boolean, nome: string})
  const [nomesEditados, setNomesEditados] = useState({});

  // ============================================================================
  // EFFECTS
  // ============================================================================

  useEffect(() => {
    carregarRelatorioCompleto();
  }, []);

  // ============================================================================
  // FUNÇÕES DE CARREGAMENTO
  // ============================================================================

  const carregarRelatorioCompleto = async () => {
    try {
      setLoading(true);
      const res = await api.get("/racoes/sugestoes/relatorio-completo");
      setRelatorioCompleto(res.data);
      setLoading(false);
    } catch (error) {
      console.error("Erro ao carregar relatório:", error);
      toast.error("Erro ao carregar relatório de sugestões");
      setLoading(false);
    }
  };

  const carregarDuplicatas = async () => {
    try {
      setLoading(true);
      const res = await api.get(
        `/racoes/sugestoes/duplicatas?threshold_similaridade=${filtroThreshold}`,
      );
      setDuplicatas(res.data);
      setLoading(false);
    } catch (error) {
      console.error("Erro ao carregar duplicatas:", error);
      toast.error("Erro ao carregar duplicatas");
      setLoading(false);
    }
  };

  const carregarPadronizacoes = async () => {
    try {
      setLoading(true);
      const res = await api.get("/racoes/sugestoes/padronizar-nomes?limite=50");
      setPadronizacoes(res.data);
      setLoading(false);
    } catch (error) {
      console.error("Erro ao carregar padronizações:", error);
      toast.error("Erro ao carregar sugestões de padronização");
      setLoading(false);
    }
  };

  const carregarGapsEstoque = async () => {
    try {
      setLoading(true);
      const res = await api.get(
        `/racoes/sugestoes/gaps-estoque?tipo_segmento=${filtroTipoSegmento}`,
      );
      setGapsEstoque(res.data);
      setLoading(false);
    } catch (error) {
      console.error("Erro ao carregar gaps:", error);
      toast.error("Erro ao carregar gaps de estoque");
      setLoading(false);
    }
  };

  // ============================================================================
  // HANDLERS
  // ============================================================================

  const handleMudarAba = (aba) => {
    setAbaAtiva(aba);

    // Carregar dados específicos da aba
    if (aba === "duplicatas" && duplicatas.length === 0) {
      carregarDuplicatas();
    } else if (aba === "padronizacao" && padronizacoes.length === 0) {
      carregarPadronizacoes();
    } else if (aba === "gaps" && gapsEstoque.length === 0) {
      carregarGapsEstoque();
    }
  };

  const handleAplicarPadronizacao = async (padronizacao) => {
    try {
      // Usar nome editado se houver, senão usar sugestão original
      const nomeEditado = nomesEditados[padronizacao.produto_id];
      const nomeFinal = nomeEditado?.nome || padronizacao.nome_sugerido;

      await api.patch(`/produtos/${padronizacao.produto_id}`, {
        nome: nomeFinal,
      });

      toast.success("Nome atualizado com sucesso!");

      // Remover da lista
      setPadronizacoes((prev) => prev.filter((p) => p.produto_id !== padronizacao.produto_id));

      // Limpar estado de edição
      setNomesEditados((prev) => {
        const novo = { ...prev };
        delete novo[padronizacao.produto_id];
        return novo;
      });

      // Atualizar relatório
      carregarRelatorioCompleto();
    } catch (error) {
      console.error("Erro ao aplicar padronização:", error);
      toast.error("Erro ao atualizar nome do produto");
    }
  };

  const handleIgnorarDuplicata = async (duplicata) => {
    try {
      await api.post("/racoes/sugestoes/duplicatas/ignorar", null, {
        params: {
          produto_id_1: duplicata.produto_1.id,
          produto_id_2: duplicata.produto_2.id,
        },
      });

      toast.success("Duplicata ignorada com sucesso!");

      // Remover da lista
      setDuplicatas((prev) =>
        prev.filter(
          (d) =>
            !(
              d.produto_1.id === duplicata.produto_1.id && d.produto_2.id === duplicata.produto_2.id
            ),
        ),
      );

      // Atualizar relatório
      carregarRelatorioCompleto();
    } catch (error) {
      console.error("Erro ao ignorar duplicata:", error);
      toast.error("Erro ao ignorar duplicata");
    }
  };

  const handleSelecionarProduto = (duplicataIndex, produto) => {
    setProdutosSelecionados((prev) => ({
      ...prev,
      [duplicataIndex]: produto,
    }));
  };

  const handleConfirmarMesclagem = async (duplicata, duplicataIndex) => {
    const produtoSelecionado = produtosSelecionados[duplicataIndex];

    if (!produtoSelecionado) {
      toast.error("Selecione qual produto deseja manter antes de confirmar");
      return;
    }

    const produto_id_manter =
      produtoSelecionado === "produto_1" ? duplicata.produto_1.id : duplicata.produto_2.id;
    const produto_id_remover =
      produtoSelecionado === "produto_1" ? duplicata.produto_2.id : duplicata.produto_1.id;

    try {
      const response = await api.post("/racoes/sugestoes/duplicatas/mesclar", null, {
        params: {
          produto_id_manter,
          produto_id_remover,
          transferir_estoque: true,
        },
      });

      toast.success(response.data.mensagem);

      // Remover da lista
      setDuplicatas((prev) =>
        prev.filter(
          (d) =>
            !(
              d.produto_1.id === duplicata.produto_1.id && d.produto_2.id === duplicata.produto_2.id
            ),
        ),
      );

      // Limpar seleção
      setProdutosSelecionados((prev) => {
        const novo = { ...prev };
        delete novo[duplicataIndex];
        return novo;
      });

      // Atualizar relatório
      carregarRelatorioCompleto();
    } catch (error) {
      console.error("Erro ao mesclar produtos:", error);
      toast.error("Erro ao mesclar produtos");
    }
  };

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  // ============================================================================
  // RENDER PRINCIPAL
  // ============================================================================

  if (loading && abaAtiva === "resumo") {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <AlertCircle className="h-7 w-7 text-blue-600" />
            Sugestões Inteligentes
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Otimize seu cadastro de rações com sugestões automáticas
          </p>
        </div>
      </div>

      {/* Abas */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="border-b border-gray-200">
          <div className="flex space-x-1 p-2">
            <button
              onClick={() => handleMudarAba("resumo")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === "resumo"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <CheckCircle className="h-4 w-4 inline mr-2" />
              Resumo Geral
            </button>

            <button
              onClick={() => handleMudarAba("duplicatas")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === "duplicatas"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <Copy className="h-4 w-4 inline mr-2" />
              Duplicatas
              {relatorioCompleto?.resumo?.duplicatas_detectadas > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-orange-500 text-white text-xs rounded-full">
                  {relatorioCompleto.resumo.duplicatas_detectadas}
                </span>
              )}
            </button>

            <button
              onClick={() => handleMudarAba("padronizacao")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === "padronizacao"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <Edit className="h-4 w-4 inline mr-2" />
              Padronização
              {relatorioCompleto?.resumo?.nomes_padronizar > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-blue-500 text-white text-xs rounded-full">
                  {relatorioCompleto.resumo.nomes_padronizar}
                </span>
              )}
            </button>

            <button
              onClick={() => handleMudarAba("gaps")}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                abaAtiva === "gaps"
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <PackageX className="h-4 w-4 inline mr-2" />
              Gaps de Estoque
              {relatorioCompleto?.resumo?.gaps_criticos > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                  {relatorioCompleto.resumo.gaps_criticos}
                </span>
              )}
            </button>
          </div>
        </div>

        <div className="p-4">
          <SugestoesInteligentesRacoesPanels
            abaAtiva={abaAtiva}
            carregarDuplicatas={carregarDuplicatas}
            carregarGapsEstoque={carregarGapsEstoque}
            carregarRelatorioCompleto={carregarRelatorioCompleto}
            duplicatas={duplicatas}
            filtroThreshold={filtroThreshold}
            filtroTipoSegmento={filtroTipoSegmento}
            gapsEstoque={gapsEstoque}
            handleAplicarPadronizacao={handleAplicarPadronizacao}
            handleConfirmarMesclagem={handleConfirmarMesclagem}
            handleIgnorarDuplicata={handleIgnorarDuplicata}
            handleSelecionarProduto={handleSelecionarProduto}
            loading={loading}
            nomesEditados={nomesEditados}
            padronizacoes={padronizacoes}
            produtosSelecionados={produtosSelecionados}
            relatorioCompleto={relatorioCompleto}
            setFiltroThreshold={setFiltroThreshold}
            setFiltroTipoSegmento={setFiltroTipoSegmento}
            setNomesEditados={setNomesEditados}
          />
        </div>
      </div>
    </div>
  );
};

export default SugestoesInteligentesRacoes;
