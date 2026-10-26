import { useEffect, useState } from "react";
import { buscarClientes } from "../../../api/clientes";
import { ordenarSugestoesEntidade } from "../../../utils/buscaEntidades";

export default function useBuscaPessoaResultados({
  value = "",
  enabled,
  minChars = 1,
  searchParams,
}) {
  const [resultado, setResultado] = useState({ suggestions: [], loading: false, error: "" });
  const parametros = JSON.stringify(searchParams || {});
  useEffect(() => {
    const texto = String(value || "").trim();
    if (!enabled || texto.length < minChars) {
      setResultado({ suggestions: [], loading: false, error: "" });
      return;
    }
    let ativo = true;
    const controller = new AbortController();
    setResultado({ suggestions: [], loading: true, error: "" });
    const timer = setTimeout(async () => {
      try {
        const pessoas = await buscarClientes(
          { ...JSON.parse(parametros), search: texto, limit: 20 },
          { signal: controller.signal },
        );
        if (ativo)
          setResultado({
            suggestions: ordenarSugestoesEntidade(pessoas || [], texto, "pessoa"),
            loading: false,
            error: "",
          });
      } catch (error) {
        if (ativo && error?.code !== "ERR_CANCELED")
          setResultado({
            suggestions: [],
            loading: false,
            error: "Não foi possível buscar pessoas. Tente novamente.",
          });
      }
    }, 300);
    return () => {
      ativo = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [value, enabled, minChars, parametros]);
  return resultado;
}
