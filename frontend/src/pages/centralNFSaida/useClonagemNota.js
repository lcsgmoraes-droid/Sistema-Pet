import { useEffect, useRef, useState } from "react";
import api from "../../api";
import { textoRespostaFiscal } from "../../utils/pdvFiscalStatus";
import { resumirCancelamentoNota } from "../../utils/nfeCancelamentoFeedback";
import { atualizarCampoClone, atualizarCanalClone, referenciaClonagem } from "./clonagemNotaUtils";

async function mensagemErro(error) {
  let dados = error.response?.data;
  if (typeof Blob !== "undefined" && dados instanceof Blob) {
    try {
      dados = JSON.parse(await dados.text());
    } catch {
      dados = null;
    }
  }
  return (
    textoRespostaFiscal(dados || error.message) || "Não foi possível concluir a clonagem da nota."
  );
}

export default function useClonagemNota(nota, aoFechar, aoAtualizar) {
  const [registros, setRegistros] = useState([]);
  const [registro, setRegistro] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [aberto, setAberto] = useState(false);
  const operacaoRef = useRef(false);
  const requisicaoRef = useRef(0);
  const aoAtualizarRef = useRef(aoAtualizar);
  aoAtualizarRef.current = aoAtualizar;

  async function atualizarLista() {
    const { data } = await api.get("/nfe/clones");
    setRegistros(data.rascunhos || []);
  }

  useEffect(() => {
    let ativo = true;
    api
      .get("/nfe/clones")
      .then(({ data }) => {
        if (ativo) setRegistros(data.rascunhos || []);
      })
      .catch(() => {});
    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    if (!nota) return undefined;
    let ativo = true;
    const requisicao = ++requisicaoRef.current;
    setAberto(true);
    setCarregando(true);
    setRegistro(null);
    setErro("");
    setMensagem("");
    api
      .post("/nfe/clones/preparar", referenciaClonagem(nota))
      .then(({ data }) => {
        if (ativo && requisicao === requisicaoRef.current) setRegistro(data);
      })
      .catch(async (error) => {
        const mensagem = await mensagemErro(error);
        if (ativo && requisicao === requisicaoRef.current) setErro(mensagem);
      })
      .finally(() => {
        if (ativo && requisicao === requisicaoRef.current) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [nota]);

  function fechar() {
    if (operacaoRef.current) return;
    requisicaoRef.current += 1;
    setAberto(false);
    setRegistro(null);
    setErro("");
    aoFechar?.();
  }

  async function abrirSalvo(id) {
    if (operacaoRef.current) return;
    const requisicao = ++requisicaoRef.current;
    setAberto(true);
    setCarregando(true);
    setRegistro(null);
    setErro("");
    setMensagem("");
    try {
      const { data } = await api.get(`/nfe/clones/${id}`);
      if (requisicao === requisicaoRef.current) setRegistro(data);
    } catch (error) {
      const mensagem = await mensagemErro(error);
      if (requisicao === requisicaoRef.current) setErro(mensagem);
    } finally {
      if (requisicao === requisicaoRef.current) setCarregando(false);
    }
  }

  function alterar(caminho, valor) {
    if (operacaoRef.current || (registro?.id && registro.status !== "rascunho")) return;
    setRegistro((atual) => ({ ...atual, dados: atualizarCampoClone(atual.dados, caminho, valor) }));
    setMensagem("");
  }

  function alterarCanal(canal) {
    if (operacaoRef.current || (registro?.id && registro.status !== "rascunho")) return;
    setRegistro((atual) => ({ ...atual, dados: atualizarCanalClone(atual.dados, canal) }));
    setMensagem("");
  }

  async function persistir() {
    const body = { origem: registro.origem, dados: registro.dados };
    const { data } = registro.id
      ? await api.put(`/nfe/clones/${registro.id}`, { dados: registro.dados })
      : await api.post("/nfe/clones", body);
    setRegistro(data);
    return data;
  }

  async function executar(acao) {
    if (operacaoRef.current) return;
    operacaoRef.current = true;
    setOcupado(true);
    setErro("");
    setMensagem("");
    try {
      await acao();
      await atualizarLista().catch(() => {});
    } catch (error) {
      setErro(await mensagemErro(error));
    } finally {
      operacaoRef.current = false;
      setOcupado(false);
    }
  }

  const salvar = () =>
    executar(async () => {
      if (!registro || (registro.id && registro.status !== "rascunho")) return;
      await persistir();
      setMensagem("Rascunho salvo. A próxima numeração será atribuída na emissão.");
    });

  const emitir = () =>
    executar(async () => {
      if (!registro || (registro.id && registro.status !== "rascunho")) return;
      const salvo = await persistir();
      let data;
      try {
        ({ data } = await api.post(`/nfe/clones/${salvo.id}/emitir`));
      } catch (error) {
        try {
          const resposta = await api.get(`/nfe/clones/${salvo.id}`);
          setRegistro(resposta.data);
        } catch {
          setRegistro({ ...salvo, status: "inconclusiva" });
        }
        throw error;
      }
      setRegistro(data);
      setMensagem(
        data.status === "autorizada"
          ? "Nota clonada autorizada."
          : data.status === "rejeitada"
            ? "O emissor recusou esta nota. Confira o motivo informado."
            : data.status === "inconclusiva"
              ? "O envio ainda não foi confirmado. Consulte a situação antes de qualquer nova tentativa."
              : "Emissão enviada. Consulte a situação para acompanhar o resultado antes de tentar novamente.",
      );
      aoAtualizarRef.current?.();
    });

  const consultar = () =>
    executar(async () => {
      const { data } = await api.post(`/nfe/clones/${registro.id}/consultar`);
      setRegistro(data);
      setMensagem("Situação da nota atualizada.");
      aoAtualizarRef.current?.();
    });

  const baixarDocumento = (tipo) =>
    executar(async () => {
      const resposta = await api.get(`/nfe/clones/${registro.id}/${tipo}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(resposta.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `NF-${registro.numero || registro.id}.${tipo === "xml" ? "xml" : "pdf"}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });

  const cancelar = (justificativa) =>
    executar(async () => {
      let data;
      try {
        ({ data } = await api.post(`/nfe/clones/${registro.id}/cancelar`, { justificativa }));
      } catch (error) {
        try {
          const resposta = await api.get(`/nfe/clones/${registro.id}`);
          setRegistro(resposta.data);
        } catch {
          setRegistro({ ...registro, cancelamento_status: "pendente" });
        }
        throw error;
      }
      setRegistro(data);
      setMensagem(resumirCancelamentoNota({ ...data, situacao: data.status }).mensagem);
      aoAtualizarRef.current?.();
    });

  return {
    registros,
    registro,
    aberto,
    carregando,
    ocupado,
    erro,
    mensagem,
    fechar,
    abrirSalvo,
    alterar,
    alterarCanal,
    salvar,
    emitir,
    consultar,
    baixarDocumento,
    cancelar,
  };
}
