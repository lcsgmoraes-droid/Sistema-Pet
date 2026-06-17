import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";

const USUARIO_INICIAL = {
  email: "",
  password: "",
  role_id: null,
};

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
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [novoUsuario, setNovoUsuario] = useState(USUARIO_INICIAL);
  const [usuarioFormError, setUsuarioFormError] = useState("");

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
    if (!confirm(`Confirma ${acao} deste usuario?`)) return;

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
      !confirm("Forcar logout deste usuario em todos os dispositivos? A conta continuara ativa.")
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

    const email = (novoUsuario.email || "").trim().toLowerCase();
    if (!emailPareceValido(email)) {
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
        email,
      });
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
    forcarLogout,
    loading,
    novoUsuario,
    onAbrirModalUsuario: abrirModalUsuario,
    onCloseModalUsuario: resetarModalUsuario,
    roles,
    setNovoUsuario,
    setShowPassword,
    showModal,
    showPassword,
    toggleStatus,
    usuarioFormError,
    usuarios,
  };
}
