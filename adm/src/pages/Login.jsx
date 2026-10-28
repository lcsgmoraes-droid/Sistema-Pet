import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { Aviso, Botao, Campo } from "../components/ui";

export default function Login() {
  const { admin, aviso, entrar } = useAuth();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrar, setMostrar] = useState(false);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  if (admin) return <Navigate to={admin.precisa_trocar_a_senha ? "/trocar-senha" : "/"} replace />;

  const enviar = async (evento) => {
    evento.preventDefault();
    if (!email.trim() || !senha) {
      setErro("Informe o e-mail e a senha.");
      return;
    }
    setErro("");
    setEnviando(true);
    try {
      await entrar(email.trim(), senha);
    } catch (falha) {
      setErro(falha.message || "Não foi possível entrar. Tente de novo.");
      setSenha("");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center px-4 py-10">
      <form
        onSubmit={enviar}
        noValidate
        className="w-full max-w-sm space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <div>
          <h1 className="text-2xl font-bold">Administração CorePet</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Acesso restrito à equipe.</p>
        </div>
        {aviso ? <Aviso tom="atencao">{aviso}</Aviso> : null}
        {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
        <Campo
          rotulo="E-mail"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Campo
          rotulo="Senha"
          type={mostrar ? "text" : "password"}
          autoComplete="current-password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          direita={
            <button
              type="button"
              aria-label={mostrar ? "Ocultar senha" : "Mostrar senha"}
              onClick={() => setMostrar(!mostrar)}
              className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {mostrar ? <EyeOff className="h-5 w-5" aria-hidden="true" /> : <Eye className="h-5 w-5" aria-hidden="true" />}
            </button>
          }
        />
        <Botao type="submit" carregando={enviando} className="w-full">
          Entrar
        </Botao>
      </form>
    </div>
  );
}
