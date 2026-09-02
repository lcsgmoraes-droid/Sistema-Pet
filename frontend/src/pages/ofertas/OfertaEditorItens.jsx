import {
  AlertTriangle,
  Camera,
  CheckSquare,
  Image,
  ImagePlus,
  Save,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";

import CurrencyInput from "../../components/CurrencyInput";
import { formatMoneyBRL } from "../../utils/formatters";
import { resolveMediaUrl } from "../../utils/mediaUrl";
import { calcularDesconto, calcularMargem } from "./ofertasEstudioUtils";

export default function OfertaEditorItens({
  itens,
  tipoArte,
  onUpdate,
  onRemove,
  onRemoveMany,
  onUpload,
  onGerarImagem,
  onSalvarImagemGerada,
  gerandoImagemId,
  enviandoImagemId,
  salvandoImagemId,
}) {
  const [marcados, setMarcados] = useState([]);
  const [promptAbertoId, setPromptAbertoId] = useState(null);

  useEffect(() => {
    const idsAtuais = new Set(itens.map((item) => item.produto_id));
    setMarcados((atuais) => atuais.filter((id) => idsAtuais.has(id)));
  }, [itens]);

  if (!itens.length) return null;
  const todosMarcados = marcados.length === itens.length;

  function alternarMarcado(produtoId) {
    setMarcados((atuais) =>
      atuais.includes(produtoId) ? atuais.filter((id) => id !== produtoId) : [...atuais, produtoId],
    );
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-black text-slate-950">Preços e imagens da arte</h2>
          <p className="text-xs text-slate-500">
            O preço abaixo vale somente para a imagem. O ERP não será alterado.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setMarcados(todosMarcados ? [] : itens.map((item) => item.produto_id))}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700"
          >
            <CheckSquare size={15} /> {todosMarcados ? "Desmarcar todos" : "Selecionar todos"}
          </button>
          <button
            type="button"
            disabled={!marcados.length}
            onClick={() => {
              onRemoveMany(marcados);
              setMarcados([]);
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-xs font-bold text-red-700 disabled:opacity-40"
          >
            <Trash2 size={15} /> Remover selecionados
          </button>
        </div>
      </div>
      <div className="space-y-4">
        {itens.map((item) => {
          const margem = calcularMargem(item.preco_arte, item.preco_custo);
          const desconto = calcularDesconto(item.preco_erp, item.preco_arte);
          const imagem = resolveMediaUrl(item.imagem_url_arte || item.imagem_url);
          const imagensDisponiveis = Array.isArray(item.imagens_disponiveis)
            ? item.imagens_disponiveis
            : [];
          const marcado = marcados.includes(item.produto_id);
          const promptAberto = promptAbertoId === item.produto_id;
          return (
            <article
              key={item.produto_id}
              className={`rounded-xl border p-4 ${marcado ? "border-teal-500 bg-teal-50/30" : "border-slate-200"}`}
            >
              <div className="flex gap-3">
                <input
                  type="checkbox"
                  checked={marcado}
                  onChange={() => alternarMarcado(item.produto_id)}
                  aria-label={`Selecionar ${item.nome}`}
                  className="mt-1 h-4 w-4 shrink-0 accent-teal-700"
                />
                <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-50">
                  {imagem ? (
                    <img src={imagem} alt="" className="h-full w-full object-contain" />
                  ) : (
                    <Image className="text-slate-300" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="break-words font-bold leading-tight text-slate-900">
                        {item.nome}
                      </h3>
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

              {imagensDisponiveis.length > 1 ? (
                <div className="mt-3 border-t border-slate-100 pt-3">
                  <p className="mb-2 flex items-center gap-2 text-xs font-bold text-slate-600">
                    <ImagePlus size={15} /> Escolha uma foto cadastrada
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {imagensDisponiveis.map((foto, indice) => {
                      const fotoUrl = foto?.url;
                      const ativa = fotoUrl && item.imagem_url_arte === fotoUrl;
                      return fotoUrl ? (
                        <button
                          key={`${foto.id || "principal"}-${fotoUrl}`}
                          type="button"
                          onClick={() =>
                            onUpdate(item.produto_id, {
                              imagem_original_url: fotoUrl,
                              imagem_url_arte: fotoUrl,
                              imagem_gerada_url: null,
                              imagem_gerada_salva: false,
                            })
                          }
                          className={`h-16 w-16 overflow-hidden rounded-lg border-2 bg-white p-1 ${
                            ativa ? "border-teal-600 ring-2 ring-teal-100" : "border-slate-200"
                          }`}
                          title={`Usar foto ${indice + 1}`}
                        >
                          <img
                            src={resolveMediaUrl(fotoUrl)}
                            alt={`Opção ${indice + 1}`}
                            className="h-full w-full object-contain"
                          />
                        </button>
                      ) : null;
                    })}
                  </div>
                </div>
              ) : null}

              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
                <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700">
                  <Camera size={15} />{" "}
                  {enviandoImagemId === item.produto_id ? "Enviando..." : "Adicionar outra foto"}
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
                    onClick={() =>
                      tipoArte === "produto"
                        ? setPromptAbertoId(promptAberto ? null : item.produto_id)
                        : onGerarImagem(item)
                    }
                    className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                  >
                    <Sparkles size={15} />{" "}
                    {gerandoImagemId === item.produto_id
                      ? "Criando..."
                      : tipoArte === "produto"
                        ? "Criar a partir desta foto"
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
                    <button
                      type="button"
                      disabled={item.imagem_gerada_salva || salvandoImagemId === item.produto_id}
                      onClick={() => onSalvarImagemGerada(item)}
                      className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-700 disabled:opacity-50"
                    >
                      <Save size={15} />{" "}
                      {item.imagem_gerada_salva
                        ? "Salva no produto"
                        : salvandoImagemId === item.produto_id
                          ? "Salvando..."
                          : "Salvar na galeria do produto"}
                    </button>
                  </>
                ) : null}
              </div>

              {tipoArte === "produto" && promptAberto ? (
                <div className="mt-3 rounded-xl border border-violet-200 bg-violet-50 p-3">
                  <label className="text-xs font-black text-violet-950">
                    O que você quer criar a partir desta foto?
                    <textarea
                      value={item.prompt_criacao || ""}
                      onChange={(event) =>
                        onUpdate(item.produto_id, {
                          prompt_criacao: event.target.value.slice(0, 800),
                        })
                      }
                      rows={3}
                      className="mt-2 w-full resize-y rounded-lg border border-violet-200 bg-white p-3 text-sm font-medium text-slate-800"
                      placeholder="Ex.: colocar o produto em uma bancada de pet shop moderna, com luz natural e fundo verde suave."
                    />
                  </label>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <p className="text-[11px] text-violet-700">
                      A embalagem, a marca e o rótulo continuarão preservados.
                    </p>
                    <button
                      type="button"
                      disabled={gerandoImagemId === item.produto_id}
                      onClick={() => onGerarImagem(item)}
                      className="shrink-0 rounded-lg bg-violet-700 px-3 py-2 text-xs font-black text-white disabled:opacity-50"
                    >
                      Gerar com IA
                    </button>
                  </div>
                </div>
              ) : null}

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
