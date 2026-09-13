// Placeholder para painéis sem dado no período (gráfico vazio, lista vazia etc.).
// Não define altura própria — quem chama controla o tamanho do espaço (gráfico, lista) por fora.
export default function EstadoVazio({ descricao, icone: Icone, titulo }) {
  return (
    <div className="flex h-full min-h-[160px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-center dark:border-slate-700 dark:bg-slate-950/40">
      <div>
        <Icone className="mx-auto h-7 w-7 text-slate-300 dark:text-slate-600" aria-hidden="true" />
        <p className="mt-2 text-sm font-medium text-slate-600 dark:text-slate-300">{titulo}</p>
        {descricao ? (
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{descricao}</p>
        ) : null}
      </div>
    </div>
  );
}
