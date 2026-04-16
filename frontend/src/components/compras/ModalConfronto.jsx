import React, { useState, useEffect } from 'react';
import api from '../../api';
import { toast } from 'react-hot-toast';
import { formatMoneyBRL } from '../../utils/formatters';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const STATUS_LABELS = {
  ok: { label: 'OK', cls: 'bg-green-100 text-green-800' },
  divergencia_quantidade: { label: 'Dif. Qtd', cls: 'bg-yellow-100 text-yellow-800' },
  divergencia_preco: { label: 'Dif. Preço', cls: 'bg-yellow-100 text-yellow-800' },
  divergencia_mista: { label: 'Dif. Mista', cls: 'bg-red-100 text-red-800' },
  nao_encontrado: { label: 'Não Recebido', cls: 'bg-red-100 text-red-800' },
  nao_pedido: { label: 'Não Pedido', cls: 'bg-purple-100 text-purple-800' },
};

const CONFRONTO_LABELS = {
  sem_divergencia: { label: '✅ Sem divergências', cls: 'bg-green-100 text-green-800 border-green-300' },
  divergencia_quantidade: { label: '⚠️ Divergência de quantidade', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  divergencia_preco: { label: '⚠️ Divergência de preço', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
  divergencia_mista: { label: '🔴 Divergência de quantidade e preço', cls: 'bg-red-100 text-red-800 border-red-300' },
};

function fmt(v, decimals = 2) {
  const n = Number(v || 0);
  return n.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function fmtMoeda(v) { return `R$ ${fmt(v)}`; }
function fmtSinal(v, decimals = 2) { const n = Number(v || 0); return (n >= 0 ? '+' : '') + fmt(n, decimals); }

// ─────────────────────────────────────────────────────────────────────────────
// Modal principal
// ─────────────────────────────────────────────────────────────────────────────

const ModalConfronto = ({ pedido, onClose, onPedidoComplementarCriado }) => {
  const [etapa, setEtapa] = useState('selecionar'); // 'selecionar' | 'confronto'
  const [notas, setNotas] = useState([]);
  const [notaVinculadaId, setNotaVinculadaId] = useState(null);
  const [loadingNotas, setLoadingNotas] = useState(true);
  const [loadingConfronto, setLoadingConfronto] = useState(false);
  const [confronto, setConfronto] = useState(null);
  const [notaSelecionada, setNotaSelecionada] = useState(null);
  const [loadingAcao, setLoadingAcao] = useState(false);
  const [emailTexto, setEmailTexto] = useState(null);
  const [mostrarEmail, setMostrarEmail] = useState(false);
  const [pedidoComplementarInfo, setPedidoComplementarInfo] = useState(null);
  const [confrontoFinalizado, setConfrontoFinalizado] = useState(false);
  const [loadingFinalizar, setLoadingFinalizar] = useState(false);

  const ALL_STATUS = ['ok', 'divergencia_quantidade', 'divergencia_preco', 'divergencia_mista', 'nao_encontrado', 'nao_pedido'];
  const [filtrosSelecionados, setFiltrosSelecionados] = useState(new Set(ALL_STATUS));

  useEffect(() => {
    carregarNotas();
  }, []);

  const carregarNotas = async () => {
    try {
      setLoadingNotas(true);
      const res = await api.get(`/pedidos-compra/${pedido.id}/notas-candidatas`);
      setNotas(res.data.notas || []);
      setNotaVinculadaId(res.data.nota_vinculada_id);

      // Se já tem NF vinculada, ir direto pro confronto
      if (res.data.nota_vinculada_id) {
        await carregarConfrontoSalvo();
        setEtapa('confronto');
      }
    } catch {
      toast.error('Erro ao carregar notas fiscais');
    } finally {
      setLoadingNotas(false);
    }
  };

  const carregarConfrontoSalvo = async () => {
    try {
      const res = await api.get(`/pedidos-compra/${pedido.id}/confronto`);
      setConfronto(res.data.confronto);
      setNotaVinculadaId(res.data.nota_entrada_id);
      if (res.data.confronto_finalizado) setConfrontoFinalizado(true);
    } catch {
      // sem confronto salvo ainda
    }
  };

  const selecionarNota = async (nota) => {
    setNotaSelecionada(nota);
    setLoadingConfronto(true);
    try {
      const res = await api.post(`/pedidos-compra/${pedido.id}/vincular-nota/${nota.id}`);
      setConfronto(res.data.confronto);
      setNotaVinculadaId(nota.id);
      setEtapa('confronto');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao realizar confronto');
    } finally {
      setLoadingConfronto(false);
    }
  };

  const filtrosParam = [...filtrosSelecionados].join(',');

  const toggleFiltro = (status) => {
    setFiltrosSelecionados(prev => {
      const next = new Set(prev);
      if (next.has(status)) { next.delete(status); } else { next.add(status); }
      return next;
    });
  };

  const finalizarConfronto = async () => {
    if (!window.confirm('Finalizar a conferência? Isso cria um vínculo permanente entre este pedido e a NF. Não será possível revincular depois.')) return;
    setLoadingFinalizar(true);
    try {
      await api.post(`/pedidos-compra/${pedido.id}/finalizar-confronto`);
      setConfrontoFinalizado(true);
      toast.success('Conferência finalizada! Vínculo permanente criado.');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao finalizar confronto');
    } finally {
      setLoadingFinalizar(false);
    }
  };

  const baixarCSV = async () => {
    try {
      const res = await api.get(`/pedidos-compra/${pedido.id}/confronto/csv?filtros=${filtrosParam}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `confronto_${pedido.numero_pedido}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Erro ao baixar CSV');
    }
  };

  const baixarPDF = async () => {
    try {
      const res = await api.get(`/pedidos-compra/${pedido.id}/confronto/pdf?filtros=${filtrosParam}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `confronto_${pedido.numero_pedido}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error('Erro ao gerar PDF');
    }
  };

  const gerarEmail = async () => {
    try {
      const res = await api.get(`/pedidos-compra/${pedido.id}/confronto/email-texto?filtros=${filtrosParam}`);
      setEmailTexto(res.data.texto);
      setMostrarEmail(true);
    } catch {
      toast.error('Erro ao gerar texto do e-mail');
    }
  };

  const criarPedidoComplementar = async () => {
    setLoadingAcao(true);
    try {
      const res = await api.post(`/pedidos-compra/${pedido.id}/sugerir-pedido-complementar`);
      setPedidoComplementarInfo(res.data);
      toast.success(`Pedido complementar ${res.data.numero_pedido} criado em rascunho!`);
      if (onPedidoComplementarCriado) onPedidoComplementarCriado();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Erro ao criar pedido complementar');
    } finally {
      setLoadingAcao(false);
    }
  };

  const temFaltantes = confronto?.itens?.some(
    i => ['nao_encontrado', 'divergencia_quantidade'].includes(i.status) && (i.dif_qtd || 0) < 0
  );

  const temDivergencia = confronto && confronto.status_confronto !== 'sem_divergencia';

  // ── Etapa 1: selecionar NF ──────────────────────────────────────────────────
  if (etapa === 'selecionar') {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
          <div className="p-5 border-b flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-900">🔍 Selecionar Nota Fiscal</h2>
              <p className="text-sm text-gray-500 mt-0.5">Pedido {pedido.numero_pedido} — escolha a NF para confronto</p>
            </div>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-2xl leading-none">&times;</button>
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            {loadingNotas ? (
              <div className="text-center py-12 text-gray-500">Carregando notas fiscais...</div>
            ) : notas.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-4xl mb-3">📭</div>
                <p className="text-gray-600 font-medium">Nenhuma NF importada para este fornecedor</p>
                <p className="text-sm text-gray-500 mt-1">Importe o XML na <b>Central NF Entradas</b> e volte aqui</p>
              </div>
            ) : (
              <div className="space-y-2">
                {notas.map(nota => (
                  <button
                    key={nota.id}
                    onClick={() => selecionarNota(nota)}
                    disabled={loadingConfronto}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-all hover:shadow-md ${
                      nota.ja_vinculada
                        ? 'border-blue-400 bg-blue-50'
                        : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/30'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-semibold text-gray-900">NF {nota.numero_nota}</span>
                        <span className="text-gray-500 text-sm ml-2">Série {nota.serie}</span>
                        {nota.ja_vinculada && (
                          <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-semibold">Já vinculada</span>
                        )}
                      </div>
                      <span className="font-bold text-green-700">{fmtMoeda(nota.valor_total)}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {nota.fornecedor_nome} · {nota.data_emissao ? new Date(nota.data_emissao).toLocaleDateString('pt-BR') : ''}
                    </div>
                  </button>
                ))}
              </div>
            )}
            {loadingConfronto && (
              <div className="text-center py-6 text-blue-600 font-medium animate-pulse">Realizando confronto...</div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── Etapa 2: confronto ─────────────────────────────────────────────────────
  const statusInfo = CONFRONTO_LABELS[confronto?.status_confronto] || CONFRONTO_LABELS.sem_divergencia;
  const resumo = confronto?.resumo || {};
  const itens = confronto?.itens || [];

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[95vh] flex flex-col">

        {/* Header */}
        <div className="p-5 border-b flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-bold text-gray-900">📊 Confronto Pedido x NF</h2>
              {confrontoFinalizado && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-100 text-green-800 text-xs font-bold rounded-full border border-green-300">
                  🔒 Conferência Finalizada
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-0.5">
              Pedido <b>{pedido.numero_pedido}</b> · Nota Fiscal vinculada
              {!confrontoFinalizado && (
                <button
                  onClick={() => setEtapa('selecionar')}
                  className="ml-2 text-blue-600 hover:underline text-xs"
                >trocar NF</button>
              )}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-2xl leading-none">&times;</button>
        </div>

        {/* Status badge + ações */}
        <div className="px-5 py-3 border-b flex items-center justify-between flex-wrap gap-2">
          <span className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${statusInfo.cls}`}>
            {statusInfo.label}
          </span>
          <div className="flex items-center gap-2 flex-wrap">
            {!confrontoFinalizado && (
              <button
                onClick={finalizarConfronto}
                disabled={loadingFinalizar}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-700 text-white text-sm rounded-lg hover:bg-emerald-800 disabled:opacity-50 font-semibold"
              >
                🔒 Finalizar Conferência
              </button>
            )}
            <button
              onClick={baixarCSV}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700"
            >
              📊 CSV
            </button>
            <button
              onClick={baixarPDF}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700"
            >
              📄 PDF
            </button>
            {temDivergencia && (
              <button
                onClick={gerarEmail}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
              >
                ✉️ Gerar E-mail Fornecedor
              </button>
            )}
            {temFaltantes && !pedidoComplementarInfo && (
              <button
                onClick={criarPedidoComplementar}
                disabled={loadingAcao}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 text-white text-sm rounded-lg hover:bg-violet-700 disabled:opacity-50"
              >
                🔄 Criar Pedido Complementar
              </button>
            )}
            {pedidoComplementarInfo && (
              <span className="text-sm text-green-700 font-semibold bg-green-50 border border-green-200 px-3 py-1.5 rounded-lg">
                ✅ Pedido {pedidoComplementarInfo.numero_pedido} criado em rascunho
              </span>
            )}
          </div>
        </div>

        {/* Resumo financeiro */}
        <div className="px-5 py-3 bg-gray-50 border-b grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-gray-500 text-xs font-medium uppercase tracking-wide">Total Pedido</div>
            <div className="font-bold text-gray-900 mt-0.5">{fmtMoeda(resumo.total_pedido)}</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs font-medium uppercase tracking-wide">Total NF</div>
            <div className="font-bold text-gray-900 mt-0.5">{fmtMoeda(resumo.total_nf)}</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs font-medium uppercase tracking-wide">Diferença</div>
            <div className={`font-bold mt-0.5 ${(resumo.dif_total || 0) > 0 ? 'text-red-600' : (resumo.dif_total || 0) < 0 ? 'text-yellow-600' : 'text-green-600'}`}>
              {fmtSinal(resumo.dif_total)} R$
            </div>
          </div>
          <div>
            <div className="text-gray-500 text-xs font-medium uppercase tracking-wide">Frete NF</div>
            <div className="font-bold text-gray-900 mt-0.5">{fmtMoeda(resumo.frete_nf)}</div>
          </div>
        </div>

        {/* Filtros de status */}
        <div className="px-5 py-2 border-b bg-gray-50 flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filtrar:</span>
          {[
            { key: 'ok', label: '✅ OK', cls: 'bg-green-100 text-green-800 border-green-300' },
            { key: 'divergencia_quantidade', label: '⚠️ Dif. Qtd', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
            { key: 'divergencia_preco', label: '⚠️ Dif. Preço', cls: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
            { key: 'divergencia_mista', label: '🔴 Dif. Mista', cls: 'bg-red-100 text-red-800 border-red-300' },
            { key: 'nao_encontrado', label: '🔴 Não Recebido', cls: 'bg-red-100 text-red-800 border-red-300' },
            { key: 'nao_pedido', label: '🟣 Não Pedido', cls: 'bg-purple-100 text-purple-800 border-purple-300' },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => toggleFiltro(f.key)}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition-all ${
                filtrosSelecionados.has(f.key)
                  ? f.cls
                  : 'bg-gray-100 text-gray-400 border-gray-200 line-through opacity-60'
              }`}
            >
              {f.label}
            </button>
          ))}
          <span className="text-xs text-gray-400 ml-1">
            ({itens.filter(i => filtrosSelecionados.has(i.status)).length} de {itens.length} itens)
          </span>
        </div>

        {/* Tabela de itens */}
        <div className="flex-1 overflow-auto p-5">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-100 text-gray-600 text-xs uppercase tracking-wide">
                <th className="px-3 py-2 text-left">Produto</th>
                <th className="px-3 py-2 text-center">Qtd Pedida</th>
                <th className="px-3 py-2 text-center">Qtd NF</th>
                <th className="px-3 py-2 text-center">Dif. Qtd</th>
                <th className="px-3 py-2 text-right">R$ Pedido</th>
                <th className="px-3 py-2 text-right">R$ NF</th>
                <th className="px-3 py-2 text-center">Dif. %</th>
                <th className="px-3 py-2 text-right">Vl. Pedido</th>
                <th className="px-3 py-2 text-right">Vl. NF</th>
                <th className="px-3 py-2 text-right">Dif. R$</th>
                <th className="px-3 py-2 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {itens.filter(it => filtrosSelecionados.has(it.status)).map((it, idx) => {
                const st = STATUS_LABELS[it.status] || { label: it.status, cls: 'bg-gray-100 text-gray-700' };
                const rowBg = it.status === 'ok' ? '' :
                  ['nao_encontrado', 'divergencia_mista'].includes(it.status) ? 'bg-red-50' :
                  it.status === 'nao_pedido' ? 'bg-purple-50' : 'bg-yellow-50';
                return (
                  <tr key={idx} className={`${rowBg} hover:brightness-95`}>
                    <td className="px-3 py-2">
                      <div className="font-medium text-gray-900">{it.produto_nome}</div>
                      {it.produto_codigo && <div className="text-xs text-gray-400">{it.produto_codigo}</div>}
                    </td>
                    <td className="px-3 py-2 text-center">{fmt(it.qtd_pedida, 0)}</td>
                    <td className="px-3 py-2 text-center">{it.encontrado_na_nf ? fmt(it.qtd_nf, 0) : <span className="text-gray-400">—</span>}</td>
                    <td className={`px-3 py-2 text-center font-semibold ${it.dif_qtd < 0 ? 'text-red-600' : it.dif_qtd > 0 ? 'text-blue-600' : 'text-green-600'}`}>
                      {it.dif_qtd === 0 ? '—' : fmtSinal(it.dif_qtd, 0)}
                    </td>
                    <td className="px-3 py-2 text-right">{fmtMoeda(it.preco_pedido)}</td>
                    <td className="px-3 py-2 text-right">{it.encontrado_na_nf ? fmtMoeda(it.preco_nf) : <span className="text-gray-400">—</span>}</td>
                    <td className={`px-3 py-2 text-center font-semibold ${it.dif_preco_pct > 0.5 ? 'text-red-600' : it.dif_preco_pct < -0.5 ? 'text-green-600' : 'text-gray-400'}`}>
                      {Math.abs(it.dif_preco_pct) < 0.5 ? '—' : `${it.dif_preco_pct > 0 ? '+' : ''}${fmt(it.dif_preco_pct, 1)}%`}
                    </td>
                    <td className="px-3 py-2 text-right">{fmtMoeda(it.valor_pedido)}</td>
                    <td className="px-3 py-2 text-right">{it.encontrado_na_nf ? fmtMoeda(it.valor_nf) : <span className="text-gray-400">—</span>}</td>
                    <td className={`px-3 py-2 text-right font-semibold ${it.dif_valor > 0 ? 'text-red-600' : it.dif_valor < 0 ? 'text-yellow-600' : 'text-gray-400'}`}>
                      {it.dif_valor === 0 ? '—' : `${it.dif_valor > 0 ? '+' : ''}${fmtMoeda(it.dif_valor)}`}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${st.cls}`}>{st.label}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de e-mail */}
      {mostrarEmail && emailTexto && (
        <div className="fixed inset-0 bg-black/60 z-60 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-bold text-gray-900">✉️ Texto para E-mail ao Fornecedor</h3>
              <button onClick={() => setMostrarEmail(false)} className="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <textarea
                className="w-full h-72 p-3 border border-gray-300 rounded-lg text-sm font-mono resize-none focus:ring-2 focus:ring-blue-500"
                value={emailTexto}
                onChange={e => setEmailTexto(e.target.value)}
              />
            </div>
            <div className="p-4 border-t flex gap-2 justify-end">
              <button
                onClick={() => { navigator.clipboard.writeText(emailTexto); toast.success('Copiado!'); }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
              >
                📋 Copiar Texto
              </button>
              <button
                onClick={() => setMostrarEmail(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModalConfronto;
