import { useEffect } from "react";
import { DoorOpen, X } from "lucide-react";

import ActionButton from "../../../components/ui/ActionButton";
import IconActionButton from "../../../components/ui/IconActionButton";
import { TextField } from "../../../components/ui/FormField";
import { shouldCloseModalWithKeyboardEvent } from "./modalKeyboardUtils";

export default function NovoConsultorioInlineModal({
  erro,
  form,
  isOpen,
  onChange,
  onClose,
  onSubmit,
  salvando,
}) {
  useEffect(() => {
    if (!isOpen) return undefined;

    function handleKeyDown(event) {
      if (shouldCloseModalWithKeyboardEvent(event)) {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/35 p-4"
      onClick={onClose}
    >
      <form
        className="w-full max-w-lg rounded-xl bg-white p-5 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
              <DoorOpen size={22} aria-hidden="true" />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">Novo consultorio</h3>
            <p className="mt-1 text-sm text-slate-500">
              Cadastre uma sala e continue o agendamento sem sair desta tela.
            </p>
          </div>
          <IconActionButton aria-label="Fechar" icon={X} onClick={onClose} tone="ghost" />
        </div>

        {erro && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
            {erro}
          </div>
        )}

        <div className="mt-5 grid gap-4">
          <TextField
            autoComplete="off"
            label="Nome do consultorio"
            onChange={(valor) => onChange({ nome: valor })}
            placeholder="Ex.: Sala 2"
            required
            value={form.nome}
          />

          <TextField
            autoComplete="off"
            label="Descricao"
            onChange={(valor) => onChange({ descricao: valor })}
            placeholder="Ex.: Atendimento clinico"
            value={form.descricao}
          />

          <TextField
            label="Ordem"
            onChange={(valor) => onChange({ ordem: valor })}
            placeholder="Opcional"
            type="number"
            value={form.ordem}
          />
        </div>

        <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <ActionButton
            className="justify-center"
            disabled={salvando}
            intent="neutral"
            onClick={onClose}
            tone="soft"
          >
            Cancelar
          </ActionButton>
          <ActionButton
            className="justify-center"
            icon={DoorOpen}
            intent="create"
            loading={salvando}
            type="submit"
          >
            Criar consultorio
          </ActionButton>
        </div>
      </form>
    </div>
  );
}
