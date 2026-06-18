import { FiCreditCard, FiPackage, FiSettings, FiShield, FiTruck, FiUsers } from "react-icons/fi";
import { Link } from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import { useAuth } from "../contexts/AuthContext";
import { useModulos } from "../contexts/ModulosContext";

const cards = [
  {
    title: "Usuarios",
    description: "Gerenciar usuarios do sistema",
    icon: FiUsers,
    link: "/admin/usuarios",
    color: "blue",
    permission: "usuarios.manage",
  },
  {
    title: "Permissoes",
    description: "Gerenciar roles e permissoes",
    icon: FiShield,
    link: "/admin/roles",
    color: "purple",
    permission: "usuarios.manage",
  },
  {
    title: "Configuracao da Empresa",
    description: "Dados cadastrais e tributacao padrao",
    icon: FiSettings,
    link: "/configuracoes/fiscal",
    color: "green",
    anyOfPermissions: ["configuracoes.empresa", "configuracoes.editar"],
  },
  {
    title: "Parametros Gerais",
    description: "Margens do PDV, mensagens, metas e alertas",
    icon: FiSettings,
    link: "/configuracoes/geral",
    color: "orange",
    permission: "configuracoes.editar",
  },
  {
    title: "Estoque",
    description: "Comportamento do controle de estoque",
    icon: FiPackage,
    link: "/configuracoes/estoque",
    color: "indigo",
    permission: "configuracoes.editar",
  },
  {
    title: "Entregas",
    description: "Entregadores e ponto inicial de rotas",
    icon: FiTruck,
    link: "/configuracoes/entregas",
    color: "blue",
    modulo: "entregas",
    permission: "configuracoes.entregas",
  },
  {
    title: "Custos da Moto",
    description: "Custos operacionais da moto de entregas",
    icon: FiSettings,
    link: "/configuracoes/custos-moto",
    color: "orange",
    modulo: "entregas",
    permission: "configuracoes.custos_moto",
  },
  {
    title: "Integracoes",
    description: "Conectores externos ativos",
    icon: FiCreditCard,
    link: "/configuracoes/integracoes",
    color: "green",
    modulo: "integracoes",
    permission: "configuracoes.editar",
  },
];

const colorClasses = {
  blue: "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100",
  purple: "border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100",
  green: "border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100",
  orange: "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100",
  indigo: "border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100",
};

export default function Configuracoes() {
  const { user } = useAuth();
  const { moduloAtivo } = useModulos();

  const permissions = user?.permissions || [];
  const roleName = user?.role?.name?.toLowerCase();
  const isAdmin = roleName === "admin";

  const hasPermission = (permission) => !permission || isAdmin || permissions.includes(permission);

  const hasAnyPermission = (required = []) =>
    required.length === 0 || isAdmin || required.some((item) => permissions.includes(item));

  const cardsVisiveis = cards.filter((card) => {
    if (card.modulo && !moduloAtivo(card.modulo)) return false;
    if (card.anyOfPermissions && !hasAnyPermission(card.anyOfPermissions)) return false;
    return hasPermission(card.permission);
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <PageHeader
        icon={FiSettings}
        title="Configuracoes"
        subtitle="Ajustes essenciais da empresa, usuarios, permissoes e operacao."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cardsVisiveis.map((card) => {
          const Icon = card.icon;

          return (
            <Link
              key={card.title}
              to={card.link}
              className={[
                "rounded-lg border p-5 shadow-sm transition hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500",
                colorClasses[card.color] || colorClasses.blue,
              ].join(" ")}
            >
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/70">
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-base font-semibold text-slate-950">{card.title}</h2>
                  <p className="mt-1 text-sm text-slate-600">{card.description}</p>
                  <span className="mt-4 inline-flex text-sm font-semibold text-current">
                    Acessar
                  </span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {cardsVisiveis.length === 0 ? (
        <Panel className="text-center text-sm text-slate-500">
          Nenhuma configuracao disponivel para o seu perfil.
        </Panel>
      ) : null}
    </div>
  );
}
