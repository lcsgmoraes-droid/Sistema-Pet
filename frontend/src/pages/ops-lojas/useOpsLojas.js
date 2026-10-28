import { useEffect, useMemo, useState } from "react";
import api from "../../platformApi";
import { agruparPorGrupo } from "./opsLojasUtils";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

// Lista de lojas do OPS: um único loading do início até a lista aparecer.
export default function useOpsLojas() {
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [lojas, setLojas] = useState([]);
  const [cortou, setCortou] = useState(false);
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");

  useEffect(() => {
    const espera = setTimeout(() => setBuscaAplicada(busca), 300);
    return () => clearTimeout(espera);
  }, [busca]);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await api.get("/admin/lojas", {
          params: { search: buscaAplicada || undefined },
        });
        if (!ativo) return;
        setLojas(data.items || []);
        setCortou(Boolean(data.cortou));
        setErro("");
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível carregar as lojas."));
      } finally {
        if (ativo) setCarregando(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, [buscaAplicada]);

  const grupos = useMemo(() => agruparPorGrupo(lojas), [lojas]);

  return { busca, carregando, cortou, erro, grupos, lojas, setBusca };
}
