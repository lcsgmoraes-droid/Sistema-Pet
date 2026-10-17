import { TONS_BADGE, TONS_ICONE } from "../utils/tons";

// Faixa de aviso dentro de uma tela ("proteção por validade desativada", "já houve contato hoje"...).
// "tom" usa o mesmo vocabulário de BotaoBase.variante; o padrão é "atencao". "titulo" e "icone" são
// opcionais; "children" é o texto explicativo; "acoes" é um espaço à direita para o botão da ação
// (ex.: "Abrir configurações") — quem chama passa o botão v2 pronto.
export default function FaixaAviso({ acoes, children, icone: Icone, titulo, tom = "atencao" }) {
  return (
    <div
      className={[
        "flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3",
        TONS_BADGE[tom] || TONS_BADGE.atencao,
      ].join(" ")}
    >
      <div className="flex min-w-0 items-start gap-3">
        {Icone ? (
          <span
            className={`mt-0.5 flex-none rounded-lg p-1.5 ${TONS_ICONE[tom] || TONS_ICONE.atencao}`}
          >
            <Icone className="h-4 w-4" aria-hidden="true" />
          </span>
        ) : null}
        <div className="min-w-0">
          {titulo ? <p className="text-sm font-semibold">{titulo}</p> : null}
          {children ? <div className="text-sm leading-5">{children}</div> : null}
        </div>
      </div>
      {acoes ? <div className="flex flex-none flex-wrap items-center gap-2">{acoes}</div> : null}
    </div>
  );
}
