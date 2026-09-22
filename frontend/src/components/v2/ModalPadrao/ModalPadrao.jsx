import { X } from "lucide-react";

const LARGURAS = {
  pequena: "max-w-md",
  normal: "max-w-2xl",
  grande: "max-w-3xl",
};

// Casca padrão de modal do sistema — título + corpo + rodapé de ações, com o fechar (X) sempre no
// mesmo lugar e no mesmo estilo. Clicar fora NUNCA fecha a modal (não existe onClick no fundo
// escurecido, de propósito): o usuário só sai por um botão explícito (o X aqui, ou Cancelar/Salvar
// que a tela passa no `rodape`) — evita perder preenchimento por um clique sem querer.
export default function ModalPadrao({ children, onFechar, rodape, tamanho = "normal", titulo }) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div
        className={[
          "flex max-h-[90vh] w-full flex-col overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-slate-900",
          LARGURAS[tamanho] || LARGURAS.normal,
        ].join(" ")}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-slate-700">
          <h3 className="text-xl font-bold text-gray-900 dark:text-slate-100">{titulo}</h3>
          <button
            type="button"
            onClick={onFechar}
            aria-label="Fechar"
            className="rounded-md p-1 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-300"
          >
            <X className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-6">{children}</div>

        {rodape ? (
          <div className="flex flex-none justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4 dark:border-slate-700 dark:bg-slate-950/40">
            {rodape}
          </div>
        ) : null}
      </div>
    </div>
  );
}
