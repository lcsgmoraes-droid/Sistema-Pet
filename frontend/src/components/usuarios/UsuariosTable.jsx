import { KeyRound, LogOut, Trash2, UserCheck, UserX } from "lucide-react";
import DataTable from "../ui/DataTable";
import IconActionButton from "../ui/IconActionButton";
import Panel from "../ui/Panel";
import StatusBadge from "../ui/StatusBadge";
import { formatBrazilianLoginPhone } from "../../utils/loginPhone";

function formatPessoaTipo(tipoCadastro) {
  const value = (tipoCadastro || "").trim();
  if (!value) return "";
  return value.charAt(0).toUpperCase() + value.slice(1).replaceAll("_", " ");
}

export default function UsuariosTable({
  loading,
  onForcarLogout,
  onManageCredentials,
  onToggleStatus,
  onDelete,
  onToggleCrediario,
  savingLiberacaoId,
  usuarios,
}) {
  const columns = [
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
                formatPessoaTipo(usuario.pessoa_tipo_cadastro),
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
        <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-slate-700">
          <input
            type="checkbox"
            aria-label={`Autorizar ${usuario.nome || usuario.email || usuario.user_id} a liberar venda com crediário atrasado`}
            checked={Boolean(usuario.pode_liberar_venda_crediario_atrasado)}
            disabled={savingLiberacaoId === usuario.user_id}
            onChange={(event) => onToggleCrediario(usuario, event.target.checked)}
            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          {usuario.pode_liberar_venda_crediario_atrasado ? "Concedida" : "Não concedida"}
        </label>
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
    {
      key: "actions",
      header: "Acoes",
      align: "center",
      render: (usuario) => (
        <div className="flex items-center justify-center gap-2">
          <IconActionButton
            icon={KeyRound}
            intent="edit"
            onClick={() => onManageCredentials(usuario)}
            title="Gerenciar usuario e senha"
          />
          <IconActionButton
            icon={LogOut}
            intent="warning"
            onClick={() => onForcarLogout(usuario.user_id)}
            title="Forcar logout"
          />
          <IconActionButton
            icon={usuario.is_active ? UserX : UserCheck}
            intent={usuario.is_active ? "danger" : "success"}
            onClick={() => onToggleStatus(usuario.user_id, usuario.is_active)}
            title={usuario.is_active ? "Desativar acesso" : "Ativar acesso"}
          />
          <IconActionButton
            icon={Trash2}
            intent="danger"
            onClick={() => onDelete(usuario)}
            title="Excluir acesso definitivamente"
          />
        </div>
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
    </Panel>
  );
}
