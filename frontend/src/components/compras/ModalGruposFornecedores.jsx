import React, { useMemo, useState } from 'react';

const ModalGruposFornecedores = ({
  grupos,
  fornecedores,
  form,
  setForm,
  salvando,
  onClose,
  onSubmit,
  onNovo,
  onEditar,
  onExcluir,
  onToggleFornecedor,
}) => {
  const [buscaFornecedor, setBuscaFornecedor] = useState('');
  const fornecedoresSelecionadosSet = useMemo(
    () => new Set((form.fornecedor_ids || []).map((id) => Number(id))),
    [form.fornecedor_ids],
  );
  const fornecedoresSelecionados = useMemo(
    () => fornecedores.filter((fornecedor) => fornecedoresSelecionadosSet.has(Number(fornecedor.id))),
    [fornecedores, fornecedoresSelecionadosSet],
  );
  const normalizar = (texto = '') => texto
    .toLowerCase()
    .normalize('NFD')
    .replaceAll(/[\u0300-\u036f]/g, '');
  const fornecedoresFiltrados = useMemo(() => {
    const termo = normalizar(buscaFornecedor.trim());
    return fornecedores
      .filter((fornecedor) => {
        if (!termo) return true;
        return normalizar([
          fornecedor.nome,
          fornecedor.cnpj,
          fornecedor.cpf,
          fornecedor.razao_social,
          fornecedor.nome_fantasia,
        ].filter(Boolean).join(' ')).includes(termo);
      })
      .slice(0, 120);
  }, [fornecedores, buscaFornecedor]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Grupos de fornecedor</h2>
              <p className="mt-1 text-sm text-slate-600">
                Una CNPJs do mesmo fornecedor comercial sem alterar o cadastro fiscal de cada empresa.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100"
            >
              Fechar
            </button>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 gap-0 overflow-y-auto lg:grid-cols-[0.95fr_1.2fr]">
          <div className="border-r border-slate-200 bg-slate-50 p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Cadastrados</div>
                <div className="text-sm text-slate-600">{grupos.length} grupo(s)</div>
              </div>
              <button
                type="button"
                onClick={onNovo}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Novo
              </button>
            </div>

            <div className="space-y-3">
              {grupos.length === 0 && (
                <div className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
                  Nenhum grupo criado ainda.
                </div>
              )}

              {grupos.map((grupo) => (
                <div
                  key={grupo.id}
                  className={`rounded-xl border p-4 ${
                    Number(form.id) === Number(grupo.id)
                      ? 'border-blue-300 bg-blue-50'
                      : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{grupo.nome}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {(grupo.fornecedores || []).length} CNPJ(s) vinculado(s)
                      </div>
                      {grupo.fornecedor_principal_nome && (
                        <div className="mt-1 text-xs font-semibold text-emerald-700">
                          Principal: {grupo.fornecedor_principal_nome}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => onEditar(grupo)}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => onExcluir(grupo)}
                        className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                      >
                        Excluir
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-5 p-6">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.16em] text-blue-600">
                {form.id ? 'Editar grupo' : 'Novo grupo'}
              </div>
              <h3 className="text-xl font-bold text-slate-900">Unificacao comercial de CNPJs</h3>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-semibold text-slate-700">Nome do grupo</label>
                <input
                  value={form.nome}
                  onChange={(event) => setForm((prev) => ({ ...prev, nome: event.target.value }))}
                  placeholder="Ex: Distribuidora Pet Brasil"
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-400"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-semibold text-slate-700">Fornecedor principal</label>
                <select
                  value={form.fornecedor_principal_id}
                  onChange={(event) => setForm((prev) => ({ ...prev, fornecedor_principal_id: event.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-400"
                >
                  <option value="">Selecione</option>
                  {fornecedoresSelecionados.map((fornecedor) => (
                    <option key={fornecedor.id} value={fornecedor.id}>
                      {fornecedor.nome}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-semibold text-slate-700">Descricao interna</label>
              <textarea
                value={form.descricao}
                onChange={(event) => setForm((prev) => ({ ...prev, descricao: event.target.value }))}
                placeholder="Observacao opcional para compras, condicoes comerciais ou contatos."
                className="h-20 w-full rounded-lg border border-slate-300 px-4 py-2 focus:ring-2 focus:ring-blue-400"
              />
            </div>

            <div className="rounded-xl border border-slate-200">
              <div className="border-b border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div className="font-semibold text-slate-900">CNPJs do grupo</div>
                    <div className="text-sm text-slate-500">
                      {fornecedoresSelecionados.length} fornecedor(es) selecionado(s)
                    </div>
                  </div>
                  <input
                    value={buscaFornecedor}
                    onChange={(event) => setBuscaFornecedor(event.target.value)}
                    placeholder="Buscar fornecedor, CNPJ ou razao social"
                    className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm md:w-80"
                  />
                </div>
              </div>

              <div className="max-h-72 divide-y divide-slate-100 overflow-y-auto">
                {fornecedoresFiltrados.map((fornecedor) => {
                  const selecionado = fornecedoresSelecionadosSet.has(Number(fornecedor.id));
                  return (
                    <label
                      key={fornecedor.id}
                      className={`flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-blue-50 ${
                        selecionado ? 'bg-blue-50/70' : 'bg-white'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selecionado}
                        onChange={() => onToggleFornecedor(fornecedor.id)}
                        className="mt-1 h-4 w-4 rounded"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block font-semibold text-slate-900">{fornecedor.nome}</span>
                        <span className="block text-xs text-slate-500">
                          {fornecedor.cnpj || fornecedor.cpf || 'Sem CNPJ/CPF informado'}
                          {fornecedor.razao_social ? ` | ${fornecedor.razao_social}` : ''}
                        </span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-5 md:flex-row md:justify-end">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg border border-slate-300 px-5 py-2.5 font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={salvando}
                className="rounded-lg bg-blue-600 px-5 py-2.5 font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
              >
                {salvando ? 'Salvando...' : 'Salvar grupo'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ModalGruposFornecedores;
