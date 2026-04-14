import React, { useState, useEffect } from 'react';
import { FiPlus, FiEdit2, FiTrash2, FiCheck } from 'react-icons/fi';
import api from '../../api.js';
import { toast } from 'react-hot-toast';

const TipoDespesa = () => {
  const [tipos, setTipos] = useState([]);
  const [subcategoriasDre, setSubcategoriasDre] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({ nome: '', e_custo_fixo: true, dre_subcategoria_id: '' });
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    carregar();
  }, []);

  const carregar = async () => {
    try {
      setLoading(true);
      const [tiposRes, subcategoriasRes] = await Promise.all([
        api.get('/cadastros/tipo-despesa/'),
        api.get('/dre/subcategorias'),
      ]);
      setTipos(Array.isArray(tiposRes.data) ? tiposRes.data : []);
      setSubcategoriasDre(
        Array.isArray(subcategoriasRes.data)
          ? subcategoriasRes.data.filter((item) => item?.ativo !== false)
          : [],
      );
    } catch {
      toast.error('Erro ao carregar tipos de despesa');
    } finally {
      setLoading(false);
    }
  };

  const abrirNovo = () => {
    setEditando(null);
    setForm({ nome: '', e_custo_fixo: true, dre_subcategoria_id: '' });
    setShowModal(true);
  };

  const abrirEdicao = (tipo) => {
    setEditando(tipo.id);
    setForm({
      nome: tipo.nome,
      e_custo_fixo: tipo.e_custo_fixo,
      dre_subcategoria_id: tipo.dre_subcategoria_id ? String(tipo.dre_subcategoria_id) : '',
    });
    setShowModal(true);
  };

  const salvar = async () => {
    if (!form.nome.trim()) {
      toast.error('Informe o nome do tipo de despesa');
      return;
    }

    if (!form.dre_subcategoria_id) {
      toast.error('Selecione a subcategoria DRE');
      return;
    }

    try {
      setSalvando(true);
      const payload = {
        nome: form.nome,
        e_custo_fixo: form.e_custo_fixo,
        dre_subcategoria_id: Number(form.dre_subcategoria_id),
      };
      if (editando) {
        await api.put(`/cadastros/tipo-despesa/${editando}`, payload);
        toast.success('Tipo atualizado!');
      } else {
        await api.post('/cadastros/tipo-despesa/', payload);
        toast.success('Tipo criado!');
      }
      setShowModal(false);
      carregar();
    } catch {
      toast.error('Erro ao salvar');
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async (id) => {
    if (!window.confirm('Desativar este tipo de despesa?')) return;
    try {
      await api.delete(`/cadastros/tipo-despesa/${id}`);
      toast.success('Tipo desativado');
      carregar();
    } catch {
      toast.error('Erro ao desativar');
    }
  };

  const fixos = tipos.filter((t) => t.e_custo_fixo && t.ativo);
  const variaveis = tipos.filter((t) => !t.e_custo_fixo && t.ativo);
  const nomeSubcategoria = (id) =>
    subcategoriasDre.find((item) => Number(item.id) === Number(id))?.nome || 'Subcategoria não encontrada';

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">📋 Tipos de Despesa</h1>
          <p className="text-sm text-gray-500 mt-1">
            Classifique cada tipo como <strong>Fixo</strong> ou <strong>Variável</strong> para calcular o Ponto de Equilíbrio corretamente.
          </p>
        </div>
        <button
          onClick={abrirNovo}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          <FiPlus /> Novo Tipo
        </button>
      </div>

      {/* Legenda */}
      <div className="flex gap-4 mb-6">
        <div className="flex items-center gap-2 bg-orange-50 border border-orange-200 rounded-lg px-4 py-2 text-sm">
          <span className="w-3 h-3 rounded-full bg-orange-400 inline-block" />
          <span><strong>Custo Fixo</strong> — existe todo mês independente das vendas (aluguel, salário, impostos...)</span>
        </div>
        <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-sm">
          <span className="w-3 h-3 rounded-full bg-blue-400 inline-block" />
          <span><strong>Custo Variável</strong> — cresce conforme as vendas (mercadorias, frete, comissões...)</span>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Carregando...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* FIXOS */}
          <div>
            <h2 className="text-lg font-semibold text-orange-700 mb-3 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-orange-400 inline-block" />
              Custos Fixos ({fixos.length})
            </h2>
            <div className="space-y-2">
              {fixos.map((tipo) => (
                <div
                  key={tipo.id}
                  className="flex items-center justify-between bg-white border border-orange-100 rounded-lg px-4 py-3 shadow-sm hover:shadow-md transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-orange-500 font-bold text-lg">F</span>
                    <div>
                      <span className="text-gray-800 font-medium">{tipo.nome}</span>
                      <p className="text-xs text-gray-500">DRE: {nomeSubcategoria(tipo.dre_subcategoria_id)}</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => abrirEdicao(tipo)}
                      className="text-gray-400 hover:text-blue-600 p-1 rounded"
                      title="Editar"
                    >
                      <FiEdit2 size={15} />
                    </button>
                    <button
                      onClick={() => excluir(tipo.id)}
                      className="text-gray-400 hover:text-red-600 p-1 rounded"
                      title="Desativar"
                    >
                      <FiTrash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
              {fixos.length === 0 && (
                <p className="text-sm text-gray-400 italic pl-2">Nenhum tipo fixo cadastrado.</p>
              )}
            </div>
          </div>

          {/* VARIÁVEIS */}
          <div>
            <h2 className="text-lg font-semibold text-blue-700 mb-3 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-400 inline-block" />
              Custos Variáveis ({variaveis.length})
            </h2>
            <div className="space-y-2">
              {variaveis.map((tipo) => (
                <div
                  key={tipo.id}
                  className="flex items-center justify-between bg-white border border-blue-100 rounded-lg px-4 py-3 shadow-sm hover:shadow-md transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-blue-500 font-bold text-lg">V</span>
                    <div>
                      <span className="text-gray-800 font-medium">{tipo.nome}</span>
                      <p className="text-xs text-gray-500">DRE: {nomeSubcategoria(tipo.dre_subcategoria_id)}</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => abrirEdicao(tipo)}
                      className="text-gray-400 hover:text-blue-600 p-1 rounded"
                      title="Editar"
                    >
                      <FiEdit2 size={15} />
                    </button>
                    <button
                      onClick={() => excluir(tipo.id)}
                      className="text-gray-400 hover:text-red-600 p-1 rounded"
                      title="Desativar"
                    >
                      <FiTrash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
              {variaveis.length === 0 && (
                <p className="text-sm text-gray-400 italic pl-2">Nenhum tipo variável cadastrado.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold mb-5 text-gray-800">
              {editando ? 'Editar Tipo de Despesa' : 'Novo Tipo de Despesa'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Ex: Aluguel, Salários, Fornecedor..."
                  value={form.nome}
                  onChange={(e) => setForm({ ...form, nome: e.target.value })}
                  onKeyDown={(e) => e.key === 'Enter' && salvar()}
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Classificação</label>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, e_custo_fixo: true })}
                    className={`flex-1 flex items-center justify-center gap-2 rounded-lg border-2 px-4 py-3 text-sm font-semibold transition ${
                      form.e_custo_fixo
                        ? 'border-orange-500 bg-orange-50 text-orange-700'
                        : 'border-gray-200 text-gray-500 hover:border-orange-300'
                    }`}
                  >
                    {form.e_custo_fixo && <FiCheck size={14} />}
                    🔒 Custo Fixo
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, e_custo_fixo: false })}
                    className={`flex-1 flex items-center justify-center gap-2 rounded-lg border-2 px-4 py-3 text-sm font-semibold transition ${
                      !form.e_custo_fixo
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 text-gray-500 hover:border-blue-300'
                    }`}
                  >
                    {!form.e_custo_fixo && <FiCheck size={14} />}
                    📈 Custo Variável
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {form.e_custo_fixo
                    ? '🔒 Fixo: valor não muda com o volume de vendas (ex: aluguel, salário, impostos)'
                    : '📈 Variável: valor cresce com as vendas (ex: mercadorias, frete, comissões)'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Subcategoria DRE</label>
                <select
                  value={form.dre_subcategoria_id}
                  onChange={(e) => setForm({ ...form, dre_subcategoria_id: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Selecione...</option>
                  {subcategoriasDre.map((sub) => (
                    <option key={sub.id} value={String(sub.id)}>
                      {sub.nome}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 border border-gray-300 text-gray-700 rounded-lg py-2 text-sm hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={salvar}
                disabled={salvando}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50"
              >
                {salvando ? 'Salvando...' : editando ? 'Salvar Alterações' : 'Criar Tipo'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TipoDespesa;
