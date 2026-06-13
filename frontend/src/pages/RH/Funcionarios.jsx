import { useEffect, useMemo, useState } from "react";
import api from "../../api";
import EventosFuncionario from "./components/EventosFuncionario";

const funcionarioPadrao = () => ({
  nome: "",
  cpf: "",
  email: "",
  telefone: "",
  cargo_id: "",
  ativo: true,
  salario_base_override: "",
  liquido_combinado: "",
  complemento_modo: "automatico",
  complemento_fixo_valor: 0,
  remuneracao_observacoes: "",
  app_access_profiles: ["funcionario"],
});

const valorOuNull = (valor) => {
  if (valor === "" || valor === null || valor === undefined) return null;
  return Number(valor);
};

const formatarMoeda = (valor) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(valor || 0));

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
    setForm(funcionarioPadrao());
  };

  const editarFuncionario = (funcionario) => {
    setForm({
      ...funcionarioPadrao(),
      ...funcionario,
      cargo_id: funcionario.cargo?.id || "",
      salario_base_override: funcionario.salario_base_override ?? "",
      liquido_combinado: funcionario.liquido_combinado ?? "",
      complemento_modo: funcionario.complemento_modo || "automatico",
      complemento_fixo_valor: funcionario.complemento_fixo_valor ?? 0,
      remuneracao_observacoes: funcionario.remuneracao_observacoes || "",
      app_access_profiles:
        funcionario.app_access_profiles?.length
          ? funcionario.app_access_profiles
          : ["funcionario"],
    });
  };

  const salvar = async () => {
    if (!form.nome || !form.cargo_id) {
      alert("Nome e cargo sao obrigatorios");
      return;
    }

    const payload = {
      nome: form.nome,
      cargo_id: Number(form.cargo_id),
      ativo: form.ativo,
      email: form.email?.trim() || null,
      telefone: form.telefone?.trim() || null,
      cpf: form.cpf?.trim() || null,
      salario_base_override: valorOuNull(form.salario_base_override),
      liquido_combinado: valorOuNull(form.liquido_combinado),
      complemento_modo: form.complemento_modo || "automatico",
      complemento_fixo_valor: Number(form.complemento_fixo_valor || 0),
      remuneracao_observacoes: form.remuneracao_observacoes?.trim() || null,
      app_access_profiles: form.app_access_profiles || [],
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
      console.error("Erro ao salvar funcionario:", error);
      alert(error.response?.data?.detail || "Erro ao salvar funcionario");
    }
  };

  const inativar = async (id) => {
    if (!window.confirm("Deseja inativar este funcionario?")) return;
    await api.delete(`/funcionarios/${id}`);
    carregar();
  };

  const ativar = async (id) => {
    if (!window.confirm("Deseja ativar este funcionario?")) return;
    await api.post(`/funcionarios/${id}/ativar`);
    carregar();
  };

  const alternarAppAccess = (profileType) => {
    const atuais = new Set(form.app_access_profiles || []);
    if (atuais.has(profileType)) {
      atuais.delete(profileType);
    } else {
      atuais.add(profileType);
    }
    setForm({ ...form, app_access_profiles: Array.from(atuais) });
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

  const cargoSelecionado = useMemo(() => {
    if (!form?.cargo_id) return null;
    return cargos.find((cargo) => Number(cargo.id) === Number(form.cargo_id)) || null;
  }, [cargos, form?.cargo_id]);

  const resumoForm = useMemo(() => {
    if (!form || !cargoSelecionado) return null;

    const salario = Number(form.salario_base_override || cargoSelecionado.salario_base || 0);
    const usaEncargos =
      (cargoSelecionado.regime_remuneracao || "clt") === "clt" &&
      cargoSelecionado.gera_encargos !== false;
    const inssFuncionarioFixo = Number(cargoSelecionado.inss_funcionario_valor || 0);
    const inssFuncionario =
      usaEncargos && inssFuncionarioFixo > 0
        ? inssFuncionarioFixo
        : usaEncargos
          ? salario * Number(cargoSelecionado.inss_funcionario_percentual || 0) / 100
          : 0;
    const descontos =
      inssFuncionario +
      (usaEncargos ? Number(cargoSelecionado.desconto_transporte_valor || 0) : 0) +
      (usaEncargos ? Number(cargoSelecionado.outros_descontos_valor || 0) : 0);
    const liquidoHolerite = Math.max(0, salario - descontos);
    const liquidoCombinado = Number(form.liquido_combinado || 0);
    const complemento =
      form.complemento_modo === "manual"
        ? Number(form.complemento_fixo_valor || 0)
        : form.complemento_modo === "nenhum"
          ? 0
          : Math.max(0, liquidoCombinado - liquidoHolerite);
    const inssPatronal = usaEncargos
      ? salario * Number(cargoSelecionado.inss_patronal_percentual || 0) / 100
      : 0;
    const fgts = usaEncargos ? salario * Number(cargoSelecionado.fgts_percentual || 0) / 100 : 0;
    const ferias = usaEncargos && cargoSelecionado.gera_ferias ? salario / 12 : 0;
    const tercoFerias = usaEncargos && cargoSelecionado.gera_ferias ? salario / 36 : 0;
    const decimo = usaEncargos && cargoSelecionado.gera_decimo_terceiro ? salario / 12 : 0;

    return {
      salario,
      liquidoHolerite,
      complemento,
      custoTotal: salario + complemento + inssPatronal + fgts + ferias + tercoFerias + decimo,
    };
  }, [cargoSelecionado, form]);

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Funcionarios</h2>

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
          + Novo Funcionario
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left font-semibold">Nome</th>
              <th className="px-4 py-3 text-left font-semibold">Cargo</th>
              <th className="px-4 py-3 text-left font-semibold">Salario</th>
              <th className="px-4 py-3 text-left font-semibold">Custo mensal</th>
              <th className="px-4 py-3 text-center font-semibold">Status</th>
              <th className="px-4 py-3 text-center font-semibold">Acoes</th>
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
                  {f.remuneracao
                    ? formatarMoeda(f.remuneracao.salario_base)
                    : <span className="text-gray-400">-</span>}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {f.remuneracao ? (
                    <div>
                      <div className="font-medium text-gray-800">
                        {formatarMoeda(f.remuneracao.custo_total_empresa)}
                      </div>
                      <div className="text-xs text-gray-500">
                        Complemento {formatarMoeda(f.remuneracao.complemento_interno)}
                      </div>
                    </div>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
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
                      onClick={() => editarFuncionario(f)}
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
                    {!f.ativo && (
                      <button
                        className="px-3 py-1.5 text-xs font-medium rounded-md bg-green-50 text-green-700 hover:bg-green-100 border border-green-200 transition-colors"
                        onClick={() => ativar(f.id)}
                      >
                        Ativar
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {listaFiltrada.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400 italic">
                  Nenhum funcionario encontrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {form && (
        <div className="border rounded p-4 mt-6 bg-white">
          <h3 className="font-semibold mb-3">
            {form.id ? "Editar Funcionario" : "Novo Funcionario"}
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
              onChange={(e) => setForm({ ...form, telefone: e.target.value })}
            />

            <select
              className="border p-2 md:col-span-2"
              value={form.cargo_id}
              onChange={(e) => setForm({ ...form, cargo_id: e.target.value })}
            >
              <option value="">Selecione o cargo</option>
              {cargos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>

            <div className="md:col-span-2 border rounded-md p-3 bg-gray-50">
              <h4 className="font-semibold text-gray-800 mb-2">Acessos do app</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                {[
                  ["cliente", "Cliente"],
                  ["funcionario", "Funcionario"],
                  ["entregador", "Entregador"],
                  ["veterinario", "Veterinario"],
                ].map(([profileType, label]) => (
                  <label
                    key={profileType}
                    className="flex items-center gap-2 rounded border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
                  >
                    <input
                      type="checkbox"
                      checked={(form.app_access_profiles || []).includes(profileType)}
                      onChange={() => alternarAppAccess(profileType)}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="md:col-span-2 border-t pt-4">
              <h4 className="font-semibold text-gray-800 mb-3">Composicao de remuneracao</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="text-sm text-gray-700">
                  Salario base especifico
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="border p-2 w-full mt-1"
                    placeholder="Usa o salario do cargo"
                    value={form.salario_base_override}
                    onChange={(e) => setForm({ ...form, salario_base_override: e.target.value })}
                  />
                </label>

                <label className="text-sm text-gray-700">
                  Liquido combinado
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="border p-2 w-full mt-1"
                    placeholder="Ex: 2800.00"
                    value={form.liquido_combinado}
                    onChange={(e) => setForm({ ...form, liquido_combinado: e.target.value })}
                  />
                </label>

                <label className="text-sm text-gray-700">
                  Complemento interno
                  <select
                    className="border p-2 w-full mt-1"
                    value={form.complemento_modo}
                    onChange={(e) => setForm({ ...form, complemento_modo: e.target.value })}
                  >
                    <option value="automatico">Automatico pelo liquido combinado</option>
                    <option value="manual">Manual</option>
                    <option value="nenhum">Sem complemento</option>
                  </select>
                </label>

                <label className="text-sm text-gray-700">
                  Complemento manual (R$)
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="border p-2 w-full mt-1"
                    disabled={form.complemento_modo !== "manual"}
                    value={form.complemento_fixo_valor}
                    onChange={(e) => setForm({ ...form, complemento_fixo_valor: e.target.value })}
                  />
                </label>

                <textarea
                  className="border p-2 md:col-span-2"
                  rows={3}
                  placeholder="Observacoes internas sobre acordo, extra ou regra de pagamento"
                  value={form.remuneracao_observacoes || ""}
                  onChange={(e) => setForm({ ...form, remuneracao_observacoes: e.target.value })}
                />
              </div>
            </div>

            {resumoForm && (
              <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-4 gap-3">
                <div className="rounded border bg-gray-50 p-3">
                  <div className="text-xs text-gray-500">Base holerite</div>
                  <div className="font-semibold">{formatarMoeda(resumoForm.salario)}</div>
                </div>
                <div className="rounded border bg-gray-50 p-3">
                  <div className="text-xs text-gray-500">Liquido holerite</div>
                  <div className="font-semibold">{formatarMoeda(resumoForm.liquidoHolerite)}</div>
                </div>
                <div className="rounded border bg-blue-50 p-3">
                  <div className="text-xs text-blue-700">Complemento interno</div>
                  <div className="font-semibold text-blue-800">{formatarMoeda(resumoForm.complemento)}</div>
                </div>
                <div className="rounded border bg-green-50 p-3">
                  <div className="text-xs text-green-700">Custo total mensal</div>
                  <div className="font-semibold text-green-800">{formatarMoeda(resumoForm.custoTotal)}</div>
                </div>
              </div>
            )}
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
