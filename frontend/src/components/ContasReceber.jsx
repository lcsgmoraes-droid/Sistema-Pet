import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowDownUp, Plus, Receipt } from "lucide-react";
import api from "../api";
import { getAccessToken } from "../auth/tokenStorage";
import { toast } from "react-hot-toast";
import { safeArray } from "../utils/safeArray";
import ActionButton from "./ui/ActionButton";
import CustomerIdentity from "./ui/CustomerIdentity";
import DataTable from "./ui/DataTable";
import LoadingState from "./ui/LoadingState";
import MoneyCell, { formatMoneyCellValue } from "./ui/MoneyCell";
import PageHeader from "./ui/PageHeader";
import StatusBadge from "./ui/StatusBadge";
import {
  ContasReceberDetalhesModal,
  ContasReceberFilters,
  ContasReceberRecebimentoModal,
} from "./contasReceber/ContasReceberPanels";

const ContasReceber = () => {
  const navigate = useNavigate();
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    status: "todos",
    cliente_id: null,
    data_inicio: "",
    data_fim: "",
    apenas_vencidas: false,
    apenas_vencer: false,
  });

  const [buscaNumeroVenda, setBuscaNumeroVenda] = useState("");
  const [ordenacao, setOrdenacao] = useState("desc"); // 'asc' = mais antiga primeiro, 'desc' = mais nova primeiro

  const [clientes, setClientes] = useState([]);
  const [contaSelecionada, setContaSelecionada] = useState(null);
  const [detalhesCompletos, setDetalhesCompletos] = useState(null);
  const [mostrarModalRecebimento, setMostrarModalRecebimento] = useState(false);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [formasPagamento, setFormasPagamento] = useState([]);
  const [contasBancarias, setContasBancarias] = useState([]);

  const [dadosRecebimento, setDadosRecebimento] = useState({
    valor_recebido: 0,
    data_recebimento: new Date().toISOString().split("T")[0],
    forma_pagamento_id: null,
    conta_bancaria_id: null,
    valor_juros: 0,
    valor_multa: 0,
    valor_desconto: 0,
    observacoes: "",
  });

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarFormasPagamento = async (headers) => {
    const response = await api.get("/comissoes/formas-pagamento", { headers });
    const lista = response.data?.formas || [];
    return safeArray(lista).map((forma) => ({
      id: forma.id,
      nome: forma.nome,
      tipo: forma.nome?.toLowerCase()?.replace(/\s+/g, "_") || "outro",
      icone: "💳",
      conta_bancaria_destino_id: null,
    }));
  };

  // Aplicar filtro automaticamente quando buscaNumeroVenda mudar
  useEffect(() => {
    if (buscaNumeroVenda.trim().length > 0) {
      const timer = setTimeout(() => {
        aplicarFiltros();
      }, 500); // Debounce de 500ms
      return () => clearTimeout(timer);
    } else if (buscaNumeroVenda === "") {
      // Se limpar o campo, recarregar tudo
      carregarDados();
    }
  }, [buscaNumeroVenda]);

  const carregarDados = async () => {
    try {
      const token = getAccessToken();
      const headers = { Authorization: `Bearer ${token}` };

      const [contasRes, clientesRes, formasRes, bancariasRes] = await Promise.allSettled([
        api.get(`/contas-receber/`, { headers }),
        api.get(`/clientes/`, { headers }),
        carregarFormasPagamento(headers),
        api.get(`/contas-bancarias?apenas_ativas=true`, { headers }),
      ]);

      if (contasRes.status !== "fulfilled") throw contasRes.reason;
      if (clientesRes.status !== "fulfilled") throw clientesRes.reason;
      if (bancariasRes.status !== "fulfilled") throw bancariasRes.reason;

      // Ordenar por ID (mais recentes primeiro por padrao)
      const contasOrdenadas = [...safeArray(contasRes.value.data)].sort((a, b) => b.id - a.id);
      setContas(contasOrdenadas);
      setClientes(safeArray(clientesRes.value.data));

      if (formasRes.status === "fulfilled") {
        setFormasPagamento(safeArray(formasRes.value));
      } else {
        setFormasPagamento([]);
        console.warn("Nao foi possivel carregar formas de pagamento. Usando lista vazia.");
      }

      setContasBancarias(safeArray(bancariasRes.value.data));
    } catch (error) {
      console.error("Erro ao carregar dados:", error);
      toast.error("Erro ao carregar contas a receber");
    } finally {
      setLoading(false);
    }
  };

  const aplicarFiltros = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filtros.status !== "todos") params.append("status", filtros.status);
      if (filtros.cliente_id) params.append("cliente_id", filtros.cliente_id);
      if (filtros.data_inicio) params.append("data_inicio", filtros.data_inicio);
      if (filtros.data_fim) params.append("data_fim", filtros.data_fim);
      if (filtros.apenas_vencidas) params.append("apenas_vencidas", "true");
      if (filtros.apenas_vencer) params.append("apenas_vencer", "true");
      if (buscaNumeroVenda) params.append("numero_venda", buscaNumeroVenda); // Filtro pelo backend

      const response = await api.get(`/contas-receber/?${params}`);

      setContas(response.data);
    } catch (error) {
      console.error("Erro ao filtrar:", error);
      toast.error("Erro ao aplicar filtros");
    } finally {
      setLoading(false);
    }
  };

  const abrirVendaNoPDV = (vendaId) => {
    // Armazena ID da venda para abrir automaticamente no PDV
    sessionStorage.setItem("abrirVenda", vendaId);
    sessionStorage.setItem("abrirModalPagamento", "true");
    toast.success("Redirecionando para o PDV...");
    navigate("/pdv");
  };

  const abrirFluxoDeCaixa = (conta) => {
    // Redireciona para o fluxo de caixa com filtros da conta
    const params = new URLSearchParams();
    if (conta.cliente_nome) {
      params.append("busca", conta.cliente_nome);
    }
    if (conta.documento) {
      params.append("documento", conta.documento);
    }
    navigate(`/financeiro/fluxo-caixa?${params.toString()}`);
    toast.success("Redirecionando para o Fluxo de Caixa...");
  };

  const alternarOrdenacao = () => {
    const novaOrdenacao = ordenacao === "desc" ? "asc" : "desc";
    setOrdenacao(novaOrdenacao);

    const contasOrdenadas = [...contas].sort((a, b) => {
      if (novaOrdenacao === "desc") {
        return b.id - a.id; // Mais nova primeiro
      } else {
        return a.id - b.id; // Mais antiga primeiro
      }
    });

    setContas(contasOrdenadas);
    toast.success(
      novaOrdenacao === "desc"
        ? "Ordenado: mais recentes primeiro"
        : "Ordenado: mais antigas primeiro",
    );
  };

  const abrirModalRecebimento = (conta) => {
    setContaSelecionada(conta);
    setDadosRecebimento({
      valor_recebido: parseFloat((conta.valor_final - conta.valor_recebido).toFixed(2)),
      data_recebimento: new Date().toISOString().split("T")[0],
      forma_pagamento_id: conta.forma_pagamento_id || null,
      conta_bancaria_id: null,
      valor_juros: 0,
      valor_multa: 0,
      valor_desconto: 0,
      observacoes: "",
    });
    setMostrarModalRecebimento(true);
  };

  const abrirDetalhes = async (conta) => {
    try {
      const response = await api.get(`/contas-receber/${conta.id}`);

      setContaSelecionada(conta);
      setDetalhesCompletos(response.data);
      setMostrarDetalhes(true);
    } catch (error) {
      console.error("Erro ao carregar detalhes:", error);
      toast.error("Erro ao carregar detalhes da conta");
    }
  };

  const abrirVenda = (vendaId) => {
    // Navegar para o PDV com a venda
    navigate(`/pdv?venda=${vendaId}`);
  };

  const registrarRecebimento = async () => {
    try {
      await api.post(`/contas-receber/${contaSelecionada.id}/receber`, dadosRecebimento);

      toast.success("Recebimento registrado com sucesso!");
      setMostrarModalRecebimento(false);
      carregarDados();
    } catch (error) {
      console.error("Erro ao registrar recebimento:", error);
      toast.error(error.response?.data?.detail || "Erro ao registrar recebimento");
    }
  };

  const formatarData = (data) => {
    if (!data) return "-";
    // Evita problemas de timezone ao criar data diretamente dos componentes
    const partes = data.split("T")[0].split("-");
    const dataLocal = new Date(parseInt(partes[0]), parseInt(partes[1]) - 1, parseInt(partes[2]));
    return dataLocal.toLocaleDateString("pt-BR");
  };

  const formatarMoeda = (valor) => {
    return formatMoneyCellValue(valor);
  };

  const getStatusBadge = (conta) => {
    const hoje = new Date();
    const vencimento = new Date(conta.data_vencimento);
    if (conta.status === "recebido") return <StatusBadge status="recebido" />;
    if (vencimento < hoje) return <StatusBadge status="vencida" />;
    if (conta.status === "parcial") return <StatusBadge status="parcial" />;
    return <StatusBadge status="pendente" />;
  };

  const contasReceberExibidas = safeArray(contas).filter((conta) => {
    if (!buscaNumeroVenda) return true;

    const numeroVenda = String(conta.numero_venda || "");
    const descricao = String(conta.descricao || "");
    const busca = buscaNumeroVenda.toLowerCase();

    return numeroVenda.toLowerCase().includes(busca) || descricao.toLowerCase().includes(busca);
  });

  const contasReceberColumns = [
    {
      key: "id",
      header: "ID",
      render: (conta) => conta.id,
    },
    {
      key: "descricao",
      header: "Descricao",
      className: "min-w-[220px]",
      render: (conta) => (
        <div>
          {conta.descricao}
          {conta.eh_parcelado && (
            <span className="ml-2 px-2 py-1 text-xs rounded bg-gray-100 text-gray-700">
              {conta.numero_parcela}/{conta.total_parcelas}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "cliente",
      header: "Cliente",
      className: "min-w-[160px]",
      render: (conta) => (
        <CustomerIdentity fallback="" nameClassName="font-medium text-slate-800" record={conta} />
      ),
    },
    {
      key: "vencimento",
      header: "Vencimento",
      render: (conta) => formatarData(conta.data_vencimento),
    },
    {
      key: "valor_original",
      header: "Valor Original",
      align: "right",
      render: (conta) => <MoneyCell value={conta.valor_original} />,
    },
    {
      key: "valor_recebido",
      header: "Valor Recebido",
      align: "right",
      render: (conta) => <MoneyCell value={conta.valor_recebido} zeroAsDash />,
    },
    {
      key: "saldo",
      header: "Saldo",
      align: "right",
      className: "font-bold",
      render: (conta) => <MoneyCell value={conta.valor_final - conta.valor_recebido} zeroAsDash />,
    },
    {
      key: "status",
      header: "Status",
      render: getStatusBadge,
    },
    {
      key: "acoes",
      header: "Acoes",
      className: "min-w-[230px]",
      render: (conta) => (
        <div className="flex flex-wrap items-center gap-2">
          {conta.status !== "recebido" && (
            <>
              {conta.nsu && !conta.conciliado ? (
                <>
                  <ActionButton
                    intent="warning"
                    size="xs"
                    onClick={() => navigate(`/conciliacao-cartao?nsu=${conta.nsu}`)}
                    title={`Conciliar NSU ${conta.nsu} com extrato da operadora`}
                  >
                    Conciliar
                  </ActionButton>
                  <ActionButton
                    intent="create"
                    size="xs"
                    onClick={() => abrirModalRecebimento(conta)}
                    title="Receber manual (caso nao consiga conciliar)"
                  >
                    Manual
                  </ActionButton>
                </>
              ) : conta.venda_id && !conta.nsu ? (
                <>
                  <ActionButton
                    intent="neutral"
                    size="xs"
                    onClick={() => {
                      if (conta.venda_id) {
                        abrirVendaNoPDV(conta.venda_id);
                      } else {
                        abrirModalRecebimento(conta);
                      }
                    }}
                    title="Receber no PDV (movimenta caixa)"
                  >
                    PDV
                  </ActionButton>
                  <ActionButton
                    intent="create"
                    size="xs"
                    onClick={() => abrirModalRecebimento(conta)}
                    title="Receber manual (sem PDV)"
                  >
                    Manual
                  </ActionButton>
                </>
              ) : (
                <ActionButton
                  intent="create"
                  size="xs"
                  onClick={() => abrirModalRecebimento(conta)}
                  title="Registrar recebimento manual"
                >
                  Receber Manual
                </ActionButton>
              )}
            </>
          )}
          {conta.conciliado && (
            <span
              className="text-xs text-green-600 font-semibold"
              title={`Conciliado em ${conta.data_conciliacao}`}
            >
              Conciliado
            </span>
          )}
          <ActionButton
            intent="neutral"
            tone="soft"
            size="xs"
            title="Ver Detalhes"
            onClick={() => abrirDetalhes(conta)}
          >
            Ver
          </ActionButton>
        </div>
      ),
    },
  ];

  const handleFiltrosSubmit = (event) => {
    event.preventDefault();
  };

  if (loading) {
    return <LoadingState label="Carregando contas a receber..." />;
  }

  return (
    <div className="p-6">
      <PageHeader
        actions={
          <>
            <ActionButton
              onClick={alternarOrdenacao}
              intent="neutral"
              tone="soft"
              size="md"
              icon={ArrowDownUp}
              title={
                ordenacao === "desc"
                  ? "Clique para ver mais antigas primeiro"
                  : "Clique para ver mais recentes primeiro"
              }
            >
              {ordenacao === "desc" ? "Mais recentes" : "Mais antigas"}
            </ActionButton>
            <ActionButton intent="create" size="md" icon={Plus}>
              Nova Conta
            </ActionButton>
          </>
        }
        className="mb-6"
        icon={Receipt}
        subtitle="Acompanhe recebimentos, vencimentos e saldos"
        title="Contas a Receber"
      />

      <ContasReceberFilters
        aplicarFiltros={aplicarFiltros}
        buscaNumeroVenda={buscaNumeroVenda}
        clientes={clientes}
        filtros={filtros}
        handleFiltrosSubmit={handleFiltrosSubmit}
        setBuscaNumeroVenda={setBuscaNumeroVenda}
        setFiltros={setFiltros}
      />
      {/* Tabela de Contas */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <DataTable
          columns={contasReceberColumns}
          data={contasReceberExibidas}
          emptyMessage="Nenhuma conta encontrada"
          getRowKey={(conta) => conta.id}
          tableClassName="min-w-[960px]"
          theadClassName="bg-gray-50"
          tbodyClassName="divide-y divide-gray-200"
        />

        {contasReceberExibidas.length > 0 && (
          <div className="bg-green-50 border-t border-green-200 px-4 py-3">
            <strong>Total:</strong> {contasReceberExibidas.length} conta(s) |
            <strong className="ml-3">Saldo a Receber:</strong>{" "}
            <MoneyCell
              value={contasReceberExibidas.reduce(
                (sum, c) => sum + (c.valor_final - c.valor_recebido),
                0,
              )}
              zeroAsDash
            />
          </div>
        )}
      </div>

      <ContasReceberRecebimentoModal
        contaSelecionada={contaSelecionada}
        contasBancarias={contasBancarias}
        dadosRecebimento={dadosRecebimento}
        formasPagamento={formasPagamento}
        formatarMoeda={formatarMoeda}
        mostrarModalRecebimento={mostrarModalRecebimento}
        registrarRecebimento={registrarRecebimento}
        setDadosRecebimento={setDadosRecebimento}
        setMostrarModalRecebimento={setMostrarModalRecebimento}
      />
      <ContasReceberDetalhesModal
        abrirFluxoDeCaixa={abrirFluxoDeCaixa}
        abrirVenda={abrirVenda}
        contaSelecionada={contaSelecionada}
        detalhesCompletos={detalhesCompletos}
        formatarData={formatarData}
        formatarMoeda={formatarMoeda}
        mostrarDetalhes={mostrarDetalhes}
        setMostrarDetalhes={setMostrarDetalhes}
      />
    </div>
  );
};

export default ContasReceber;
