import { useEffect, useRef, useState } from "react";
import {
  confirmarIfoodProdutoPortal,
  enviarIfoodPublicacaoProduto,
  getIfoodPublicacaoProduto,
  prepararIfoodPublicacaoProduto,
  vincularIfoodProduto,
} from "../../api/ifood";
import { getProduto } from "../../api/produtos";
import {
  assinaturaCadastroIfood,
  cadastroIfoodAlterado,
  valorConferidoPortal,
} from "./ifoodPublicacaoDraft";
import { mensagemErroIfood } from "./ifoodPresentation";

export default function useIfoodPublicacaoProduto({ productId, draft = null, imagens } = {}) {
  const [publication, setPublication] = useState(null);
  const [loading, setLoading] = useState(Boolean(productId));
  const [stale, setStale] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [revision, setRevision] = useState(0);
  const [review, setReview] = useState(null);
  const [mode, setMode] = useState("existing");
  const [portalChecked, setPortalChecked] = useState(false);
  const [fields, setFields] = useState(["price", "stock"]);
  const [confirmSend, setConfirmSend] = useState(false);
  const [confirmPortal, setConfirmPortal] = useState(false);
  const [confirmedContextToken, setConfirmedContextToken] = useState(null);
  const [confirmationContextChanged, setConfirmationContextChanged] = useState(false);
  const [present, setPresent] = useState(true);
  const [observedActive, setObservedActive] = useState(null);
  const [observedPrice, setObservedPrice] = useState(null);
  const [observedStock, setObservedStock] = useState(null);
  const [uncertain, setUncertain] = useState(false);
  const [savedProduct, setSavedProduct] = useState(null);
  const lock = useRef(false);
  const generation = useRef(0);
  const identity = useRef(productId);
  const loaded = useRef(false);
  const previousConfirmationContext = useRef(null);
  const draftKey = assinaturaCadastroIfood(draft, { formulario: true, imagens });
  const latestDraft = useRef(draftKey);
  latestDraft.current = draftKey;
  const saved = publication?.snapshot_saved
    ? { ...savedProduct, ...publication.snapshot_saved }
    : null;
  const dirty = cadastroIfoodAlterado(draft, saved, imagens);
  const ready = Boolean(
    productId &&
    Number(publication?.product_id) === Number(productId) &&
    !loading &&
    !stale &&
    !dirty &&
    !busy,
  );
  const caps = publication?.capabilities || {};
  const confirmationContextToken = publication?.confirmation_context_token || null;
  const operation = publication?.link?.mode === "new" ? "create" : "update";

  useEffect(() => {
    if (identity.current !== productId) {
      identity.current = productId;
      loaded.current = false;
      lock.current = false;
      setBusy("");
      setPublication(null);
      setSavedProduct(null);
      setReview(null);
      setPortalChecked(false);
      setConfirmSend(false);
      setConfirmPortal(false);
      setConfirmedContextToken(null);
      setConfirmationContextChanged(false);
      setPresent(true);
      setObservedActive(null);
      setObservedPrice(null);
      setObservedStock(null);
      setUncertain(false);
      setSuccess("");
    }
    const version = ++generation.current;
    const abort = new AbortController();
    setLoading(Boolean(productId));
    setStale(true);
    setError("");
    if (!productId)
      return () => {
        abort.abort();
        generation.current++;
      };
    (async () => {
      try {
        const [response, product] = await Promise.all([
          getIfoodPublicacaoProduto(productId, { signal: abort.signal }),
          draft ? getProduto(productId) : Promise.resolve({ data: null }),
        ]);
        if (version !== generation.current || abort.signal.aborted) return;
        setPublication(response.data);
        setSavedProduct(product.data);
        if (!loaded.current) {
          setMode(response.data.link?.mode || "existing");
          loaded.current = true;
        }
        setStale(false);
      } catch (err) {
        if (version === generation.current && !abort.signal.aborted)
          setError(
            mensagemErroIfood(
              err,
              "Não foi possível consultar o vínculo e os envios. Os últimos dados foram mantidos; atualize antes de agir.",
            ),
          );
      } finally {
        if (version === generation.current && !abort.signal.aborted) setLoading(false);
      }
    })();
    return () => {
      abort.abort();
      generation.current++;
    };
  }, [productId, revision]);

  useEffect(() => {
    if (previousConfirmationContext.current !== confirmationContextToken) {
      if (previousConfirmationContext.current && confirmPortal) setConfirmationContextChanged(true);
      setConfirmPortal(false);
      setConfirmedContextToken(null);
      previousConfirmationContext.current = confirmationContextToken;
    }
  }, [confirmationContextToken, confirmPortal]);

  useEffect(() => {
    setReview(null);
    setConfirmSend(false);
  }, [draftKey]);

  async function action(name, capability, run) {
    if (!ready || !caps[capability] || lock.current) return;
    lock.current = true;
    setBusy(name);
    setError("");
    setSuccess("");
    const version = generation.current;
    try {
      await run(() => version === generation.current);
    } catch (err) {
      if (version === generation.current) {
        if (err.response?.status === 403) setStale(true);
        if (name === "confirm" && err.response?.status === 409) {
          setStale(true);
          setConfirmPortal(false);
          setConfirmedContextToken(null);
          setConfirmationContextChanged(true);
        }
        if (name === "send") {
          setReview(null);
          setConfirmSend(false);
        }
        if (name === "send" && !err.response) {
          setUncertain(true);
        }
        setError(
          mensagemErroIfood(
            err,
            name === "send"
              ? "Não foi possível confirmar o resultado do envio. Confira o Portal e atualize o acompanhamento antes de tentar novamente."
              : "Não foi possível concluir a ação. Os rascunhos e os últimos dados foram mantidos.",
          ),
        );
      }
    } finally {
      if (version === generation.current) {
        lock.current = false;
        setBusy("");
      }
    }
  }

  async function reload(isCurrent) {
    const [{ data }, product] = await Promise.all([
      getIfoodPublicacaoProduto(productId),
      draft ? getProduto(productId) : Promise.resolve({ data: null }),
    ]);
    if (isCurrent()) {
      setPublication(data);
      setSavedProduct(product.data);
      setStale(false);
    }
  }

  const vincular = () => {
    if (!portalChecked) return;
    return action("link", "can_link", async (isCurrent) => {
      await vincularIfoodProduto(productId, {
        merchant_id: publication.merchant_id,
        barcode: publication.barcode,
        mode,
        portal_checked: true,
      });
      if (!isCurrent()) return;
      setReview(null);
      setPortalChecked(false);
      setConfirmSend(false);
      await reload(isCurrent);
      if (isCurrent())
        setSuccess(
          "Conferência do EAN registrada no CorePet. Nenhum produto foi enviado por esta ação.",
        );
    });
  };

  const preparar = () => {
    if ((!fields.length && operation !== "create") || uncertain) return;
    return action("prepare", "can_prepare", async (isCurrent) => {
      const key = latestDraft.current;
      const { data } = await prepararIfoodPublicacaoProduto(productId, {
        operation,
        fields: operation === "create" ? ["price", "stock"] : fields,
      });
      if (!isCurrent()) return;
      setPublication(data.publication);
      if (key !== latestDraft.current) {
        setError("O cadastro foi alterado durante a preparação. Salve e prepare novamente.");
        return;
      }
      setReview({ ...data, requestKey: crypto.randomUUID() });
      setConfirmSend(false);
      setSuccess("Prévia de um produto preparada. Nada foi enviado ao iFood.");
    });
  };

  const enviar = () => {
    if (!review?.eligible || !review.review_token || !confirmSend || uncertain) return;
    return action("send", "can_send", async (isCurrent) => {
      const { data } = await enviarIfoodPublicacaoProduto(productId, {
        operation: review.operation,
        fields: review.fields,
        review_token: review.review_token,
        request_key: review.requestKey,
        confirm_send: true,
      });
      if (!isCurrent()) return;
      setPublication(data.publication);
      setReview(null);
      setConfirmSend(false);
      setUncertain(data.status === "uncertain");
      if (data.status === "accepted")
        setSuccess(
          "Envio aceito para processamento pelo iFood. A publicação ainda precisa ser conferida no Portal.",
        );
      else
        setError(
          data.submission?.message ||
            "O envio não foi confirmado. Confira o acompanhamento e o Portal.",
        );
    });
  };

  const confirmar = () => {
    if (
      !confirmPortal ||
      !confirmationContextToken ||
      confirmedContextToken !== confirmationContextToken
    )
      return;
    const price = valorConferidoPortal(observedPrice, 2);
    const stock = valorConferidoPortal(observedStock, 3);
    if (!price.valid || !stock.valid) {
      setError(
        "Informe valores não negativos: preço com até 2 casas e estoque com até 3 casas decimais, ou deixe vazio se não conferiu.",
      );
      return;
    }
    return action("confirm", "can_confirm", async (isCurrent) => {
      await confirmarIfoodProdutoPortal(productId, {
        merchant_id: publication.merchant_id,
        barcode: publication.barcode,
        present,
        portal_active: present ? observedActive : null,
        confirmation_context_token: confirmedContextToken,
        price: present ? price.value : null,
        stock: present ? stock.value : null,
      });
      if (!isCurrent()) return;
      setConfirmPortal(false);
      setConfirmedContextToken(null);
      setConfirmationContextChanged(false);
      setReview(null);
      setConfirmSend(false);
      await reload(isCurrent);
      if (isCurrent()) {
        setUncertain(false);
        setSuccess(
          "Conferência manual do Portal registrada com responsável e data. Não representa validação automática pelo iFood.",
        );
      }
    });
  };

  return {
    publication,
    loading,
    stale,
    busy,
    error,
    success,
    dirty,
    ready,
    review,
    mode,
    portalChecked,
    fields,
    confirmSend,
    confirmPortal,
    confirmationContextChanged,
    present,
    observedActive,
    observedPrice,
    observedStock,
    uncertain,
    operation,
    canLink: ready && Boolean(caps.can_link),
    canPrepare:
      ready &&
      Boolean(caps.can_prepare) &&
      !uncertain &&
      (operation === "create" || fields.length > 0),
    canSend:
      ready && Boolean(caps.can_send) && Boolean(review?.eligible && confirmSend) && !uncertain,
    canConfirm:
      ready &&
      Boolean(caps.can_confirm) &&
      confirmPortal &&
      Boolean(confirmationContextToken) &&
      confirmedContextToken === confirmationContextToken,
    alterar(campo, value) {
      if (lock.current) return;
      if (campo === "mode") {
        setMode(value);
        setPortalChecked(false);
        setReview(null);
      }
      if (campo === "portalChecked") setPortalChecked(value);
      if (campo === "fields") {
        setFields(value);
        setReview(null);
        setConfirmSend(false);
      }
      if (campo === "confirmSend") setConfirmSend(value);
      if (campo === "confirmPortal") {
        const accepted = Boolean(value && ready && caps.can_confirm && confirmationContextToken);
        setConfirmPortal(accepted);
        setConfirmedContextToken(accepted ? confirmationContextToken : null);
        if (accepted) setConfirmationContextChanged(false);
      }
      if (campo === "present") {
        setPresent(value);
        setConfirmPortal(false);
        setConfirmedContextToken(null);
        if (!value) {
          setObservedActive(null);
          setObservedPrice(null);
          setObservedStock(null);
        }
      }
      if (campo === "observedActive") {
        setObservedActive(value === true || value === false ? value : null);
        setConfirmPortal(false);
        setConfirmedContextToken(null);
      }
      if (campo === "observedPrice") {
        setObservedPrice(value);
        setConfirmPortal(false);
        setConfirmedContextToken(null);
      }
      if (campo === "observedStock") {
        setObservedStock(value);
        setConfirmPortal(false);
        setConfirmedContextToken(null);
      }
    },
    atualizar() {
      if (!lock.current) {
        setReview(null);
        setConfirmSend(false);
        setRevision((v) => v + 1);
      }
    },
    vincular,
    preparar,
    enviar,
    confirmar,
  };
}
