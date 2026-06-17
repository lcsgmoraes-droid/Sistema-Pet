import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../api";

const EMPTY_ROLE = {
  nome: "",
  permissions: [],
};

const CATEGORY_LABELS = {
  cadastros: "Cadastros",
  clientes: "Clientes",
  compras: "Compras",
  configuracoes: "Configuracoes",
  entregas: "Entregas",
  estoque: "Estoque",
  financeiro: "Financeiro",
  ia: "Inteligencia Artificial",
  produtos: "Produtos",
  relatorios: "Relatorios",
  rh: "Recursos Humanos",
  usuarios: "Usuarios",
  vendas: "Vendas",
};

function cloneEmptyRole() {
  return {
    ...EMPTY_ROLE,
    permissions: [],
  };
}

function getCategory(permissionName = "") {
  return permissionName.includes(".") ? permissionName.split(".")[0] : "outras";
}

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  const status = error?.response?.status;
  const detailText = typeof detail === "string" ? detail : "";

  if (status === 400 && detailText.toLowerCase().includes("existe")) {
    return "Este perfil ja existe neste tenant. Use outro nome ou edite o perfil existente.";
  }

  if (status === 400 && detailText.toLowerCase().includes("uso")) {
    return "Este perfil esta em uso por um usuario. Troque o perfil dos usuarios antes de excluir.";
  }

  if (status === 403) {
    return "Seu usuario nao tem permissao para gerenciar perfis.";
  }

  return detailText || fallback;
}

export default function useRolesPage() {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [expandedCategories, setExpandedCategories] = useState({});
  const [roleForm, setRoleForm] = useState(cloneEmptyRole);
  const [roleFormError, setRoleFormError] = useState("");

  const carregarDados = useCallback(async () => {
    setLoading(true);
    try {
      const [rolesRes, permsRes] = await Promise.all([api.get("/roles"), api.get("/permissions")]);
      setRoles(Array.isArray(rolesRes.data) ? rolesRes.data : []);
      setPermissions(Array.isArray(permsRes.data) ? permsRes.data : []);
    } catch (error) {
      if (!error?.response || error.response.status >= 500) {
        console.error("Erro ao carregar perfis:", error);
      }
      toast.error(getErrorMessage(error, "Nao foi possivel carregar os perfis."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const permissionGroups = useMemo(() => {
    const groups = permissions.reduce((acc, permission) => {
      const category = getCategory(permission.nome);
      if (!acc[category]) {
        acc[category] = {
          key: category,
          label: CATEGORY_LABELS[category] || category,
          permissions: [],
        };
      }
      acc[category].permissions.push(permission);
      return acc;
    }, {});

    return Object.values(groups)
      .map((group) => ({
        ...group,
        permissions: [...group.permissions].sort((a, b) =>
          String(a.nome).localeCompare(String(b.nome), "pt-BR"),
        ),
      }))
      .sort((a, b) => a.label.localeCompare(b.label, "pt-BR"));
  }, [permissions]);

  const abrirCriacao = useCallback(() => {
    setEditingRole(null);
    setRoleForm(cloneEmptyRole());
    setRoleFormError("");
    setShowModal(true);
  }, []);

  const abrirEdicao = useCallback((role) => {
    setEditingRole(role);
    setRoleForm({
      nome: role.nome || "",
      permissions: (role.permissions || []).map((permission) => permission.permission_id),
    });
    setRoleFormError("");
    setShowModal(true);
  }, []);

  const fecharModal = useCallback(() => {
    if (saving) return;
    setShowModal(false);
    setEditingRole(null);
    setRoleForm(cloneEmptyRole());
    setRoleFormError("");
  }, [saving]);

  const setNome = useCallback((nome) => {
    setRoleForm((current) => ({ ...current, nome }));
    setRoleFormError("");
  }, []);

  const togglePermission = useCallback((permissionId) => {
    setRoleForm((current) => {
      const selected = current.permissions.includes(permissionId);
      return {
        ...current,
        permissions: selected
          ? current.permissions.filter((id) => id !== permissionId)
          : [...current.permissions, permissionId],
      };
    });
  }, []);

  const toggleCategory = useCallback((permissionIds) => {
    setRoleForm((current) => {
      const allSelected = permissionIds.every((id) => current.permissions.includes(id));
      return {
        ...current,
        permissions: allSelected
          ? current.permissions.filter((id) => !permissionIds.includes(id))
          : [...new Set([...current.permissions, ...permissionIds])],
      };
    });
  }, []);

  const toggleExpandedCategory = useCallback((category) => {
    setExpandedCategories((current) => ({
      ...current,
      [category]: !current[category],
    }));
  }, []);

  const salvarRole = useCallback(
    async (event) => {
      event.preventDefault();
      const nome = roleForm.nome.trim();
      if (!nome) {
        setRoleFormError("Informe um nome para o perfil.");
        return;
      }

      setSaving(true);
      setRoleFormError("");
      const payload = {
        nome,
        permissions: roleForm.permissions,
      };

      try {
        if (editingRole) {
          await api.put(`/roles/${editingRole.role_id}`, payload);
          toast.success("Perfil atualizado com sucesso.");
        } else {
          await api.post("/roles", payload);
          toast.success("Perfil criado com sucesso.");
        }

        setShowModal(false);
        setEditingRole(null);
        setRoleForm(cloneEmptyRole());
        await carregarDados();
      } catch (error) {
        if (!error?.response || error.response.status >= 500) {
          console.error("Erro ao salvar perfil:", error);
        }
        setRoleFormError(getErrorMessage(error, "Nao foi possivel salvar o perfil."));
      } finally {
        setSaving(false);
      }
    },
    [carregarDados, editingRole, roleForm],
  );

  const deletarRole = useCallback(
    async (roleId) => {
      if (!window.confirm("Excluir este perfil de acesso?")) return;

      try {
        await api.delete(`/roles/${roleId}`);
        toast.success("Perfil excluido com sucesso.");
        await carregarDados();
      } catch (error) {
        if (!error?.response || error.response.status >= 500) {
          console.error("Erro ao excluir perfil:", error);
        }
        toast.error(getErrorMessage(error, "Nao foi possivel excluir o perfil."));
      }
    },
    [carregarDados],
  );

  return {
    abrirCriacao,
    abrirEdicao,
    deletarRole,
    editingRole,
    expandedCategories,
    fecharModal,
    loading,
    permissionGroups,
    permissions,
    roleForm,
    roleFormError,
    roles,
    salvarRole,
    saving,
    setNome,
    showModal,
    toggleCategory,
    toggleExpandedCategory,
    togglePermission,
  };
}
