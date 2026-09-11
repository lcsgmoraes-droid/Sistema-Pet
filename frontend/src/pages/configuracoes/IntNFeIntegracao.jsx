import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../services/api";
import { useAuth } from "../../contexts/AuthContext";
import IntNFeAtivacaoView from "./IntNFeAtivacaoView";
import IntNFeNumeracao from "./IntNFeNumeracao.jsx";
import IntNFeCsc from "./IntNFeCsc.jsx";

function ActivationPanel() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [numberingBusy, setNumberingBusy] = useState(false);
  const [cscBusy, setCscBusy] = useState(false);
  const [credentials, setCredentials] = useState({ client_id: "", client_secret: "" });
  const inFlight = useRef(false);
  const mounted = useRef(false);

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
        busy={busy || numberingBusy || cscBusy}
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
          <IntNFeCsc apiClient={api} disabled={busy || numberingBusy} onBusy={setCscBusy} />
          <IntNFeNumeracao apiClient={api} disabled={busy || cscBusy} onBusy={setNumberingBusy} />
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
