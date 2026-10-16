import { Plus, Users } from "lucide-react";
import UsuarioAcessoInicialModal from "../components/usuarios/UsuarioAcessoInicialModal";
import UsuarioCredenciaisModal from "../components/usuarios/UsuarioCredenciaisModal";
import UsuarioLojaLoginCard from "../components/usuarios/UsuarioLojaLoginCard";
import UsuarioModal from "../components/usuarios/UsuarioModal";
import UsuarioVincularLojaModal from "../components/usuarios/UsuarioVincularLojaModal";
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
    alterarLiberacaoCrediario,
    criarUsuario,
    credenciais,
    credenciaisError,
    excluirUsuario,
    fecharCredenciais,
    filtroPerfil,
    filtroStatus,
    forcarLogout,
    gerarNovaSenha,
    generatedPassword,
    initialAccessCredentials,
    itensPorPagina,
    limparErroServidor,
    loading,
    novoUsuario,
    onAbrirModalUsuario,
    onAbrirCredenciais,
    onAbrirVincularLoja,
    onCloseModalUsuario,
    onFecharVincularLoja,
    onUsuarioVinculadoLoja,
    paginaAtual,
    perfisApp,
    pessoaVinculadaCredenciais,
    recriarSenha,
    roles,
    rolesUsuariosDiretos,
    salvarCredenciais,
    salvarPerfisApp,
    savingCredentials,
    savingLiberacaoId,
    savingPerfisApp,
    searchTerm,
    setCredenciais,
    setFiltroPerfil,
    setFiltroStatus,
    setInitialAccessCredentials,
    setItensPorPagina,
    setNovoUsuario,
    setPaginaAtual,
    setSearchTerm,
    showModal,
    tenantLoginReference,
    toggleStatus,
    totalPaginas,
    totalUsuariosFiltrados,
    usuarioCredenciais,
    usuarioServerErrors,
    usuarios,
    vincularLojaUsuario,
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
        subtitle="Gerencie usuários, perfis e autorizações individuais desta loja."
        actions={
          <BotaoInteracao icon={Plus} onClick={onAbrirModalUsuario}>
            Novo usuario
          </BotaoInteracao>
        }
      />

      <UsuarioLojaLoginCard tenantReference={tenantLoginReference} />

      <Panel padding="md">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          <div className="md:col-span-2 lg:col-span-1">
            <InputTexto
              id="usuarios-busca"
              label="Buscar"
              value={searchTerm}
              onChange={setSearchTerm}
              placeholder="Buscar por nome, celular, usuário ou e-mail..."
            />
          </div>
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
        onDelete={excluirUsuario}
        onForcarLogout={forcarLogout}
        onManageCredentials={onAbrirCredenciais}
        onRecriarSenha={recriarSenha}
        onToggleCrediario={alterarLiberacaoCrediario}
        onToggleStatus={toggleStatus}
        onVincularLoja={onAbrirVincularLoja}
        paginacaoRodape={paginacao("bottom")}
        savingLiberacaoId={savingLiberacaoId}
        usuarios={usuarios}
      />

      <UsuarioModal
        limparErroServidor={limparErroServidor}
        novoUsuario={novoUsuario}
        onClose={onCloseModalUsuario}
        onSubmit={criarUsuario}
        roles={rolesUsuariosDiretos}
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
        onSalvarPerfisApp={salvarPerfisApp}
        onSubmit={salvarCredenciais}
        perfisApp={perfisApp}
        pessoaVinculada={pessoaVinculadaCredenciais}
        roles={rolesUsuariosDiretos}
        savingPerfisApp={savingPerfisApp}
        tenantReference={tenantLoginReference}
        usuario={usuarioCredenciais}
      />

      {vincularLojaUsuario ? (
        <UsuarioVincularLojaModal
          usuario={vincularLojaUsuario}
          onClose={onFecharVincularLoja}
          onAlterado={onUsuarioVinculadoLoja}
        />
      ) : null}

      <UsuarioAcessoInicialModal
        credentials={initialAccessCredentials}
        onClose={() => setInitialAccessCredentials(null)}
      />
    </div>
  );
}
