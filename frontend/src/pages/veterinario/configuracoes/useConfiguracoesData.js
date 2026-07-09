import { useCallback, useEffect, useState } from "react";

import { vetApi } from "../vetApi";

export function useConfiguracoesData() {
  const [parceiros, setParceiros] = useState([]);
  const [tenantsVet, setTenantsVet] = useState([]);
  const [consultorios, setConsultorios] = useState([]);
  const [lembretesConfig, setLembretesConfig] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const [parcRes, tenRes, consultRes, lembretesRes] = await Promise.all([
        vetApi.listarParceiros(),
        vetApi.listarTenantsVeterinarios(),
        vetApi.listarConsultorios({ ativos_only: false }),
        vetApi.obterConfigLembretes(),
      ]);
      setParceiros(Array.isArray(parcRes.data) ? parcRes.data : []);
      setTenantsVet(Array.isArray(tenRes.data) ? tenRes.data : []);
      setConsultorios(Array.isArray(consultRes.data) ? consultRes.data : []);
      setLembretesConfig(lembretesRes.data || null);
    } catch {
      setErro("Nao foi possivel carregar as configuracoes de parceria.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  return {
    carregar,
    carregando,
    consultorios,
    erro,
    lembretesConfig,
    parceiros,
    setConsultorios,
    setErro,
    setLembretesConfig,
    setParceiros,
    tenantsVet,
  };
}
