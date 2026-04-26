import { useCallback, useEffect, useState } from "react";

import { vetApi } from "../vetApi";

export function useConfiguracoesData() {
  const [parceiros, setParceiros] = useState([]);
  const [tenantsVet, setTenantsVet] = useState([]);
  const [consultorios, setConsultorios] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const [parcRes, tenRes, consultRes] = await Promise.all([
        vetApi.listarParceiros(),
        vetApi.listarTenantsVeterinarios(),
        vetApi.listarConsultorios({ ativos_only: false }),
      ]);
      setParceiros(Array.isArray(parcRes.data) ? parcRes.data : []);
      setTenantsVet(Array.isArray(tenRes.data) ? tenRes.data : []);
      setConsultorios(Array.isArray(consultRes.data) ? consultRes.data : []);
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
    parceiros,
    setConsultorios,
    setErro,
    setParceiros,
    tenantsVet,
  };
}
