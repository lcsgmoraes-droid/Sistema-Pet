import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../../platformApi";
import { MODULOS_INFO } from "../../contexts/ModulosContext";
import { confirmarCorePet } from "../../services/corepetDialog";
import { agruparPorGrupo, nomeDoModulo } from "./opsLojasUtils";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

export default function useOpsLojas() {
  // Um único loading do início até a lista aparecer.
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [lojas, setLojas] = useState([]);
  const [cortou, setCortou] = useState(false);
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [salvando, setSalvando] = useState({});

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

  const alternarModulo = useCallback(async (loja, modulo, ativar) => {
    const nomeModulo = nomeDoModulo(modulo, MODULOS_INFO);
    if (!ativar) {
      const confirmado = await confirmarCorePet({
        titulo: "Desativar módulo",
        mensagem: `Desativar “${nomeModulo}” para a loja ${loja.nome}? Quem usa essa loja perde o acesso ao módulo.`,
        confirmarTexto: "Desativar",
      });
      if (!confirmado) return;
    }
    setSalvando((atual) => ({ ...atual, [loja.id]: true }));
    try {
      const { data } = await api.post(
        `/admin/lojas/${loja.id}/modulos/${modulo}/${ativar ? "ativar" : "desativar"}`,
      );
      setLojas((atual) =>
        atual.map((item) =>
          item.id === loja.id
            ? {
                ...item,
                modulos: data.modulos,
                acesso_bloqueado_por_cobranca: data.acesso_bloqueado_por_cobranca,
              }
            : item,
        ),
      );
      if (data.continua_ativo) {
        toast.error(
          `“${nomeModulo}” continua ativo: ele vem do plano ou do teste grátis da loja, não de uma ativação manual.`,
          { duration: 7000 },
        );
      } else {
        toast.success(`${nomeModulo} ${ativar ? "ativado" : "desativado"} para ${loja.nome}.`);
      }
    } catch (error) {
      toast.error(mensagemDeErro(error, "Não foi possível alterar o módulo."));
    } finally {
      setSalvando((atual) => ({ ...atual, [loja.id]: false }));
    }
  }, []);

  const grupos = useMemo(() => agruparPorGrupo(lojas), [lojas]);

  return { alternarModulo, busca, carregando, cortou, erro, grupos, lojas, salvando, setBusca };
}
