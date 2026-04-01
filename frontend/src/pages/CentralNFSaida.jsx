import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  FileOutput,
  FileText,
  Download,
  X,
  CheckCircle,
  AlertCircle,
  Calendar,
  Search,
  Filter,
  Eye,
  Printer,
  XCircle,
  Trash2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Zap,
} from 'lucide-react';
import api from '../api';
import { formatMoneyBRL } from '../utils/formatters';

// ─── helpers ────────────────────────────────────────────────────────────────

function formatarChave(valor) {
  return valor.replaceAll(/\D/g, '').slice(0, 44);
}

function tratarColagemChave(event, setChave) {
  event.preventDefault();
  const texto = event.clipboardData?.getData('text') || '';
  setChave(formatarChave(texto));
}

function formatarDataHora(valor) {
  if (!valor) return '-';
  const d = new Date(valor);
  if (Number.isNaN(d.getTime())) return '-';
  return d.toLocaleString('pt-BR');
}

function soDigitos(v) {
  return String(v || '').replaceAll(/\D/g, '');
}

function getSituacaoCor(status) {
  switch (status?.toLowerCase()) {
    case 'autorizada':
    case 'emitida danfe':
      return 'bg-green-100 text-green-800';
    case 'cancelada':
      return 'bg-red-100 text-red-800';
    case 'pendente':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

function getSituacaoIcone(status) {
  switch (status?.toLowerCase()) {
    case 'autorizada':
    case 'emitida danfe':
      return <CheckCircle className="w-4 h-4" />;
    case 'cancelada':
      return <X className="w-4 h-4" />;
    case 'pendente':
      return <AlertCircle className="w-4 h-4" />;
    default:
      return <FileText className="w-4 h-4" />;
  }
}

function formatarDataBR(valor) {
  if (!valor) return '-';
  if (typeof valor === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(valor)) {
    const [ano, mes, dia] = valor.split('-');
    return `${dia}/${mes}/${ano}`;
  }
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return valor;
  return data.toLocaleDateString('pt-BR');
}

function formatarValorDetalhe(valor) {
  if (valor === 0) return '0';
  if (valor === false) return 'Nao';
  if (valor === true) return 'Sim';
  if (!valor) return '-';
  if (Array.isArray(valor)) {
    const partes = valor.map((item) => formatarValorDetalhe(item)).filter((item) => item && item !== '-');
    return partes.length ? partes.join(', ') : '-';
  }
  if (typeof valor === 'object') {
    return (
      valor.nome ||
      valor.descricao ||
      valor.label ||
      valor.endereco ||
      valor.logradouro ||
      valor.identificacao ||
      '-'
    );
  }
  return String(valor);
}

function valorBooleanoLabel(valor) {
  if (valor === true) return 'Sim';
  if (valor === false) return 'Nao';
  return '-';
}

function montarDetalheFallback(nota) {
  return {
    id: nota.id,
    numero: nota.numero,
    serie: nota.serie,
    modelo: nota.modelo,
    tipo: nota.tipo,
    tipo_label: nota.tipo === 'nfce' ? 'NFC-e' : 'NF-e',
    chave: nota.chave,
    status: nota.status,
    data_emissao: nota.data_emissao,
    cliente: {
      nome: nota.cliente?.nome,
      cpf_cnpj: nota.cliente?.cpf_cnpj,
    },
    totais: {
      valor_total: nota.valor,
    },
    canal: nota.canal,
    canal_label: nota.canal_label,
    loja: nota.loja,
    unidade_negocio: nota.unidade_negocio,
    informacoes_adicionais: {
      numero_pedido_loja: nota.numero_pedido_loja,
      numero_loja_virtual: nota.numero_loja_virtual,
      origem_loja_virtual: nota.origem_loja_virtual,
      origem_canal_venda: nota.origem_canal_venda,
    },
    itens: [],
    pagamento: { parcelas: [] },
    transporte: {},
    endereco_entrega: {},
    intermediador: {},
  };
}

function CampoDetalhe({ label, value, mono = false, destaque = false }) {
  return (
    <div>
      <label className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</label>
      <p className={`mt-1 ${mono ? 'font-mono text-xs break-all' : 'text-sm'} ${destaque ? 'text-lg font-bold text-gray-900' : 'text-gray-900'}`}>
        {formatarValorDetalhe(value)}
      </p>
    </div>
  );
}

function SecaoDetalhe({ titulo, children }) {
  return (
    <section className="rounded-xl border border-gray-200 bg-gray-50/60 p-4 space-y-4">
      <h4 className="text-sm font-bold text-gray-800 uppercase tracking-wide">{titulo}</h4>
      {children}
    </section>
  );
}

// ─── componente principal ───────────────────────────────────────────────────

export default function CentralNFSaida() {

  // ── listagem Bling ───────────────────────────────────────────────────────
  const [notas, setNotas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroSituacao, setFiltroSituacao] = useState('');
  const [dataInicial, setDataInicial] = useState('');
  const [dataFinal, setDataFinal] = useState('');
  const [busca, setBusca] = useState('');
  const [erro, setErro] = useState('');
  const [notaSelecionada, setNotaSelecionada] = useState(null);
  const [detalheNota, setDetalheNota] = useState(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);
  const [erroDetalhe, setErroDetalhe] = useState('');
  const [modalCancelar, setModalCancelar] = useState(null);
  const [justificativa, setJustificativa] = useState('');
  const [cancelando, setCancelando] = useState(false);
  const [reconciliandoNotaId, setReconciliandoNotaId] = useState('');
  const detalhesNotasCacheRef = useRef(new Map());

  const SITUACOES = [
    { value: '', label: 'Todas' },
    { value: 'Autorizada', label: 'Autorizada' },
    { value: 'Emitida DANFE', label: 'Emitida DANFE' },
    { value: 'Cancelada', label: 'Cancelada' },
    { value: 'Pendente', label: 'Pendente' },
  ];

  // ── painel SEFAZ ─────────────────────────────────────────────────────────
  const [painelSefazAberto, setPainelSefazAberto] = useState(false);
  const [chave, setChave] = useState('');
  const [consultando, setConsultando] = useState(false);
  const [erroConsulta, setErroConsulta] = useState('');
  const [consultasSessao, setConsultasSessao] = useState([]);
  const [consultaExpandidaId, setConsultaExpandidaId] = useState(null);
  const listaConsultasRef = useRef(null);

  // ── config rotina automática ──────────────────────────────────────────────
  const [cfgLoading, setCfgLoading] = useState(true);
  const [salvandoRotina, setSalvandoRotina] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [msgRotina, setMsgRotina] = useState('');
  const [cfg, setCfg] = useState({
    enabled: false,
    modo: 'mock',
    importacao_automatica: false,
    importacao_intervalo_min: 15,
    cert_ok: false,
    ultimo_sync_status: 'nunca',
    ultimo_sync_mensagem: 'Ainda não sincronizado.',
    ultimo_sync_at: null,
    ultimo_sync_documentos: 0,
  });

  // ─────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    carregarNotas(false);
  }, [filtroSituacao, dataInicial, dataFinal]);

  useEffect(() => {
    if (painelSefazAberto && cfgLoading) {
      carregarConfigSefaz();
    }
  }, [painelSefazAberto]);

  useEffect(() => {
    if (!consultasSessao.length || !listaConsultasRef.current) return;
    listaConsultasRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [consultasSessao.length]);

  // ── Bling ─────────────────────────────────────────────────────────────────

  async function carregarNotas(forceRefresh = false) {
    try {
      setLoading(true);
      setErro('');
      if (forceRefresh) {
        detalhesNotasCacheRef.current.clear();
      }
      const params = new URLSearchParams();
      if (filtroSituacao) params.append('situacao', filtroSituacao);
      if (dataInicial) params.append('data_inicial', dataInicial);
      if (dataFinal) params.append('data_final', dataFinal);
      if (forceRefresh) params.append('force_refresh', 'true');
      const response = await api.get(`/nfe/?${params.toString()}`);
      setNotas(response.data.notas || []);
    } catch (error) {
      setErro('Erro ao carregar notas fiscais');
    } finally {
      setLoading(false);
    }
  }

  async function baixarDanfe(nfeId, numero) {
    try {
      const response = await api.get(`/nfe/${nfeId}/danfe`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `danfe_${numero}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Erro ao baixar DANFE');
    }
  }

  async function baixarXml(nfeId, numero) {
    try {
      const response = await api.get(`/nfe/${nfeId}/xml`);
      const blob = new Blob([response.data.xml], { type: 'application/xml' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `nfe_${numero}.xml`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Erro ao baixar XML');
    }
  }

  async function reconciliarFluxoNota(nota) {
    const notaId = String(nota?.id || '').trim();
    if (!notaId) {
      alert('Nao foi possivel identificar esta NF para reconciliar.');
      return;
    }

    try {
      setReconciliandoNotaId(notaId);
      const response = await api.post(`/nfe/${notaId}/reconciliar-fluxo`);
      const numero = response.data?.nf_numero || nota.numero || notaId;
      alert(`Fluxo da NF ${numero} reconciliado com sucesso.`);
      await carregarNotas(true);
    } catch (error) {
      const detail = typeof error.response?.data?.detail === 'string'
        ? error.response.data.detail
        : error.response?.data?.detail?.motivo || 'Erro ao reconciliar o fluxo desta NF.';
      alert(detail);
    } finally {
      setReconciliandoNotaId('');
    }
  }

  async function abrirDetalhes(nota) {
    setNotaSelecionada(nota);
    setDetalheNota(montarDetalheFallback(nota));
    setErroDetalhe('');
    try {
      setCarregandoDetalhe(true);
      const cacheKey = `${nota.id}:${nota.modelo || ''}`;
      const detalheCache = detalhesNotasCacheRef.current.get(cacheKey);
      if (detalheCache) {
        setDetalheNota(detalheCache);
        return;
      }
      const response = await api.get(`/nfe/${nota.id}`, {
        params: { modelo: nota.modelo },
      });
      detalhesNotasCacheRef.current.set(cacheKey, response.data);
      setDetalheNota(response.data);
    } catch (error) {
      setErroDetalhe(error.response?.data?.detail || 'Nao foi possivel carregar todos os detalhes desta nota.');
    } finally {
      setCarregandoDetalhe(false);
    }
  }

  function fecharDetalhes() {
    setNotaSelecionada(null);
    setDetalheNota(null);
    setErroDetalhe('');
    setCarregandoDetalhe(false);
  }

  async function cancelarNota() {
    if (!justificativa || justificativa.length < 15) {
      alert('A justificativa deve ter no mínimo 15 caracteres');
      return;
    }
    try {
      setCancelando(true);
      await api.post(`/nfe/${modalCancelar.id}/cancelar`, { justificativa });
      alert('Nota fiscal cancelada com sucesso!');
      setModalCancelar(null);
      setJustificativa('');
      carregarNotas(true);
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao cancelar nota fiscal');
    } finally {
      setCancelando(false);
    }
  }

  async function excluirNota(venda_id, numero) {
    if (!globalThis.confirm(`Deseja realmente excluir a nota ${numero}?\n\nIsso apenas remove os dados da nota do sistema, não cancela no Bling/SEFAZ.`)) return;
    try {
      await api.delete(`/nfe/${venda_id}`);
      alert('Nota fiscal excluída com sucesso!');
      carregarNotas(true);
    } catch (error) {
      alert(error.response?.data?.detail || 'Erro ao excluir nota fiscal');
    }
  }

  // ── SEFAZ ─────────────────────────────────────────────────────────────────

  async function carregarConfigSefaz() {
    try {
      setCfgLoading(true);
      const { data } = await api.get('/sefaz/config');
      setCfg((prev) => ({
        ...prev,
        enabled: Boolean(data.enabled),
        modo: data.modo || 'mock',
        importacao_automatica: Boolean(data.importacao_automatica),
        importacao_intervalo_min: Number(data.importacao_intervalo_min || 15),
        cert_ok: Boolean(data.cert_ok),
        ultimo_sync_status: data.ultimo_sync_status || 'nunca',
        ultimo_sync_mensagem: data.ultimo_sync_mensagem || 'Ainda não sincronizado.',
        ultimo_sync_at: data.ultimo_sync_at || null,
        ultimo_sync_documentos: Number(data.ultimo_sync_documentos || 0),
      }));
    } catch {
      setMsgRotina('Não foi possível carregar a configuração SEFAZ.');
    } finally {
      setCfgLoading(false);
    }
  }

  async function salvarRotina() {
    setMsgRotina('');
    try {
      setSalvandoRotina(true);
      await api.post('/sefaz/config', {
        enabled: cfg.enabled,
        modo: cfg.modo,
        importacao_automatica: cfg.importacao_automatica,
        importacao_intervalo_min: Number(cfg.importacao_intervalo_min || 15),
      });
      setMsgRotina('Rotina automática salva com sucesso.');
      await carregarConfigSefaz();
    } catch (err) {
      setMsgRotina(err?.response?.data?.detail || 'Erro ao salvar rotina automática.');
    } finally {
      setSalvandoRotina(false);
    }
  }

  async function sincronizarAgora() {
    setMsgRotina('');
    try {
      setSincronizando(true);
      const { data } = await api.post('/sefaz/sync-now');
      setMsgRotina(data?.mensagem || 'Sincronização solicitada.');
      await carregarConfigSefaz();
    } catch (err) {
      setMsgRotina(err?.response?.data?.detail || 'Erro ao sincronizar agora.');
    } finally {
      setSincronizando(false);
    }
  }

  async function consultarChave(e) {
    e.preventDefault();
    setErroConsulta('');
    if (chave.length !== 44) {
      setErroConsulta('A chave de acesso deve ter exatamente 44 dígitos.');
      return;
    }
    try {
      setConsultando(true);
      const resp = await api.post('/sefaz/consultar', { chave_acesso: chave });
      const dados = resp.data;

      // Aviso se parecer NF de entrada (destinatário = tenant)
      const cnpjEmpresa = soDigitos(cfg.cnpj);
      const cnpjDest = soDigitos(dados.destinatario_cnpj);
      if (cnpjEmpresa && cnpjDest && cnpjDest === cnpjEmpresa) {
        setErroConsulta('Esta chave parece ser NF de entrada (para a própria empresa). Use a tela Central NF-e Entradas.');
        return;
      }

      // Verificar se já existe na listagem Bling (dedup)
      const chaveDigitos = soDigitos(chave);
      const jaExiste = notas.some((n) => soDigitos(n.chave) === chaveDigitos);

      setConsultasSessao((prev) => [
        { id: `${Date.now()}-${chave}`, criadoEm: new Date().toISOString(), dados, jaExiste },
        ...prev,
      ]);
      setChave('');
    } catch (err) {
      setErroConsulta(err?.response?.data?.detail || 'Erro ao consultar a SEFAZ.');
    } finally {
      setConsultando(false);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────

  const notasFiltradas = notas.filter((nota) => {
    if (!busca) return true;
    const bl = busca.toLowerCase();
    return (
      nota.numero?.toLowerCase().includes(bl) ||
      nota.serie?.toLowerCase().includes(bl) ||
      nota.cliente?.nome?.toLowerCase().includes(bl) ||
      nota.cliente?.cpf_cnpj?.toLowerCase().includes(bl) ||
      nota.canal_label?.toLowerCase().includes(bl) ||
      nota.loja?.nome?.toLowerCase().includes(bl) ||
      nota.numero_pedido_loja?.toLowerCase().includes(bl)
    );
  });

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div className="p-6">

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <FileOutput className="w-8 h-8 text-purple-600" />
          NF de Saída
        </h1>
        <p className="text-gray-600 mt-1">Notas fiscais emitidas pelo PDV/Bling. Use o painel SEFAZ abaixo para consultar ou configurar sincronização.</p>
      </div>

      {/* ── Painel SEFAZ (accordion) ─────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-purple-200 mb-6 overflow-hidden">
        <button
          type="button"
          onClick={() => setPainelSefazAberto((p) => !p)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-purple-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-purple-600" />
            <span className="font-semibold text-gray-800">Ferramentas SEFAZ</span>
            <span className="text-xs text-gray-500 ml-1">
              (consulta por chave · rotina automática)
            </span>
          </div>
          {painelSefazAberto ? (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </button>

        {painelSefazAberto && (
          <div className="border-t border-purple-100 p-5 space-y-5">

            {/* Consulta por chave */}
            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">Consultar NF-e por chave de acesso</p>
              <p className="text-xs text-gray-500 mb-3">
                A configuração do certificado e ambiente fica em{' '}
                <Link to="/configuracoes/integracoes" className="text-indigo-600 font-semibold">
                  Configurações → Integrações
                </Link>.
              </p>
              <form onSubmit={consultarChave} className="flex gap-3">
                <input
                  type="text"
                  value={chave}
                  onChange={(e) => setChave(formatarChave(e.target.value))}
                  onPaste={(e) => tratarColagemChave(e, setChave)}
                  placeholder="44 dígitos — Ex: 35250112345678000195550010000001231234567890"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                  maxLength={80}
                />
                <button
                  type="submit"
                  disabled={consultando || chave.length !== 44}
                  className="px-5 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {consultando ? 'Consultando...' : 'Consultar'}
                </button>
              </form>
              <p className="text-xs text-gray-400 mt-1">{chave.length}/44 dígitos</p>
              {erroConsulta && (
                <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {erroConsulta}
                </div>
              )}
            </div>

            {/* Rotina automática */}
            <div className="border-t border-gray-100 pt-4">
              <p className="text-sm font-semibold text-gray-700 mb-3">Rotina automática de sincronização</p>
              {cfgLoading ? (
                <p className="text-sm text-gray-500">Carregando...</p>
              ) : (
                <div className="space-y-3">
                  {(!cfg.enabled || !cfg.cert_ok) && (
                    <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm">
                      Integração ainda não está pronta para rotina automática. Finalize em Configurações &gt; Integrações.
                    </div>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={cfg.importacao_automatica}
                        onChange={(e) => setCfg((p) => ({ ...p, importacao_automatica: e.target.checked }))}
                      />
                      <span>Ativar sincronização automática</span>
                    </label>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Intervalo (minutos)</label>
                      <input
                        type="number"
                        min={5}
                        value={cfg.importacao_intervalo_min}
                        onChange={(e) => setCfg((p) => ({ ...p, importacao_intervalo_min: Number(e.target.value || 15) }))}
                        className="w-full border rounded-lg px-3 py-1.5 text-sm"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <div>Última sync: <strong>{formatarDataHora(cfg.ultimo_sync_at)}</strong></div>
                    <div>Status: <strong>{cfg.ultimo_sync_status}</strong></div>
                    <div>Documentos: <strong>{cfg.ultimo_sync_documentos}</strong></div>
                    <div>Modo: <strong>{cfg.modo}</strong></div>
                    <div className="col-span-2">Mensagem: <strong>{cfg.ultimo_sync_mensagem}</strong></div>
                  </div>
                  {msgRotina && (
                    <div className="text-sm bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-700">
                      {msgRotina}
                    </div>
                  )}
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={salvarRotina}
                      disabled={salvandoRotina}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60"
                    >
                      {salvandoRotina ? 'Salvando...' : 'Salvar rotina'}
                    </button>
                    <button
                      type="button"
                      onClick={sincronizarAgora}
                      disabled={sincronizando}
                      className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:opacity-60"
                    >
                      {sincronizando ? 'Sincronizando...' : 'Sincronizar agora'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Resultados de consulta da sessão ─────────────────────────────── */}
      {consultasSessao.length > 0 && (
        <div ref={listaConsultasRef} className="mb-6">
          <h2 className="text-sm font-bold text-gray-700 mb-2 flex items-center gap-2">
            <Search className="w-4 h-4 text-purple-500" />
            Consultas da sessão ({consultasSessao.length})
          </h2>
          <div className="space-y-2">
            {consultasSessao.map((c) => {
              const expandida = consultaExpandidaId === c.id;
              const d = c.dados;
              return (
                <div key={c.id} className="bg-white rounded-xl border border-purple-200 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setConsultaExpandidaId(expandida ? null : c.id)}
                    className="w-full text-left px-4 py-3 hover:bg-purple-50"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-gray-800">
                        NF {d.numero_nf}/{d.serie} — {d.emitente_nome}
                      </div>
                      <div className="flex items-center gap-2">
                        {c.jaExiste && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">✓ Já está na listagem</span>
                        )}
                        <span className="text-xs text-gray-500">{formatarDataHora(c.criadoEm)}</span>
                      </div>
                    </div>
                    <div className="mt-1 text-xs text-gray-500 flex gap-4">
                      <span>Chave: <span className="font-mono">{d.chave_acesso}</span></span>
                      <span>Total: <strong className="text-gray-800">{formatMoneyBRL(d.valor_total_nf)}</strong></span>
                      <span className="text-purple-600">{expandida ? 'Fechar' : 'Expandir'}</span>
                    </div>
                  </button>
                  {expandida && (
                    <div className="border-t border-purple-100 p-4 space-y-3">
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div><span className="text-gray-500">Número/Série:</span> <strong>{d.numero_nf}/{d.serie}</strong></div>
                        <div><span className="text-gray-500">Emissão:</span> <strong>{d.data_emissao}</strong></div>
                        <div><span className="text-gray-500">Emitente:</span> <strong>{d.emitente_nome}</strong></div>
                        <div><span className="text-gray-500">CNPJ Emitente:</span> <strong>{d.emitente_cnpj}</strong></div>
                        <div><span className="text-gray-500">Destinatário:</span> <strong>{d.destinatario_nome || '-'}</strong></div>
                        <div><span className="text-gray-500">Valor Total:</span> <strong className="text-green-700">{formatMoneyBRL(d.valor_total_nf)}</strong></div>
                      </div>
                      {d.itens?.length > 0 && (
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="bg-gray-50 text-gray-600 uppercase">
                                <th className="text-left px-2 py-1">#</th>
                                <th className="text-left px-2 py-1">Descrição</th>
                                <th className="text-right px-2 py-1">Qtd</th>
                                <th className="text-right px-2 py-1">Unit.</th>
                                <th className="text-right px-2 py-1">Total</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {d.itens.map((item) => (
                                <tr key={item.numero_item} className="hover:bg-gray-50">
                                  <td className="px-2 py-1 text-gray-400">{item.numero_item}</td>
                                  <td className="px-2 py-1">{item.descricao}</td>
                                  <td className="px-2 py-1 text-right">{item.quantidade}</td>
                                  <td className="px-2 py-1 text-right">{formatMoneyBRL(item.valor_unitario)}</td>
                                  <td className="px-2 py-1 text-right font-semibold">{formatMoneyBRL(item.valor_total)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Filtros ───────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold text-gray-800">Notas Fiscais Emitidas</h2>
          </div>
          <button
            type="button"
            onClick={() => carregarNotas(true)}
            disabled={loading}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar por número, cliente..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <input
            type="date"
            value={dataInicial}
            onChange={(e) => setDataInicial(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="date"
            value={dataFinal}
            onChange={(e) => setDataFinal(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <select
            value={filtroSituacao}
            onChange={(e) => setFiltroSituacao(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            {SITUACOES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Erro ─────────────────────────────────────────────────────────── */}
      {erro && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 mb-6 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {erro}
        </div>
      )}

      {/* ── Listagem ─────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto" />
          <p className="text-gray-600 mt-4">Carregando notas fiscais...</p>
        </div>
      ) : notasFiltradas.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-800 mb-2">Nenhuma nota encontrada</h3>
          <p className="text-gray-600">
            {busca || filtroSituacao || dataInicial || dataFinal
              ? 'Tente ajustar os filtros'
              : 'Emita sua primeira nota fiscal em uma venda'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Número</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Data Emissão</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Canal / Loja</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Situação</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Ações</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {notasFiltradas.map((nota) => (
                <tr key={nota.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{nota.numero}</div>
                    <div className="text-sm text-gray-500">Série {nota.serie}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatarDataBR(nota.data_emissao)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">{nota.cliente?.nome || 'Cliente não informado'}</div>
                    <div className="text-sm text-gray-500">{nota.cliente?.cpf_cnpj || ''}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="space-y-1">
                      <div className="flex flex-wrap gap-2">
                        {nota.canal_label || nota.origem_loja_virtual || nota.origem_canal_venda ? (
                          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                            {nota.canal_label || nota.origem_loja_virtual || nota.origem_canal_venda}
                          </span>
                        ) : null}
                        {nota.loja?.nome ? (
                          <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                            {nota.loja.nome}
                          </span>
                        ) : null}
                      </div>
                      {nota.numero_pedido_loja ? (
                        <div className="text-xs text-gray-500">Pedido loja: {nota.numero_pedido_loja}</div>
                      ) : nota.origem_loja_virtual || nota.origem_canal_venda ? (
                        <div className="text-xs text-gray-500">Origem: {nota.origem_loja_virtual || nota.origem_canal_venda}</div>
                      ) : (
                        <div className="text-xs text-gray-400">Sem origem detalhada</div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getSituacaoCor(nota.status)}`}>
                      {getSituacaoIcone(nota.status)}
                      {nota.status || 'Pendente'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatMoneyBRL(nota.valor)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      {(nota.status?.toLowerCase() === 'autorizada' || nota.status?.toLowerCase() === 'emitida danfe') && (
                        <button
                          onClick={() => setModalCancelar(nota)}
                          className="text-red-600 hover:text-red-900 p-1 hover:bg-red-50 rounded"
                          title="Cancelar NF-e"
                        >
                          <XCircle className="w-5 h-5" />
                        </button>
                      )}
                      <button
                        onClick={() => excluirNota(nota.venda_id, nota.numero)}
                        className="text-gray-600 hover:text-gray-900 p-1 hover:bg-gray-50 rounded"
                        title="Excluir nota do sistema"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => reconciliarFluxoNota(nota)}
                        disabled={reconciliandoNotaId === String(nota.id)}
                        className="text-amber-600 hover:text-amber-900 p-1 hover:bg-amber-50 rounded disabled:opacity-50"
                        title="Forcar reconciliacao desta NF"
                      >
                        <Zap className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => baixarDanfe(nota.id, nota.numero)}
                        className="text-blue-600 hover:text-blue-900 p-1 hover:bg-blue-50 rounded"
                        title="Baixar DANFE"
                      >
                        <Printer className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => baixarXml(nota.id, nota.numero)}
                        className="text-green-600 hover:text-green-900 p-1 hover:bg-green-50 rounded"
                        title="Baixar XML"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => abrirDetalhes(nota)}
                        className="text-gray-600 hover:text-gray-900 p-1 hover:bg-gray-50 rounded"
                        title="Ver Detalhes"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && notasFiltradas.length > 0 && (
        <div className="mt-4 text-sm text-gray-600 text-center">
          {notasFiltradas.length} {notasFiltradas.length === 1 ? 'nota encontrada' : 'notas encontradas'}
        </div>
      )}

      {/* ── Modal Detalhes ───────────────────────────────────────────────── */}
      {notaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[92vh] overflow-y-auto m-4">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-800">Detalhes — NF #{notaSelecionada.numero}</h3>
              <button onClick={fecharDetalhes} className="text-gray-400 hover:text-gray-600">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              {carregandoDetalhe && (
                <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800 flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Carregando detalhes completos da nota no Bling...
                </div>
              )}
              {erroDetalhe && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {erroDetalhe}
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <div><label className="text-sm font-medium text-gray-600">Número</label><p>{notaSelecionada.numero}</p></div>
                <div><label className="text-sm font-medium text-gray-600">Série</label><p>{notaSelecionada.serie}</p></div>
                <div><label className="text-sm font-medium text-gray-600">Modelo</label><p>{notaSelecionada.modelo}</p></div>
                <div><label className="text-sm font-medium text-gray-600">Tipo</label><p>{notaSelecionada.tipo === 'nfe' ? 'NF-e' : 'NFC-e'}</p></div>
                <div className="col-span-2">
                  <label className="text-sm font-medium text-gray-600">Chave de Acesso</label>
                  <p className="text-xs break-all font-mono">{notaSelecionada.chave || '-'}</p>
                </div>
                <div><label className="text-sm font-medium text-gray-600">Cliente</label><p>{notaSelecionada.cliente?.nome}</p></div>
                <div><label className="text-sm font-medium text-gray-600">CPF/CNPJ</label><p>{notaSelecionada.cliente?.cpf_cnpj}</p></div>
                <div>
                  <label className="text-sm font-medium text-gray-600">Valor Total</label>
                  <p className="text-lg font-bold">{formatMoneyBRL(notaSelecionada.valor)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-600">Situação</label>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getSituacaoCor(notaSelecionada.status)}`}>
                    {getSituacaoIcone(notaSelecionada.status)}
                    {notaSelecionada.status}
                  </span>
                </div>
              </div>
              <SecaoDetalhe titulo="Dados fiscais">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <CampoDetalhe label="Data emissao" value={formatarDataBR(detalheNota?.data_emissao)} />
                  <CampoDetalhe label="Hora emissao" value={detalheNota?.hora_emissao} />
                  <CampoDetalhe label="Data saida" value={formatarDataBR(detalheNota?.data_saida)} />
                  <CampoDetalhe label="Hora saida" value={detalheNota?.hora_saida} />
                  <CampoDetalhe label="Natureza operacao" value={detalheNota?.natureza_operacao} />
                  <CampoDetalhe label="Regime tributario" value={detalheNota?.codigo_regime_tributario} />
                  <CampoDetalhe label="Finalidade" value={detalheNota?.finalidade} />
                  <CampoDetalhe label="Indicador presenca" value={detalheNota?.indicador_presenca} />
                </div>
              </SecaoDetalhe>

              <SecaoDetalhe titulo="Loja e canal">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <CampoDetalhe label="Loja" value={detalheNota?.loja?.nome} />
                  <CampoDetalhe label="Unidade negocio" value={detalheNota?.unidade_negocio?.nome} />
                  <CampoDetalhe label="Canal venda" value={detalheNota?.canal_label || detalheNota?.informacoes_adicionais?.origem_loja_virtual || detalheNota?.informacoes_adicionais?.origem_canal_venda || detalheNota?.canal} />
                  <CampoDetalhe label="Origem loja virtual" value={detalheNota?.informacoes_adicionais?.origem_loja_virtual || detalheNota?.canal_label} />
                  <CampoDetalhe label="Origem canal venda" value={detalheNota?.informacoes_adicionais?.origem_canal_venda || detalheNota?.canal_label} />
                  <CampoDetalhe label="Numero loja virtual" value={detalheNota?.informacoes_adicionais?.numero_loja_virtual} />
                  <CampoDetalhe label="Numero pedido loja" value={detalheNota?.informacoes_adicionais?.numero_pedido_loja} />
                </div>
              </SecaoDetalhe>

              <SecaoDetalhe titulo="Destinatario">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <CampoDetalhe label="Nome" value={detalheNota?.cliente?.nome} />
                  <CampoDetalhe label="Tipo pessoa" value={detalheNota?.cliente?.tipo_pessoa} />
                  <CampoDetalhe label="CPF/CNPJ" value={detalheNota?.cliente?.cpf_cnpj} />
                  <CampoDetalhe label="Vendedor" value={detalheNota?.cliente?.vendedor} />
                  <CampoDetalhe label="Consumidor final" value={valorBooleanoLabel(detalheNota?.cliente?.consumidor_final)} />
                  <CampoDetalhe label="Telefone" value={detalheNota?.cliente?.telefone} />
                  <CampoDetalhe label="Email" value={detalheNota?.cliente?.email} />
                  <CampoDetalhe label="CEP" value={detalheNota?.cliente?.cep} />
                  <CampoDetalhe label="UF" value={detalheNota?.cliente?.uf} />
                  <CampoDetalhe label="Municipio" value={detalheNota?.cliente?.municipio} />
                  <CampoDetalhe label="Bairro" value={detalheNota?.cliente?.bairro} />
                  <CampoDetalhe label="Endereco" value={detalheNota?.cliente?.endereco} />
                  <CampoDetalhe label="Numero" value={detalheNota?.cliente?.numero} />
                  <CampoDetalhe label="Complemento" value={detalheNota?.cliente?.complemento} />
                </div>
              </SecaoDetalhe>

              <SecaoDetalhe titulo="Itens da nota">
                {detalheNota?.itens?.length ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                      <thead className="bg-white">
                        <tr>
                          <th className="px-3 py-2 text-left font-semibold text-gray-500">Produto</th>
                          <th className="px-3 py-2 text-left font-semibold text-gray-500">Codigo</th>
                          <th className="px-3 py-2 text-left font-semibold text-gray-500">UN</th>
                          <th className="px-3 py-2 text-right font-semibold text-gray-500">Qtd</th>
                          <th className="px-3 py-2 text-right font-semibold text-gray-500">Preco un</th>
                          <th className="px-3 py-2 text-right font-semibold text-gray-500">Preco total</th>
                          <th className="px-3 py-2 text-left font-semibold text-gray-500">NCM</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 bg-white">
                        {detalheNota.itens.map((item, index) => (
                          <tr key={`${item.codigo || item.descricao || 'item'}-${index}`}>
                            <td className="px-3 py-2 text-gray-900">{item.descricao || '-'}</td>
                            <td className="px-3 py-2 text-gray-600">{item.codigo || '-'}</td>
                            <td className="px-3 py-2 text-gray-600">{item.unidade || '-'}</td>
                            <td className="px-3 py-2 text-right text-gray-900">{item.quantidade || 0}</td>
                            <td className="px-3 py-2 text-right text-gray-900">{formatMoneyBRL(item.valor_unitario || 0)}</td>
                            <td className="px-3 py-2 text-right font-semibold text-gray-900">{formatMoneyBRL(item.valor_total || 0)}</td>
                            <td className="px-3 py-2 text-gray-600">{item.ncm || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">Nenhum item detalhado retornado para esta nota.</p>
                )}
              </SecaoDetalhe>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                <SecaoDetalhe titulo="Totais">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <CampoDetalhe label="Valor produtos" value={formatMoneyBRL(detalheNota?.totais?.valor_produtos || 0)} />
                    <CampoDetalhe label="Frete" value={formatMoneyBRL(detalheNota?.totais?.valor_frete || 0)} />
                    <CampoDetalhe label="Seguro" value={formatMoneyBRL(detalheNota?.totais?.valor_seguro || 0)} />
                    <CampoDetalhe label="Outras despesas" value={formatMoneyBRL(detalheNota?.totais?.outras_despesas || 0)} />
                    <CampoDetalhe label="Desconto" value={formatMoneyBRL(detalheNota?.totais?.valor_desconto || 0)} />
                    <CampoDetalhe label="Valor total" value={formatMoneyBRL(detalheNota?.totais?.valor_total || 0)} destaque />
                  </div>
                </SecaoDetalhe>

                <SecaoDetalhe titulo="Entrega e transporte">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <CampoDetalhe label="Transporte" value={detalheNota?.transporte?.tipo} />
                    <CampoDetalhe label="Frete por conta" value={detalheNota?.transporte?.frete_por_conta} />
                    <CampoDetalhe label="Nome entrega" value={detalheNota?.endereco_entrega?.nome} />
                    <CampoDetalhe label="CEP entrega" value={detalheNota?.endereco_entrega?.cep} />
                    <CampoDetalhe label="UF entrega" value={detalheNota?.endereco_entrega?.uf} />
                    <CampoDetalhe label="Municipio entrega" value={detalheNota?.endereco_entrega?.municipio} />
                    <CampoDetalhe label="Bairro entrega" value={detalheNota?.endereco_entrega?.bairro} />
                    <CampoDetalhe label="Endereco entrega" value={detalheNota?.endereco_entrega?.endereco} />
                    <CampoDetalhe label="Numero entrega" value={detalheNota?.endereco_entrega?.numero} />
                    <CampoDetalhe label="Complemento entrega" value={detalheNota?.endereco_entrega?.complemento} />
                  </div>
                </SecaoDetalhe>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                <SecaoDetalhe titulo="Pagamento">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <CampoDetalhe label="Condicao pagamento" value={detalheNota?.pagamento?.condicao} />
                    <CampoDetalhe label="Categoria" value={detalheNota?.pagamento?.categoria} />
                  </div>
                  {detalheNota?.pagamento?.parcelas?.length ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200 text-sm">
                        <thead className="bg-white">
                          <tr>
                            <th className="px-3 py-2 text-left font-semibold text-gray-500">Dias</th>
                            <th className="px-3 py-2 text-left font-semibold text-gray-500">Data</th>
                            <th className="px-3 py-2 text-right font-semibold text-gray-500">Valor</th>
                            <th className="px-3 py-2 text-left font-semibold text-gray-500">Forma</th>
                            <th className="px-3 py-2 text-left font-semibold text-gray-500">Observacao</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 bg-white">
                          {detalheNota.pagamento.parcelas.map((parcela, index) => (
                            <tr key={`parcela-${index}`}>
                              <td className="px-3 py-2">{parcela.dias || '-'}</td>
                              <td className="px-3 py-2">{formatarDataBR(parcela.data)}</td>
                              <td className="px-3 py-2 text-right">{formatMoneyBRL(parcela.valor || 0)}</td>
                              <td className="px-3 py-2">{parcela.forma || '-'}</td>
                              <td className="px-3 py-2">{parcela.observacao || '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Sem parcelas detalhadas na resposta do Bling.</p>
                  )}
                </SecaoDetalhe>

                <SecaoDetalhe titulo="Intermediador">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <CampoDetalhe label="Intermediador" value={detalheNota?.intermediador?.ativo} />
                    <CampoDetalhe label="CNPJ" value={detalheNota?.intermediador?.cnpj} />
                    <CampoDetalhe label="Identificacao" value={detalheNota?.intermediador?.identificacao} />
                  </div>
                </SecaoDetalhe>
              </div>

              <SecaoDetalhe titulo="Informacoes adicionais">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <CampoDetalhe label="Numero pedido loja" value={detalheNota?.informacoes_adicionais?.numero_pedido_loja} />
                  <CampoDetalhe label="Numero loja virtual" value={detalheNota?.informacoes_adicionais?.numero_loja_virtual} />
                  <div className="md:col-span-2">
                    <CampoDetalhe label="Informacoes complementares" value={detalheNota?.informacoes_adicionais?.informacoes_complementares} />
                  </div>
                  <div className="md:col-span-2">
                    <CampoDetalhe label="Informacoes de interesse do fisco" value={detalheNota?.informacoes_adicionais?.informacoes_fisco} />
                  </div>
                </div>
              </SecaoDetalhe>

              <SecaoDetalhe titulo="Pessoas autorizadas no XML">
                {detalheNota?.pessoas_autorizadas_xml?.length ? (
                  <div className="flex flex-wrap gap-2">
                    {detalheNota.pessoas_autorizadas_xml.map((pessoa, index) => (
                      <span
                        key={`${pessoa}-${index}`}
                        className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
                      >
                        {pessoa}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">Nenhuma pessoa autorizada retornada para esta nota.</p>
                )}
              </SecaoDetalhe>

              <div className="flex gap-2 pt-4">
                <button
                  onClick={() => baixarDanfe(notaSelecionada.id, notaSelecionada.numero)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                >
                  <Printer className="w-5 h-5" /> Baixar DANFE
                </button>
                <button
                  onClick={() => baixarXml(notaSelecionada.id, notaSelecionada.numero)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
                >
                  <Download className="w-5 h-5" /> Baixar XML
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal Cancelamento ───────────────────────────────────────────── */}
      {modalCancelar && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full m-4">
            <div className="bg-red-50 border-b px-6 py-4 flex items-center gap-3">
              <XCircle className="w-6 h-6 text-red-600" />
              <h3 className="text-xl font-bold text-gray-800">Cancelar Nota Fiscal</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm text-yellow-800">
                <strong>Atenção:</strong> O cancelamento é irreversível e será enviado para a SEFAZ.
              </div>
              <div>
                <p className="text-sm text-gray-600"><strong>Nota:</strong> #{modalCancelar.numero} — Série {modalCancelar.serie}</p>
                <p className="text-sm text-gray-600"><strong>Cliente:</strong> {modalCancelar.cliente?.nome}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Justificativa *</label>
                <textarea
                  value={justificativa}
                  onChange={(e) => setJustificativa(e.target.value)}
                  placeholder="Digite o motivo do cancelamento (mínimo 15 caracteres)"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                />
                <p className="text-xs text-gray-500 mt-1">{justificativa.length}/15 caracteres</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => { setModalCancelar(null); setJustificativa(''); }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  disabled={cancelando}
                >
                  Voltar
                </button>
                <button
                  onClick={cancelarNota}
                  disabled={cancelando || justificativa.length < 15}
                  className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {cancelando ? (
                    <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" /> Cancelando...</>
                  ) : (
                    <><XCircle className="w-5 h-5" /> Confirmar Cancelamento</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
