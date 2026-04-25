import { useEffect, useState } from "react";

import { vetApi } from "../vetApi";

export default function useConsultaAssinatura({
  modoSomenteLeitura,
  consultaIdAtual,
}) {
  const [assinatura, setAssinatura] = useState(null);

  useEffect(() => {
    if (!modoSomenteLeitura || !consultaIdAtual) return;
    vetApi
      .validarAssinaturaConsulta(consultaIdAtual)
      .then((res) => setAssinatura(res.data))
      .catch(() => setAssinatura(null));
  }, [modoSomenteLeitura, consultaIdAtual]);

  return assinatura;
}
