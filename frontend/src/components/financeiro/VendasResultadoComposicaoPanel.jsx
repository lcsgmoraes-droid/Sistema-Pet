export default function VendasResultadoComposicaoPanel({
  abaAtiva,
  abrirVendasEmAberto,
  filtroStatusLista,
  fluxoResultadoCards,
  formatarMoeda,
  resumo,
}) {
  return (
    <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Composicao do resultado</h3>
          <p className="text-sm text-gray-500">
            Sequencia da venda bruta ate o lucro do periodo filtrado.
          </p>
        </div>
        <div className="self-start rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 sm:self-auto">
          {formatarMoeda(resumo.venda_liquida || 0)} liquido antes do CMV
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5 2xl:grid-cols-6">
        {fluxoResultadoCards.map((card) => {
          const clicavel = card.acao === "vendas_em_aberto";
          const Container = clicavel ? "button" : "div";
          const ativo = clicavel && abaAtiva === "lista" && filtroStatusLista === "em_aberto";

          return (
            <Container
              key={card.titulo}
              type={clicavel ? "button" : undefined}
              onClick={clicavel ? abrirVendasEmAberto : undefined}
              className={`min-h-[116px] rounded-lg border p-3 text-left shadow-sm transition ${card.cor} ${
                clicavel
                  ? "hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-red-100"
                  : ""
              } ${ativo ? "ring-4 ring-red-100" : ""}`}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide">{card.titulo}</span>
                <span className="rounded-full bg-white/70 px-2 py-0.5 text-xs font-bold">
                  {card.sinal || "R$"}
                </span>
              </div>
              <div className="text-xl font-bold">
                {card.percentual ? `${card.valor}%` : formatarMoeda(card.valor)}
              </div>
              <p className="mt-2 text-xs opacity-75">{card.detalhe}</p>
              {clicavel ? (
                <p className="mt-1 text-xs font-semibold opacity-80">
                  Clique para ver as vendas em aberto.
                </p>
              ) : null}
            </Container>
          );
        })}
      </div>
    </div>
  );
}
