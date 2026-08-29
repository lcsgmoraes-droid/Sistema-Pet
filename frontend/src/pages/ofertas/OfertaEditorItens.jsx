import { AlertTriangle, Camera, Image, Sparkles, Trash2 } from "lucide-react";

import CurrencyInput from "../../components/CurrencyInput";
import { formatMoneyBRL } from "../../utils/formatters";
import { resolveMediaUrl } from "../../utils/mediaUrl";
import { calcularDesconto, calcularMargem } from "./ofertasEstudioUtils";

export default function OfertaEditorItens({
  itens,
  onUpdate,
  onRemove,
  onUpload,
  onGerarImagem,
  gerandoImagemId,
  enviandoImagemId,
}) {
  if (!itens.length) return null;
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h2 className="font-black text-slate-950">Preços e imagens da arte</h2>
        <p className="text-xs text-slate-500">
          O preço abaixo vale somente para a imagem. O ERP não será alterado.
        </p>
      </div>
      <div className="space-y-4">
        {itens.map((item) => {
          const margem = calcularMargem(item.preco_arte, item.preco_custo);
          const desconto = calcularDesconto(item.preco_erp, item.preco_arte);
          const imagem = resolveMediaUrl(item.imagem_url_arte || item.imagem_url);
          return (
            <article key={item.produto_id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex gap-3">
                <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-50">
                  {imagem ? (
                    <img src={imagem} alt="" className="h-full w-full object-contain" />
                  ) : (
                    <Image className="text-slate-300" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-bold leading-tight text-slate-900">{item.nome}</h3>
                      <p className="mt-1 text-xs text-slate-500">
                        ERP {formatMoneyBRL(item.preco_erp)}
                        {item.precos_divergentes
                          ? ` · App ${formatMoneyBRL(item.preco_app)} · Site ${formatMoneyBRL(item.preco_ecommerce)}`
                          : ""}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => onRemove(item.produto_id)}
                      className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      title="Remover"
                    >
                      <Trash2 size={17} />
                    </button>
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-[160px_1fr]">
                    <label className="text-xs font-bold text-slate-700">
                      Preço da arte
                      <CurrencyInput
                        value={item.preco_arte}
                        onChange={(value) => onUpdate(item.produto_id, { preco_arte: value })}
                        className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm font-black"
                      />
                    </label>
                    <div className="flex flex-wrap items-end gap-2 text-xs">
                      <span className="rounded-full bg-blue-50 px-2 py-1 font-bold text-blue-700">
                        Desconto {desconto.toLocaleString("pt-BR")}%
                      </span>
                      <span
                        className={`rounded-full px-2 py-1 font-bold ${margem < 0 ? "bg-red-100 text-red-700" : "bg-emerald-50 text-emerald-700"}`}
                      >
                        Margem {margem.toLocaleString("pt-BR")}%
                      </span>
                      {margem < 0 ? (
                        <span className="flex items-center gap-1 font-bold text-red-600">
                          <AlertTriangle size={14} /> Abaixo do custo
                        </span>
                      ) : null}
                    </div>
                  </div>
                  {item.precos_divergentes ? (
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px]">
                      <span className="font-bold text-slate-500">Escolher preço de origem:</span>
                      {[
                        ["ERP", item.preco_erp],
                        ["App", item.preco_app],
                        ["Site", item.preco_ecommerce],
                      ].map(([canal, preco]) => (
                        <button
                          key={canal}
                          type="button"
                          onClick={() => onUpdate(item.produto_id, { preco_arte: Number(preco) })}
                          className={`rounded-full border px-2 py-1 font-black ${
                            Number(item.preco_arte) === Number(preco)
                              ? "border-teal-600 bg-teal-50 text-teal-800"
                              : "border-slate-300 text-slate-600"
                          }`}
                        >
                          {canal} {formatMoneyBRL(preco)}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
                <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700">
                  <Camera size={15} />{" "}
                  {enviandoImagemId === item.produto_id ? "Enviando..." : "Trocar foto"}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    className="hidden"
                    disabled={enviandoImagemId === item.produto_id}
                    onChange={(event) => onUpload(item, event.target.files?.[0])}
                  />
                </label>
                {imagem ? (
                  <button
                    type="button"
                    disabled={gerandoImagemId === item.produto_id}
                    onClick={() => onGerarImagem(item)}
                    className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                  >
                    <Sparkles size={15} />{" "}
                    {gerandoImagemId === item.produto_id
                      ? "Criando..."
                      : "Criar versão profissional"}
                  </button>
                ) : null}
                {item.imagem_gerada_url ? (
                  <>
                    <button
                      type="button"
                      onClick={() =>
                        onUpdate(item.produto_id, { imagem_url_arte: item.imagem_original_url })
                      }
                      className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold"
                    >
                      Usar original
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        onUpdate(item.produto_id, { imagem_url_arte: item.imagem_gerada_url })
                      }
                      className="rounded-lg border border-violet-300 bg-violet-50 px-3 py-2 text-xs font-bold text-violet-700"
                    >
                      Usar versão IA
                    </button>
                  </>
                ) : null}
              </div>

              {item.lote_validade ? (
                <label className="mt-3 flex cursor-pointer items-start gap-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-950">
                  <input
                    type="checkbox"
                    checked={item.mostrar_validade}
                    onChange={(event) =>
                      onUpdate(item.produto_id, {
                        mostrar_validade: event.target.checked,
                        lote_id: event.target.checked ? item.lote_validade.id : null,
                        preco_arte:
                          event.target.checked && item.preco_sugerido_validade
                            ? item.preco_sugerido_validade
                            : item.preco_arte,
                      })
                    }
                    className="mt-0.5 h-4 w-4 accent-amber-600"
                  />
                  <span>
                    <strong>Exibir aviso de validade próxima</strong>
                    <br />
                    Validade{" "}
                    {new Date(item.lote_validade.data_validade).toLocaleDateString("pt-BR", {
                      timeZone: "UTC",
                    })}{" "}
                    · será incluído “Quantidade limitada ao lote”.
                  </span>
                </label>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
