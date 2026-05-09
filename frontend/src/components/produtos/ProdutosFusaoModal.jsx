import React, { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { GitMerge, Loader2, X } from "lucide-react";
import {
  executarFusaoProdutos,
  formatarMoeda,
  previewFusaoProdutos,
} from "../../api/produtos";
import ActionButton from "../ui/ActionButton";

function formatarValor(valor) {
  if (valor === null || valor === undefined || valor === "") return "-";
  if (typeof valor === "boolean") return valor ? "Sim" : "Nao";
  if (typeof valor === "number") return Number.isInteger(valor) ? String(valor) : valor.toLocaleString("pt-BR");
  if (Array.isArray(valor)) return valor.length ? valor.join(", ") : "-";
  if (typeof valor === "object") return JSON.stringify(valor);
  const texto = String(valor);
  if (/^\d{4}-\d{2}-\d{2}T/.test(texto) || /^\d{4}-\d{2}-\d{2} /.test(texto)) {
    const data = new Date(texto);
    if (!Number.isNaN(data.getTime())) return data.toLocaleString("pt-BR");
  }
  return texto;
}

function ProdutoResumo({ produto, selected, onSelect, label }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border p-3 text-left transition ${
        selected ? "border-blue-500 bg-blue-50" : "border-slate-200 bg-white hover:border-blue-200"
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase text-slate-500">{label}</span>
        <span className={`h-3 w-3 rounded-full border ${selected ? "border-blue-600 bg-blue-600" : "border-slate-300"}`} />
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-slate-900">{produto?.nome || "Produto sem nome"}</div>
        <div className="mt-1 font-mono text-xs text-slate-500">SKU: {produto?.codigo || produto?.sku || "-"}</div>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600">
        <span>Estoque: <strong>{Number(produto?.estoque_atual || 0).toLocaleString("pt-BR")}</strong></span>
        <span>PV: <strong>{formatarMoeda(produto?.preco_venda || 0)}</strong></span>
      </div>
    </button>
  );
}

export default function ProdutosFusaoModal({
  isOpen,
  onClose,
  onSuccess,
  produtosSelecionados = [],
}) {
  const [principalId, setPrincipalId] = useState(null);
  const [preview, setPreview] = useState(null);
  const [decisoes, setDecisoes] = useState({});
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [confirmado, setConfirmado] = useState(false);
  const [observacao, setObservacao] = useState("");

  const produtosValidos = produtosSelecionados.filter(Boolean).slice(0, 2);
  const duplicadoId = useMemo(() => {
    if (produtosValidos.length !== 2 || !principalId) return null;
    return produtosValidos.find((produto) => Number(produto.id) !== Number(principalId))?.id || null;
  }, [principalId, produtosValidos]);

  useEffect(() => {
    if (!isOpen) return;
    setPreview(null);
    setDecisoes({});
    setConfirmado(false);
    setObservacao("");
    setPrincipalId(produtosValidos[0]?.id || null);
  }, [isOpen, produtosSelecionados]);

  useEffect(() => {
    if (!isOpen || produtosValidos.length !== 2 || !principalId || !duplicadoId) return;
    let cancelado = false;

    const carregarPreview = async () => {
      setLoadingPreview(true);
      try {
        const { data } = await previewFusaoProdutos({
          produto_principal_id: Number(principalId),
          produto_duplicado_id: Number(duplicadoId),
        });
        if (cancelado) return;
        setPreview(data);
        setDecisoes(
          (data.campos || []).reduce((acc, campo) => {
            acc[campo.campo] = campo.origem_padrao || "principal";
            return acc;
          }, {}),
        );
      } catch (error) {
        if (!cancelado) {
          toast.error(error?.response?.data?.detail || "Nao foi possivel preparar a fusao.");
        }
      } finally {
        if (!cancelado) setLoadingPreview(false);
      }
    };

    carregarPreview();
    return () => {
      cancelado = true;
    };
  }, [duplicadoId, isOpen, principalId, produtosValidos.length]);

  if (!isOpen) return null;

  const camposRelevantes = (preview?.campos || []).filter(
    (campo) => campo.conflito || campo.automatico_por_vazio || ["codigo", "nome", "codigo_barras"].includes(campo.campo),
  );
  const conflitos = camposRelevantes.filter((campo) => campo.conflito).length;
  const automaticos = camposRelevantes.filter((campo) => campo.automatico_por_vazio).length;

  const executar = async () => {
    if (produtosValidos.length !== 2 || !principalId || !duplicadoId || salvando) return;
    setSalvando(true);
    try {
      await executarFusaoProdutos({
        produto_principal_id: Number(principalId),
        produto_duplicado_id: Number(duplicadoId),
        decisoes_campos: decisoes,
        observacao,
      });
      toast.success("Produtos fundidos com sucesso.");
      onSuccess?.();
      onClose?.();
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Erro ao fundir produtos.");
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-blue-50 text-blue-700">
              <GitMerge size={22} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Fundir produtos</h2>
              <p className="text-sm text-slate-500">Escolha o cadastro principal e confira o que sera transferido.</p>
            </div>
          </div>
          <button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" onClick={onClose}>
            <X size={22} />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5">
          {produtosValidos.length !== 2 ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              Selecione exatamente 2 produtos na listagem para usar a fusao.
            </div>
          ) : (
            <>
              <div className="mb-4 grid gap-3 md:grid-cols-2">
                {produtosValidos.map((produto) => (
                  <ProdutoResumo
                    key={produto.id}
                    label={Number(produto.id) === Number(principalId) ? "Produto principal" : "Produto que sera fundido"}
                    onSelect={() => setPrincipalId(produto.id)}
                    produto={produto}
                    selected={Number(produto.id) === Number(principalId)}
                  />
                ))}
              </div>

              {loadingPreview ? (
                <div className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 p-8 text-slate-500">
                  <Loader2 className="animate-spin" size={18} />
                  Analisando historico e conflitos...
                </div>
              ) : preview ? (
                <>
                  <div className="mb-4 grid gap-3 md:grid-cols-3">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs font-semibold uppercase text-slate-500">Conflitos</div>
                      <div className="mt-1 text-2xl font-bold text-slate-900">{conflitos}</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs font-semibold uppercase text-slate-500">Dados completados</div>
                      <div className="mt-1 text-2xl font-bold text-slate-900">{automaticos}</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs font-semibold uppercase text-slate-500">Referencias no duplicado</div>
                      <div className="mt-1 text-2xl font-bold text-slate-900">
                        {(preview.referencias_duplicado || []).reduce((total, item) => total + Number(item.total || 0), 0)}
                      </div>
                    </div>
                  </div>

                  <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                    <div className="mb-2 text-sm font-semibold text-emerald-900">Estoque atual sera somado no produto principal</div>
                    <div className="grid gap-2 text-xs text-emerald-900 md:grid-cols-3">
                      {Object.entries(preview.estoque_somado || {}).map(([campo, valores]) => (
                        <div key={campo} className="rounded-md bg-white/70 p-2">
                          <span className="block font-semibold">{campo.replace("estoque_", "Estoque ")}</span>
                          {Number(valores.principal || 0).toLocaleString("pt-BR")} + {Number(valores.duplicado || 0).toLocaleString("pt-BR")} = <strong>{Number(valores.final || 0).toLocaleString("pt-BR")}</strong>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mb-4 rounded-lg border border-slate-200">
                    <div className="border-b border-slate-200 px-4 py-3">
                      <h3 className="font-semibold text-slate-900">Decisoes de cadastro</h3>
                      <p className="text-xs text-slate-500">Campos vazios sao completados automaticamente. Em conflito, escolha qual valor fica.</p>
                    </div>
                    <div className="max-h-72 overflow-y-auto divide-y divide-slate-100">
                      {camposRelevantes.map((campo) => (
                        <div key={campo.campo} className="grid gap-3 px-4 py-3 text-sm md:grid-cols-[180px_1fr_1fr_160px]">
                          <div>
                            <div className="font-semibold text-slate-800">{campo.label}</div>
                            {campo.conflito ? (
                              <span className="mt-1 inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">conflito</span>
                            ) : campo.automatico_por_vazio ? (
                              <span className="mt-1 inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800">completa vazio</span>
                            ) : null}
                          </div>
                          <div className="rounded-md bg-slate-50 p-2">
                            <div className="text-xs font-semibold uppercase text-slate-400">Principal</div>
                            <div className="break-words text-slate-700">{formatarValor(campo.principal)}</div>
                          </div>
                          <div className="rounded-md bg-slate-50 p-2">
                            <div className="text-xs font-semibold uppercase text-slate-400">Duplicado</div>
                            <div className="break-words text-slate-700">{formatarValor(campo.duplicado)}</div>
                          </div>
                          <select
                            className="h-10 rounded-lg border border-slate-300 px-3 text-sm"
                            value={decisoes[campo.campo] || campo.origem_padrao || "principal"}
                            onChange={(event) => setDecisoes((prev) => ({ ...prev, [campo.campo]: event.target.value }))}
                          >
                            <option value="principal">Manter principal</option>
                            <option value="duplicado">Usar duplicado</option>
                          </select>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mb-4 rounded-lg border border-slate-200 p-3">
                    <div className="mb-2 text-sm font-semibold text-slate-900">Historico que sera transferido</div>
                    <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
                      {(preview.referencias_duplicado || []).map((item) => (
                        <div key={`${item.tabela}-${item.campo}`} className="rounded-md bg-slate-50 px-3 py-2">
                          {item.tabela}.{item.campo}: <strong>{item.total}</strong>
                        </div>
                      ))}
                    </div>
                  </div>

                  <textarea
                    className="mb-4 min-h-20 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    placeholder="Observacao interna da fusao (opcional)"
                    value={observacao}
                    onChange={(event) => setObservacao(event.target.value)}
                  />

                  <label className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                    <input
                      type="checkbox"
                      checked={confirmado}
                      onChange={(event) => setConfirmado(event.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-amber-300"
                    />
                    <span>
                      Confirmo que o produto duplicado sera inativado, o SKU dele sera reservado como fundido e o historico sera transferido para o principal.
                    </span>
                  </label>
                </>
              ) : null}
            </>
          )}
        </div>

        <div className="flex flex-col-reverse gap-3 border-t border-slate-200 px-6 py-4 sm:flex-row sm:justify-end">
          <ActionButton intent="neutral" tone="soft" onClick={onClose}>
            Cancelar
          </ActionButton>
          <ActionButton
            disabled={!preview || !confirmado || salvando || produtosValidos.length !== 2}
            icon={salvando ? Loader2 : GitMerge}
            intent="warning"
            tone="solid"
            onClick={executar}
            className={salvando ? "opacity-80" : ""}
          >
            {salvando ? "Fundindo..." : "Confirmar fusao"}
          </ActionButton>
        </div>
      </div>
    </div>
  );
}
