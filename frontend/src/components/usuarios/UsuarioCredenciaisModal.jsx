import { Clipboard, KeyRound, RefreshCw, UserCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { formatInitialAccessCredentials } from "../../utils/usuarioAcessoInicial";
import { PERFIS_APP } from "../../utils/appAccessProfiles";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCheckGroup from "../v2/InputCheckGroup/InputCheckGroup";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

export default function UsuarioCredenciaisModal({
  credenciais,
  erro,
  generatedPassword,
  loading,
  onChange,
  onClose,
  onGenerate,
  onSalvarPerfisApp,
  onSubmit,
  perfisApp,
  pessoaVinculada,
  roles,
  savingPerfisApp,
  tenantReference,
  usuario,
}) {
  const [perfisSelecionados, setPerfisSelecionados] = useState([]);

  useEffect(() => {
    setPerfisSelecionados(perfisApp || []);
  }, [perfisApp, usuario]);

  if (!usuario) return null;

  const copiarSenha = async () => {
    if (!generatedPassword) return;
    await navigator.clipboard.writeText(generatedPassword);
  };

  const copiarDadosDeAcesso = async () => {
    if (!generatedPassword || !tenantReference) return;
    await navigator.clipboard.writeText(
      formatInitialAccessCredentials({
        tenant: tenantReference,
        loginPhone: credenciais.login_phone,
        password: generatedPassword,
      }),
    );
  };

  return (
    <ModalPadrao
      titulo="Gerenciar acesso"
      tamanho="grande"
      onFechar={onClose}
      rodape={
        <>
          <BotaoCancelar onClick={onClose}>Fechar</BotaoCancelar>
          <BotaoInteracao icon={RefreshCw} onClick={onGenerate} disabled={loading}>
            Gerar nova senha
          </BotaoInteracao>
          <BotaoSalva form="credenciais-usuario-form" icon={KeyRound} disabled={loading}>
            Salvar
          </BotaoSalva>
        </>
      }
    >
      <div className="space-y-5">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {usuario.nome || usuario.login_phone || usuario.username || usuario.email}
        </p>

        {pessoaVinculada ? (
          <div className="flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
            <UserCheck className="h-4 w-4 flex-none" aria-hidden="true" />
            Vinculado à pessoa: {pessoaVinculada.nome}
          </div>
        ) : null}

        <form id="credenciais-usuario-form" onSubmit={onSubmit} className="space-y-4">
          {erro ? (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
              {erro}
            </p>
          ) : null}

          <InputCombobox
            id="cred-role"
            label="Perfil de acesso"
            required
            permitirLimpar={false}
            opcoes={roles.map((role) => ({ value: String(role.role_id), label: role.nome }))}
            value={credenciais.role_id ? String(credenciais.role_id) : ""}
            onChange={(role_id) => onChange({ ...credenciais, role_id })}
            help="Ao trocar o perfil, as sessões abertas deste usuário serão encerradas."
          />

          <InputTexto
            id="cred-login-phone"
            label="Celular de acesso"
            required
            type="tel"
            maxLength={25}
            value={credenciais.login_phone}
            onChange={(login_phone) => onChange({ ...credenciais, login_phone })}
            placeholder="(18) 99740-1641"
          />

          <InputTexto
            id="cred-password"
            label="Definir nova senha (opcional)"
            type="password"
            value={credenciais.new_password}
            onChange={(new_password) => onChange({ ...credenciais, new_password })}
            placeholder="Mínimo 8 caracteres"
            minLength={8}
            maxLength={72}
            autoComplete="new-password"
          />

          {generatedPassword ? (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 dark:border-emerald-500/30 dark:bg-emerald-500/10">
              <p className="text-xs font-medium text-emerald-800 dark:text-emerald-200">
                Copie e entregue esta senha ao usuário. Ela não será mostrada novamente.
              </p>
              <div className="mt-2 flex items-center gap-2">
                <code className="min-w-0 flex-1 break-all rounded bg-white px-2 py-1.5 text-sm dark:bg-slate-900">
                  {generatedPassword}
                </code>
                <BotaoInteracao icon={Clipboard} tamanho="pequeno" onClick={copiarSenha}>
                  Copiar
                </BotaoInteracao>
              </div>
              {tenantReference ? (
                <button
                  type="button"
                  onClick={copiarDadosDeAcesso}
                  className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-emerald-800 underline-offset-2 hover:underline dark:text-emerald-200"
                >
                  <Clipboard className="h-3.5 w-3.5" aria-hidden="true" />
                  Copiar celular e nova senha
                </button>
              ) : null}
            </div>
          ) : null}

          <p className="text-xs text-slate-500 dark:text-slate-400">
            Ao trocar a senha, as sessões abertas desta conta serão encerradas.
          </p>
        </form>

        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          {pessoaVinculada ? (
            <>
              <InputCheckGroup
                name="cred-perfis"
                label="Perfis de acesso ao app (Clique para alternar permissão)"
                opcoes={PERFIS_APP}
                value={perfisSelecionados}
                onChange={setPerfisSelecionados}
              />
              <div className="mt-3">
                <BotaoSalva
                  type="button"
                  tamanho="pequeno"
                  loading={savingPerfisApp}
                  onClick={() => onSalvarPerfisApp(perfisSelecionados)}
                >
                  Salvar perfis de acesso
                </BotaoSalva>
              </div>
            </>
          ) : (
            <>
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Perfis de acesso ao app
              </span>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Este usuário não tem uma pessoa vinculada — não é possível definir perfis de app.
              </p>
            </>
          )}
        </div>
      </div>
    </ModalPadrao>
  );
}
