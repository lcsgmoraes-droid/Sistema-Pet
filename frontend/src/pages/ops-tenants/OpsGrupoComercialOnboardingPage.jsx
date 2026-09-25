import { useState } from "react";
import { Link } from "react-router-dom";
import { FiChevronLeft, FiMail, FiPlusCircle, FiTrash2, FiUserPlus, FiUsers } from "react-icons/fi";

import platformApi from "../../platformApi";

function novaLojaVazia() {
  return { nome_loja: "", nome_acesso: "" };
}

function extrairErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

export default function OpsGrupoComercialOnboardingPage() {
  const [titularEmail, setTitularEmail] = useState("");
  const [titularNome, setTitularNome] = useState("");
  const [lojas, setLojas] = useState([novaLojaVazia()]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [resultado, setResultado] = useState(null);

  function atualizarLoja(indice, campo, valor) {
    setLojas((atual) =>
      atual.map((loja, i) => (i === indice ? { ...loja, [campo]: valor } : loja)),
    );
  }

  function adicionarLoja() {
    setLojas((atual) => [...atual, novaLojaVazia()]);
  }

  function removerLoja(indice) {
    setLojas((atual) => atual.filter((_, i) => i !== indice));
  }

  function validar() {
    if (!titularEmail.trim() || !titularEmail.includes("@")) {
      return "Informe um e-mail valido para o titular.";
    }
    if (lojas.length === 0) {
      return "Adicione ao menos uma loja.";
    }
    if (lojas.some((loja) => loja.nome_loja.trim().length < 2)) {
      return "Toda loja precisa de um nome com pelo menos 2 caracteres.";
    }
    return "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const mensagemValidacao = validar();
    if (mensagemValidacao) {
      setErro(mensagemValidacao);
      return;
    }
    setErro("");
    setResultado(null);
    setEnviando(true);
    try {
      const { data } = await platformApi.post("/admin/grupos-comerciais/onboarding", {
        titular_email: titularEmail.trim().toLowerCase(),
        titular_nome: titularNome.trim() || undefined,
        lojas: lojas.map((loja) => ({
          nome_loja: loja.nome_loja.trim(),
          nome_acesso: loja.nome_acesso.trim() || undefined,
        })),
      });
      setResultado(data);
      setTitularEmail("");
      setTitularNome("");
      setLojas([novaLojaVazia()]);
    } catch (error) {
      setErro(extrairErro(error, "Nao foi possivel concluir o onboarding. Tente novamente."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <Link
        to="/ops/tenants"
        className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
      >
        <FiChevronLeft aria-hidden="true" />
        Voltar para tenants
      </Link>

      <div>
        <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
          <FiUsers className="h-5 w-5" />
          Onboarding assistido
        </div>
        <h1 className="mt-1 text-2xl font-bold text-slate-950">Novo grupo comercial</h1>
        <p className="mt-1 text-sm text-slate-500">
          Use esta tela quando o contrato inicial do cliente já inclui mais de uma loja. Cada
          loja listada aqui é criada de uma vez, todas dentro de um único grupo comercial novo.
          Para adicionar mais uma loja a um cliente que já tem grupo comercial, use o botão
          "Adicionar loja" dentro do grupo dele, na tela de Tenants.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
              E-mail do titular
            </span>
            <div className="relative mt-1">
              <FiMail className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                type="email"
                value={titularEmail}
                onChange={(event) => setTitularEmail(event.target.value)}
                placeholder="dono@empresa.com"
                className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </label>
          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
              Nome do titular (opcional)
            </span>
            <div className="relative mt-1">
              <FiUserPlus className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={titularNome}
                onChange={(event) => setTitularNome(event.target.value)}
                placeholder="Ex.: Maria Silva"
                maxLength={160}
                className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
            </div>
          </label>
        </div>

        <div className="space-y-3">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-500">Lojas</span>
          {lojas.map((loja, indice) => (
            <div
              key={indice}
              className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-center"
            >
              <input
                type="text"
                value={loja.nome_loja}
                onChange={(event) => atualizarLoja(indice, "nome_loja", event.target.value)}
                placeholder={`Nome da loja ${indice + 1}`}
                maxLength={150}
                className="h-10 min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
              <input
                type="text"
                value={loja.nome_acesso}
                onChange={(event) => atualizarLoja(indice, "nome_acesso", event.target.value)}
                placeholder="Nome de acesso (opcional)"
                maxLength={150}
                className="h-10 min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
              {lojas.length > 1 ? (
                <button
                  type="button"
                  onClick={() => removerLoja(indice)}
                  className="inline-flex h-10 items-center justify-center gap-1 rounded-lg border border-rose-200 px-3 text-sm font-semibold text-rose-600 hover:bg-rose-50 sm:w-auto"
                >
                  <FiTrash2 className="h-4 w-4" />
                  Remover
                </button>
              ) : null}
            </div>
          ))}
          <button
            type="button"
            onClick={adicionarLoja}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 text-sm font-semibold text-blue-700 hover:bg-blue-100"
          >
            <FiPlusCircle className="h-4 w-4" />
            Adicionar outra loja
          </button>
        </div>

        {erro ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {erro}
          </div>
        ) : null}

        {resultado ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800">
            <p className="font-semibold">
              Grupo comercial #{resultado.grupo_id} criado com {resultado.lojas.length} loja(s).
            </p>
            <p className="mt-1">
              Um e-mail para definir a senha foi enviado para {resultado.titular_email}.
            </p>
            <ul className="mt-2 list-disc space-y-0.5 pl-5">
              {resultado.lojas.map((loja) => (
                <li key={loja.tenant_id}>
                  {loja.nome} — login: {loja.login_name}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <button
          type="submit"
          disabled={enviando}
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FiPlusCircle className={`h-4 w-4 ${enviando ? "animate-pulse" : ""}`} />
          {enviando ? "Criando..." : "Criar grupo comercial"}
        </button>
      </form>
    </div>
  );
}
