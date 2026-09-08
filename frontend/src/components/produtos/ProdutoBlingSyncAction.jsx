import { useEffect, useState } from "react";
import { Loader2, X } from "lucide-react";
import { alterarHabilitacaoBlingProduto, getHabilitacaoBlingProduto } from "../../api/produtos";
import ActionButton from "../ui/ActionButton";

function mensagemErro(error) {
  const detail = error?.response?.data?.detail;
  return typeof detail === "string"
    ? detail
    : "Não foi possível consultar ou alterar a sincronização. Consulte o estado novamente.";
}

function ProdutoBlingSyncModal({ produtoId, onClose }) {
  const [estado, setEstado] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [confirmado, setConfirmado] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [revisao, setRevisao] = useState(0);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setEstado(null);
    setConfirmado(false);
    getHabilitacaoBlingProduto(produtoId)
      .then(({ data }) => {
        if (ativo) setEstado(data);
      })
      .catch((error) => {
        if (ativo) setErro(mensagemErro(error));
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [produtoId, revisao]);

  const podeAlterar = Boolean(
    estado?.vinculado && !estado.retirado && typeof estado.sincronizar === "boolean",
  );
  const habilitada = estado?.sincronizar === true;
  const alterar = async () => {
    if (!podeAlterar || salvando || (!habilitada && !confirmado)) return;
    setSalvando(true);
    setErro("");
    setMensagem("");
    try {
      const { data } = await alterarHabilitacaoBlingProduto(produtoId, !habilitada);
      setEstado(data);
      setConfirmado(false);
      setMensagem(data.sincronizar ? "Sincronização retomada." : "Sincronização pausada.");
    } catch (error) {
      setEstado(null);
      setConfirmado(false);
      setErro(mensagemErro(error));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="bling-habilitacao-titulo"
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl space-y-4"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="bling-habilitacao-titulo" className="text-lg font-bold text-slate-900">
            Sincronização Bling do produto
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={salvando}
            aria-label="Fechar sincronização Bling"
            className="p-1 text-slate-600"
          >
            <X size={20} />
          </button>
        </div>
        {carregando && (
          <p role="status" className="flex items-center gap-2 text-sm text-slate-600">
            <Loader2 size={18} className="animate-spin" />
            Consultando sincronização...
          </p>
        )}
        {erro && (
          <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
            <p>{erro}</p>
            <button
              type="button"
              disabled={carregando || salvando}
              onClick={() => {
                setErro("");
                setRevisao((value) => value + 1);
              }}
              className="mt-2 underline"
            >
              Consultar novamente
            </button>
          </div>
        )}
        {estado && (
          <>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 space-y-1">
              <p className="font-semibold">{estado.produto_nome}</p>
              <p>
                Produto {estado.produto_id} · SKU {estado.sku || "Não informado"}
              </p>
              <p>Vínculo Bling: {estado.bling_produto_id || "Não configurado"}</p>
            </div>
            {estado.retirado ? (
              <p className="text-sm text-amber-800">
                Este vínculo foi retirado por fusão e permanece apenas no histórico. A sincronização
                não pode ser retomada.
              </p>
            ) : !estado.vinculado ? (
              <p className="text-sm text-slate-600">
                Este produto ainda não possui vínculo com o Bling.
              </p>
            ) : podeAlterar ? (
              <>
                <p className="font-semibold text-slate-900">
                  Envio automático: {habilitada ? "habilitado" : "pausado"}
                </p>
                <p className="text-sm text-slate-600">
                  Este controle pausa ou retoma o envio automático de estoque deste produto ao
                  Bling.
                </p>
                {!habilitada && (
                  <label className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                    <input
                      type="checkbox"
                      checked={confirmado}
                      disabled={salvando}
                      onChange={(event) => setConfirmado(event.target.checked)}
                      className="mt-1"
                    />
                    <span>
                      Confirmo retomar a sincronização. O saldo deste produto poderá ser enviado ao
                      Bling.
                    </span>
                  </label>
                )}
              </>
            ) : (
              <p role="alert" className="text-sm text-amber-800">
                Estado da sincronização indisponível. Feche e consulte novamente.
              </p>
            )}
          </>
        )}
        {mensagem && (
          <p role="status" className="text-sm text-emerald-700">
            {mensagem}
          </p>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <ActionButton onClick={onClose} disabled={salvando} tone="soft">
            Fechar
          </ActionButton>
          {podeAlterar && (
            <ActionButton
              onClick={alterar}
              disabled={salvando || (!habilitada && !confirmado)}
              loading={salvando}
              intent={habilitada ? "warning" : "edit"}
            >
              {habilitada ? "Pausar sincronização" : "Retomar sincronização"}
            </ActionButton>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProdutoBlingSyncAction({ produtoId }) {
  const [aberto, setAberto] = useState(false);
  return (
    <>
      <ActionButton onClick={() => setAberto(true)} tone="soft">
        Sincronização Bling
      </ActionButton>
      {aberto && (
        <ProdutoBlingSyncModal
          key={produtoId}
          produtoId={produtoId}
          onClose={() => setAberto(false)}
        />
      )}
    </>
  );
}
