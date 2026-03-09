/**
 * CanalDescontos.jsx
 *
 * Página para gerenciar descontos globais por canal de venda (Ecommerce / App Móvel).
 *
 * Lógica de prioridade ao exibir preço:
 *   1. Promoção específica do produto no canal (com data válida) ← máxima prioridade
 *   2. Desconto global deste módulo (% sobre preço de venda padrão)
 *   3. Preço de canal configurado no produto
 *   4. Preço de venda padrão
 */

import React, { useEffect, useState } from 'react';
import api from '../api';

const CANAIS = [
  { value: 'ecommerce', label: '🛒 Ecommerce', cor: 'purple' },
  { value: 'app',       label: '📱 App Móvel (Aplicativo)', cor: 'green' },
];

const VAZIO = {
  canal: 'ecommerce',
  nome: '',
  desconto_pct: '',
  ativo: true,
  data_inicio: '',
  data_fim: '',
};

export default function CanalDescontos() {
  const [descontos, setDescontos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(VAZIO);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [editando, setEditando] = useState(null); // id sendo editado
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState('');

  const carregar = async () => {
    setLoading(true);
    try {
      const res = await api.get('/canal-descontos');
      setDescontos(res.data || []);
    } catch {
      setErro('Erro ao carregar descontos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { carregar(); }, []);

  const iniciarCriacao = () => {
    setEditando(null);
    setForm({ ...VAZIO });
    setMostrarForm(true);
    setErro('');
  };

  const iniciarEdicao = (d) => {
    setEditando(d.id);
    setMostrarForm(true);
    setForm({
      canal: d.canal,
      nome: d.nome,
      desconto_pct: d.desconto_pct,
      ativo: d.ativo,
      data_inicio: d.data_inicio ? d.data_inicio.slice(0, 16) : '',
      data_fim:    d.data_fim    ? d.data_fim.slice(0, 16)    : '',
    });
    setErro('');
  };

  const cancelar = () => {
    setEditando(null);
    setForm({ ...VAZIO });
    setMostrarForm(false);
    setErro('');
  };

  const salvar = async (e) => {
    e.preventDefault();
    setErro('');
    const pct = parseFloat(form.desconto_pct);
    if (!form.nome.trim()) { setErro('Informe o nome da campanha.'); return; }
    if (isNaN(pct) || pct <= 0 || pct > 100) { setErro('Desconto deve ser entre 0,01% e 100%.'); return; }

    const payload = {
      canal: form.canal,
      nome: form.nome.trim(),
      desconto_pct: pct,
      ativo: form.ativo,
      data_inicio: form.data_inicio || null,
      data_fim:    form.data_fim    || null,
    };

    if (payload.ativo) {
      const conflito = descontos.find((d) => {
        if (!d.ativo) return false;
        if (d.canal !== payload.canal) return false;
        if (editando && d.id === editando) return false;

        const novoInicio = payload.data_inicio ? new Date(payload.data_inicio).getTime() : Number.NEGATIVE_INFINITY;
        const novoFim = payload.data_fim ? new Date(payload.data_fim).getTime() : Number.POSITIVE_INFINITY;
        const existenteInicio = d.data_inicio ? new Date(d.data_inicio).getTime() : Number.NEGATIVE_INFINITY;
        const existenteFim = d.data_fim ? new Date(d.data_fim).getTime() : Number.POSITIVE_INFINITY;

        return novoInicio <= existenteFim && novoFim >= existenteInicio;
      });

      if (conflito) {
        setErro(
          `Conflito de período com campanha ativa: "${conflito.nome}" ` +
          `(de ${formatData(conflito.data_inicio)} até ${formatData(conflito.data_fim)}). ` +
          'Pause, edite ou exclua a campanha anterior para salvar esta.'
        );
        return;
      }
    }

    try {
      setSalvando(true);
      if (editando) {
        await api.put(`/canal-descontos/${editando}`, payload);
      } else {
        await api.post('/canal-descontos', payload);
      }
      await carregar();
      cancelar();
    } catch (err) {
      setErro(err.response?.data?.detail || 'Erro ao salvar.');
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (id) => {
    if (!window.confirm('Excluir este desconto?')) return;
    try {
      await api.delete(`/canal-descontos/${id}`);
      setDescontos(prev => prev.filter(d => d.id !== id));
    } catch {
      alert('Erro ao excluir.');
    }
  };

  const alternarAtivo = async (d) => {
    if (!d.ativo) {
      const conflito = descontos.find((x) => {
        if (!x.ativo) return false;
        if (x.id === d.id) return false;
        if (x.canal !== d.canal) return false;

        const novoInicio = d.data_inicio ? new Date(d.data_inicio).getTime() : Number.NEGATIVE_INFINITY;
        const novoFim = d.data_fim ? new Date(d.data_fim).getTime() : Number.POSITIVE_INFINITY;
        const existenteInicio = x.data_inicio ? new Date(x.data_inicio).getTime() : Number.NEGATIVE_INFINITY;
        const existenteFim = x.data_fim ? new Date(x.data_fim).getTime() : Number.POSITIVE_INFINITY;

        return novoInicio <= existenteFim && novoFim >= existenteInicio;
      });

      if (conflito) {
        alert(
          `Não foi possível ativar. Já existe campanha ativa no mesmo período: ` +
          `${conflito.nome} (${formatData(conflito.data_inicio)} até ${formatData(conflito.data_fim)}).`
        );
        return;
      }
    }

    try {
      await api.put(`/canal-descontos/${d.id}`, { ativo: !d.ativo });
      setDescontos(prev => prev.map(x => x.id === d.id ? { ...x, ativo: !x.ativo } : x));
    } catch {
      alert('Erro ao alterar status.');
    }
  };

  const formatData = (str) => {
    if (!str) return '—';
    return new Date(str).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  };

  const labelCanal = (canal) => CANAIS.find(c => c.value === canal)?.label ?? canal;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Descontos por Canal de Venda</h1>
          <p className="text-sm text-gray-500 mt-1">
            Configure um desconto global (%) para o Ecommerce ou App. Se o produto já tiver promoção
            própria ativa, ela prevalece sobre o desconto global.
          </p>
        </div>
        <button
          onClick={iniciarCriacao}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
        >
          + Nova Campanha
        </button>
      </div>

      {/* Formulário */}
      {mostrarForm && (
        <form
          onSubmit={salvar}
          className="bg-white border border-blue-200 rounded-xl shadow p-5 space-y-4"
        >
          <h2 className="text-lg font-semibold text-gray-800">
            {editando ? '✏️ Editar Campanha' : '➕ Nova Campanha'}
          </h2>

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-2 text-sm">{erro}</div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Canal */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Canal</label>
              <select
                value={form.canal}
                onChange={e => setForm(p => ({ ...p, canal: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              >
                {CANAIS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>

            {/* Desconto */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Desconto (%)</label>
              <input
                type="number" step="0.5" min="0.5" max="100"
                placeholder="Ex: 5"
                value={form.desconto_pct}
                onChange={e => setForm(p => ({ ...p, desconto_pct: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Nome */}
            <div className="col-span-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Nome da Campanha</label>
              <input
                type="text"
                placeholder="Ex: Promoção de Verão — 5% Ecommerce"
                value={form.nome}
                onChange={e => setForm(p => ({ ...p, nome: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Data início */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Início (opcional)</label>
              <input
                type="datetime-local"
                value={form.data_inicio}
                onChange={e => setForm(p => ({ ...p, data_inicio: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Data fim */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Fim (opcional)</label>
              <input
                type="datetime-local"
                value={form.data_fim}
                onChange={e => setForm(p => ({ ...p, data_fim: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Ativo */}
            <div className="col-span-2 flex items-center gap-2">
              <input
                type="checkbox"
                id="ativo"
                checked={form.ativo}
                onChange={e => setForm(p => ({ ...p, ativo: e.target.checked }))}
                className="w-4 h-4 accent-blue-600"
              />
              <label htmlFor="ativo" className="text-sm text-gray-700">Campanha ativa</label>
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={salvando}
              className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {salvando ? 'Salvando...' : 'Salvar'}
            </button>
            <button
              type="button"
              onClick={cancelar}
              className="text-gray-600 px-4 py-2 rounded-lg text-sm border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {/* Lista */}
      {loading ? (
        <div className="text-center py-10 text-gray-400">Carregando...</div>
      ) : descontos.length === 0 ? (
        <div className="bg-white border border-dashed border-gray-300 rounded-xl p-10 text-center">
          <div className="text-4xl mb-3">🏷️</div>
          <p className="text-gray-500 text-sm">Nenhuma campanha de canal cadastrada.</p>
          <p className="text-gray-400 text-xs mt-1">Clique em "+ Nova Campanha" para começar.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {CANAIS.map(canal => {
            const lista = descontos.filter(d => d.canal === canal.value);
            if (lista.length === 0) return null;
            return (
              <div key={canal.value}>
                <h3 className="text-xs font-bold text-gray-500 uppercase mb-2 tracking-wide">{canal.label}</h3>
                <div className="space-y-2">
                  {lista.map(d => (
                    <div
                      key={d.id}
                      className={`bg-white border rounded-xl p-4 flex items-center justify-between gap-4 shadow-sm ${
                        d.ativo ? 'border-green-200' : 'border-gray-200 opacity-60'
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            d.ativo ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                          }`}>
                            {d.ativo ? 'Ativa' : 'Inativa'}
                          </span>
                          <span className="text-sm font-semibold text-gray-800 truncate">{d.nome}</span>
                        </div>
                        <div className="text-xs text-gray-500">
                          <span className="font-bold text-blue-700 text-base">{d.desconto_pct}%</span>
                          {' '}de desconto
                          {d.data_inicio && <> · de {formatData(d.data_inicio)}</>}
                          {d.data_fim    && <> até {formatData(d.data_fim)}</>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => alternarAtivo(d)}
                          title={d.ativo ? 'Desativar' : 'Ativar'}
                          className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                            d.ativo
                              ? 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100 border border-yellow-200'
                              : 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-200'
                          }`}
                        >
                          {d.ativo ? '⏸ Pausar' : '▶ Ativar'}
                        </button>
                        <button
                          onClick={() => iniciarEdicao(d)}
                          className="px-3 py-1 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors"
                        >
                          ✏️ Editar
                        </button>
                        <button
                          onClick={() => excluir(d.id)}
                          className="px-3 py-1 rounded-lg text-xs font-medium bg-red-50 text-red-600 hover:bg-red-100 border border-red-200 transition-colors"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
