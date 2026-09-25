import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";
import { confirmarCorePet } from "../services/corepetDialog";
import { resolveTenantLoginReference } from "../utils/usuarioAcessoInicial";
import { isBrazilianMobileLogin, normalizeBrazilianLoginPhone } from "../utils/loginPhone";

const USUARIO_INICIAL = {
  nome: "",
  login_phone: "",
  celular_whatsapp: false,
  email: "",
  password: "",
  role_id: null,
  pessoa_id: null,
  app_access_profiles: [],
  tipo_pessoa: "PF",
};

const CREDENCIAIS_INICIAIS = { login_phone: "", new_password: "", role_id: "" };

function detalhesValidacaoParaMensagem(details) {
  const validationDetails = Array.isArray(details) ? details : [];

  if (
    validationDetails.some((item) =>
      [...(item.loc || []), item.msg || "", item.type || ""]
        .join(" ")
        .toLowerCase()
        .includes("email"),
    )
  ) {
    return "E-mail invalido. Use o formato nome@dominio.com, por exemplo usuario@empresa.com.br.";
  }

  if (validationDetails.some((item) => (item.loc || []).includes("password"))) {
    return "Senha invalida. Use uma senha com no minimo 8 caracteres.";
  }

  if (validationDetails.some((item) => (item.loc || []).includes("role_id"))) {
    return "Selecione um perfil de acesso para o usuario.";
  }

  const erroDeValidacaoCustomizado = validationDetails.find(
    (item) => item.type === "value_error" && typeof item.msg === "string",
  );
  if (erroDeValidacaoCustomizado) {
    return erroDeValidacaoCustomizado.msg.replace(/^Value error,\s*/i, "");
  }

  return null;
}

function mensagemErroCriacaoUsuario(error) {
  const status = error.response?.status;
  const data = error.response?.data || {};

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    const detailMessage = detalhesValidacaoParaMensagem(data.detail);
    if (detailMessage) return detailMessage;
  }

  const detailsMessage = detalhesValidacaoParaMensagem(data.details);
  if (detailsMessage) return detailsMessage;

  if (typeof data.message === "string" && data.message !== "Dados invalidos") {
    return data.message;
  }

  if (status === 422) {
    return "Dados invalidos. Revise e-mail, senha e perfil de acesso antes de tentar novamente.";
  }

  if (status === 409) {
    return "Este e-mail ja esta cadastrado. Use outro e-mail ou verifique se o usuario ja existe.";
  }

  return "Nao foi possivel criar o usuario agora. Tente novamente em instantes.";
}

function campoDoErroServidor(mensagem) {
  const texto = String(mensagem || "").toLowerCase();
  if (texto.includes("e-mail") || texto.includes("email")) return "email";
  if (texto.includes("celular")) return "login_phone";
  if (texto.includes("nome de usuario") || texto.includes("username")) return "username";
  if (texto.includes("perfil")) return "role_id";
  return null;
}

export default function useUsuariosPage() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [novoUsuario, setNovoUsuario] = useState(USUARIO_INICIAL);
  const [usuarioServerErrors, setUsuarioServerErrors] = useState({});
  const [usuarioCredenciais, setUsuarioCredenciais] = useState(null);
  const [credenciais, setCredenciais] = useState(CREDENCIAIS_INICIAIS);
  const [credenciaisError, setCredenciaisError] = useState("");
  const [generatedPassword, setGeneratedPassword] = useState("");
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [perfisApp, setPerfisApp] = useState([]);
  const [pessoaVinculadaCredenciais, setPessoaVinculadaCredenciais] = useState(null);
  const [savingPerfisApp, setSavingPerfisApp] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filtroPerfil, setFiltroPerfil] = useState([]);
  const [filtroStatus, setFiltroStatus] = useState([]);
  const [paginaAtual, setPaginaAtual] = useState(1);
  const [itensPorPagina, setItensPorPagina] = useState(20);
  const tenantLoginReference = resolveTenantLoginReference(
    user,
    typeof window === "undefined" ? null : window.localStorage.getItem("selectedTenant"),
  );

  // Busca/filtro/paginação são só de navegador — a lista de usuários de uma loja é pequena
  // (dezenas, não milhares como Pessoas), então não precisa de endpoint com skip/limit/search.
  const usuariosFiltrados = useMemo(() => {
    const termo = searchTerm.trim().toLowerCase();
    return usuarios.filter((usuario) => {
      if (termo) {
        const alvo = [usuario.nome, usuario.login_phone, usuario.username, usuario.email]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!alvo.includes(termo)) return false;
      }
      if (filtroPerfil.length > 0 && !filtroPerfil.includes(String(usuario.role_id))) {
        return false;
      }
      if (filtroStatus.length > 0) {
        const statusUsuario = usuario.is_active ? "ativo" : "inativo";
        if (!filtroStatus.includes(statusUsuario)) return false;
      }
      return true;
    });
  }, [usuarios, searchTerm, filtroPerfil, filtroStatus]);

  useEffect(() => {
    setPaginaAtual(1);
  }, [searchTerm, filtroPerfil, filtroStatus]);

  const totalUsuariosFiltrados = usuariosFiltrados.length;
  const totalPaginas = Math.max(Math.ceil(totalUsuariosFiltrados / itensPorPagina), 1);
  const paginaSegura = Math.min(paginaAtual, totalPaginas);
  const usuariosPaginados = usuariosFiltrados.slice(
    (paginaSegura - 1) * itensPorPagina,
    paginaSegura * itensPorPagina,
  );

  async function carregarUsuarios() {
    try {
      setLoading(true);
      const response = await api.get("/usuarios");
      setUsuarios(response.data);
    } catch (error) {
      console.error("Erro ao carregar usuarios:", error);
      toast.error("Nao foi possivel carregar os usuarios.");
    } finally {
      setLoading(false);
    }
  }

  async function carregarRoles() {
    try {
      const response = await api.get("/roles");
      setRoles(response.data);
    } catch (error) {
      console.error("Erro ao carregar perfis:", error);
      toast.error("Nao foi possivel carregar os perfis de acesso.");
    }
  }

  async function toggleStatus(userId, isActive) {
    const acao = isActive ? "desativar acesso" : "ativar acesso";
    if (!(await confirmarCorePet(`Confirma ${acao} deste usuario?`))) return;

    try {
      await api.patch(`/usuarios/${userId}/status`, {
        is_active: !isActive,
      });
      toast.success(isActive ? "Acesso desativado." : "Acesso ativado.");
      carregarUsuarios();
    } catch (error) {
      console.error("Erro ao alterar status:", error);
      toast.error(error.response?.data?.detail || "Nao foi possivel alterar o status do usuario.");
    }
  }

  async function forcarLogout(userId) {
    if (
      !(await confirmarCorePet(
        "Forcar logout deste usuario em todos os dispositivos? A conta continuara ativa.",
      ))
    ) {
      return;
    }

    try {
      const response = await api.post(`/usuarios/${userId}/forcar-logout`);
      toast.success(
        `Logout forcado com sucesso. Sessoes encerradas: ${response.data?.sessions_revogadas ?? 0}`,
      );
    } catch (error) {
      console.error("Erro ao forcar logout:", error);
      toast.error(error.response?.data?.detail || "Nao foi possivel forcar logout do usuario.");
    }
  }

  // Validação síncrona (formato/obrigatoriedade) fica no UsuarioModal, exibida campo a campo.
  // Esta função assume que o formulário já passou por ela e só cuida do envio.
  async function criarUsuario() {
    setUsuarioServerErrors({});
    const loginPhone = normalizeBrazilianLoginPhone(novoUsuario.login_phone);
    const email = (novoUsuario.email || "").trim().toLowerCase();

    try {
      await api.post("/usuarios", {
        ...novoUsuario,
        login_phone: loginPhone,
        email: email || null,
      });
      toast.success("Usuario criado com sucesso.");
      resetarModalUsuario();
      carregarUsuarios();
    } catch (error) {
      if ((error.response?.status || 500) >= 500) {
        console.error("Erro ao criar usuario:", error);
      }
      const mensagem = mensagemErroCriacaoUsuario(error);
      const campo = campoDoErroServidor(mensagem);
      if (campo) {
        setUsuarioServerErrors({ [campo]: mensagem });
      } else {
        toast.error(mensagem);
      }
    }
  }

  function limparErroServidor(campo) {
    setUsuarioServerErrors((atuais) => {
      if (!atuais[campo]) return atuais;
      const proximos = { ...atuais };
      delete proximos[campo];
      return proximos;
    });
  }

  function abrirCredenciais(usuario) {
    setUsuarioCredenciais(usuario);
    setCredenciais({
      login_phone: usuario.login_phone || "",
      new_password: "",
      role_id: usuario.role_id || "",
    });
    setCredenciaisError("");
    setGeneratedPassword("");
    setPerfisApp([]);
    setPessoaVinculadaCredenciais(
      usuario.pessoa_id ? { id: usuario.pessoa_id, nome: usuario.pessoa_nome } : null,
    );
    if (usuario.pessoa_id) {
      api
        .get(`/usuarios/${usuario.user_id}/perfis-app`)
        .then((response) => setPerfisApp(response.data?.profiles || []))
        .catch(() => setPerfisApp([]));
    }
  }

  function fecharCredenciais() {
    setUsuarioCredenciais(null);
    setCredenciais({ ...CREDENCIAIS_INICIAIS });
    setCredenciaisError("");
    setGeneratedPassword("");
    setPerfisApp([]);
    setPessoaVinculadaCredenciais(null);
  }

  async function salvarPerfisApp(profiles) {
    if (!usuarioCredenciais) return;
    setSavingPerfisApp(true);
    try {
      const response = await api.put(`/usuarios/${usuarioCredenciais.user_id}/perfis-app`, {
        profiles,
      });
      setPerfisApp(response.data?.profiles || []);
      toast.success("Perfis de acesso ao app atualizados.");
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "Não foi possível atualizar os perfis de acesso.",
      );
    } finally {
      setSavingPerfisApp(false);
    }
  }

  async function salvarCredenciais(event) {
    event.preventDefault();
    await atualizarCredenciais(false);
  }

  async function gerarNovaSenha() {
    await atualizarCredenciais(true);
  }

  async function atualizarCredenciais(generatePassword) {
    if (!usuarioCredenciais) return;
    const loginPhone = normalizeBrazilianLoginPhone(credenciais.login_phone);
    if (!isBrazilianMobileLogin(credenciais.login_phone)) {
      setCredenciaisError("Informe um celular valido com DDD.");
      return;
    }
    if (!generatePassword && credenciais.new_password && credenciais.new_password.length < 8) {
      setCredenciaisError("A nova senha deve ter no minimo 8 caracteres.");
      return;
    }
    if (!credenciais.role_id) {
      setCredenciaisError("Selecione um perfil de acesso para o usuario.");
      return;
    }

    setSavingCredentials(true);
    setCredenciaisError("");
    setGeneratedPassword("");
    try {
      const response = await api.patch(`/usuarios/${usuarioCredenciais.user_id}/credenciais`, {
        login_phone: loginPhone,
        new_password: generatePassword ? null : credenciais.new_password || null,
        generate_password: generatePassword,
        role_id: Number(credenciais.role_id),
      });
      setCredenciais((current) => ({ ...current, login_phone: loginPhone, new_password: "" }));
      await carregarUsuarios();
      if (response.data?.generated_password) {
        setGeneratedPassword(response.data.generated_password);
        toast.success("Nova senha gerada. Copie antes de fechar.");
      } else {
        toast.success("Acesso atualizado com sucesso.");
        fecharCredenciais();
      }
    } catch (error) {
      setCredenciaisError(
        error.response?.data?.detail || "Nao foi possivel atualizar o acesso deste usuario.",
      );
    } finally {
      setSavingCredentials(false);
    }
  }

  function abrirModalUsuario() {
    setNovoUsuario({ ...USUARIO_INICIAL });
    setUsuarioServerErrors({});
    setShowModal(true);
  }

  function resetarModalUsuario() {
    setShowModal(false);
    setNovoUsuario({ ...USUARIO_INICIAL });
    setUsuarioServerErrors({});
  }

  useEffect(() => {
    carregarUsuarios();
    carregarRoles();
  }, []);

  return {
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
    onAbrirModalUsuario: abrirModalUsuario,
    onAbrirCredenciais: abrirCredenciais,
    onCloseModalUsuario: resetarModalUsuario,
    paginaAtual: paginaSegura,
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
    usuarios: usuariosPaginados,
  };
}
