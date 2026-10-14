import { useState } from "react";
import api from "../../api";

export default function ModalDadosVendaFinalizada({ venda, onClose, onUpdated }) {
  const pagamentosCartao = (venda.pagamentos || []).filter((pagamento) =>
    /cart[aã]o/i.test(pagamento.forma_pagamento || ""),
  );
  const [observacoes, setObservacoes] = useState(venda.observacoes || "");
  const [nsus, setNsus] = useState(() =>
    Object.fromEntries(
      pagamentosCartao.map((pagamento) => [pagamento.id, pagamento.nsu_cartao || ""]),
    ),
  );
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  const salvar = async (event) => {
    event.preventDefault();
    setSalvando(true);
    setErro("");
    try {
      for (const pagamento of pagamentosCartao) {
        const nsu = (nsus[pagamento.id] || "").trim();
        if (nsu && nsu !== (pagamento.nsu_cartao || "")) {
          await api.patch(`/vendas/${venda.id}/pagamento/${pagamento.id}/nsu`, {
            nsu_cartao: nsu,
          });
        }
      }
      if (observacoes.trim() !== (venda.observacoes || "").trim()) {
        await api.patch(`/vendas/${venda.id}/observacoes`, { observacoes });
      }
      await onUpdated();
      onClose();
    } catch (error) {
      setErro(
        error.response?.data?.detail ||
          "Não foi possível salvar. Confira os dados e tente novamente.",
      );
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/50 p-4">
      <form
        onSubmit={salvar}
        className="max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl"
      >
        <h2 className="text-lg font-semibold text-gray-900">NSU e observação da venda</h2>
        <p className="mt-1 text-sm text-gray-600">
          Venda {venda.numero_venda}. A nota fiscal já emitida não será alterada.
        </p>
        {venda.nao_gerar_beneficios && (
          <div className="mt-4 rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm text-indigo-900">
            <strong>Benefícios de campanhas não gerados nesta venda.</strong>
            {venda.justificativa_nao_gerar_beneficios && (
              <p className="mt-1">Justificativa: {venda.justificativa_nao_gerar_beneficios}</p>
            )}
            {venda.beneficios_bloqueados_em && (
              <p className="mt-1 text-xs">
                Registrado em {new Date(venda.beneficios_bloqueados_em).toLocaleString("pt-BR")}
                {venda.beneficios_bloqueados_por_id &&
                  ` pelo usuário #${venda.beneficios_bloqueados_por_id}`}
              </p>
            )}
          </div>
        )}
        {pagamentosCartao.map((pagamento, index) => (
          <label key={pagamento.id} className="mt-4 block text-sm font-medium text-gray-800">
            NSU do cartão {pagamentosCartao.length > 1 ? index + 1 : ""}
            <input
              type="text"
              maxLength={50}
              value={nsus[pagamento.id] || ""}
              onChange={(event) =>
                setNsus((atuais) => ({ ...atuais, [pagamento.id]: event.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
              placeholder="Número da transação"
            />
          </label>
        ))}
        {pagamentosCartao.length === 0 && (
          <p className="mt-4 text-sm text-gray-500">Esta venda não tem pagamento em cartão.</p>
        )}
        <label className="mt-4 block text-sm font-medium text-gray-800">
          Observação da venda
          <textarea
            value={observacoes}
            onChange={(event) => setObservacoes(event.target.value)}
            maxLength={5000}
            rows={4}
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
          />
        </label>
        {erro && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {erro}
          </p>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={salvando}
            className="rounded-lg border border-gray-300 px-4 py-2 disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={salvando}
            className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white disabled:opacity-50"
          >
            {salvando ? "Salvando..." : "Salvar"}
          </button>
        </div>
      </form>
    </div>
  );
}
