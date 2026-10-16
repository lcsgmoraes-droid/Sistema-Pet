import { MoreVertical } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const ALTURA_ITEM_PX = 36;
const PADDING_MENU_PX = 16;
const LARGURA_MENU_PX = 224; // w-56
const MARGEM_VIEWPORT_PX = 8;

const CORES_TOM = {
  neutro: "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800",
  perigo: "text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10",
};

function proximoIndiceHabilitado(acoes, indiceAtual, direcao) {
  if (acoes.length === 0) return -1;
  let indice = indiceAtual;
  for (let tentativa = 0; tentativa < acoes.length; tentativa += 1) {
    indice = (indice + direcao + acoes.length) % acoes.length;
    if (!acoes[indice]?.disabled) return indice;
  }
  return indiceAtual;
}

// Botão padrão para linha de listagem/tabela com várias ações (editar, excluir, histórico,
// vincular, etc.): em vez de uma fileira de ícones soltos — não escala (cada ação nova aperta
// mais a linha) e vira ruído visual —, um único ícone de "mais opções" revela a lista completa
// num menu. Abre sempre à direita do botão (a coluna Ações é sempre a primeira da tabela — ver
// AGENTS.md —, então "à direita" é sempre em direção ao resto da tabela, nunca pra fora da tela)
// e sozinho pra cima ou para baixo conforme o espaço livre na viewport.
// Renderiza o menu via portal direto no body (position: fixed, coordenadas calculadas a partir
// do botão) — não um <div absolute> dentro da célula, porque tabelas quase sempre moram num
// wrapper com overflow-x-auto (ver DataTable.jsx), e isso recorta qualquer menu que tentasse
// estourar as bordas dele.
//
// Cada ação do array `acoes` é {icon, label, onClick, disabled?, title?, tom?: "perigo"} — mesmo
// vocabulário de variante já usado em BotaoBase (perigo = ação destrutiva, ex. excluir).
//
// Ver a diretriz de padronização de ícones por tipo de ação (editar/excluir/histórico/abrir em
// nova janela/...) em frontend/src/pages/styleGuide/styleGuideCatalog.js — antes de usar um ícone
// novo para uma ação, checar se uma tela já existente usa um ícone equivalente pra mesma ação.
export default function BotaoMenuAcoes({ acoes = [], rotulo = "Mais ações" }) {
  const [aberto, setAberto] = useState(false);
  const [posicao, setPosicao] = useState(null);
  const [focoIndice, setFocoIndice] = useState(-1);
  const botaoRef = useRef(null);
  const menuRef = useRef(null);
  const itemRefs = useRef([]);

  const acoesVisiveis = acoes.filter(Boolean);

  useEffect(() => {
    if (!aberto) return undefined;

    function recalcularPosicao() {
      const retangulo = botaoRef.current?.getBoundingClientRect();
      if (!retangulo) return;
      const alturaEstimada = acoesVisiveis.length * ALTURA_ITEM_PX + PADDING_MENU_PX;
      const espacoAbaixo = window.innerHeight - retangulo.bottom;
      const abrirParaCima = espacoAbaixo < alturaEstimada && retangulo.top > espacoAbaixo;
      const esquerdaMaxima = window.innerWidth - LARGURA_MENU_PX - MARGEM_VIEWPORT_PX;
      setPosicao({
        left: Math.max(MARGEM_VIEWPORT_PX, Math.min(retangulo.left, esquerdaMaxima)),
        top: abrirParaCima ? undefined : retangulo.bottom + 4,
        bottom: abrirParaCima ? window.innerHeight - retangulo.top + 4 : undefined,
      });
    }

    recalcularPosicao();
    window.addEventListener("resize", recalcularPosicao);
    window.addEventListener("scroll", recalcularPosicao, true);

    function aoClicarFora(evento) {
      if (botaoRef.current?.contains(evento.target) || menuRef.current?.contains(evento.target)) {
        return;
      }
      setAberto(false);
    }
    document.addEventListener("mousedown", aoClicarFora);

    return () => {
      window.removeEventListener("resize", recalcularPosicao);
      window.removeEventListener("scroll", recalcularPosicao, true);
      document.removeEventListener("mousedown", aoClicarFora);
    };
  }, [aberto, acoesVisiveis.length]);

  useEffect(() => {
    if (!aberto) {
      setFocoIndice(-1);
      return;
    }
    const indiceInicial = proximoIndiceHabilitado(acoesVisiveis, -1, 1);
    setFocoIndice(indiceInicial);
  }, [aberto, acoesVisiveis]);

  useEffect(() => {
    if (focoIndice < 0) return;
    itemRefs.current[focoIndice]?.focus();
  }, [focoIndice]);

  function fechar({ devolverFoco = true } = {}) {
    setAberto(false);
    if (devolverFoco) botaoRef.current?.focus();
  }

  function aoPressionarTeclaNoMenu(evento) {
    if (evento.key === "Escape") {
      evento.preventDefault();
      fechar();
    } else if (evento.key === "ArrowDown") {
      evento.preventDefault();
      setFocoIndice((atual) => proximoIndiceHabilitado(acoesVisiveis, atual, 1));
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      setFocoIndice((atual) => proximoIndiceHabilitado(acoesVisiveis, atual, -1));
    } else if (evento.key === "Home") {
      evento.preventDefault();
      setFocoIndice(proximoIndiceHabilitado(acoesVisiveis, -1, 1));
    } else if (evento.key === "End") {
      evento.preventDefault();
      setFocoIndice(proximoIndiceHabilitado(acoesVisiveis, 0, -1));
    } else if (evento.key === "Tab") {
      fechar({ devolverFoco: false });
    }
  }

  if (acoesVisiveis.length === 0) return null;

  return (
    <>
      <button
        ref={botaoRef}
        type="button"
        onClick={() => setAberto((atual) => !atual)}
        aria-haspopup="true"
        aria-expanded={aberto}
        aria-label={rotulo}
        title={rotulo}
        className="flex h-9 w-9 flex-none items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        <MoreVertical className="h-4 w-4" aria-hidden="true" />
      </button>

      {aberto && posicao && typeof document !== "undefined"
        ? createPortal(
            <div
              ref={menuRef}
              role="menu"
              aria-label={rotulo}
              onKeyDown={aoPressionarTeclaNoMenu}
              style={{
                position: "fixed",
                left: posicao.left,
                top: posicao.top,
                bottom: posicao.bottom,
                width: LARGURA_MENU_PX,
              }}
              className="z-50 rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
            >
              {acoesVisiveis.map((acao, indice) => (
                <button
                  key={acao.key || indice}
                  ref={(elemento) => {
                    itemRefs.current[indice] = elemento;
                  }}
                  type="button"
                  role="menuitem"
                  tabIndex={indice === focoIndice ? 0 : -1}
                  disabled={acao.disabled}
                  title={acao.title}
                  onClick={() => {
                    fechar();
                    acao.onClick?.();
                  }}
                  className={[
                    "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500",
                    acao.disabled
                      ? "cursor-not-allowed text-slate-400 dark:text-slate-500"
                      : CORES_TOM[acao.tom] || CORES_TOM.neutro,
                  ].join(" ")}
                >
                  {acao.icon ? (
                    <acao.icon className="h-4 w-4 flex-none" aria-hidden="true" />
                  ) : null}
                  <span className="min-w-0 flex-1 truncate">{acao.label}</span>
                </button>
              ))}
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
