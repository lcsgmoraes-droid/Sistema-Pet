// Cliente da API do painel.
//
// Seguranca:
// - o token de acesso fica SO na memoria desta aba (nunca em localStorage/sessionStorage);
// - a renovacao usa o cookie HttpOnly do servidor, que o JavaScript nao consegue ler;
// - todo pedido leva o cabecalho do painel, que o servidor confere junto com a origem.

const BASE = "/api";
const CABECALHO_DO_PAINEL = { "X-Corepet-Adm": "1" };

let tokenDeAcesso = null;
let aoPerderASessao = () => {};
let renovacaoEmAndamento = null;

export class ErroDaApi extends Error {
  constructor(mensagem, status, detalhe) {
    super(mensagem);
    this.name = "ErroDaApi";
    this.status = status;
    this.detalhe = detalhe;
  }
}

export function definirToken(token) {
  tokenDeAcesso = token || null;
}

export function temToken() {
  return Boolean(tokenDeAcesso);
}

export function aoPerderSessao(funcao) {
  aoPerderASessao = funcao;
}

function mensagemDoErro(corpo, padrao) {
  const detalhe = corpo?.detail;
  if (typeof detalhe === "string") return detalhe;
  if (Array.isArray(detalhe) && detalhe[0]?.msg) return detalhe[0].msg;
  return padrao;
}

async function lerCorpo(resposta) {
  const texto = await resposta.text();
  if (!texto) return null;
  try {
    return JSON.parse(texto);
  } catch {
    return null;
  }
}

async function pedir(metodo, caminho, { corpo, autenticado = true } = {}) {
  const cabecalhos = { ...CABECALHO_DO_PAINEL };
  if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";
  if (autenticado && tokenDeAcesso) cabecalhos.Authorization = `Bearer ${tokenDeAcesso}`;
  let resposta;
  try {
    resposta = await fetch(`${BASE}${caminho}`, {
      method: metodo,
      headers: cabecalhos,
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    throw new ErroDaApi("Sem conexão com o servidor. Verifique a internet e tente de novo.", 0);
  }
  const dados = await lerCorpo(resposta);
  if (!resposta.ok) {
    throw new ErroDaApi(mensagemDoErro(dados, "Não foi possível concluir."), resposta.status, dados);
  }
  return dados;
}

const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

/** Renova o token usando o cookie. Varias chamadas ao mesmo tempo viram uma so. */
export function renovarSessao() {
  if (!renovacaoEmAndamento) {
    renovacaoEmAndamento = (async () => {
      for (let tentativa = 0; tentativa < 3; tentativa += 1) {
        try {
          const dados = await pedir("POST", "/adm/auth/refresh", { autenticado: false });
          definirToken(dados.access_token);
          return dados;
        } catch (erro) {
          // 409 = outra aba esta renovando agora; o cookie novo ja chega na proxima tentativa.
          if (erro.status === 409 && tentativa < 2) {
            await esperar(700);
            continue;
          }
          throw erro;
        }
      }
      throw new ErroDaApi("Sessão expirada.", 401);
    })().finally(() => {
      renovacaoEmAndamento = null;
    });
  }
  return renovacaoEmAndamento;
}

/** Pedido autenticado: se o token venceu, renova uma vez e repete. */
export async function api(metodo, caminho, opcoes) {
  try {
    return await pedir(metodo, caminho, opcoes);
  } catch (erro) {
    if (erro.status !== 401 || opcoes?.autenticado === false) throw erro;
    try {
      await renovarSessao();
    } catch {
      definirToken(null);
      aoPerderASessao();
      throw erro;
    }
    return pedir(metodo, caminho, opcoes);
  }
}

export const obter = (caminho) => api("GET", caminho);
export const enviar = (caminho, corpo) => api("POST", caminho, { corpo });
export const entrarNoPainel = (email, senha) =>
  pedir("POST", "/adm/auth/login", { corpo: { email, password: senha }, autenticado: false });
export const alterar = (caminho, corpo) => api("PATCH", caminho, { corpo });
export const substituir = (caminho, corpo) => api("PUT", caminho, { corpo });
