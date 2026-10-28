import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../platformApi";
import { MODULOS_INFO } from "../../contexts/ModulosContext";
import { confirmarCorePet } from "../../services/corepetDialog";
import { nomeDoModulo } from "./opsLojasUtils";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

// Detalhe de uma loja do OPS (dados, módulos, usuários) e a troca de módulos.
export default function useOpsLojaDetalhe(lojaId) {
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [loja, setLoja] = useState(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    let ativo = true;
    (async () => {
      setCarregando(true);
      try {
        const { data } = await api.get(`/admin/lojas/${lojaId}`);
        if (!ativo) return;
        setLoja(data);
        setErro("");
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível abrir esta loja."));
      } finally {
        if (ativo) setCarregando(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, [lojaId]);

  const alternarModulo = useCallback(
    async (modulo, ativar) => {
      const nome = nomeDoModulo(modulo, MODULOS_INFO);
      if (!ativar) {
        const confirmado = await confirmarCorePet({
          titulo: "Desativar módulo",
          mensagem: `Desativar “${nome}” para a loja ${loja.nome}? Quem usa essa loja perde o acesso ao módulo.`,
          confirmarTexto: "Desativar",
        });
        if (!confirmado) return false;
      }
      setSalvando(true);
      try {
        const { data } = await api.post(
          `/admin/lojas/${lojaId}/modulos/${modulo}/${ativar ? "ativar" : "desativar"}`,
        );
        setLoja((atual) => ({
          ...atual,
          modulos: data.modulos,
          acesso_bloqueado_por_cobranca: data.acesso_bloqueado_por_cobranca,
        }));
        if (data.continua_ativo) {
          toast.error(
            `“${nome}” continua ativo: ele vem do plano ou do teste grátis da loja, não de uma ativação manual.`,
            { duration: 7000 },
          );
        } else {
          toast.success(`${nome} ${ativar ? "ativado" : "desativado"} para ${loja.nome}.`);
        }
        return true;
      } catch (error) {
        toast.error(mensagemDeErro(error, "Não foi possível alterar o módulo."));
        return false;
      } finally {
        setSalvando(false);
      }
    },
    [loja, lojaId],
  );

  return { alternarModulo, carregando, erro, loja, salvando };
}
