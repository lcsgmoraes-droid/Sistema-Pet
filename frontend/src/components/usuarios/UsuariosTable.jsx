import { Building2, KeyRound, LogOut, Mail, Trash2, UserCheck, UserX } from "lucide-react";
import BotaoMenuAcoes from "../v2/BotaoMenuAcoes/BotaoMenuAcoes";
import InputCheckbox from "../v2/InputCheckbox/InputCheckbox";
import DataTable from "../ui/DataTable";
import Panel from "../ui/Panel";
import StatusBadge from "../ui/StatusBadge";
import { formatBrazilianLoginPhone } from "../../utils/loginPhone";

function formatUmTipo(tipo) {
  const value = (tipo || "").trim();
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll("_", " ");
}

function formatPessoaTipo(tiposCadastro) {
  const lista = Array.isArray(tiposCadastro) ? tiposCadastro.filter(Boolean) : [];
  return lista.map(formatUmTipo).join(" / ");
}

export default function UsuariosTable({
  loading,
  onDelete,
  onForcarLogout,
  onManageCredentials,
  onRecriarSenha,
  onToggleCrediario,
  onToggleStatus,
  onVincularLoja,
  paginacaoRodape,
  savingLiberacaoId,
  usuarios,
}) {
  const columns = [
    {
      key: "actions",
      header: "Acoes",
      align: "left",
      render: (usuario) => (
        <BotaoMenuAcoes
          rotulo={`Mais ações para ${usuario.nome || usuario.login_phone || usuario.email}`}
          acoes={[
            {
              icon: KeyRound,
              label: "Gerenciar usuário e senha",
              onClick: () => onManageCredentials(usuario),
            },
            {
              icon: Mail,
              label: "Recriar senha",
              disabled: !usuario.email,
              title: usuario.email
                ? undefined
                : "Usuário sem e-mail cadastrado — não é possível enviar recriação de senha",
              onClick: () => onRecriarSenha(usuario.user_id),
            },
            {
              icon: Building2,
              label: "Vincular a outra loja do grupo",
              onClick: () => onVincularLoja(usuario),
            },
            {
              icon: LogOut,
              label: "Forçar logout",
              onClick: () => onForcarLogout(usuario.user_id),
            },
            {
              icon: usuario.is_active ? UserX : UserCheck,
              label: usuario.is_active ? "Desativar acesso" : "Ativar acesso",
              tom: usuario.is_active ? "perigo" : "neutro",
              onClick: () => onToggleStatus(usuario.user_id, usuario.is_active),
            },
            {
              icon: Trash2,
              label: "Excluir acesso definitivamente",
              tom: "perigo",
              onClick: () => onDelete(usuario),
            },
          ]}
        />
      ),
    },
    {
      key: "login_phone",
      header: "Usuario",
      render: (usuario) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900">
            {usuario.login_phone
              ? formatBrazilianLoginPhone(usuario.login_phone)
              : usuario.username || usuario.email}
          </p>
          <p className="truncate text-xs text-slate-500">
            {usuario.nome || usuario.email || `ID ${usuario.user_id}`}
          </p>
        </div>
      ),
    },
    {
      key: "pessoa",
      header: "Pessoa vinculada",
      render: (usuario) =>
        usuario.pessoa_id ? (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {usuario.pessoa_nome || `Pessoa ${usuario.pessoa_id}`}
            </p>
            <p className="truncate text-xs text-slate-500">
              {[
                usuario.pessoa_codigo ? `Codigo ${usuario.pessoa_codigo}` : null,
                formatPessoaTipo(usuario.pessoa_tipos_cadastro),
              ]
                .filter(Boolean)
                .join(" - ")}
            </p>
          </div>
        ) : (
          <StatusBadge intent="warning" size="sm">
            Sem pessoa
          </StatusBadge>
        ),
    },
    {
      key: "role",
      header: "Perfil",
      render: (usuario) => (
        <StatusBadge intent="info" size="sm">
          {usuario.role || "Sem perfil"}
        </StatusBadge>
      ),
    },
    {
      key: "liberacao_crediario",
      header: "Pode liberar venda bloqueada",
      align: "center",
      render: (usuario) => (
        <div className="inline-flex items-center gap-2 text-xs text-slate-700">
          <InputCheckbox
            rotulo={`Autorizar ${usuario.nome || usuario.email || usuario.user_id} a liberar venda com crediário atrasado`}
            checked={Boolean(usuario.pode_liberar_venda_crediario_atrasado)}
            disabled={savingLiberacaoId === usuario.user_id}
            onChange={(event) => onToggleCrediario(usuario, event.target.checked)}
          />
          <span>{usuario.pode_liberar_venda_crediario_atrasado ? "Concedida" : "Não concedida"}</span>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      align: "center",
      render: (usuario) => (
        <StatusBadge
          status={usuario.is_active ? "ativo" : "inativo"}
          intent={usuario.is_active ? "success" : "neutral"}
        />
      ),
    },
  ];

  return (
    <Panel padding="none">
      <DataTable
        columns={columns}
        data={usuarios}
        emptyMessage="Nenhum usuario encontrado"
        getRowKey={(usuario) => usuario.user_id}
        loading={loading}
        loadingMessage="Carregando usuarios..."
        tableClassName="min-w-[1060px]"
      />
      {paginacaoRodape}
    </Panel>
  );
}
