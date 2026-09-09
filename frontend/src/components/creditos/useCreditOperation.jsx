import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import {
  consultarOperacaoCredito,
  obterCarteiraCreditos,
  obterCatalogoCreditos,
  obterExtratoCreditos,
  orcarCreditos,
} from "../../services/creditos";
import CreditUsageModal from "./CreditUsageModal";
import {
  classificarResultadoOperacao,
  enviarGeracaoUmaVez,
  identidadeSessaoCreditos,
  modoCreditos,
  orcamentoExpirou,
  rejeicaoAntesDaExecucao,
  validarOrcamento,
} from "./creditosModel";

export function mensagemErroCreditos(
  error,
  fallback = "Não foi possível continuar com a geração.",
) {
  const detail = error?.response?.data?.detail;
  return (typeof detail === "string" ? detail : detail?.message) || error?.message || fallback;
}

export default function useCreditOperation() {
  const { user } = useAuth();
  const authUserRef = useRef(user);
  authUserRef.current = user;
  const lockRef = useRef(false);
  const decisionRef = useRef(null);
  const [catalog, setCatalog] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [entries, setEntries] = useState([]);
  const [warning, setWarning] = useState("");
  const [dialog, setDialog] = useState(null);
  const [pending, setPending] = useState(null);
  const [busy, setBusy] = useState(false);

  function identidadeAtual() {
    const tenant = JSON.parse(localStorage.getItem("selectedTenant") || "null");
    const savedUser = JSON.parse(localStorage.getItem("user") || "null");
    return identidadeSessaoCreditos(tenant, savedUser, authUserRef.current);
  }

  function validarIdentidade(expected) {
    if (identidadeAtual() !== expected) {
      throw new Error(
        "A empresa ou o usuário mudou. Volte à conta original para consultar esta geração.",
      );
    }
  }

  useEffect(() => () => decisionRef.current?.(false), []);

  useEffect(() => {
    decisionRef.current?.(false);
    decisionRef.current = null;
    setDialog(null);
    setCatalog(null);
    setWallet(null);
    setEntries([]);
    setPending(null);
    setWarning("");
  }, [user?.id, user?.tenant_id, user?.tenant?.id]);

  async function refreshWallet(identity = identidadeAtual()) {
    validarIdentidade(identity);
    const results = await Promise.allSettled([obterCarteiraCreditos(), obterExtratoCreditos()]);
    validarIdentidade(identity);
    setWallet(results[0].status === "fulfilled" ? results[0].value.data : null);
    const ledger = results[1].status === "fulfilled" ? results[1].value.data : null;
    setEntries(Array.isArray(ledger) ? ledger : ledger?.items || []);
    setWarning(
      results.some((item) => item.status === "rejected")
        ? "Não foi possível atualizar todo o saldo/extrato. Valores indisponíveis não significam saldo zero."
        : "",
    );
  }

  function finishDecision(accepted) {
    const resolve = decisionRef.current;
    decisionRef.current = null;
    setDialog(null);
    resolve?.(accepted);
  }

  async function recover(operation, { silent = false, requestError = null } = {}) {
    validarIdentidade(operation.identity);
    let result;
    try {
      result = (await consultarOperacaoCredito(operation.operationId)).data;
    } catch {
      validarIdentidade(operation.identity);
      setPending(operation);
      throw new Error(
        "Ainda não foi possível consultar a geração anterior. Não iniciaremos outra para evitar consumo duplicado.",
      );
    }
    validarIdentidade(operation.identity);
    if (rejeicaoAntesDaExecucao(requestError, result)) {
      sessionStorage.removeItem(operation.storageKey);
      setPending(null);
      throw new Error(mensagemErroCreditos(requestError));
    }
    const status = classificarResultadoOperacao(result);
    if (status === "completed") {
      // Mantém o identificador até o resultado chegar ao formulário correto.
      try {
        operation.onResult(result.result);
      } catch (error) {
        setPending(operation);
        throw error;
      }
      sessionStorage.removeItem(operation.storageKey);
      setPending(null);
      await refreshWallet(operation.identity);
      return true;
    }
    if (status === "failed") {
      sessionStorage.removeItem(operation.storageKey);
      setPending(null);
      await refreshWallet(operation.identity);
      throw new Error(
        result.error || "A geração anterior falhou. Uma nova tentativa exige uma nova confirmação.",
      );
    }
    setPending(operation);
    if (!silent)
      throw new Error(
        "A geração anterior ainda está pendente. Consulte o andamento abaixo; não enviaremos uma nova solicitação.",
      );
    return false;
  }

  async function run({ serviceCode, contextKey, payload, request, onResult }) {
    if (lockRef.current) return false;
    lockRef.current = true;
    setBusy(true);
    try {
      const identity = identidadeAtual();
      const nextCatalog = (await obterCatalogoCreditos()).data;
      validarIdentidade(identity);
      const mode = modoCreditos(nextCatalog);
      setCatalog(nextCatalog);
      // Mesmo ao desativar a cobrança, uma geração já enviada não deve ser duplicada.
      const storageKey = `corepet.creditos.operacao:${identity}:${serviceCode}:${contextKey}`;
      const previousId = sessionStorage.getItem(storageKey);
      if (previousId) {
        return await recover({ operationId: previousId, storageKey, onResult, identity });
      }
      if (pending)
        throw new Error("Consulte a geração pendente antes de iniciar outra nesta tela.");
      if (mode === "off") {
        validarIdentidade(identity);
        const result = await request(null);
        validarIdentidade(identity);
        onResult(result);
        return true;
      }
      const service = nextCatalog.services?.find(
        (item) => (item.service_code || item.code) === serviceCode,
      );
      if (!service?.enabled)
        throw new Error("Este serviço de IA ainda não está disponível para créditos.");
      const quote = validarOrcamento((await orcarCreditos(serviceCode, payload)).data, mode);
      validarIdentidade(identity);
      await refreshWallet(identity);
      const accepted = await new Promise((resolve) => {
        decisionRef.current = resolve;
        setDialog({ quote, title: service.title });
      });
      if (!accepted) return false;
      validarIdentidade(identity);
      if (orcamentoExpirou(quote))
        throw new Error("O orçamento expirou. Solicite um novo antes de gerar.");
      const operation = { operationId: quote.operation_id, storageKey, onResult, identity };
      // Não grava payload, texto, imagem ou credencial: apenas o ID opaco da operação.
      sessionStorage.setItem(storageKey, quote.operation_id);
      const response = await enviarGeracaoUmaVez(request, quote.operation_id, async (error) => {
        try {
          return await recover(operation, { requestError: error });
        } catch (recoveryError) {
          const code = error?.response?.data?.detail?.code;
          if (code === "insufficient_credits")
            setWarning("Saldo insuficiente. Não foi iniciada uma nova geração.");
          throw recoveryError;
        }
      });
      if (response.recovered) return response.result;
      validarIdentidade(identity);
      try {
        onResult(response.result);
      } catch (error) {
        setPending(operation);
        throw error;
      }
      sessionStorage.removeItem(storageKey);
      setPending(null);
      await refreshWallet(identity);
      return true;
    } catch (error) {
      throw new Error(mensagemErroCreditos(error), { cause: error });
    } finally {
      lockRef.current = false;
      setBusy(false);
    }
  }

  async function checkPending() {
    if (!pending || lockRef.current) return;
    lockRef.current = true;
    setBusy(true);
    try {
      const completed = await recover(pending, { silent: true });
      setWarning(
        completed
          ? "Resultado recuperado sem iniciar uma nova geração."
          : "A geração continua pendente. Você pode consultar novamente; nenhuma geração adicional será enviada.",
      );
    } catch (error) {
      setWarning(mensagemErroCreditos(error));
    } finally {
      lockRef.current = false;
      setBusy(false);
    }
  }

  async function openWallet() {
    if (lockRef.current) return;
    lockRef.current = true;
    setBusy(true);
    try {
      await refreshWallet();
      setDialog({ quote: null });
    } catch (error) {
      setWarning(mensagemErroCreditos(error));
    } finally {
      lockRef.current = false;
      setBusy(false);
    }
  }

  const visible = catalog?.mode && catalog.mode !== "off";
  const ui = (
    <>
      {(visible || pending) && (
        <section
          aria-label="Créditos da geração de IA"
          className="my-3 rounded-xl border border-violet-200 bg-white p-4 text-sm text-slate-700"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-semibold">
              Créditos CorePet {catalog?.mode === "shadow" ? "· simulação sem débito" : ""}
            </p>
            {visible && (
              <button
                type="button"
                disabled={busy}
                onClick={openWallet}
                className="rounded-lg border border-violet-300 px-3 py-1.5 font-medium text-violet-800 disabled:opacity-50"
              >
                Ver saldo e extrato
              </button>
            )}
          </div>
          {warning && (
            <p role="status" className="mt-2 text-amber-800">
              {warning}
            </p>
          )}
          {pending && (
            <div className="mt-3 rounded-lg bg-amber-50 p-3">
              <p>
                A geração anterior precisa ser conferida. Reenviar pode duplicar custos; use a
                consulta abaixo.
              </p>
              <button
                type="button"
                disabled={busy}
                onClick={checkPending}
                className="mt-2 rounded-lg border border-amber-300 px-3 py-2 font-semibold disabled:opacity-50"
              >
                {busy ? "Consultando..." : "Consultar geração anterior"}
              </button>
            </div>
          )}
        </section>
      )}
      {dialog && (
        <CreditUsageModal
          {...dialog}
          mode={catalog?.mode}
          wallet={wallet}
          entries={entries}
          warning={warning}
          onClose={() => finishDecision(false)}
          onConfirm={() => finishDecision(true)}
        />
      )}
    </>
  );
  return { run, busy, ui };
}
