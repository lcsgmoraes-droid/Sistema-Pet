import { useState } from "react";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import { reabrirCaixa } from "../../api/caixa";

export default function ModalReabrirCaixa({ caixa, onClose, onSuccess }) {
  const [motivo, setMotivo] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");
  const reabrir = async (event) => {
    event.preventDefault();
    setSalvando(true);
    try {
      await reabrirCaixa(caixa.id, motivo.trim());
      onSuccess();
    } catch (error) {
      setErro(error.response?.data?.detail || "Não foi possível reabrir o caixa.");
      setSalvando(false);
    }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <form
        onSubmit={reabrir}
        className="w-full max-w-lg rounded-xl bg-white p-6 text-slate-900 shadow-xl dark:bg-slate-900 dark:text-slate-100"
      >
        <h2 className="text-xl font-semibold">Reabrir caixa #{caixa.numero_caixa}</h2>
        <p className="mt-2 text-sm text-gray-600">
          O fechamento anterior ficará preservado no histórico da auditoria. O caixa voltará a
          aceitar lançamentos e precisará ser fechado novamente.
        </p>
        <InputTextoLongo
          id="motivo-reabertura"
          label="Motivo da reabertura"
          value={motivo}
          onChange={setMotivo}
          required
          maxLength={1000}
          help="Informe pelo menos 10 caracteres."
          placeholder="Descreva o que precisa ser corrigido ou conferido"
        />
        {erro && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {erro}
          </p>
        )}
        <div className="mt-5 flex justify-end gap-3">
          <BotaoCancelar
            type="button"
            disabled={salvando}
            onClick={onClose}
            className="rounded px-4 py-2"
          >
            Cancelar
          </BotaoCancelar>
          <BotaoSalva
            type="submit"
            disabled={salvando || motivo.trim().length < 10}
            className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
          >
            {salvando ? "Reabrindo..." : "Reabrir caixa"}
          </BotaoSalva>
        </div>
      </form>
    </div>
  );
}
