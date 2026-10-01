import { KeyRound, UserCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { PERFIS_APP } from "../../utils/appAccessProfiles";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCheckGroup from "../v2/InputCheckGroup/InputCheckGroup";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

export default function UsuarioCredenciaisModal({
  credenciais,
  erro,
  loading,
  onChange,
  onClose,
  onSalvarPerfisApp,
  onSubmit,
  perfisApp,
  pessoaVinculada,
  roles,
  savingPerfisApp,
  usuario,
}) {
  const [perfisSelecionados, setPerfisSelecionados] = useState([]);

  useEffect(() => {
    setPerfisSelecionados(perfisApp || []);
  }, [perfisApp, usuario]);

  if (!usuario) return null;

  const alternarPerfisApp = async (novosPerfis) => {
    const anteriores = perfisSelecionados;
    setPerfisSelecionados(novosPerfis);
    const sucesso = await onSalvarPerfisApp(novosPerfis);
    if (!sucesso) setPerfisSelecionados(anteriores);
  };

  return (
    <ModalPadrao
      titulo="Gerenciar acesso"
      tamanho="grande"
      onFechar={onClose}
      rodape={
        <>
          <BotaoCancelar onClick={onClose}>Fechar</BotaoCancelar>
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
        </form>

        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          {pessoaVinculada ? (
            <InputCheckGroup
              name="cred-perfis"
              label="Perfis de acesso ao app (clique para marcar ou desmarcar — salva na hora)"
              opcoes={PERFIS_APP}
              value={perfisSelecionados}
              onChange={alternarPerfisApp}
              disabled={savingPerfisApp}
            />
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
