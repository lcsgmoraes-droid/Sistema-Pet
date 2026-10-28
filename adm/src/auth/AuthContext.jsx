import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  aoPerderSessao,
  definirToken,
  entrarNoPainel,
  enviar,
  renovarSessao,
} from "../api/cliente";

const AuthContext = createContext(null);

// Sem nenhuma atividade por este tempo, a sessao e encerrada neste navegador.
const INATIVIDADE_MAXIMA_MS = 30 * 60 * 1000;
const EVENTOS_DE_ATIVIDADE = ["pointerdown", "keydown", "touchstart", "scroll"];

export function AuthProvider({ children }) {
  // "carregando" cobre a tentativa de restaurar a sessao pelo cookie ao abrir o painel.
  const [carregando, setCarregando] = useState(true);
  const [admin, setAdmin] = useState(null);
  const [aviso, setAviso] = useState("");
  const temporizador = useRef(null);

  const limpar = useCallback((mensagem = "") => {
    definirToken(null);
    setAdmin(null);
    setAviso(mensagem);
  }, []);

  useEffect(() => {
    aoPerderSessao(() => limpar("Sua sessão expirou. Entre novamente."));
  }, [limpar]);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const dados = await renovarSessao();
        if (ativo) setAdmin(dados.admin);
      } catch {
        // Sem cookie valido: segue para a tela de login.
      } finally {
        if (ativo) setCarregando(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  const entrar = useCallback(async (email, senha) => {
    const dados = await entrarNoPainel(email, senha);
    definirToken(dados.access_token);
    setAviso("");
    setAdmin(dados.admin);
    return dados.admin;
  }, []);

  const sair = useCallback(
    async (mensagem = "") => {
      try {
        await enviar("/adm/auth/logout");
      } catch {
        // Mesmo se o servidor nao responder, a sessao local e encerrada.
      }
      limpar(mensagem);
    },
    [limpar],
  );

  const trocarSenha = useCallback(async (senhaAtual, novaSenha) => {
    const dados = await enviar("/adm/auth/change-password", {
      senha_atual: senhaAtual,
      nova_senha: novaSenha,
    });
    definirToken(dados.access_token);
    setAdmin(dados.admin);
    return dados;
  }, []);

  useEffect(() => {
    if (!admin) return undefined;
    const reiniciar = () => {
      clearTimeout(temporizador.current);
      temporizador.current = setTimeout(
        () => sair("Você foi desconectado por inatividade."),
        INATIVIDADE_MAXIMA_MS,
      );
    };
    reiniciar();
    EVENTOS_DE_ATIVIDADE.forEach((nome) => window.addEventListener(nome, reiniciar, { passive: true }));
    return () => {
      clearTimeout(temporizador.current);
      EVENTOS_DE_ATIVIDADE.forEach((nome) => window.removeEventListener(nome, reiniciar));
    };
  }, [admin, sair]);

  const valor = useMemo(
    () => ({ admin, aviso, carregando, entrar, sair, trocarSenha }),
    [admin, aviso, carregando, entrar, sair, trocarSenha],
  );
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth precisa estar dentro de AuthProvider");
  return contexto;
}
