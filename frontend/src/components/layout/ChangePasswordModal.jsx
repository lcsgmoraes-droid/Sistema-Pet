import { useState } from "react";
import { createPortal } from "react-dom";
import api from "../../api";
import { clearAuthTokens } from "../../auth/tokenStorage";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputSenha from "../v2/InputSenha/InputSenha";

// Modal só sai por Cancelar ou Salvar: sem onClick no fundo escurecido e sem
// botão de fechar (X) no cabeçalho, de propósito — evita perder o
// preenchimento com um clique ou Esc sem querer.
export default function ChangePasswordModal({ onClose }) {
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erros, setErros] = useState({});
  const [erroGeral, setErroGeral] = useState("");
  const [salvando, setSalvando] = useState(false);

  const validar = () => {
    const proximosErros = {};
    if (!senhaAtual) proximosErros.senhaAtual = "Informe a senha atual.";
    if (!novaSenha) {
      proximosErros.novaSenha = "Informe a nova senha.";
    } else if (novaSenha.length < 8) {
      proximosErros.novaSenha = "A nova senha deve ter pelo menos 8 caracteres.";
    }
    if (!confirmacao) {
      proximosErros.confirmacao = "Confirme a nova senha.";
    } else if (novaSenha && confirmacao !== novaSenha) {
      proximosErros.confirmacao = "A confirmação não corresponde à nova senha.";
    }
    setErros(proximosErros);
    return Object.keys(proximosErros).length === 0;
  };

  const salvar = async (evento) => {
    evento.preventDefault();
    setErroGeral("");
    if (!validar()) return;

    setSalvando(true);
    try {
      await api.post("/auth/change-password", {
        senha_atual: senhaAtual,
        nova_senha: novaSenha,
      });
      clearAuthTokens();
      localStorage.removeItem("tenants");
      localStorage.removeItem("user");
      localStorage.removeItem("selectedTenant");
      window.location.assign("/login?senha=alterada");
    } catch (error) {
      const detalhe = error.response?.data?.detail;
      setErroGeral(
        typeof detalhe === "string"
          ? detalhe
          : "Não foi possível alterar a senha. Tente novamente.",
      );
      setSalvando(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-password-title"
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900"
      >
        <h2
          id="change-password-title"
          className="text-xl font-semibold text-slate-900 dark:text-white"
        >
          Trocar senha
        </h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Informe sua senha atual e escolha uma nova senha. Depois, entre novamente em seus
          dispositivos.
        </p>
        <form onSubmit={salvar} noValidate className="mt-5 space-y-4">
          <InputSenha
            id="trocar-senha-atual"
            label="Senha atual"
            value={senhaAtual}
            onChange={(valor) => {
              setSenhaAtual(valor);
              if (erros.senhaAtual) setErros((atual) => ({ ...atual, senhaAtual: "" }));
            }}
            autoComplete="current-password"
            autoFocus
            required
            disabled={salvando}
            error={erros.senhaAtual}
          />
          <InputSenha
            id="trocar-senha-nova"
            label="Nova senha"
            value={novaSenha}
            onChange={(valor) => {
              setNovaSenha(valor);
              if (erros.novaSenha) setErros((atual) => ({ ...atual, novaSenha: "" }));
            }}
            autoComplete="new-password"
            required
            disabled={salvando}
            error={erros.novaSenha}
            help={erros.novaSenha ? "" : "Pelo menos 8 caracteres."}
          />
          <InputSenha
            id="trocar-senha-confirmacao"
            label="Confirmar nova senha"
            value={confirmacao}
            onChange={(valor) => {
              setConfirmacao(valor);
              if (erros.confirmacao) setErros((atual) => ({ ...atual, confirmacao: "" }));
            }}
            autoComplete="new-password"
            required
            disabled={salvando}
            error={erros.confirmacao}
          />
          {erroGeral ? (
            <p role="alert" className="text-sm text-red-600 dark:text-red-300">
              {erroGeral}
            </p>
          ) : null}
          <div className="flex justify-end gap-3 pt-2">
            <BotaoCancelar onClick={onClose} disabled={salvando} />
            <BotaoSalva loading={salvando}>
              {salvando ? "Salvando..." : "Salvar nova senha"}
            </BotaoSalva>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
