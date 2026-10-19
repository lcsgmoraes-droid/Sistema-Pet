import { useEffect, useState } from "react";
import { MODELO_CASHBACK } from "./cashbackCrmUtils";

const LIMITE = 2000;
const ERRO_SALVAR =
  "Não foi possível salvar neste navegador. Seu texto será mantido apenas enquanto esta tela estiver aberta.";

function inicial(chave) {
  return { chave, selecao: "padrao", personalizado: MODELO_CASHBACK, erro: "" };
}

function carregar(chave) {
  const padrao = inicial(chave);
  if (!chave) return padrao;
  try {
    const salvo = JSON.parse(window.localStorage.getItem(chave) || "null");
    if (salvo?.versao !== 1) return padrao;
    return {
      ...padrao,
      selecao: salvo.selecao === "minha" ? "minha" : "padrao",
      personalizado:
        typeof salvo.personalizado === "string" && salvo.personalizado.length <= LIMITE
          ? salvo.personalizado
          : MODELO_CASHBACK,
    };
  } catch {
    return { ...padrao, erro: "Não foi possível recuperar o modelo salvo neste navegador." };
  }
}

export default function useCashbackModelo(user) {
  const tenantId = user?.tenant?.id || user?.tenant_id;
  const chave = tenantId && user?.id ? `corepet:cashback-modelo:v1:${tenantId}:${user.id}` : null;
  const [registro, setRegistro] = useState(() => carregar(chave));

  useEffect(() => {
    setRegistro(carregar(chave));
  }, [chave]);

  // Nunca mostrar ou gravar o modelo de outra conta durante a troca de identidade.
  const atual = registro.chave === chave ? registro : inicial(chave);
  const salvar = (mudanca) => {
    const proximo = { ...atual, ...mudanca, erro: "" };
    try {
      if (!chave) throw new Error("Identidade indisponível");
      // Gravar no evento evita efeitos que possam sobrescrever a preferência de outra empresa.
      window.localStorage.setItem(
        chave,
        JSON.stringify({
          versao: 1,
          selecao: proximo.selecao,
          personalizado: proximo.personalizado,
        }),
      );
    } catch {
      proximo.erro = ERRO_SALVAR;
    }
    setRegistro(proximo);
  };

  return {
    modelo: atual.selecao === "minha" ? atual.personalizado : MODELO_CASHBACK,
    tipoModelo: atual.selecao,
    erroModelo: atual.erro,
    selecionarModelo: (selecao) => {
      if (selecao === "padrao" || selecao === "minha") salvar({ selecao });
    },
    setModelo: (texto) =>
      salvar({ selecao: "minha", personalizado: String(texto).slice(0, LIMITE) }),
  };
}
