import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import TutorAutocomplete from "../../components/TutorAutocomplete";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputData from "../../components/v2/InputData/InputData";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import {
  FiFilter,
  FiDollarSign,
  FiChevronLeft,
  FiChevronRight,
  FiChevronDown,
  FiChevronUp,
  FiShoppingCart,
  FiPackage,
  FiAlertCircle,
} from "react-icons/fi";
import ProductIdentity from "../../components/ui/ProductIdentity";
import SaleReference from "../../components/ui/SaleReference";
import { DetalhesTransacao } from "../clienteFinanceiro/ClienteFinanceiroView";
import { formatarDataHistorico, obterStatusHistorico } from "../../utils/historicoFinanceiro";
import { formatMoneyBRL } from "../../utils/formatters";

const filtrosIniciais = {
  page: 1,
  per_page: 20,
  data_inicio: "",
  data_fim: "",
  tipo: "",
  status: "",
};
const tonsStatus = {
  sucesso: "bg-green-100 text-green-700",
  atencao: "bg-yellow-100 text-yellow-700",
  perigo: "bg-red-100 text-red-700",
  neutro: "bg-gray-100 text-gray-700",
};

/* -----------------------------------------------------------------------
   Componente interno: histórico do cliente selecionado (sem wrapper de página)
   ----------------------------------------------------------------------- */
export const HistoricoInline = ({ clienteId, clienteInfo }) => {
  const navigate = useNavigate();

  const [resumo, setResumo] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [paginacao, setPaginacao] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [expandedRows, setExpandedRows] = useState({});
  const [detalhesVendas, setDetalhesVendas] = useState({});
  const [loadingDetalhes, setLoadingDetalhes] = useState({});
  const [errosDetalhes, setErrosDetalhes] = useState({});
  const [tentativa, setTentativa] = useState(0);
  const cicloConsulta = useRef(0);

  const [filtros, setFiltros] = useState(filtrosIniciais);

  useEffect(() => {
    let ativo = true;
    cicloConsulta.current += 1;
    setLoading(true);
    setError("");
    setExpandedRows({});
    setDetalhesVendas({});
    setLoadingDetalhes({});
    setErrosDetalhes({});
    const carregarDados = async () => {
      try {
        const params = new URLSearchParams({ page: filtros.page, per_page: filtros.per_page });
        for (const campo of ["data_inicio", "data_fim", "tipo", "status"])
          if (filtros[campo]) params.set(campo, filtros[campo]);
        const response = await api.get(`/financeiro/cliente/${clienteId}?${params.toString()}`);
        if (!ativo) return;
        setResumo(response.data.resumo);
        setHistorico(response.data.historico || []);
        setPaginacao(response.data.paginacao);
      } catch (err) {
        if (ativo) setError(err.response?.data?.detail || "Erro ao carregar histórico financeiro");
      } finally {
        if (ativo) setLoading(false);
      }
    };
    carregarDados();
    return () => {
      ativo = false;
      cicloConsulta.current += 1;
    };
  }, [clienteId, filtros, tentativa]);

  const aplicarFiltros = (novos) => setFiltros((f) => ({ ...f, ...novos, page: 1 }));
  const limparFiltros = () => setFiltros({ ...filtrosIniciais });
  const mudarPagina = (p) => setFiltros((f) => ({ ...f, page: p }));

  const carregarDetalhesVenda = async (vendaId) => {
    const ciclo = cicloConsulta.current;
    setLoadingDetalhes((l) => ({ ...l, [vendaId]: true }));
    setErrosDetalhes((e) => ({ ...e, [vendaId]: "" }));
    try {
      const res = await api.get(`/vendas/${vendaId}`);
      if (ciclo === cicloConsulta.current)
        setDetalhesVendas((d) => ({ ...d, [vendaId]: res.data }));
    } catch {
      if (ciclo === cicloConsulta.current)
        setErrosDetalhes((e) => ({
          ...e,
          [vendaId]: "Não foi possível carregar os itens da venda.",
        }));
    } finally {
      if (ciclo === cicloConsulta.current) setLoadingDetalhes((l) => ({ ...l, [vendaId]: false }));
    }
  };

  const toggleExpansao = async (transacao, index) => {
    const key = `${transacao.tipo}-${index}`;
    if (expandedRows[key]) {
      setExpandedRows((r) => ({ ...r, [key]: false }));
      return;
    }
    setExpandedRows((r) => ({ ...r, [key]: true }));
    if (
      transacao.tipo === "venda" &&
      transacao.detalhes?.venda_id &&
      !detalhesVendas[transacao.detalhes.venda_id] &&
      !loadingDetalhes[transacao.detalhes.venda_id]
    ) {
      await carregarDetalhesVenda(transacao.detalhes.venda_id);
    }
  };

  const getTipoIcon = (tipo) =>
    ({ venda: "🛒", devolucao: "↩️", conta_receber: "📄", recebimento: "💰", credito: "💳" })[
      tipo
    ] || "📊";
  const getTipoLabel = (tipo) =>
    ({
      venda: "Venda",
      devolucao: "Devolução",
      conta_receber: "Conta a Receber",
      recebimento: "Recebimento",
      credito: "Crédito",
    })[tipo] || tipo;

  if (error)
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center mt-4">
        <FiAlertCircle className="text-red-500 text-3xl mx-auto mb-2" />
        <p className="text-red-700 font-medium">{error}</p>
        <BotaoInteracao tamanho="pequeno" onClick={() => setTentativa((t) => t + 1)}>
          Tentar novamente
        </BotaoInteracao>
      </div>
    );

  return (
    <div className="mt-4 space-y-4">
      {/* Info do cliente + crédito */}
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white font-bold text-lg">
            {clienteInfo?.nome?.[0]?.toUpperCase() || "?"}
          </div>
          <div>
            <p className="font-semibold text-gray-900">{clienteInfo?.nome}</p>
            <p className="text-xs text-gray-500">
              Código: {clienteInfo?.codigo || "-"}
              {clienteInfo?.telefone && ` · ${clienteInfo.telefone}`}
            </p>
          </div>
        </div>
        {clienteInfo?.credito_atual != null && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-2 text-right">
            <p className="text-xs text-gray-500">Crédito disponível</p>
            <p className="text-xl font-bold text-purple-600">
              {formatMoneyBRL(clienteInfo.credito_atual)}
            </p>
          </div>
        )}
      </div>

      {/* Cards resumo */}
      {resumo && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            {
              label: "Total Vendas (90d)",
              value: formatMoneyBRL(resumo.total_vendas_90d),
              color: "text-blue-600",
            },
            {
              label: "Total em Aberto",
              value: formatMoneyBRL(resumo.total_em_aberto),
              color: "text-orange-600",
            },
            {
              label: "Última Compra",
              value: resumo.ultima_compra ? formatMoneyBRL(resumo.ultima_compra.valor) : "—",
              color: "text-green-600",
            },
            {
              label: "Total Transações",
              value: resumo.total_transacoes_historico || 0,
              color: "text-purple-600",
            },
          ].map((c) => (
            <div key={c.label} className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">{c.label}</p>
              <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filtros */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <FiFilter /> Filtros
          </span>
          <BotaoInteracao tamanho="pequeno" onClick={limparFiltros}>
            Limpar filtros
          </BotaoInteracao>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <InputData
            label="Data inicial"
            value={filtros.data_inicio}
            onChange={(data_inicio) => aplicarFiltros({ data_inicio })}
          />
          <InputData
            label="Data final"
            value={filtros.data_fim}
            onChange={(data_fim) => aplicarFiltros({ data_fim })}
          />
          <InputCombobox
            label="Tipo"
            value={filtros.tipo}
            onChange={(tipo) => aplicarFiltros({ tipo: tipo || "" })}
            opcoes={[
              { value: "", label: "Todas as transações" },
              { value: "venda", label: "Vendas" },
              { value: "devolucao", label: "Devoluções" },
              { value: "conta_receber", label: "Contas a receber" },
              { value: "recebimento", label: "Recebimentos" },
              { value: "credito", label: "Créditos" },
            ]}
          />
          <InputCombobox
            label="Situação"
            value={filtros.status}
            onChange={(status) => aplicarFiltros({ status: status || "" })}
            opcoes={[
              { value: "", label: "Todas as situações" },
              { value: "recebido", label: "Pago / recebido" },
              { value: "em_aberto", label: "Em aberto" },
              { value: "vencido", label: "Vencido" },
              { value: "parcial", label: "Parcial" },
              { value: "cancelado", label: "Cancelada" },
              { value: "estornado", label: "Estornado" },
            ]}
          />
          <InputCombobox
            label="Por página"
            value={filtros.per_page}
            permitirLimpar={false}
            onChange={(per_page) => aplicarFiltros({ per_page: Number(per_page) || 20 })}
            opcoes={[10, 20, 50].map((value) => ({ value, label: String(value) }))}
          />
        </div>
      </div>

      {/* Tabela */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="text-center py-10">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600 mx-auto mb-3"></div>
            <p className="text-sm text-gray-500">Carregando histórico...</p>
          </div>
        ) : historico.length === 0 ? (
          <div className="text-center py-14">
            <FiDollarSign className="text-gray-300 text-5xl mx-auto mb-3" />
            <p className="text-gray-600 font-medium">Nenhuma transação encontrada</p>
            {(filtros.tipo || filtros.status || filtros.data_inicio || filtros.data_fim) && (
              <BotaoInteracao onClick={limparFiltros} tamanho="pequeno">
                Limpar filtros
              </BotaoInteracao>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-3 w-10"></th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Data
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Tipo
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Descrição
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                      Valor
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Status
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      Ações
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {historico.map((transacao, index) => {
                    const key = `${transacao.tipo}-${index}`;
                    const isExpanded = expandedRows[key];
                    const vendaId = transacao.detalhes?.venda_id;
                    const detalhes = vendaId ? detalhesVendas[vendaId] : null;
                    const situacao = obterStatusHistorico(transacao);
                    return (
                      <React.Fragment key={key}>
                        <tr className="hover:bg-gray-50 transition-colors">
                          <td className="px-3 py-4 text-center">
                            <BotaoInteracao
                              onClick={() => toggleExpansao(transacao, index)}
                              icon={isExpanded ? FiChevronUp : FiChevronDown}
                              aria-label={isExpanded ? "Recolher detalhes" : "Ver detalhes"}
                              aria-expanded={!!isExpanded}
                              tamanho="pequeno"
                            />
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 whitespace-nowrap">
                            {formatarDataHistorico(transacao.data)}
                          </td>
                          <td className="px-4 py-4 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1 text-sm font-medium">
                              <span className="text-lg">{getTipoIcon(transacao.tipo)}</span>
                              {getTipoLabel(transacao.tipo)}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-sm text-gray-900 max-w-xs">
                            <div className="truncate">{transacao.descricao}</div>
                            {transacao.detalhes?.numero_venda && (
                              <div className="mt-0.5 text-xs text-blue-600">
                                <SaleReference
                                  showPrefix={false}
                                  value={transacao.detalhes.numero_venda}
                                />
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-4 text-sm text-right whitespace-nowrap">
                            <span
                              className={`font-bold ${transacao.valor < 0 ? "text-red-600" : "text-green-600"}`}
                            >
                              {transacao.valor < 0 ? "- " : "+ "}
                              {formatMoneyBRL(Math.abs(transacao.valor))}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-center whitespace-nowrap">
                            <span
                              className={`px-2 py-1 text-xs font-semibold rounded-full ${tonsStatus[situacao.tom]}`}
                            >
                              {situacao.label}
                            </span>
                          </td>
                          <td className="px-4 py-4 text-center whitespace-nowrap">
                            {transacao.tipo === "venda" && vendaId && (
                              <BotaoInteracao
                                onClick={() => navigate(`/pdv?venda=${vendaId}`)}
                                icon={FiShoppingCart}
                                tamanho="pequeno"
                              >
                                Ver no PDV
                              </BotaoInteracao>
                            )}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr>
                            <td colSpan="7" className="px-4 py-4 bg-gray-50">
                              <DetalhesTransacao transacao={transacao} />
                              {transacao.tipo === "venda" && vendaId ? (
                                loadingDetalhes[vendaId] ? (
                                  <div className="text-center py-3 text-sm text-gray-500">
                                    Carregando detalhes...
                                  </div>
                                ) : detalhes ? (
                                  <div className="space-y-3">
                                    {detalhes.itens?.length > 0 && (
                                      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                        <div className="bg-blue-50 px-4 py-2 border-b border-gray-200 flex items-center gap-2">
                                          <FiPackage className="text-blue-600" />
                                          <span className="font-semibold text-sm text-gray-800">
                                            Produtos
                                          </span>
                                        </div>
                                        <table className="min-w-full divide-y divide-gray-200">
                                          <thead className="bg-gray-50">
                                            <tr>
                                              {[
                                                "Produto",
                                                "Qtd",
                                                "Preço Unit.",
                                                "Desc.",
                                                "Subtotal",
                                              ].map((h) => (
                                                <th
                                                  key={h}
                                                  className="px-4 py-2 text-xs font-medium text-gray-500 text-left"
                                                >
                                                  {h}
                                                </th>
                                              ))}
                                            </tr>
                                          </thead>
                                          <tbody className="divide-y divide-gray-200">
                                            {detalhes.itens.map((item, i) => (
                                              <tr key={i} className="hover:bg-gray-50">
                                                <td className="px-4 py-2 text-sm text-gray-900">
                                                  <ProductIdentity product={item} />
                                                </td>
                                                <td className="px-4 py-2 text-sm text-center font-semibold">
                                                  {item.quantidade}
                                                </td>
                                                <td className="px-4 py-2 text-sm text-right">
                                                  {formatMoneyBRL(item.preco_unitario)}
                                                </td>
                                                <td className="px-4 py-2 text-sm text-right text-orange-600">
                                                  {formatMoneyBRL(item.desconto)}
                                                </td>
                                                <td className="px-4 py-2 text-sm text-right font-bold text-green-600">
                                                  {formatMoneyBRL(item.subtotal)}
                                                </td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    )}
                                  </div>
                                ) : (
                                  <div
                                    role="alert"
                                    className="text-sm text-gray-600 text-center py-2"
                                  >
                                    <p>
                                      {errosDetalhes[vendaId] ||
                                        "Não foi possível carregar os itens da venda."}
                                    </p>
                                    <BotaoInteracao
                                      tamanho="pequeno"
                                      onClick={() => carregarDetalhesVenda(vendaId)}
                                    >
                                      Tentar novamente os itens
                                    </BotaoInteracao>
                                  </div>
                                )
                              ) : null}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {paginacao && paginacao.total_paginas > 1 && (
              <div className="bg-gray-50 px-5 py-3 border-t border-gray-200 flex items-center justify-between">
                <span className="text-sm text-gray-600">
                  {(paginacao.pagina_atual - 1) * paginacao.itens_por_pagina + 1}–
                  {Math.min(
                    paginacao.pagina_atual * paginacao.itens_por_pagina,
                    paginacao.total_itens,
                  )}{" "}
                  de {paginacao.total_itens}
                </span>
                <div className="flex items-center gap-2">
                  <BotaoInteracao
                    onClick={() => mudarPagina(paginacao.pagina_atual - 1)}
                    disabled={!paginacao.tem_anterior}
                    icon={FiChevronLeft}
                    tamanho="pequeno"
                  >
                    Anterior
                  </BotaoInteracao>
                  <span className="text-sm text-gray-600">
                    Pág. {paginacao.pagina_atual}/{paginacao.total_paginas}
                  </span>
                  <BotaoInteracao
                    onClick={() => mudarPagina(paginacao.pagina_atual + 1)}
                    disabled={!paginacao.tem_proxima}
                    icon={FiChevronRight}
                    tamanho="pequeno"
                  >
                    Próxima
                  </BotaoInteracao>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

/* -----------------------------------------------------------------------
   Componente principal: busca de cliente + histórico inline
   ----------------------------------------------------------------------- */
const HistoricoVendasClienteTab = () => {
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  return (
    <div className="p-6">
      <div className="mb-5">
        <h2 className="text-xl font-bold text-gray-800">Histórico de Vendas por Cliente</h2>
        <p className="mt-1 text-sm text-gray-500">
          Pesquise pelo código, nome, documento ou telefone.
        </p>
      </div>
      <div className="max-w-xl space-y-2">
        <TutorAutocomplete
          label="Cliente"
          inputId="historico-financeiro-cliente"
          selectedTutor={clienteSelecionado}
          onSelect={setClienteSelecionado}
        />
        {clienteSelecionado && (
          <BotaoCancelar tamanho="pequeno" onClick={() => setClienteSelecionado(null)}>
            Limpar cliente
          </BotaoCancelar>
        )}
      </div>
      {!clienteSelecionado && (
        <p className="mt-12 text-center text-gray-500">
          Selecione um cliente acima para consultar seu histórico financeiro.
        </p>
      )}
      {clienteSelecionado && (
        <HistoricoInline
          key={clienteSelecionado.id}
          clienteId={clienteSelecionado.id}
          clienteInfo={clienteSelecionado}
        />
      )}
    </div>
  );
};

export default HistoricoVendasClienteTab;
