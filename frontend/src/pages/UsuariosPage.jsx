import { Plus, Users } from "lucide-react";
import UsuarioModal from "../components/usuarios/UsuarioModal";
import UsuarioCredenciaisModal from "../components/usuarios/UsuarioCredenciaisModal";
import UsuariosTable from "../components/usuarios/UsuariosTable";
import BotaoInteracao from "../components/v2/BotaoInteracao/BotaoInteracao";
import InputComboboxMultiplo from "../components/v2/InputComboboxMultiplo/InputComboboxMultiplo";
import InputTexto from "../components/v2/InputTexto/InputTexto";
import PageHeader from "../components/ui/PageHeader";
import Panel from "../components/ui/Panel";
import PaginationControls from "../components/ui/PaginationControls";
import useUsuariosPage from "../hooks/useUsuariosPage";

const OPCOES_STATUS = [
  { value: "ativo", label: "Ativos" },
  { value: "inativo", label: "Inativos" },
];

export default function UsuariosPage() {
  const {
    criarUsuario,
    credenciais,
    credenciaisError,
    fecharCredenciais,
    filtroPerfil,
    filtroStatus,
    forcarLogout,
    generatedPassword,
    gerarNovaSenha,
    itensPorPagina,
    limparErroServidor,
    loading,
    novoUsuario,
    onAbrirModalUsuario,
    onAbrirCredenciais,
    onCloseModalUsuario,
    paginaAtual,
    perfisApp,
    pessoaVinculadaCredenciais,
    roles,
    searchTerm,
    setFiltroPerfil,
    setFiltroStatus,
    setItensPorPagina,
    setNovoUsuario,
    setCredenciais,
    setPaginaAtual,
    setSearchTerm,
    showModal,
    salvarCredenciais,
    salvarPerfisApp,
    savingCredentials,
    savingPerfisApp,
    tenantLoginReference,
    toggleStatus,
    totalPaginas,
    totalUsuariosFiltrados,
    usuarioServerErrors,
    usuarioCredenciais,
    usuarios,
  } = useUsuariosPage();

  const opcoesPerfil = roles.map((role) => ({
    value: String(role.role_id),
    label: role.nome,
  }));

  const paginacao = (variant) => (
    <PaginationControls
      currentPage={paginaAtual}
      itemName="usuarios"
      itemsPerPage={itensPorPagina}
      loading={loading}
      onItemsPerPageChange={setItensPorPagina}
      onPageChange={setPaginaAtual}
      totalItems={totalUsuariosFiltrados}
      totalPages={totalPaginas}
      variant={variant}
    />
  );

  return (
    <div className="space-y-4 p-4 sm:p-6">
      <PageHeader
        icon={Users}
        title="Usuarios"
        subtitle="Gerencie usuarios, perfis e acessos do tenant atual."
        actions={
          <BotaoInteracao icon={Plus} onClick={onAbrirModalUsuario}>
            Novo usuario
          </BotaoInteracao>
        }
      />

      <Panel padding="md">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_320px_280px]">
          <InputTexto
            id="usuarios-busca"
            label="Buscar"
            value={searchTerm}
            onChange={setSearchTerm}
            placeholder="Buscar por nome, celular, usuário ou e-mail..."
          />
          <InputComboboxMultiplo
            id="usuarios-filtro-perfil"
            label="Perfil"
            placeholder="Todos os perfis"
            opcoes={opcoesPerfil}
            value={filtroPerfil}
            onChange={setFiltroPerfil}
          />
          <InputComboboxMultiplo
            id="usuarios-filtro-status"
            label="Status"
            placeholder="Todos os status"
            opcoes={OPCOES_STATUS}
            value={filtroStatus}
            onChange={setFiltroStatus}
          />
        </div>
      </Panel>

      {paginacao("top")}

      <UsuariosTable
        loading={loading}
        onForcarLogout={forcarLogout}
        onManageCredentials={onAbrirCredenciais}
        onToggleStatus={toggleStatus}
        paginacaoRodape={paginacao("bottom")}
        usuarios={usuarios}
      />

      <UsuarioModal
        limparErroServidor={limparErroServidor}
        novoUsuario={novoUsuario}
        onClose={onCloseModalUsuario}
        onSubmit={criarUsuario}
        roles={roles}
        setNovoUsuario={setNovoUsuario}
        showModal={showModal}
        usuarioServerErrors={usuarioServerErrors}
      />

      <UsuarioCredenciaisModal
        credenciais={credenciais}
        erro={credenciaisError}
        generatedPassword={generatedPassword}
        loading={savingCredentials}
        onChange={setCredenciais}
        onClose={fecharCredenciais}
        onGenerate={gerarNovaSenha}
        onSubmit={salvarCredenciais}
        perfisApp={perfisApp}
        pessoaVinculada={pessoaVinculadaCredenciais}
        onSalvarPerfisApp={salvarPerfisApp}
        savingPerfisApp={savingPerfisApp}
        roles={roles}
        tenantReference={tenantLoginReference}
        usuario={usuarioCredenciais}
      />
    </div>
  );
}
