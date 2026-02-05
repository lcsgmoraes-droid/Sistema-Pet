import { useEffect, useState } from "react";
import { api } from "../../services/api";

export default function CustosMoto() {
  const [form, setForm] = useState({
    preco_combustivel: "",
    km_por_litro: "",
    km_troca_oleo: "",
    custo_troca_oleo: "",
    km_troca_pneu_dianteiro: "",
    custo_pneu_dianteiro: "",
    km_troca_pneu_traseiro: "",
    custo_pneu_traseiro: "",
    km_troca_kit_traseiro: "",
    custo_kit_traseiro: "",
    km_manutencao_geral: "",
    custo_manutencao_geral: "",
    seguro_mensal: "",
    licenciamento_mensal: "",
    ipva_mensal: "",
    outros_custos_mensais: "",
    km_medio_mensal: "",
  });

  const [loading, setLoading] = useState(false);

  // Funções de cálculo de custo por KM
  const calcularCustoCombustivelPorKm = () => {
    const preco = parseFloat(form.preco_combustivel) || 0;
    const kmPorLitro = parseFloat(form.km_por_litro) || 1;
    return kmPorLitro > 0 ? (preco / kmPorLitro).toFixed(4) : "0.0000";
  };

  const calcularCustoOleoPorKm = () => {
    const custo = parseFloat(form.custo_troca_oleo) || 0;
    const km = parseFloat(form.km_troca_oleo) || 1;
    return km > 0 ? (custo / km).toFixed(4) : "0.0000";
  };

  const calcularCustoPneuDianteiroPorKm = () => {
    const custo = parseFloat(form.custo_pneu_dianteiro) || 0;
    const km = parseFloat(form.km_troca_pneu_dianteiro) || 1;
    return km > 0 ? (custo / km).toFixed(4) : "0.0000";
  };

  const calcularCustoPneuTraseiroPorKm = () => {
    const custo = parseFloat(form.custo_pneu_traseiro) || 0;
    const km = parseFloat(form.km_troca_pneu_traseiro) || 1;
    return km > 0 ? (custo / km).toFixed(4) : "0.0000";
  };

  const calcularCustoKitPorKm = () => {
    const custo = parseFloat(form.custo_kit_traseiro) || 0;
    const km = parseFloat(form.km_troca_kit_traseiro) || 1;
    return km > 0 ? (custo / km).toFixed(4) : "0.0000";
  };

  const calcularCustoManutencaoPorKm = () => {
    const custo = parseFloat(form.custo_manutencao_geral) || 0;
    const km = parseFloat(form.km_manutencao_geral) || 1;
    return km > 0 ? (custo / km).toFixed(4) : "0.0000";
  };

  const calcularCustoFixoPorKm = () => {
    const seguro = parseFloat(form.seguro_mensal) || 0;
    const licenciamento = parseFloat(form.licenciamento_mensal) || 0;
    const ipva = parseFloat(form.ipva_mensal) || 0;
    const outros = parseFloat(form.outros_custos_mensais) || 0;
    const totalFixo = seguro + licenciamento + ipva + outros;
    const kmMedio = parseFloat(form.km_medio_mensal) || 1;
    return kmMedio > 0 ? (totalFixo / kmMedio).toFixed(4) : "0.0000";
  };

  useEffect(() => {
    carregarConfiguracao();
  }, []);

  async function carregarConfiguracao() {
    const res = await api.get("/configuracoes/custo-moto");
    // Converter null para string vazia para evitar warning do React
    const data = res.data;
    Object.keys(data).forEach(key => {
      if (data[key] === null) {
        data[key] = "";
      }
    });
    setForm(data);
  }

  function handleChange(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  }

  function preencherValoresSugeridos() {
    if (!confirm("Preencher com valores sugeridos baseados em uma moto de entrega típica (CG 160, Biz 125, Pop 110)? Os valores atuais serão substituídos.")) {
      return;
    }
    
    setForm({
      // Combustível (gasolina comum Brasil - fev/2026)
      preco_combustivel: "6.30",
      km_por_litro: "38",
      
      // Óleo do motor
      km_troca_oleo: "3000",
      custo_troca_oleo: "95.00",
      
      // Pneu dianteiro (menos desgaste)
      km_troca_pneu_dianteiro: "14000",
      custo_pneu_dianteiro: "210.00",
      
      // Pneu traseiro (mais desgaste - tração)
      km_troca_pneu_traseiro: "10000",
      custo_pneu_traseiro: "240.00",
      
      // Kit transmissão (corrente, coroa, pinhão)
      km_troca_kit_traseiro: "18000",
      custo_kit_traseiro: "420.00",
      
      // Manutenção preventiva geral
      km_manutencao_geral: "5000",
      custo_manutencao_geral: "180.00",
      
      // Custos fixos mensais
      seguro_mensal: "110.00",
      licenciamento_mensal: "32.00",
      ipva_mensal: "55.00", // Aprox. 2.5% de R$ 15k ÷ 12
      outros_custos_mensais: "75.00", // Lavagem, pequenos reparos
      
      // Quilometragem média mensal
      km_medio_mensal: "1200",
    });
  }

  async function salvar() {
    setLoading(true);
    await api.put("/configuracoes/custo-moto", form);
    setLoading(false);
    alert("Custos da moto salvos com sucesso");
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800">🏍️ Custos da Moto</h2>
        <p className="text-gray-600 mt-1">Configure os custos operacionais da moto de entregas</p>
        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
          💡 <strong>Dica:</strong> Não sabe por onde começar? Clique em "Preencher com Valores Sugeridos" para usar custos típicos de uma moto de entrega (CG 160, Biz 125, Pop 110 na faixa de R$ 15 mil). Depois ajuste conforme sua realidade.
        </div>
        <div className="mt-4">
          <button
            onClick={preencherValoresSugeridos}
            className="px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors shadow-sm flex items-center gap-2"
          >
            <span>💡</span> Preencher com Valores Sugeridos
          </button>
        </div>
      </div>

      {/* COMBUSTÍVEL */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span>⛽</span> Combustível
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Preço por Litro (R$)
            </label>
            <input
              type="number"
              step="0.01"
              name="preco_combustivel"
              placeholder="Ex: 6.50"
              value={form.preco_combustivel}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Consumo Médio (KM/Litro)
            </label>
            <input
              type="number"
              step="0.1"
              name="km_por_litro"
              placeholder="Ex: 35"
              value={form.km_por_litro}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              💰 Custo por KM
            </label>
            <div className="w-full px-3 py-2 bg-blue-50 border border-blue-200 rounded-md text-blue-900 font-semibold text-lg">
              R$ {calcularCustoCombustivelPorKm()}
            </div>
          </div>
        </div>
      </div>

      {/* MANUTENÇÃO */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span>🛠️</span> Manutenção (Custos Variáveis por KM)
        </h3>
        
        {/* Óleo */}
        <div className="mb-4 pb-4 border-b border-gray-100">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Troca de Óleo</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-2">KM para Troca</label>
              <input
                type="number"
                name="km_troca_oleo"
                placeholder="Ex: 3000"
                value={form.km_troca_oleo}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">Custo por Troca (R$)</label>
              <input
                type="number"
                step="0.01"
                name="custo_troca_oleo"
                placeholder="Ex: 150.00"
                value={form.custo_troca_oleo}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">💰 Custo por KM</label>
              <div className="w-full px-3 py-2 bg-green-50 border border-green-200 rounded-md text-green-900 font-semibold">
                R$ {calcularCustoOleoPorKm()}
              </div>
            </div>
          </div>
        </div>

        {/* Pneu Dianteiro */}
        <div className="mb-4 pb-4 border-b border-gray-100">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Pneu Dianteiro</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-2">Vida Útil (KM)</label>
              <input
                type="number"
                name="km_troca_pneu_dianteiro"
                placeholder="Ex: 15000"
                value={form.km_troca_pneu_dianteiro}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">Preço do Pneu (R$)</label>
              <input
                type="number"
                step="0.01"
                name="custo_pneu_dianteiro"
                placeholder="Ex: 250.00"
                value={form.custo_pneu_dianteiro}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">💰 Custo por KM</label>
              <div className="w-full px-3 py-2 bg-green-50 border border-green-200 rounded-md text-green-900 font-semibold">
                R$ {calcularCustoPneuDianteiroPorKm()}
              </div>
            </div>
          </div>
        </div>

        {/* Pneu Traseiro */}
        <div className="mb-4 pb-4 border-b border-gray-100">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Pneu Traseiro</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-2">Vida Útil (KM)</label>
              <input
                type="number"
                name="km_troca_pneu_traseiro"
                placeholder="Ex: 12000"
                value={form.km_troca_pneu_traseiro}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">Preço do Pneu (R$)</label>
              <input
                type="number"
                step="0.01"
                name="custo_pneu_traseiro"
                placeholder="Ex: 280.00"
                value={form.custo_pneu_traseiro}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">💰 Custo por KM</label>
              <div className="w-full px-3 py-2 bg-green-50 border border-green-200 rounded-md text-green-900 font-semibold">
                R$ {calcularCustoPneuTraseiroPorKm()}
              </div>
            </div>
          </div>
        </div>

        {/* Kit Transmissão */}
        <div className="mb-4 pb-4 border-b border-gray-100">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Kit Transmissão (Corrente, Coroa, Pinhão)</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-2">Vida Útil do Kit (KM)</label>
              <input
                type="number"
                name="km_troca_kit_traseiro"
                placeholder="Ex: 20000"
                value={form.km_troca_kit_traseiro}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">Preço do Kit (R$)</label>
              <input
                type="number"
                step="0.01"
                name="custo_kit_traseiro"
                placeholder="Ex: 450.00"
                value={form.custo_kit_traseiro}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">💰 Custo por KM</label>
              <div className="w-full px-3 py-2 bg-green-50 border border-green-200 rounded-md text-green-900 font-semibold">
                R$ {calcularCustoKitPorKm()}
              </div>
            </div>
          </div>
        </div>

        {/* Manutenção Geral */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">Manutenção Geral</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-2">Frequência (KM)</label>
              <input
                type="number"
                name="km_manutencao_geral"
                placeholder="Ex: 5000"
                value={form.km_manutencao_geral}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">Custo por Manutenção (R$)</label>
              <input
                type="number"
                step="0.01"
                name="custo_manutencao_geral"
                placeholder="Ex: 200.00"
                value={form.custo_manutencao_geral}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">💰 Custo por KM</label>
              <div className="w-full px-3 py-2 bg-green-50 border border-green-200 rounded-md text-green-900 font-semibold">
                R$ {calcularCustoManutencaoPorKm()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CUSTOS FIXOS MENSAIS */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span>📄</span> Custos Fixos Mensais
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Seguro Mensal (R$)</label>
            <input
              type="number"
              step="0.01"
              name="seguro_mensal"
              placeholder="Ex: 120.00"
              value={form.seguro_mensal}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Licenciamento Mensal (R$)</label>
            <input
              type="number"
              step="0.01"
              name="licenciamento_mensal"
              placeholder="Ex: 30.00"
              value={form.licenciamento_mensal}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">IPVA Mensal (R$)</label>
            <input
              type="number"
              step="0.01"
              name="ipva_mensal"
              placeholder="Ex: 50.00"
              value={form.ipva_mensal}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Outros Custos Mensais (R$)</label>
            <input
              type="number"
              step="0.01"
              name="outros_custos_mensais"
              placeholder="Ex: 100.00"
              value={form.outros_custos_mensais}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* CONTROLE */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span>📊</span> Controle
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              KM Médio Mensal (para cálculo de custos fixos)
            </label>
            <input
              type="number"
              step="0.01"
              name="km_medio_mensal"
              placeholder="Ex: 1000"
              value={form.km_medio_mensal}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Usado para ratear os custos fixos mensais por KM rodado
            </p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              💰 Custo Fixo por KM
            </label>
            <div className="w-full px-3 py-2 bg-purple-50 border border-purple-200 rounded-md text-purple-900 font-semibold text-lg">
              R$ {calcularCustoFixoPorKm()}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Total dos custos fixos ÷ KM médio mensal
            </p>
          </div>
        </div>
      </div>

      {/* BOTÃO SALVAR */}
      <div className="flex justify-end">
        <button
          onClick={salvar}
          disabled={loading}
          className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          {loading ? "Salvando..." : "💾 Salvar Configurações"}
        </button>
      </div>
    </div>
  );
}
