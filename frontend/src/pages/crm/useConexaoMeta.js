import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../../api";
import { confirmarCorePet } from "../../services/corepetDialog";

const CHAVE_PROGRESSO = "crm.guiaMeta.passosFeitos";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

function lerProgresso() {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE_PROGRESSO) || "[]");
    return Array.isArray(salvo) ? salvo : [];
  } catch {
    return [];
  }
}

export default function useConexaoMeta() {
  // Um único loading até o estado aparecer.
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [estado, setEstado] = useState(null);
  const [ocupado, setOcupado] = useState("");
  const [resultadoDoTeste, setResultadoDoTeste] = useState(null);
  const [passosFeitos, setPassosFeitos] = useState(lerProgresso);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        // Garante o token de verificação já na primeira abertura (o passo 7 precisa dele).
        const { data } = await api.post("/whatsapp/config/meta/token-de-verificacao");
        if (ativo) setEstado(data);
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível carregar a conexão."));
      } finally {
        if (ativo) setCarregando(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  const alternarPasso = useCallback((id) => {
    setPassosFeitos((atual) => {
      const novo = atual.includes(id) ? atual.filter((item) => item !== id) : [...atual, id];
      try {
        localStorage.setItem(CHAVE_PROGRESSO, JSON.stringify(novo));
      } catch {
        // Sem armazenamento local o guia funciona, só não lembra os passos marcados.
      }
      return novo;
    });
  }, []);

  const executar = useCallback(async (nome, chamada, sucesso) => {
    setOcupado(nome);
    try {
      const { data } = await chamada();
      if (sucesso) toast.success(sucesso);
      return data;
    } catch (error) {
      toast.error(mensagemDeErro(error, "Não foi possível concluir. Tente de novo."));
      return null;
    } finally {
      setOcupado("");
    }
  }, []);

  const salvarCredenciais = useCallback(
    async (dados) => {
      const data = await executar(
        "salvar",
        () => api.put("/whatsapp/config/meta/credenciais", dados),
        "Dados salvos.",
      );
      if (data) {
        setEstado(data);
        setResultadoDoTeste(null);
      }
      return Boolean(data);
    },
    [executar],
  );

  const testar = useCallback(async () => {
    const data = await executar("testar", () => api.post("/whatsapp/config/meta/testar"));
    if (data) {
      setEstado(data.estado);
      setResultadoDoTeste(data);
    }
  }, [executar]);

  const inscreverApp = useCallback(async () => {
    const data = await executar(
      "inscrever",
      () => api.post("/whatsapp/config/meta/inscrever-app"),
      "App inscrito na conta.",
    );
    if (data) await testar();
  }, [executar, testar]);

  const ativar = useCallback(async () => {
    const confirmado = await confirmarCorePet({
      titulo: "Ativar o WhatsApp oficial",
      mensagem:
        "A partir de agora as mensagens desta loja saem e chegam pela API oficial da Meta, no lugar da conexão atual. Deseja ativar?",
      confirmarTexto: "Ativar",
    });
    if (!confirmado) return;
    const data = await executar(
      "ativar",
      () => api.post("/whatsapp/config/meta/ativar"),
      "WhatsApp oficial ativado.",
    );
    if (data) setEstado(data);
  }, [executar]);

  return {
    alternarPasso,
    ativar,
    carregando,
    erro,
    estado,
    inscreverApp,
    ocupado,
    passosFeitos,
    resultadoDoTeste,
    salvarCredenciais,
    testar,
  };
}
