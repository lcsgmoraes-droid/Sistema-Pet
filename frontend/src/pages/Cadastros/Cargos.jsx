import { useEffect, useState } from "react";
import api from "../../api";
import toast from "react-hot-toast";

export default function Cargos() {
  const [cargos, setCargos] = useState([]);
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);

  const carregarCargos = async () => {
    try {
      setLoading(true);
      const res = await api.get("/cargos");
      setCargos(res.data);
    } catch (error) {
      console.error("Erro ao carregar cargos:", error);
      toast.error("Erro ao carregar cargos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarCargos();
  }, []);

  const novoCargo = () => {
    setForm({
      nome: "",
      descricao: "",
      salario_base: "",
      inss_patronal_percentual: 20,
      fgts_percentual: 8,
      gera_ferias: true,
      gera_decimo_terceiro: true,
      ativo: true,
    });
  };

  const salvarCargo = async () => {
    if (!form.nome || !form.salario_base) {
      toast.error("Nome e salário são obrigatórios");
      return;
    }

    try {
      if (form.id) {
        await api.put(`/cargos/${form.id}`, form);
        toast.success("Cargo atualizado com sucesso!");
      } else {
        await api.post("/cargos", form);
        toast.success("Cargo cadastrado com sucesso!");
      }

      setForm(null);
      carregarCargos();
    } catch (error) {
      console.error("Erro ao salvar cargo:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar cargo");
    }
  };

  const toggleAtivo = async (cargo) => {
    try {
      await api.patch(`/cargos/${cargo.id}/status?ativo=${!cargo.ativo}`);
      toast.success(`Cargo ${!cargo.ativo ? 'ativado' : 'inativado'} com sucesso!`);
      carregarCargos();
    } catch (error) {
      console.error("Erro ao alterar status:", error);
      toast.error(error.response?.data?.detail || "Erro ao alterar status");
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Cadastro de Cargos</h1>
        <p className="text-gray-600">
          Gerencie cargos, defina salários e encargos que alimentam provisões, DRE e simulações
        </p>
      </div>

      {/* Botão Novo Cargo */}
      <div className="mb-4">
        <button
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
          onClick={novoCargo}
        >
          <span className="text-xl">+</span> Novo Cargo
        </button>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Nome
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Salário Base
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                INSS %
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                FGTS %
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Férias
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                13º
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ativo
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ações
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {cargos.map((c) => (
              <tr key={c.id} className={!c.ativo ? "bg-gray-50" : ""}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{c.nome}</div>
                  {c.descricao && (
                    <div className="text-sm text-gray-500">{c.descricao}</div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium text-green-600">
                  {formatarMoeda(c.salario_base)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {Number(c.inss_patronal_percentual).toFixed(2)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {Number(c.fgts_percentual).toFixed(2)}%
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    c.gera_ferias ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {c.gera_ferias ? "Sim" : "Não"}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    c.gera_decimo_terceiro ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {c.gera_decimo_terceiro ? "Sim" : "Não"}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    c.ativo ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {c.ativo ? "Sim" : "Não"}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                  <button
                    className="text-indigo-600 hover:text-indigo-900 mr-4"
                    onClick={() => setForm(c)}
                  >
                    Editar
                  </button>
                  <button
                    className={`${c.ativo ? 'text-yellow-600 hover:text-yellow-900' : 'text-green-600 hover:text-green-900'}`}
                    onClick={() => toggleAtivo(c)}
                  >
                    {c.ativo ? "Inativar" : "Ativar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {cargos.length === 0 && (
          <div className="text-center py-12">
            <p className="text-gray-500">Nenhum cargo cadastrado</p>
          </div>
        )}
      </div>

      {/* Formulário Inline */}
      {form && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-800 mb-4">
            {form.id ? "Editar Cargo" : "Novo Cargo"}
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Nome */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome do Cargo *
              </label>
              <input
                type="text"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Ex: Vendedor, Tosador, Gerente"
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
              />
            </div>

            {/* Descrição */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Descrição
              </label>
              <textarea
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Descrição das responsabilidades..."
                rows={2}
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              />
            </div>

            {/* Salário */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Salário Base (R$) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="0.00"
                value={form.salario_base}
                onChange={(e) => setForm({ ...form, salario_base: e.target.value })}
              />
            </div>

            {/* INSS */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                INSS Patronal (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.inss_patronal_percentual}
                onChange={(e) => setForm({ ...form, inss_patronal_percentual: e.target.value })}
              />
            </div>

            {/* FGTS */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                FGTS (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.fgts_percentual}
                onChange={(e) => setForm({ ...form, fgts_percentual: e.target.value })}
              />
            </div>

            {/* Checkboxes */}
            <div className="md:col-span-2 flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.gera_ferias}
                  onChange={(e) => setForm({ ...form, gera_ferias: e.target.checked })}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700">Gera férias</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.gera_decimo_terceiro}
                  onChange={(e) => setForm({ ...form, gera_decimo_terceiro: e.target.checked })}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700">Gera 13º</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.ativo}
                  onChange={(e) => setForm({ ...form, ativo: e.target.checked })}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-sm text-gray-700">Ativo</span>
              </label>
            </div>
          </div>

          {/* Botões */}
          <div className="mt-6 flex gap-3">
            <button
              className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors"
              onClick={salvarCargo}
            >
              Salvar
            </button>
            <button
              className="bg-gray-500 text-white px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors"
              onClick={() => setForm(null)}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
