import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Circle } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { Aviso, Botao, Campo } from "../components/ui";
import { checarSenhaNova } from "../lib/formatadores";

export default function TrocarSenha() {
  const { admin, trocarSenha } = useAuth();
  const navegar = useNavigate();
  const obrigatoria = Boolean(admin?.precisa_trocar_a_senha);
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState("");
  const [pronto, setPronto] = useState("");
  const [enviando, setEnviando] = useState(false);

  const regras = checarSenhaNova(nova, atual);
  const confirmacaoErrada = confirmacao.length > 0 && confirmacao !== nova;
  const podeEnviar = Boolean(atual) && regras.every((r) => r.ok) && confirmacao === nova && !enviando;

  const enviar = async (evento) => {
    evento.preventDefault();
    if (!podeEnviar) return;
    setErro("");
    setEnviando(true);
    try {
      const dados = await trocarSenha(atual, nova);
      setAtual("");
      setNova("");
      setConfirmacao("");
      if (obrigatoria) {
        navegar("/", { replace: true });
        return;
      }
      setPronto(
        dados.outras_sessoes_encerradas
          ? "Senha alterada. Os outros dispositivos conectados foram desconectados."
          : "Senha alterada.",
      );
    } catch (falha) {
      setErro(falha.message || "Não foi possível alterar a senha.");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className={obrigatoria ? "flex min-h-full items-center justify-center px-4 py-10" : ""}>
      <form
        onSubmit={enviar}
        noValidate
        className="w-full max-w-md space-y-5 rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900"
      >
        <div>
          <h1 className="text-2xl font-bold">{obrigatoria ? "Crie sua senha" : "Trocar minha senha"}</h1>
          {obrigatoria ? (
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              A senha atual é provisória. Escolha uma nova para continuar.
            </p>
          ) : null}
        </div>
        {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
        {pronto ? <Aviso tom="ok">{pronto}</Aviso> : null}
        <Campo
          rotulo="Senha atual"
          type="password"
          autoComplete="current-password"
          value={atual}
          onChange={(e) => setAtual(e.target.value)}
        />
        <Campo
          rotulo="Nova senha"
          type="password"
          autoComplete="new-password"
          value={nova}
          onChange={(e) => setNova(e.target.value)}
        />
        <ul className="space-y-1 text-sm" aria-label="Regras da nova senha">
          {regras.map((regra) => (
            <li
              key={regra.texto}
              className={`flex items-center gap-2 ${regra.ok ? "text-emerald-800 dark:text-emerald-300" : "text-slate-600 dark:text-slate-400"}`}
            >
              {regra.ok ? <Check className="h-4 w-4" aria-hidden="true" /> : <Circle className="h-4 w-4" aria-hidden="true" />}
              {regra.texto}
              <span className="sr-only">{regra.ok ? " (atendida)" : " (pendente)"}</span>
            </li>
          ))}
        </ul>
        <Campo
          rotulo="Repita a nova senha"
          type="password"
          autoComplete="new-password"
          value={confirmacao}
          onChange={(e) => setConfirmacao(e.target.value)}
          erro={confirmacaoErrada ? "As senhas não são iguais." : ""}
        />
        <Botao type="submit" disabled={!podeEnviar} carregando={enviando} className="w-full">
          Salvar nova senha
        </Botao>
      </form>
    </div>
  );
}
