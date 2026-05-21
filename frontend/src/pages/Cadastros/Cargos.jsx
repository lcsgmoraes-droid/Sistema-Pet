import { useEffect, useState } from "react";
import api from "../../api";
import toast from "react-hot-toast";
import {
  normalizarCamposRemuneracao,
  numeroCampoParaFloat,
  sincronizarCampoRemuneracao,
} from "./cargosRemuneracaoUtils";

export default function Cargos() {
  const [cargos, setCargos] = useState([]);
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);

  const cargoPadrao = () => ({
    nome: "",
    descricao: "",
    salario_base: "",
    regime_remuneracao: "clt",
    gera_encargos: true,
    inss_patronal_percentual: 20,
    inss_patronal_valor: 0,
    fgts_percentual: 8,
    fgts_valor: 0,
    inss_funcionario_percentual: 0,
    inss_funcionario_valor: 0,
    desconto_transporte_valor: 0,
    outros_descontos_valor: 0,
    gera_ferias: true,
    gera_decimo_terceiro: true,
    ativo: true,
  });

  const prepararCargo = (dados) => {
    const { inss_patronal_valor, fgts_valor, ...dadosPersistiveis } = dados;
    return {
      ...dadosPersistiveis,
      salario_base: numeroCampoParaFloat(dados.salario_base),
      inss_patronal_percentual: numeroCampoParaFloat(dados.inss_patronal_percentual),
      fgts_percentual: numeroCampoParaFloat(dados.fgts_percentual),
      inss_funcionario_percentual: numeroCampoParaFloat(dados.inss_funcionario_percentual),
      inss_funcionario_valor: numeroCampoParaFloat(dados.inss_funcionario_valor),
      desconto_transporte_valor: numeroCampoParaFloat(dados.desconto_transporte_valor),
      outros_descontos_valor: numeroCampoParaFloat(dados.outros_descontos_valor),
    };
  };

  const editarCargo = (cargo) => {
    setForm(normalizarCamposRemuneracao({ ...cargoPadrao(), ...cargo }));
  };

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
    setForm(normalizarCamposRemuneracao(cargoPadrao()));
  };

  const atualizarCampoRemuneracao = (campo, valor) => {
    setForm((formAtual) => sincronizarCampoRemuneracao(formAtual, campo, valor));
  };

  const salvarCargo = async () => {
    if (!form.nome || !form.salario_base) {
      toast.error("Nome e salário são obrigatórios");
      return;
    }

    try {
      const payload = prepararCargo(form);
      if (form.id) {
        await api.put(`/cargos/${form.id}`, payload);
        toast.success("Cargo atualizado com sucesso!");
      } else {
        await api.post("/cargos", payload);
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
                Regime
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
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                  <div className="font-medium uppercase">{c.regime_remuneracao || "clt"}</div>
                  <div className="text-xs text-gray-400">
                    {c.gera_encargos ? "Com encargos" : "Sem encargos"}
                  </div>
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
                    onClick={() => editarCargo(c)}
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
                onChange={(e) => atualizarCampoRemuneracao("salario_base", e.target.value)}
              />
            </div>

            <div className="md:col-span-2 border-t border-gray-200 pt-4 mt-2">
              <h3 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">
                Composicao de remuneracao
              </h3>
            </div>

            <div className="md:col-span-2 border-l-4 border-indigo-400 bg-indigo-50 px-4 py-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
                  i
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-indigo-950">Guia rapido da folha</h4>
                  <div className="mt-2 grid grid-cols-1 gap-2 text-xs leading-5 text-indigo-900 md:grid-cols-2">
                    <p>
                      <strong>Salario base:</strong> use o valor bruto do holerite ou contrato. Ele alimenta provisoes, DRE e encargos.
                    </p>
                    <p>
                      <strong>INSS patronal e FGTS:</strong> sao custos da empresa calculados sobre o salario base.
                    </p>
                    <p>
                      <strong>INSS funcionario:</strong> e desconto do colaborador e reduz o liquido da folha.
                    </p>
                    <p>
                      <strong>Regimes sem encargos:</strong> use quando nao houver calculo de ferias, 13o, FGTS ou INSS patronal.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Regime
              </label>
              <select
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.regime_remuneracao || "clt"}
                onChange={(e) => {
                  const regime = e.target.value;
                  setForm({
                    ...form,
                    regime_remuneracao: regime,
                    gera_encargos: regime === "clt" ? form.gera_encargos : false,
                    gera_ferias: regime === "clt" ? form.gera_ferias : false,
                    gera_decimo_terceiro: regime === "clt" ? form.gera_decimo_terceiro : false,
                  });
                }}
              >
                <option value="clt">CLT</option>
                <option value="sem_encargos">Simples sem encargos</option>
                <option value="estagio">Estagio</option>
                <option value="informal">Informal</option>
              </select>
            </div>

            <div className="flex items-center pt-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!form.gera_encargos}
                  onChange={(e) => setForm({ ...form, gera_encargos: e.target.checked })}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  disabled={(form.regime_remuneracao || "clt") !== "clt"}
                />
                <span className="text-sm text-gray-700">Considera encargos e descontos</span>
              </label>
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
                onChange={(e) => atualizarCampoRemuneracao("inss_patronal_percentual", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                INSS Patronal (R$)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.inss_patronal_valor}
                onChange={(e) => atualizarCampoRemuneracao("inss_patronal_valor", e.target.value)}
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
                onChange={(e) => atualizarCampoRemuneracao("fgts_percentual", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                FGTS (R$)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.fgts_valor}
                onChange={(e) => atualizarCampoRemuneracao("fgts_valor", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                INSS Funcionario (%)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.inss_funcionario_percentual}
                onChange={(e) => atualizarCampoRemuneracao("inss_funcionario_percentual", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                INSS Funcionario (R$)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.inss_funcionario_valor}
                onChange={(e) => atualizarCampoRemuneracao("inss_funcionario_valor", e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Desconto transporte (R$)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.desconto_transporte_valor}
                onChange={(e) => setForm({ ...form, desconto_transporte_valor: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Outros descontos (R$)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                value={form.outros_descontos_valor}
                onChange={(e) => setForm({ ...form, outros_descontos_valor: e.target.value })}
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
