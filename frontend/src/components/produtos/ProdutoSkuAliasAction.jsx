import { useState } from "react";
import toast from "react-hot-toast";
import { X } from "lucide-react";
import { aplicarAliasSkuProduto, previewAliasSkuProduto } from "../../api/produtos";
import ActionButton from "../ui/ActionButton";

function ProdutoSkuAliasModal({ produtoId, nome, onClose, onSaved }) {
  const [sku, setSku] = useState("");
  const [motivo, setMotivo] = useState("");
  const [preview, setPreview] = useState(null);
  const [confirmado, setConfirmado] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");

  const relatarErro = (error) => {
    const detail = error?.response?.data?.detail;
    setErro(
      typeof detail === "string"
        ? detail
        : "Não foi possível concluir. Confira o SKU e tente novamente.",
    );
    setPreview(null);
    setConfirmado(false);
  };

  const revisar = async () => {
    if (ocupado || !sku.trim() || sku.trim().length > 100) return;
    setOcupado(true);
    setErro("");
    setPreview(null);
    setConfirmado(false);
    try {
      const { data } = await previewAliasSkuProduto(produtoId, sku.trim());
      setPreview(data);
    } catch (error) {
      relatarErro(error);
    } finally {
      setOcupado(false);
    }
  };

  const podeSalvar = Boolean(
    preview?.preview_token && confirmado && motivo.trim().length >= 10 && !ocupado,
  );
  const salvar = async () => {
    if (!podeSalvar) return;
    setOcupado(true);
    setErro("");
    try {
      const { data } = await aplicarAliasSkuProduto(produtoId, {
        sku: preview.sku_alias,
        motivo: motivo.trim(),
        preview_token: preview.preview_token,
      });
      toast.success("SKU alternativo adicionado.");
      onSaved(data.sku);
      onClose();
    } catch (error) {
      relatarErro(error);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="alias-sku-titulo"
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white p-5 shadow-xl space-y-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="alias-sku-titulo" className="text-lg font-bold text-slate-900">
              Adicionar SKU alternativo
            </h2>
            <p className="text-sm text-slate-600">
              {nome} · Produto {produtoId}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={ocupado}
            aria-label="Fechar SKU alternativo"
            className="p-1"
          >
            <X size={20} />
          </button>
        </div>
        <p className="text-sm text-slate-600">
          Cadastre um SKU usado em pedidos ou anúncios que corresponde a este produto. O SKU
          principal, o estoque e as reservas serão mantidos.
        </p>
        <label className="block text-sm text-slate-700">
          SKU alternativo
          <input
            value={sku}
            maxLength={100}
            disabled={ocupado}
            autoFocus
            onChange={(event) => {
              setSku(event.target.value);
              setPreview(null);
              setConfirmado(false);
              setErro("");
            }}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono"
          />
        </label>
        <label className="block text-sm text-slate-700">
          Evidência da correspondência
          <textarea
            value={motivo}
            maxLength={2000}
            disabled={ocupado}
            onChange={(event) => {
              setMotivo(event.target.value);
              setConfirmado(false);
            }}
            placeholder="Descreva como conferiu que o pedido ou anúncio é deste produto (mínimo 10 caracteres)."
            className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
        {erro && (
          <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
            {erro}
          </p>
        )}
        {preview && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900 space-y-3">
            <p>
              <strong>{preview.sku_alias}</strong> identificará o produto {preview.produto_id}, cujo
              SKU principal é <strong>{preview.sku_canonico}</strong>.
            </p>
            <p>Esta alteração não movimenta estoque nem altera reservas.</p>
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={confirmado}
                disabled={ocupado}
                onChange={(event) => setConfirmado(event.target.checked)}
                className="mt-1"
              />
              <span>
                Conferi a identidade e confirmo este SKU alternativo para o produto apresentado.
              </span>
            </label>
          </div>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <ActionButton onClick={onClose} disabled={ocupado} tone="soft">
            Cancelar
          </ActionButton>
          {!preview ? (
            <ActionButton
              onClick={revisar}
              disabled={!sku.trim() || ocupado}
              loading={ocupado}
              intent="edit"
            >
              Revisar vínculo
            </ActionButton>
          ) : (
            <ActionButton onClick={salvar} disabled={!podeSalvar} loading={ocupado} intent="edit">
              Adicionar SKU alternativo
            </ActionButton>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProdutoSkuAliasAction({ produtoId, nome }) {
  const [aberto, setAberto] = useState(false);
  const [ultimoSku, setUltimoSku] = useState("");
  return (
    <>
      <div>
        <ActionButton onClick={() => setAberto(true)} tone="soft">
          Adicionar SKU alternativo
        </ActionButton>
        {ultimoSku && (
          <p role="status" className="mt-1 text-xs text-emerald-700">
            SKU {ultimoSku} adicionado.
          </p>
        )}
      </div>
      {aberto && (
        <ProdutoSkuAliasModal
          key={produtoId}
          produtoId={produtoId}
          nome={nome}
          onClose={() => setAberto(false)}
          onSaved={setUltimoSku}
        />
      )}
    </>
  );
}
