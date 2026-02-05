import { useState, useEffect } from "react";
import api from "../api";
import toast from "react-hot-toast";

export default function ProjecaoCaixa() {
  const [mesesAFrente, setMesesAFrente] = useState(3);
  const [projecao, setProjecao] = useState([]);
  const [resumo, setResumo] = useState(null);
  const [loading, setLoading] = useState(false);

  const meses = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
  ];

  useEffect(() => {
    buscarProjecao();
  }, [mesesAFrente]);

  const buscarProjecao = async () => {
    setLoading(true);
    try {
      const [resProjecao, resResumo] = await Promise.all([
        api.get(`/projecao-caixa/?meses_a_frente=${mesesAFrente}`),
        api.get(`/projecao-caixa/resumo?meses_a_frente=${mesesAFrente}`)
      ]);

      if (resProjecao.data.sucesso) {
        setProjecao(resProjecao.data.projecao || []);
      }

      if (resResumo.data.sucesso) {
        setResumo(resResumo.data.resumo || null);
      }
    } catch (error) {
      console.error("Erro ao buscar projeção:", error);
      toast.error("Erro ao carregar projeção de caixa");
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

  const getTendenciaBadge = (tendencia) => {
    const cores = {
      POSITIVO: "bg-green-100 text-green-800",
      NEGATIVO: "bg-red-100 text-red-800",
      MISTO: "bg-yellow-100 text-yellow-800",
      NEUTRO: "bg-gray-100 text-gray-800"
    };

    const textos = {
      POSITIVO: "📈 Todos os meses positivos",
      NEGATIVO: "📉 Todos os meses negativos",
      MISTO: "⚠️ Meses positivos e negativos",
      NEUTRO: "➖ Sem dados"
    };

    return (
      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${cores[tendencia] || cores.NEUTRO}`}>
        {textos[tendencia] || textos.NEUTRO}
      </span>
    );
  };

  const getSaldoBadge = (valor) => {
    if (valor > 0) {
      return <span className="text-green-600 font-bold">{formatarMoeda(valor)}</span>;
    } else if (valor < 0) {
      return <span className="text-red-600 font-bold">{formatarMoeda(valor)}</span>;
    } else {
      return <span className="text-gray-600 font-bold">{formatarMoeda(valor)}</span>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          💰 Projeção de Caixa
        </h1>
        <p className="text-gray-600">
          Projeção futura baseada em histórico real + provisões obrigatórias
        </p>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">
            Projetar para:
          </label>
          <select
            value={mesesAFrente}
            onChange={(e) => setMesesAFrente(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={3}>3 meses</option>
            <option value={6}>6 meses</option>
            <option value={12}>12 meses</option>
          </select>
        </div>
      </div>

      {/* Resumo */}
      {resumo && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">📊 Resumo da Projeção</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <p className="text-sm text-gray-600 mb-1">Receita Total Projetada</p>
              <p className="text-2xl font-bold text-green-600">
                {formatarMoeda(resumo.receita_total)}
              </p>
            </div>

            <div className="bg-white rounded-lg p-4 shadow-sm">
              <p className="text-sm text-gray-600 mb-1">Despesas Totais Projetadas</p>
              <p className="text-2xl font-bold text-red-600">
                {formatarMoeda(resumo.despesas_totais)}
              </p>
            </div>

            <div className="bg-white rounded-lg p-4 shadow-sm">
              <p className="text-sm text-gray-600 mb-1">Saldo Total Projetado</p>
              <p className={`text-2xl font-bold ${resumo.saldo_total >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatarMoeda(resumo.saldo_total)}
              </p>
            </div>

            <div className="bg-white rounded-lg p-4 shadow-sm">
              <p className="text-sm text-gray-600 mb-1">Meses Positivos / Negativos</p>
              <p className="text-2xl font-bold text-gray-900">
                <span className="text-green-600">{resumo.meses_positivos}</span>
                {" / "}
                <span className="text-red-600">{resumo.meses_negativos}</span>
              </p>
            </div>
          </div>

          <div className="flex justify-center mt-4">
            {getTendenciaBadge(resumo.tendencia)}
          </div>
        </div>
      )}

      {/* Tabela de Projeção */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            📅 Projeção Mês a Mês
          </h2>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p className="mt-2 text-gray-600">Calculando projeção...</p>
          </div>
        ) : projecao.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg mb-2">📊 Sem dados suficientes</p>
            <p className="text-sm">É necessário ter pelo menos 3 meses de histórico para gerar projeções.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Mês
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Receita Prevista
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Imposto Simples
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Folha + Encargos
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Despesas Totais
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Saldo Previsto
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {projecao.map((p) => (
                  <tr key={p.mes_futuro} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {meses[p.mes - 1]}/{p.ano}
                      </div>
                      <div className="text-xs text-gray-500">
                        +{p.mes_futuro} {p.mes_futuro === 1 ? 'mês' : 'meses'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-green-600 font-semibold">
                      {formatarMoeda(p.receita_prevista)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-orange-600">
                      {formatarMoeda(p.imposto_simples_previsto)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-blue-600">
                      {formatarMoeda(p.folha_encargos_previstos)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-red-600">
                      {formatarMoeda(p.despesas_previstas)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                      {getSaldoBadge(p.saldo_previsto)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {p.saldo_positivo ? (
                        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">
                          ✓ Positivo
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">
                          ⚠ Negativo
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          <strong>💡 Como funciona a projeção:</strong>
        </p>
        <ul className="mt-2 text-sm text-blue-800 list-disc list-inside space-y-1">
          <li>Média de receitas dos últimos 3 meses (valores reais)</li>
          <li>Média de despesas fixas (custos + operacionais)</li>
          <li>Alíquota atual do Simples Nacional aplicada sobre receita projetada</li>
          <li>Folha de pagamento + encargos (INSS + FGTS ~28%)</li>
          <li><strong>Sem chutes</strong> – Apenas dados reais + regras contábeis</li>
        </ul>
      </div>
    </div>
  );
}
