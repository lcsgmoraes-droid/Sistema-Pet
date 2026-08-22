import { useCallback, useEffect, useState } from "react";
import {
  contarNovidadesNaoVistas,
  EVOLUCAO_VISTA_EVENT,
  listarEvolucaoCorePet,
} from "../services/evolucaoCorePet";

export default function useNovidadesNaoVistas() {
  const [quantidade, setQuantidade] = useState(0);

  const carregar = useCallback(async () => {
    try {
      const response = await listarEvolucaoCorePet();
      setQuantidade(contarNovidadesNaoVistas(response.itens));
    } catch {
      setQuantidade(0);
    }
  }, []);

  useEffect(() => {
    void carregar();
    window.addEventListener(EVOLUCAO_VISTA_EVENT, carregar);
    return () => window.removeEventListener(EVOLUCAO_VISTA_EVENT, carregar);
  }, [carregar]);

  return quantidade;
}
