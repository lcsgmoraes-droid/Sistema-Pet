import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../services/api";
import { useAuth } from "../../contexts/AuthContext";
import IntNFeAtivacaoView from "./IntNFeAtivacaoView";
import IntNFeNumeracao from "./IntNFeNumeracao.jsx";
import IntNFeCsc from "./IntNFeCsc.jsx";
import IntNFeCadastroFiscal from "./IntNFeCadastroFiscal.jsx";
import IntNFeCertificado from "./IntNFeCertificado.jsx";
import IntNFeChecklist from "./IntNFeChecklist.jsx";

function ActivationPanel() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [numberingBusy, setNumberingBusy] = useState(false);
  const [cscBusy, setCscBusy] = useState(false);
  const [certificateBusy, setCertificateBusy] = useState(false);
  const [fiscalBusy, setFiscalBusy] = useState(false);
  const [certificateData, setCertificateData] = useState(null);
  const [fiscalData, setFiscalData] = useState(null);
  const [cscData, setCscData] = useState(null);
  const [numberingData, setNumberingData] = useState(null);
  const [fiscalRefreshKey, setFiscalRefreshKey] = useState(0);
  const [credentials, setCredentials] = useState({ client_id: "", client_secret: "" });
  const inFlight = useRef(false);
  const mounted = useRef(false);
  const automaticSyncAttempted = useRef(false);

  const execute = useCallback(async (action = "status", body = {}) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const response =
        action === "status"
          ? await api.get("/intnfe/status")
          : await api.post(`/intnfe/${action}`, body);
      if (mounted.current) setData(response.data);
    } catch (failure) {
      if (mounted.current) {
        const detail = failure?.response?.data?.detail;
        setError(
          typeof detail === "string"
            ? detail
            : "Não foi possível consultar o emissor. Tente atualizar a situação.",
        );
      }
    } finally {
      inFlight.current = false;
      if (mounted.current) setBusy(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    execute();
    return () => {
      mounted.current = false;
    };
  }, [execute]);

  useEffect(() => {
    if (!data?.vinculado || automaticSyncAttempted.current) return undefined;
    automaticSyncAttempted.current = true;
    let active = true;

    api
      .post("/intnfe/cadastro-fiscal/sincronizar")
      .then((response) => {
        if (active && mounted.current) setFiscalData(response.data);
      })
      .catch(() => {
        // A tela de cadastro fiscal mostra os campos que ainda impedem a sincronização.
      })
      .finally(() => {
        if (active && mounted.current) setFiscalRefreshKey((current) => current + 1);
      });

    return () => {
      active = false;
    };
  }, [data?.vinculado]);

  async function bind(event) {
    event.preventDefault();
    if (inFlight.current) return;
    const body = {
      client_id: credentials.client_id.trim(),
      client_secret: credentials.client_secret.trim(),
    };
    setCredentials({ client_id: "", client_secret: "" });
    await execute("vincular", body);
  }

  return (
    <div className="space-y-6">
      <IntNFeAtivacaoView
        data={data}
        busy={busy || numberingBusy || cscBusy || certificateBusy || fiscalBusy}
        error={error}
        credentials={credentials}
        onCredentials={(event) =>
          setCredentials((previous) => ({ ...previous, [event.target.name]: event.target.value }))
        }
        onActivate={() => execute("ativar")}
        onConsult={() => execute("consultar")}
        onBind={bind}
        onReload={() => execute()}
      />
      {data?.pode_configurar_numeracao && (
        <>
          <IntNFeChecklist
            activation={data}
            fiscal={fiscalData}
            certificate={certificateData}
            csc={cscData}
            numbering={numberingData}
          />
          <IntNFeCadastroFiscal
            apiClient={api}
            disabled={busy || certificateBusy || cscBusy || numberingBusy}
            onBusy={setFiscalBusy}
            onData={setFiscalData}
            refreshKey={fiscalRefreshKey}
          />
          <IntNFeCertificado
            apiClient={api}
            disabled={busy || fiscalBusy || cscBusy || numberingBusy}
            onBusy={setCertificateBusy}
            onData={setCertificateData}
            onChanged={() => execute()}
          />
          <IntNFeCsc
            apiClient={api}
            disabled={busy || fiscalBusy || certificateBusy || numberingBusy}
            onBusy={setCscBusy}
            onData={setCscData}
          />
          <IntNFeNumeracao
            apiClient={api}
            disabled={busy || fiscalBusy || certificateBusy || cscBusy}
            onBusy={setNumberingBusy}
            onData={setNumberingData}
          />
        </>
      )}
    </div>
  );
}

export default function IntNFeIntegracao() {
  const { user } = useAuth();
  // A troca de empresa descarta dados e codigos da tela anterior.
  return <ActivationPanel key={`${user?.id}:${user?.tenant?.id}`} />;
}
