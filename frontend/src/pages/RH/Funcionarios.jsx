import { useEffect, useState } from "react";
import api from "../../api";
import EventosFuncionario from "./components/EventosFuncionario";

export default function Funcionarios() {
  const [funcionarios, setFuncionarios] = useState([]);
  const [cargos, setCargos] = useState([]);
  const [form, setForm] = useState(null);
  const [filtro, setFiltro] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("todos");
  const [eventosFuncionario, setEventosFuncionario] = useState(null);

  const carregar = async () => {
    const res = await api.get("/funcionarios");
    setFuncionarios(res.data);
  };

  const carregarCargos = async () => {
    const res = await api.get("/cargos");
    setCargos(res.data.filter((c) => c.ativo));
  };

  useEffect(() => {
    carregar();
    carregarCargos();
  }, []);

  const novoFuncionario = () => {
    setForm({
      nome: "",
      cpf: "",
      email: "",
      telefone: "",
      cargo_id: "",
      ativo: true,
    });
  };

  const salvar = async () => {
    if (!form.nome || !form.cargo_id) {
      alert("Nome e cargo são obrigatórios");
      return;
    }

    // Preparar payload corrigindo campos vazios para null
    const payload = {
      nome: form.nome,
      cargo_id: Number(form.cargo_id),
      ativo: form.ativo,
      email: form.email?.trim() || null,
      telefone: form.telefone?.trim() || null,
      cpf: form.cpf?.trim() || null,
    };

    try {
      if (form.id) {
        await api.put(`/funcionarios/${form.id}`, payload);
      } else {
        await api.post("/funcionarios", payload);
      }

      setForm(null);
      carregar();
    } catch (error) {
      console.error("Erro ao salvar funcionário:", error);
      alert(error.response?.data?.detail || "Erro ao salvar funcionário");
    }
  };

  const inativar = async (id) => {
    if (!window.confirm("Deseja inativar este funcionário?")) return;
    await api.delete(`/funcionarios/${id}`);
    carregar();
  };

  const listaFiltrada = funcionarios.filter((f) => {
    const matchBusca =
      f.nome.toLowerCase().includes(filtro.toLowerCase()) ||
      (f.cpf || "").includes(filtro);

    const matchStatus =
      filtroStatus === "todos" ||
      (filtroStatus === "ativos" && f.ativo) ||
      (filtroStatus === "inativos" && !f.ativo);

    return matchBusca && matchStatus;
  });

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Funcionários</h2>

      <div className="flex justify-between items-center mb-4 gap-4">
        <div className="flex gap-2">
          <input
            className="border p-2 w-64"
            placeholder="Buscar por nome ou CPF"
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
          />

          <select
            className="border p-2 bg-white"
            value={filtroStatus}
            onChange={(e) => setFiltroStatus(e.target.value)}
          >
            <option value="todos">Todos</option>
            <option value="ativos">Ativos</option>
            <option value="inativos">Inativos</option>
          </select>
        </div>

        <button
          onClick={novoFuncionario}
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          + Novo Funcionário
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Nome</th>
              <th className="px-4 py-3 text-left font-semibold">Cargo</th>
              <th className="px-4 py-3 text-left font-semibold">Salário</th>
              <th className="px-4 py-3 text-center font-semibold">Status</th>
              <th className="px-4 py-3 text-center font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {listaFiltrada.map((f) => (
              <tr key={f.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-medium text-gray-800">{f.nome}</td>
                <td className="px-4 py-3 text-gray-600">
                  {f.cargo ? f.cargo.nome : <span className="text-gray-400 italic">Sem cargo</span>}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {f.cargo
                    ? `R$ ${Number(f.cargo.salario_base).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`
                    : <span className="text-gray-400">-</span>}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    f.ativo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}>
                    {f.ativo ? "Ativo" : "Inativo"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-2">
                    <button
                      className="px-3 py-1.5 text-xs font-medium rounded-md bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 transition-colors"
                      onClick={() => setEventosFuncionario(f)}
                    >
                      Eventos
                    </button>
                    <button
                      className="px-3 py-1.5 text-xs font-medium rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors"
                      onClick={() => setForm({ ...f, cargo_id: f.cargo?.id })}
                    >
                      Editar
                    </button>
                    {f.ativo && (
                      <button
                        className="px-3 py-1.5 text-xs font-medium rounded-md bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 transition-colors"
                        onClick={() => inativar(f.id)}
                      >
                        Inativar
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {listaFiltrada.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-400 italic">
                  Nenhum funcionário encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {form && (
        <div className="border rounded p-4 mt-6">
          <h3 className="font-semibold mb-3">
            {form.id ? "Editar Funcionário" : "Novo Funcionário"}
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <input
              className="border p-2"
              placeholder="Nome"
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
            />

            <input
              className="border p-2"
              placeholder="CPF"
              value={form.cpf || ""}
              onChange={(e) => setForm({ ...form, cpf: e.target.value })}
            />

            <input
              className="border p-2"
              placeholder="Email"
              value={form.email || ""}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />

            <input
              className="border p-2"
              placeholder="Telefone"
              value={form.telefone || ""}
              onChange={(e) =>
                setForm({ ...form, telefone: e.target.value })
              }
            />

            <select
              className="border p-2 col-span-2"
              value={form.cargo_id}
              onChange={(e) =>
                setForm({ ...form, cargo_id: e.target.value })
              }
            >
              <option value="">Selecione o cargo</option>
              {cargos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-4 space-x-2">
            <button
              onClick={salvar}
              className="bg-green-600 text-white px-4 py-2 rounded"
            >
              Salvar
            </button>
            <button
              onClick={() => setForm(null)}
              className="bg-gray-400 text-white px-4 py-2 rounded"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {eventosFuncionario && (
        <EventosFuncionario
          funcionario={eventosFuncionario}
          onClose={() => setEventosFuncionario(null)}
        />
      )}
    </div>
  );
}
