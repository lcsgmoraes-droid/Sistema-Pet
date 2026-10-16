import { PawPrint } from "lucide-react";
import { resolveMediaUrl } from "../../utils/mediaUrl";

const TAMANHOS = {
  sm: { caixa: "h-9 w-9", icone: 16, letra: "text-sm" },
  md: { caixa: "h-11 w-11", icone: 18, letra: "text-base" },
  lg: { caixa: "h-14 w-14", icone: 24, letra: "text-xl" },
};

// Exibicao padrao de pet em qualquer lista/card do sistema: foto quando existe,
// senao a primeira letra do nome em destaque (mesma cor de marca usada nas
// iniciais de usuario do GlobalHeader) — nunca um icone generico de pata, que
// nao ajuda a diferenciar um pet do outro numa listagem.
export default function PetAvatar({ alt = "Pet", className = "", name = "", size = "md", url }) {
  const imageUrl = resolveMediaUrl(url);
  const tamanho = TAMANHOS[size] || TAMANHOS.md;
  const letra = (name || "").trim().charAt(0).toUpperCase();

  return (
    <div
      role="img"
      aria-label={name || alt}
      className={[
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-slate-200",
        imageUrl
          ? "bg-slate-100"
          : letra
            ? "bg-[#0f5f63] dark:bg-cyan-700"
            : "bg-slate-100 text-slate-400",
        tamanho.caixa,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      title={name || alt}
    >
      {imageUrl ? (
        <img src={imageUrl} alt="" className="h-full w-full object-cover" loading="lazy" />
      ) : letra ? (
        <span className={`font-bold text-white ${tamanho.letra}`} aria-hidden="true">
          {letra}
        </span>
      ) : (
        <PawPrint size={tamanho.icone} aria-hidden="true" />
      )}
    </div>
  );
}
