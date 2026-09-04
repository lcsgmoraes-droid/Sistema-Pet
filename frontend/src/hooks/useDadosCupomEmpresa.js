import { useEffect, useState } from "react";
import api from "../api";

export function useDadosCupomEmpresa() {
  const [dadosEmpresa, setDadosEmpresa] = useState({});
  const [carregandoEmpresa, setCarregandoEmpresa] = useState(true);

  useEffect(() => {
    let ativo = true;

    api
      .get("/empresa/dados-cupom")
      .then((response) => {
        if (ativo) setDadosEmpresa(response.data || {});
      })
      .catch((error) => {
        console.error("Erro ao carregar dados da empresa para o recibo:", error);
        if (ativo) setDadosEmpresa({});
      })
      .finally(() => {
        if (ativo) setCarregandoEmpresa(false);
      });

    return () => {
      ativo = false;
    };
  }, []);

  return { carregandoEmpresa, dadosEmpresa };
}
