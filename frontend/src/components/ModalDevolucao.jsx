import { useState, useEffect, useRef } from "react";
import { X, RotateCcw } from "lucide-react";
import api from "../api";
import ModalDevolucaoSections from "./devolucao/ModalDevolucaoSections";
import { getStatusBuscaDevolucao } from "../utils/pdvReturnEligibility";

const STATUS_BUSCA_DEVOLUCAO = getStatusBuscaDevolucao().join(",");

export default function ModalDevolucao({ caixaId, vendaInicial = null, onClose, onSucesso }) {
  const [passo, setPasso] = useState(1); // 1: listar vendas, 2: selecionar itens
  const [vendas, setVendas] = useState([]);
  const [vendaSelecionada, setVendaSelecionada] = useState(null);
  const [itensSelecionados, setItensSelecionados] = useState({});
  const [quantidades, setQuantidades] = useState({});
  const [motivo, setMotivo] = useState("");
  const [gerarCredito, setGerarCredito] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");
  const vendaInicialCarregadaRef = useRef(null);

  // 🆕 Estados para devolução de KIT
  const [modoDevolucaoKit, setModoDevolucaoKit] = useState({}); // {itemId: 'kit_inteiro' | 'componentes'}
  const [componentesSelecionados, setComponentesSelecionados] = useState({}); // {itemId: {componenteId: true/false}}
  const [quantidadesComponentes, setQuantidadesComponentes] = useState({}); // {itemId: {componenteIndex: quantidade}}

  // Filtros
  const [filtros, setFiltros] = useState({
    busca: "",
    data_inicio: "",
    data_fim: "",
    status: STATUS_BUSCA_DEVOLUCAO,
  });

  const obterDataVenda = (venda) =>
    venda?.data_venda || venda?.data_criacao || venda?.created_at || venda?.data_finalizacao;

  const formatarDataVenda = (venda) => {
    const data = obterDataVenda(venda);
    if (!data) return "Data não disponível";

    const dataObj = new Date(data);
    if (Number.isNaN(dataObj.getTime())) return "Data não disponível";

    return dataObj.toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  useEffect(() => {
    buscarVendas();
  }, [filtros]);

  useEffect(() => {
    if (!vendaInicial?.id) return;
    if (String(vendaInicialCarregadaRef.current) === String(vendaInicial.id)) return;

    vendaInicialCarregadaRef.current = vendaInicial.id;
    selecionarVenda(vendaInicial);
  }, [vendaInicial?.id]);

  const buscarVendas = async () => {
    setLoading(true);
    setErro("");

    try {
      const params = {
        per_page: 50,
        ...filtros,
      };

      const response = await api.get("/vendas", { params });
      setVendas(response.data.vendas || []);
    } catch (error) {
      console.error("Erro ao buscar vendas:", error);
      setErro("Erro ao carregar vendas");
    } finally {
      setLoading(false);
    }
  };

  const selecionarVenda = async (venda) => {
    setLoading(true);
    setErro("");

    try {
      // Buscar detalhes completos da venda
      const response = await api.get(`/vendas/${venda.id}`);
      setVendaSelecionada(response.data);
      setItensSelecionados({});
      setModoDevolucaoKit({});
      setComponentesSelecionados({});
      setQuantidadesComponentes({});
      setMotivo("");
      setErro("");

      // Inicializar quantidades com o máximo disponível
      const qtds = {};
      response.data.itens.forEach((item) => {
        qtds[item.id] = item.quantidade;
      });
      setQuantidades(qtds);

      setPasso(2);
    } catch (error) {
      console.error("Erro ao buscar venda:", error);
      setErro(error.response?.data?.detail || "Erro ao carregar detalhes da venda");
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (itemId) => {
    const wasSelected = itensSelecionados[itemId];

    setItensSelecionados((prev) => ({
      ...prev,
      [itemId]: !prev[itemId],
    }));

    // 🆕 Se está desmarcando, limpar estados do KIT
    if (wasSelected) {
      setModoDevolucaoKit((prev) => {
        const novo = { ...prev };
        delete novo[itemId];
        return novo;
      });
      setComponentesSelecionados((prev) => {
        const novo = { ...prev };
        delete novo[itemId];
        return novo;
      });
      setQuantidadesComponentes((prev) => {
        const novo = { ...prev };
        delete novo[itemId];
        return novo;
      });
    }
  };

  const handleQuantidadeChange = (itemId, valor) => {
    const item = vendaSelecionada.itens.find((i) => i.id === itemId);
    const qtdMaxima = item.quantidade;
    const qtdNova = Math.min(Math.max(0, parseFloat(valor) || 0), qtdMaxima);

    setQuantidades((prev) => ({
      ...prev,
      [itemId]: qtdNova,
    }));
  };

  // 🆕 Funções para gerenciar devolução de KIT
  const isItemKit = (item) => {
    return item.tipo_produto === "KIT" && item.composicao_kit && item.composicao_kit.length > 0;
  };

  const handleEscolhaModoKit = (itemId, modo) => {
    setModoDevolucaoKit((prev) => ({
      ...prev,
      [itemId]: modo,
    }));

    // Se escolheu componentes, inicializar estados
    if (modo === "componentes") {
      const item = vendaSelecionada.itens.find((i) => i.id === itemId);
      if (item && item.composicao_kit) {
        // Inicializar todos componentes como NÃO selecionados
        const compSel = {};
        const compQtd = {};
        item.composicao_kit.forEach((comp, index) => {
          compSel[index] = false;
          // Quantidade máxima = quantidade do componente no KIT * quantidade do KIT vendido
          compQtd[index] = comp.quantidade * item.quantidade;
        });

        setComponentesSelecionados((prev) => ({
          ...prev,
          [itemId]: compSel,
        }));

        setQuantidadesComponentes((prev) => ({
          ...prev,
          [itemId]: compQtd,
        }));
      }
    }
  };

  const toggleComponente = (itemId, componenteIndex) => {
    setComponentesSelecionados((prev) => ({
      ...prev,
      [itemId]: {
        ...(prev[itemId] || {}),
        [componenteIndex]: !prev[itemId]?.[componenteIndex],
      },
    }));
  };

  const handleQuantidadeComponenteChange = (itemId, componenteIndex, valor) => {
    const item = vendaSelecionada.itens.find((i) => i.id === itemId);
    const componente = item.composicao_kit[componenteIndex];
    const qtdMaxima = componente.quantidade * item.quantidade;
    const qtdNova = Math.min(Math.max(0, parseFloat(valor) || 0), qtdMaxima);

    setQuantidadesComponentes((prev) => ({
      ...prev,
      [itemId]: {
        ...(prev[itemId] || {}),
        [componenteIndex]: qtdNova,
      },
    }));
  };

  const handleConfirmar = async () => {
    // 🆕 Validar KITs: se selecionou KIT, precisa escolher modo
    const itensKitSemEscolha = Object.keys(itensSelecionados)
      .filter((id) => itensSelecionados[id])
      .filter((id) => {
        const item = vendaSelecionada.itens.find((i) => i.id === parseInt(id));
        return isItemKit(item) && !modoDevolucaoKit[id];
      });

    if (itensKitSemEscolha.length > 0) {
      setErro(
        "Para itens KIT, você deve escolher entre devolver o KIT inteiro ou selecionar componentes",
      );
      return;
    }

    // 🆕 Construir lista de itens para devolução
    const itensDevolucao = [];

    Object.keys(itensSelecionados)
      .filter((id) => itensSelecionados[id])
      .forEach((id) => {
        const itemId = parseInt(id);
        const item = vendaSelecionada.itens.find((i) => i.id === itemId);

        if (isItemKit(item)) {
          const modo = modoDevolucaoKit[id];

          if (modo === "kit_inteiro") {
            // Devolver KIT inteiro
            itensDevolucao.push({
              item_id: itemId,
              quantidade: quantidades[id],
            });
          } else if (modo === "componentes") {
            // Devolver apenas componentes selecionados
            const compSel = componentesSelecionados[id] || {};
            const compQtd = quantidadesComponentes[id] || {};

            const componentesParaDevolver = Object.keys(compSel)
              .filter((index) => compSel[index])
              .map((index) => parseInt(index));

            if (componentesParaDevolver.length === 0) {
              setErro(
                `Você deve selecionar pelo menos um componente do KIT "${item.produto_nome}"`,
              );
              return;
            }

            // Para cada componente selecionado, criar entrada de devolução
            componentesParaDevolver.forEach((index) => {
              const componente = item.composicao_kit[index];
              const qtd = compQtd[index] || 0;

              if (qtd <= 0) {
                setErro(
                  `Quantidade do componente "${componente.produto_nome}" deve ser maior que zero`,
                );
                return;
              }

              // 🔥 IMPORTANTE: Enviar como devolução de componente
              // O backend precisa entender que é um componente de KIT
              itensDevolucao.push({
                produto_id: componente.produto_id,
                quantidade: qtd,
                preco_unitario:
                  (item.preco_unitario /
                    item.composicao_kit.reduce((sum, c) => sum + c.quantidade, 0)) *
                  componente.quantidade,
                is_componente_kit: true,
                kit_item_id: itemId,
              });
            });
          }
        } else {
          // Item normal (não KIT)
          itensDevolucao.push({
            item_id: itemId,
            quantidade: quantidades[id],
          });
        }
      });

    if (itensDevolucao.length === 0) {
      setErro("Selecione pelo menos um item para devolução");
      return;
    }

    // Validar quantidades
    const temQuantidadeInvalida = itensDevolucao.some((item) => item.quantidade <= 0);
    if (temQuantidadeInvalida) {
      setErro("Todas as quantidades devem ser maiores que zero");
      return;
    }

    if (!motivo.trim()) {
      setErro("Informe o motivo da devolução");
      return;
    }

    setLoading(true);
    setErro("");

    try {
      await api.post(`/vendas/${vendaSelecionada.id}/devolucao`, {
        caixa_id: caixaId,
        itens: itensDevolucao,
        motivo: motivo,
        gerar_credito: gerarCredito,
      });

      alert("Devolução registrada com sucesso!");
      onSucesso();
    } catch (error) {
      console.error("Erro ao registrar devolução:", error);
      setErro(error.response?.data?.detail || "Erro ao registrar devolução");
    } finally {
      setLoading(false);
    }
  };

  const calcularTotalDevolucao = () => {
    if (!vendaSelecionada) return 0;

    let total = 0;

    Object.keys(itensSelecionados)
      .filter((id) => itensSelecionados[id])
      .forEach((id) => {
        const item = vendaSelecionada.itens.find((i) => i.id === parseInt(id));

        if (isItemKit(item)) {
          const modo = modoDevolucaoKit[id];

          if (modo === "kit_inteiro") {
            // Valor do KIT inteiro
            const qtd = quantidades[id] || 0;
            total += item.preco_unitario * qtd;
          } else if (modo === "componentes") {
            // Valor proporcional dos componentes
            const compSel = componentesSelecionados[id] || {};
            const compQtd = quantidadesComponentes[id] || {};

            // Calcular valor proporcional baseado na composição
            const totalQuantidadeComposicao = item.composicao_kit.reduce(
              (sum, c) => sum + c.quantidade,
              0,
            );

            Object.keys(compSel)
              .filter((index) => compSel[index])
              .forEach((index) => {
                const componente = item.composicao_kit[index];
                const qtd = compQtd[index] || 0;

                // Valor proporcional do componente
                const valorProporcional =
                  (item.preco_unitario / totalQuantidadeComposicao) * componente.quantidade;
                const qtdKits = qtd / componente.quantidade;
                total += valorProporcional * qtdKits;
              });
          }
        } else {
          // Item normal
          const qtd = quantidades[id] || 0;
          total += item.preco_unitario * qtd;
        }
      });

    return total;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
              <RotateCcw className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Devolução</h2>
              <p className="text-sm text-gray-500">
                {passo === 1 ? "Selecione a venda" : "Selecionar itens para devolução"}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        <ModalDevolucaoSections
          calcularTotalDevolucao={calcularTotalDevolucao}
          componentesSelecionados={componentesSelecionados}
          erro={erro}
          filtros={filtros}
          formatarDataVenda={formatarDataVenda}
          gerarCredito={gerarCredito}
          handleConfirmar={handleConfirmar}
          handleEscolhaModoKit={handleEscolhaModoKit}
          handleQuantidadeChange={handleQuantidadeChange}
          handleQuantidadeComponenteChange={handleQuantidadeComponenteChange}
          isItemKit={isItemKit}
          itensSelecionados={itensSelecionados}
          loading={loading}
          modoDevolucaoKit={modoDevolucaoKit}
          motivo={motivo}
          onClose={onClose}
          passo={passo}
          quantidades={quantidades}
          quantidadesComponentes={quantidadesComponentes}
          selecionarVenda={selecionarVenda}
          setErro={setErro}
          setFiltros={setFiltros}
          setGerarCredito={setGerarCredito}
          setItensSelecionados={setItensSelecionados}
          setMotivo={setMotivo}
          setPasso={setPasso}
          setQuantidades={setQuantidades}
          setVendaSelecionada={setVendaSelecionada}
          toggleComponente={toggleComponente}
          toggleItem={toggleItem}
          vendaSelecionada={vendaSelecionada}
          vendas={vendas}
        />
      </div>
    </div>
  );
}
