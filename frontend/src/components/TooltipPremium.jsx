/**
 * TooltipPremium — Tooltip de orientação para módulos premium.
 * - Explica por que está bloqueado
 * - Mostra ação recomendada (ver planos / contratar)
 * - Funciona em mouse (hover) e toque (touch) — mobile e desktop
 * - Sem dependência de biblioteca externa
 */
import { useEffect, useRef, useState } from "react";
import { FiLock } from "react-icons/fi";
import { useNavigate } from "react-router-dom";
import { MODULOS_INFO } from "../contexts/ModulosContext";

const TEXTOS_PADRAO = {
  titulo: "Módulo Premium",
  descricao: "Este recurso faz parte de um módulo extra do sistema.",
  acao: "Ver planos e contratar",
};

/**
 * TooltipPremium
 * Props:
 *   modulo (string) — chave do módulo (ex: "campanhas")
 *   placement ("top" | "bottom" | "right") — padrão "right"
 *   children — elemento que ativa o tooltip (ícone de cadeado, botão, etc.)
 */
const TooltipPremium = ({ modulo, placement = "right", children }) => {
  const [visivel, setVisivel] = useState(false);
  const containerRef = useRef(null);
  const navigate = useNavigate();

  const info = MODULOS_INFO[modulo];
  const nome = info?.nome ?? TEXTOS_PADRAO.titulo;
  const descricao = info?.descricao ?? TEXTOS_PADRAO.descricao;
  const preco = info?.preco;

  /* Fechar ao clicar fora */
  useEffect(() => {
    if (!visivel) return;

    const fechar = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setVisivel(false);
      }
    };
    document.addEventListener("mousedown", fechar);
    document.addEventListener("touchstart", fechar);
    return () => {
      document.removeEventListener("mousedown", fechar);
      document.removeEventListener("touchstart", fechar);
    };
  }, [visivel]);

  /* Fechar com Escape */
  useEffect(() => {
    if (!visivel) return;
    const fechar = (e) => {
      if (e.key === "Escape") setVisivel(false);
    };
    document.addEventListener("keydown", fechar);
    return () => document.removeEventListener("keydown", fechar);
  }, [visivel]);

  const posicaoTooltip =
    placement === "top"
      ? "bottom-full mb-2 left-1/2 -translate-x-1/2"
      : placement === "bottom"
        ? "top-full mt-2 left-1/2 -translate-x-1/2"
        : "left-full ml-2 top-1/2 -translate-y-1/2"; // right (padrão)

  return (
    <div
      ref={containerRef}
      className="relative inline-flex"
      onMouseEnter={() => setVisivel(true)}
      onMouseLeave={() => setVisivel(false)}
      onFocus={() => setVisivel(true)}
      onBlur={() => setVisivel(false)}
      onClick={(e) => {
        e.stopPropagation();
        setVisivel((v) => !v);
      }}
      onTouchEnd={(e) => {
        e.stopPropagation();
        setVisivel((v) => !v);
      }}
    >
      {children}

      {/* Tooltip balão */}
      {visivel && (
        <div
          role="tooltip"
          className={`absolute z-50 w-60 bg-gray-900 text-white rounded-xl shadow-xl p-3 text-xs ${posicaoTooltip}`}
          style={{ pointerEvents: "auto" }}
        >
          {/* Destaque: módulo bloqueado */}
          <div className="flex items-center gap-1.5 mb-2">
            <FiLock className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
            <span className="font-bold text-amber-300">{nome} — Premium</span>
          </div>

          {/* Descrição do benefício */}
          <p className="text-gray-300 leading-snug mb-2">{descricao}</p>

          {/* Preço se disponível */}
          {preco && (
            <p className="text-green-400 font-semibold mb-2">
              A partir de R$ {preco}/mês — sem fidelidade
            </p>
          )}

          {/* Ação recomendada */}
          <button
            className="w-full mt-1 bg-indigo-500 hover:bg-indigo-600 text-white font-semibold rounded-lg px-3 py-1.5 transition-colors text-xs"
            onMouseDown={(e) => {
              e.stopPropagation();
              setVisivel(false);
              navigate("/ajuda");
            }}
            onTouchEnd={(e) => {
              e.stopPropagation();
              setVisivel(false);
              navigate("/ajuda");
            }}
          >
            Ver planos e contratar →
          </button>
        </div>
      )}
    </div>
  );
};

export default TooltipPremium;
