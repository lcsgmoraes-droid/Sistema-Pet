import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";
import { useAuth } from "../contexts/AuthContext";
import { confirmarCorePet } from "../services/corepetDialog";
import {
  buildInitialAccessCredentials,
  resolveTenantLoginReference,
} from "../utils/usuarioAcessoInicial";

const USUARIO_INICIAL = {
  nome: "",
  username: "",
  email: "",
  password: "",
  role_id: null,
};

const CREDENCIAIS_INICIAIS = { username: "", new_password: "", role_id: "" };

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

function emailPareceValido(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function useUsuariosPage() {
  const { user } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [novoUsuario, setNovoUsuario] = useState(USUARIO_INICIAL);
  const [usuarioFormError, setUsuarioFormError] = useState("");
  const [usuarioCredenciais, setUsuarioCredenciais] = useState(null);
  const [credenciais, setCredenciais] = useState(CREDENCIAIS_INICIAIS);
  const [credenciaisError, setCredenciaisError] = useState("");
  const [generatedPassword, setGeneratedPassword] = useState("");
  const [savingCredentials, setSavingCredentials] = useState(false);
  const [initialAccessCredentials, setInitialAccessCredentials] = useState(null);
  const tenantLoginReference = resolveTenantLoginReference(
    user,
    typeof window === "undefined" ? null : window.localStorage.getItem("selectedTenant"),
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

  async function criarUsuario(event) {
    event.preventDefault();
    setUsuarioFormError("");

    const username = (novoUsuario.username || "").trim().toLowerCase();
    const email = (novoUsuario.email || "").trim().toLowerCase();
    if (username.length < 3) {
      setUsuarioFormError("Informe um nome de usuario com pelo menos 3 caracteres.");
      return;
    }
    if (email && !emailPareceValido(email)) {
      setUsuarioFormError(
        "E-mail invalido. Use o formato nome@dominio.com, por exemplo usuario@empresa.com.br.",
      );
      return;
    }

    if ((novoUsuario.password || "").length < 8) {
      setUsuarioFormError("Senha invalida. Use uma senha com no minimo 8 caracteres.");
      return;
    }

    if (!novoUsuario.role_id) {
      setUsuarioFormError("Selecione um perfil de acesso para o usuario.");
      return;
    }

    try {
      await api.post("/usuarios", {
        ...novoUsuario,
        username,
        email: email || null,
      });
      setInitialAccessCredentials(
        buildInitialAccessCredentials({
          tenant: tenantLoginReference,
          username,
          password: novoUsuario.password,
          personName: novoUsuario.nome,
        }),
      );
      toast.success("Usuario criado com sucesso.");
      resetarModalUsuario();
      carregarUsuarios();
    } catch (error) {
      if ((error.response?.status || 500) >= 500) {
        console.error("Erro ao criar usuario:", error);
      }
      setUsuarioFormError(mensagemErroCriacaoUsuario(error));
    }
  }

  function abrirCredenciais(usuario) {
    setUsuarioCredenciais(usuario);
    setCredenciais({
      username: usuario.username || "",
      new_password: "",
      role_id: usuario.role_id || "",
    });
    setCredenciaisError("");
    setGeneratedPassword("");
  }

  function fecharCredenciais() {
    setUsuarioCredenciais(null);
    setCredenciais({ ...CREDENCIAIS_INICIAIS });
    setCredenciaisError("");
    setGeneratedPassword("");
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
    const username = (credenciais.username || "").trim().toLowerCase();
    if (username.length < 3) {
      setCredenciaisError("Informe um nome de usuario com pelo menos 3 caracteres.");
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
        username,
        new_password: generatePassword ? null : credenciais.new_password || null,
        generate_password: generatePassword,
        role_id: Number(credenciais.role_id),
      });
      setCredenciais((current) => ({ ...current, username, new_password: "" }));
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
    setUsuarioFormError("");
    setShowPassword(false);
    setShowModal(true);
  }

  function resetarModalUsuario() {
    setShowModal(false);
    setNovoUsuario({ ...USUARIO_INICIAL });
    setUsuarioFormError("");
    setShowPassword(false);
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
    forcarLogout,
    generatedPassword,
    gerarNovaSenha,
    initialAccessCredentials,
    loading,
    novoUsuario,
    onAbrirModalUsuario: abrirModalUsuario,
    onAbrirCredenciais: abrirCredenciais,
    onCloseModalUsuario: resetarModalUsuario,
    roles,
    setNovoUsuario,
    setCredenciais,
    setShowPassword,
    showModal,
    showPassword,
    salvarCredenciais,
    savingCredentials,
    setInitialAccessCredentials,
    tenantLoginReference,
    toggleStatus,
    usuarioFormError,
    usuarioCredenciais,
    usuarios,
  };
}
