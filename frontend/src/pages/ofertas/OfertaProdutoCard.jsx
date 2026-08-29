import { Camera, Check, ImageOff, Sparkles } from "lucide-react";

import { formatMoneyBRL } from "../../utils/formatters";
import { resolveMediaUrl } from "../../utils/mediaUrl";

export default function OfertaProdutoCard({
  produto,
  selecionado,
  onToggle,
  onUpload,
  enviandoImagem,
}) {
  const imagem = resolveMediaUrl(produto.imagem_url);
  return (
    <article
      className={`relative overflow-hidden rounded-xl border bg-white shadow-sm transition ${
        selecionado ? "border-teal-500 ring-2 ring-teal-100" : "border-slate-200"
      }`}
    >
      <button type="button" onClick={onToggle} className="block w-full text-left">
        <div className="relative flex aspect-[4/3] items-center justify-center bg-slate-50 p-3">
          {imagem ? (
            <img src={imagem} alt="" className="h-full w-full object-contain" />
          ) : (
            <ImageOff className="h-10 w-10 text-slate-300" />
          )}
          <span
            className={`absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full border-2 ${
              selecionado ? "border-teal-600 bg-teal-600 text-white" : "border-white bg-slate-200"
            }`}
          >
            {selecionado ? <Check size={16} /> : null}
          </span>
          {produto.motivo_sugestao ? (
            <span className="absolute bottom-2 left-2 max-w-[88%] truncate rounded-full bg-amber-300 px-2 py-1 text-[10px] font-black text-amber-950">
              <Sparkles size={11} className="mr-1 inline" /> {produto.motivo_sugestao}
            </span>
          ) : null}
        </div>
        <div className="p-3">
          <p className="line-clamp-2 min-h-10 text-sm font-bold text-slate-900">{produto.nome}</p>
          <div className="mt-2 flex items-end justify-between gap-2">
            <div>
              <p className="text-[10px] uppercase text-slate-400">Preço ERP</p>
              <p className="font-black text-teal-700">{formatMoneyBRL(produto.preco_erp)}</p>
            </div>
            <span className="text-xs font-semibold text-slate-500">
              {produto.estoque_atual} {produto.unidade}
            </span>
          </div>
          {produto.precos_divergentes ? (
            <p className="mt-2 text-[10px] font-bold text-amber-700">
              Preços dos canais divergentes
            </p>
          ) : null}
        </div>
      </button>
      {!imagem ? (
        <label className="m-3 mt-0 flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-teal-400 bg-teal-50 px-3 py-2 text-xs font-bold text-teal-800">
          <Camera size={15} /> {enviandoImagem ? "Enviando..." : "Tirar ou enviar foto"}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            disabled={enviandoImagem}
            onChange={(event) => onUpload(event.target.files?.[0])}
            className="hidden"
          />
        </label>
      ) : null}
    </article>
  );
}
