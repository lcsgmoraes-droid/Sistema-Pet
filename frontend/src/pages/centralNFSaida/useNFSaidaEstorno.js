import { useEffect, useRef, useState } from "react";
import api from "../../api";
import { confirmarCorePet } from "../../services/corepetDialog";
import { mensagemErroEstorno, obterEstornoFiscal, podeEmitirEstorno } from "../../utils/nfeEstorno";

export default function useNFSaidaEstorno({ vendaId, onAtualizado }) {
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const [motivo, setMotivo] = useState("");
  const [declarado, setDeclarado] = useState(false);
  const [envioIniciado, setEnvioIniciado] = useState(false);
  const [destinatarioProprio, setDestinatarioProprio] = useState(false);
  const [destinoDaPrevia, setDestinoDaPrevia] = useState(null);
  const ativoRef = useRef(true);
  const operacaoRef = useRef(false);
  const endpoint = `/nfe/vendas/${vendaId}/estorno`;

  useEffect(() => {
    let ativo = true;
    ativoRef.current = true;
    setLoading(true);
    setErro("");
    api
      .get(endpoint, {
        params: destinatarioProprio ? { destinatario_proprio_emitente: true } : undefined,
      })
      .then(({ data }) => {
        if (ativo) {
          setDados(data);
          setDestinoDaPrevia(destinatarioProprio);
        }
      })
      .catch((error) => {
        if (ativo) setErro(mensagemErroEstorno(error));
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
      ativoRef.current = false;
    };
  }, [endpoint, destinatarioProprio]);

  async function executar(consultar) {
    if (operacaoRef.current) return;
    if (
      !consultar &&
      (destinoDaPrevia !== destinatarioProprio ||
        !podeEmitirEstorno(dados, { declarado, motivo, envioIniciado }))
    )
      return;
    operacaoRef.current = true;
    try {
      if (!consultar) {
        const confirmado = await confirmarCorePet({
          titulo: "Emitir NF-e de estorno?",
          mensagem: `Será emitida uma nova NF-e de entrada e ajuste em ${dados.previa.ambiente_label || "ambiente fiscal"}, referenciando a NFC-e original. Esta ação transmite um documento fiscal e não pode ser desfeita por este formulário. A nota original manterá seu status real.`,
          confirmarTexto: "Confirmar emissão do estorno",
          variante: "warning",
        });
        if (!confirmado || !ativoRef.current) return;
        setEnvioIniciado(true);
      }
      setOcupado(true);
      setErro("");
      const { data } = await api.post(
        consultar ? `${endpoint}/consultar` : endpoint,
        consultar
          ? undefined
          : {
              declaracao_operacao_nao_realizada: true,
              motivo: motivo.trim(),
              destinatario_proprio_emitente: destinatarioProprio,
            },
      );
      if (!ativoRef.current) return;
      setDados((anterior) => ({ ...anterior, ...data, previa: data.previa || anterior?.previa }));
      onAtualizado?.();
    } catch (error) {
      if (!ativoRef.current) return;
      setErro(mensagemErroEstorno(error));
      // Depois de qualquer envio, um erro de transporte exige consulta e nunca reemissão.
      try {
        const { data } = await api.get(endpoint, {
          params: destinatarioProprio ? { destinatario_proprio_emitente: true } : undefined,
        });
        if (ativoRef.current) {
          setDados((anterior) => ({ ...anterior, ...data }));
          onAtualizado?.();
        }
      } catch {
        /* A mensagem e a trava de envio permanecem visíveis. */
      }
    } finally {
      operacaoRef.current = false;
      if (ativoRef.current) setOcupado(false);
    }
  }

  const estorno = obterEstornoFiscal(dados || {});
  return {
    dados,
    loading,
    ocupado,
    erro,
    motivo,
    setMotivo,
    declarado,
    setDeclarado,
    envioIniciado,
    destinatarioProprio,
    setDestinatarioProprio: (valor) => {
      if (!operacaoRef.current) {
        setDeclarado(false);
        setDestinatarioProprio(valor);
      }
    },
    podeEmitir:
      podeEmitirEstorno(dados, { declarado, motivo, envioIniciado }) &&
      !ocupado &&
      !loading &&
      destinoDaPrevia === destinatarioProprio,
    podeConsultar: Boolean((estorno.status || envioIniciado) && estorno.pode_consultar !== false),
    emitir: () => executar(false),
    consultar: () => executar(true),
  };
}
