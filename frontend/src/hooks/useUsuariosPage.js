import { useEffect, useState } from "react";
import api from "../api";

const USUARIO_INICIAL = {
  email: "",
  password: "",
  role_id: null,
};

export default function useUsuariosPage() {
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [novoUsuario, setNovoUsuario] = useState(USUARIO_INICIAL);

  async function carregarUsuarios() {
    try {
      setLoading(true);
      const response = await api.get("/usuarios");
      setUsuarios(response.data);
    } catch (error) {
      console.error("Erro ao carregar usuários:", error);
      alert("Erro ao carregar usuários");
    } finally {
      setLoading(false);
    }
  }

  async function carregarRoles() {
    try {
      const response = await api.get("/roles");
      setRoles(response.data);
    } catch (error) {
      console.error("Erro ao carregar roles:", error);
    }
  }

  async function toggleStatus(userId, isActive) {
    const acao = isActive ? "desativar acesso" : "ativar acesso";
    if (!confirm(`Confirma ${acao} deste usuário?`)) return;

    try {
      await api.patch(`/usuarios/${userId}/status`, {
        is_active: !isActive,
      });
      carregarUsuarios();
    } catch (error) {
      console.error("Erro ao alterar status:", error);
      alert("Erro ao alterar status do usuário");
    }
  }

  async function forcarLogout(userId) {
    if (
      !confirm(
        "Forçar logout deste usuário em todos os dispositivos? A conta continuará ativa.",
      )
    ) {
      return;
    }

    try {
      const response = await api.post(`/usuarios/${userId}/forcar-logout`);
      alert(
        `Logout forçado com sucesso. Sessões encerradas: ${response.data?.sessions_revogadas ?? 0}`,
      );
    } catch (error) {
      console.error("Erro ao forçar logout:", error);
      alert(error.response?.data?.detail || "Erro ao forçar logout do usuário");
    }
  }

  async function criarUsuario(event) {
    event.preventDefault();
    try {
      await api.post("/usuarios", novoUsuario);
      alert("Usuário criado com sucesso!");
      resetarModalUsuario();
      carregarUsuarios();
    } catch (error) {
      console.error("Erro ao criar usuário:", error);
      alert(error.response?.data?.detail || "Erro ao criar usuário");
    }
  }

  function abrirModalUsuario() {
    setNovoUsuario(USUARIO_INICIAL);
    setShowPassword(false);
    setShowModal(true);
  }

  function resetarModalUsuario() {
    setShowModal(false);
    setNovoUsuario(USUARIO_INICIAL);
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
    usuarios,
  };
}
