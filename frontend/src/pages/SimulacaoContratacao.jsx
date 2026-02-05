import { useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

export default function SimulacaoContratacao() {
  const [formData, setFormData] = useState({
    salario_base: "",
    inss_percentual: "20",
    fgts_percentual: "8",
    meses: "6",
    cargo: "",
  });

  const [simulacao, setSimulacao] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mostrarDetalhes, setMostrarDetalhes] = useState(true);

  const meses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const simular = async (e) => {
    e.preventDefault();

    // Validações
    if (!formData.salario_base || parseFloat(formData.salario_base) <= 0) {
      toast.error("Informe um salário válido");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        salario_base: parseFloat(formData.salario_base),
        inss_percentual: parseFloat(formData.inss_percentual),
        fgts_percentual: parseFloat(formData.fgts_percentual),
        meses: parseInt(formData.meses),
        cargo: formData.cargo || null,
      };

      const response = await api.post("/simulacao-contratacao/", payload);

      if (response.data.sucesso) {
        setSimulacao(response.data.simulacao);
        toast.success("Simulação realizada com sucesso!");
      }
    } catch (error) {
      console.error("Erro ao simular contratação:", error);
      toast.error("Erro ao realizar simulação");
    } finally {
      setLoading(false);
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(valor);
  };

  const formatarPercentual = (valor) => {
    return new Intl.NumberFormat("pt-BR", {
      style: "percent",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(valor / 100);
  };

  const limparSimulacao = () => {
    setSimulacao(null);
    setFormData({
      salario_base: "",
      inss_percentual: "20",
      fgts_percentual: "8",
      meses: "6",
      cargo: "",
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          🧮 Simulação de Contratação
        </h1>
        <p className="text-gray-600">
          Calcule o impacto real de contratar um funcionário no seu negócio
        </p>
      </div>

      {/* Formulário */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          📝 Dados da Contratação
        </h2>

        <form onSubmit={simular} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Cargo */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cargo (opcional)
              </label>
              <input
                type="text"
                name="cargo"
                value={formData.cargo}
                onChange={handleChange}
                placeholder="Ex: Atendente, Veterinário..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Salário Base */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Salário Base <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="salario_base"
                value={formData.salario_base}
                onChange={handleChange}
                placeholder="Ex: 2000.00"
                step="0.01"
                min="0"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* INSS */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                INSS Patronal (%)
              </label>
              <input
                type="number"
                name="inss_percentual"
                value={formData.inss_percentual}
                onChange={handleChange}
                step="0.01"
                min="0"
                max="100"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* FGTS */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                FGTS (%)
              </label>
              <input
                type="number"
                name="fgts_percentual"
                value={formData.fgts_percentual}
                onChange={handleChange}
                step="0.01"
                min="0"
                max="100"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Meses */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Simular por quantos meses?
              </label>
              <select
                name="meses"
                value={formData.meses}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="3">3 meses</option>
                <option value="6">6 meses</option>
                <option value="12">12 meses (1 ano)</option>
                <option value="24">24 meses (2 anos)</option>
              </select>
            </div>
          </div>

          {/* Botões */}
          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? "Calculando..." : "🧮 Simular Contratação"}
            </button>

            {simulacao && (
              <button
                type="button"
                onClick={limparSimulacao}
                className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
              >
                🔄 Nova Simulação
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Resultado da Simulação */}
      {simulacao && (
        <>
          {/* Resumo Executivo */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">
              📊 Resumo Executivo
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-600 mb-1">Custo Mensal Médio</p>
                <p className="text-2xl font-bold text-blue-600">
                  {formatarMoeda(simulacao.totais.media_mensal)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatarPercentual(simulacao.analise.custo_total_vs_salario)} do salário base
                </p>
              </div>

              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-600 mb-1">Custo Total ({simulacao.parametros.meses_simulados} meses)</p>
                <p className="text-2xl font-bold text-purple-600">
                  {formatarMoeda(simulacao.totais.total_geral)}
                </p>
              </div>

              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-600 mb-1">Encargos Totais</p>
                <p className="text-2xl font-bold text-orange-600">
                  {formatarMoeda(simulacao.totais.total_inss + simulacao.totais.total_fgts)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatarPercentual(simulacao.analise.percentual_encargos)} do salário
                </p>
              </div>

              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-sm text-gray-600 mb-1">Provisões Totais</p>
                <p className="text-2xl font-bold text-green-600">
                  {formatarMoeda(
                    simulacao.totais.total_provisao_ferias +
                    simulacao.totais.total_provisao_1_3 +
                    simulacao.totais.total_provisao_13
                  )}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatarPercentual(simulacao.analise.percentual_provisoes)} do salário
                </p>
              </div>
            </div>

            {/* Alerta de Impacto */}
            <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-yellow-900">
                <strong>⚠️ Atenção:</strong> O custo real mensal é{" "}
                <strong>{formatarMoeda(simulacao.totais.media_mensal)}</strong>, não apenas{" "}
                <strong>{formatarMoeda(simulacao.parametros.salario_base)}</strong>.
                Isso representa um aumento de{" "}
                <strong>
                  {formatarPercentual(simulacao.analise.custo_total_vs_salario - 100)}
                </strong>{" "}
                devido a encargos e provisões obrigatórias.
              </p>
            </div>
          </div>

          {/* Tabela Detalhada */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">
                📅 Detalhamento Mensal
              </h2>
              <button
                onClick={() => setMostrarDetalhes(!mostrarDetalhes)}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                {mostrarDetalhes ? "▼ Ocultar detalhes" : "▶ Mostrar detalhes"}
              </button>
            </div>

            {mostrarDetalhes && (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Mês
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Salário
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        INSS ({simulacao.parametros.inss_percentual}%)
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        FGTS ({simulacao.parametros.fgts_percentual}%)
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Férias (1/12)
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        1/3 Const.
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        13º (1/12)
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Custo Total
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {simulacao.resultado_mensal.map((mes) => (
                      <tr key={mes.mes} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {meses[mes.mes_calendario - 1]}/{mes.ano}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                          {formatarMoeda(mes.salario)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-orange-600">
                          {formatarMoeda(mes.inss)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-blue-600">
                          {formatarMoeda(mes.fgts)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                          {formatarMoeda(mes.provisao_ferias)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                          {formatarMoeda(mes.provisao_1_3)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-600">
                          {formatarMoeda(mes.provisao_13)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-bold text-gray-900">
                          {formatarMoeda(mes.custo_total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-gray-100 font-bold">
                    <tr>
                      <td className="px-6 py-4 text-sm text-gray-900">TOTAL</td>
                      <td className="px-6 py-4 text-sm text-right text-gray-900">
                        {formatarMoeda(simulacao.totais.total_salarios)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-orange-600">
                        {formatarMoeda(simulacao.totais.total_inss)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-blue-600">
                        {formatarMoeda(simulacao.totais.total_fgts)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-green-600">
                        {formatarMoeda(simulacao.totais.total_provisao_ferias)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-green-600">
                        {formatarMoeda(simulacao.totais.total_provisao_1_3)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-green-600">
                        {formatarMoeda(simulacao.totais.total_provisao_13)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-900">
                        {formatarMoeda(simulacao.totais.total_geral)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>

          {/* Disclaimer */}
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>💡 Como funciona esta simulação:</strong>
            </p>
            <ul className="mt-2 text-sm text-blue-800 list-disc list-inside space-y-1">
              <li><strong>Nada é gravado no banco</strong> - é apenas uma projeção</li>
              <li>Custos diretos: Salário + INSS patronal + FGTS</li>
              <li>Provisões obrigatórias: Férias (1/12) + 1/3 constitucional + 13º (1/12)</li>
              <li>Não considera: Vale-transporte, Vale-refeição, Plano de saúde</li>
              <li>Baseado nas mesmas regras do motor de provisões real</li>
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
