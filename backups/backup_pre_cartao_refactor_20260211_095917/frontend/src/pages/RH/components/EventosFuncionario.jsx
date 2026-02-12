import { useEffect, useState } from "react";
import { api } from "../../../services/api";

export default function EventosFuncionario({ funcionario, onClose }) {
  const [provisoes, setProvisoes] = useState(null);
  const [loading, setLoading] = useState(false);

  const carregarProvisoes = async () => {
    const res = await api.get(
      `/funcionarios/${funcionario.id}/provisoes`
    );
    setProvisoes(res.data);
  };

  useEffect(() => {
    carregarProvisoes();
  }, []);

  const concederFerias = async () => {
    if (!window.confirm("Confirmar concessão de férias?")) return;
    setLoading(true);
    
    try {
      const hoje = new Date();
      const payload = {
        mes: hoje.getMonth() + 1,
        ano: hoje.getFullYear(),
        dias_ferias: 30,
        data_pagamento: null
      };
      
      await api.post(`/funcionarios/${funcionario.id}/ferias`, payload);
      await carregarProvisoes();
      alert("Férias concedidas com sucesso");
    } catch (error) {
      console.error("Erro ao conceder férias:", error);
      alert(error.response?.data?.detail || "Erro ao conceder férias");
    } finally {
      setLoading(false);
    }
  };

  const pagarDecimo = async (parcela) => {
    if (
      !window.confirm(
        `Confirmar pagamento da ${parcela}ª parcela do 13º?`
      )
    )
      return;

    setLoading(true);
    
    try {
      const hoje = new Date();
      const payload = {
        mes: hoje.getMonth() + 1,
        ano: hoje.getFullYear(),
        percentual: parcela === 1 ? 50 : 100,
        descricao_parcela: parcela === 1 ? "1ª Parcela" : "2ª Parcela",
        data_pagamento: null
      };
      
      await api.post(
        `/funcionarios/${funcionario.id}/decimo-terceiro`,
        payload
      );
      await carregarProvisoes();
      alert("13º registrado com sucesso");
    } catch (error) {
      console.error("Erro ao pagar 13º:", error);
      alert(error.response?.data?.detail || "Erro ao pagar 13º");
    } finally {
      setLoading(false);
    }
  };

  if (!provisoes) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center">
      <div className="bg-white rounded p-6 w-[500px]">
        <h3 className="text-lg font-semibold mb-4">
          Eventos — {funcionario.nome}
        </h3>

        {/* Provisões */}
        <div className="mb-4">
          <h4 className="font-semibold mb-2">Provisões</h4>
          <p>Férias: R$ {Number(provisoes.ferias || 0).toFixed(2)}</p>
          <p>13º: R$ {Number(provisoes.decimo_terceiro || 0).toFixed(2)}</p>
        </div>

        {/* Ações */}
        <div className="space-y-2">
          <button
            disabled={loading}
            onClick={concederFerias}
            className="w-full bg-blue-600 text-white py-2 rounded"
          >
            Conceder Férias
          </button>

          <button
            disabled={loading}
            onClick={() => pagarDecimo(1)}
            className="w-full bg-green-600 text-white py-2 rounded"
          >
            Pagar 1ª Parcela do 13º
          </button>

          <button
            disabled={loading}
            onClick={() => pagarDecimo(2)}
            className="w-full bg-green-700 text-white py-2 rounded"
          >
            Pagar 2ª Parcela do 13º
          </button>
        </div>

        <div className="mt-4 text-right">
          <button
            onClick={onClose}
            className="text-gray-600 underline"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
