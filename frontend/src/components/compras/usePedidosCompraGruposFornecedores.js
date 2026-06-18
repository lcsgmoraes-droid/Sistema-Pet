import { useState } from "react";
import { toast } from "react-hot-toast";
import api from "../../api";

const GRUPO_FORNECEDOR_FORM_INICIAL = {
  id: null,
  nome: "",
  descricao: "",
  fornecedor_principal_id: "",
  fornecedor_ids: [],
};

export default function usePedidosCompraGruposFornecedores({ fornecedorIdAtual, carregarDados }) {
  const [mostrarModalGruposFornecedores, setMostrarModalGruposFornecedores] = useState(false);
  const [grupoFornecedorForm, setGrupoFornecedorForm] = useState(GRUPO_FORNECEDOR_FORM_INICIAL);
  const [salvandoGrupoFornecedor, setSalvandoGrupoFornecedor] = useState(false);

  const abrirNovoGrupoFornecedor = () => {
    const fornecedorId = Number(fornecedorIdAtual);
    setGrupoFornecedorForm({
      ...GRUPO_FORNECEDOR_FORM_INICIAL,
      fornecedor_principal_id:
        Number.isFinite(fornecedorId) && fornecedorId > 0 ? fornecedorId.toString() : "",
      fornecedor_ids: Number.isFinite(fornecedorId) && fornecedorId > 0 ? [fornecedorId] : [],
    });
    setMostrarModalGruposFornecedores(true);
  };

  const editarGrupoFornecedor = (grupo) => {
    setGrupoFornecedorForm({
      id: grupo.id,
      nome: grupo.nome || "",
      descricao: grupo.descricao || "",
      fornecedor_principal_id: grupo.fornecedor_principal_id?.toString() || "",
      fornecedor_ids: (grupo.fornecedor_ids || []).map((id) => Number(id)),
    });
  };

  const alternarFornecedorNoGrupoForm = (fornecedorId) => {
    const id = Number(fornecedorId);
    setGrupoFornecedorForm((prev) => {
      const idsAtuais = new Set((prev.fornecedor_ids || []).map((item) => Number(item)));
      if (idsAtuais.has(id)) {
        idsAtuais.delete(id);
      } else {
        idsAtuais.add(id);
      }

      const fornecedorIds = Array.from(idsAtuais).sort((a, b) => a - b);
      const principalAtual = Number(prev.fornecedor_principal_id);
      const fornecedorPrincipalValido = fornecedorIds.includes(principalAtual)
        ? prev.fornecedor_principal_id
        : fornecedorIds[0]?.toString() || "";

      return {
        ...prev,
        fornecedor_ids: fornecedorIds,
        fornecedor_principal_id: fornecedorPrincipalValido,
      };
    });
  };

  const salvarGrupoFornecedor = async (event) => {
    event.preventDefault();

    const fornecedorIds = (grupoFornecedorForm.fornecedor_ids || [])
      .map((id) => Number(id))
      .filter((id) => Number.isFinite(id) && id > 0);

    if (!grupoFornecedorForm.nome.trim()) {
      toast.error("Informe o nome do grupo");
      return;
    }

    if (fornecedorIds.length < 2) {
      toast.error("Selecione pelo menos 2 CNPJs para unificar em grupo");
      return;
    }

    setSalvandoGrupoFornecedor(true);
    try {
      const payload = {
        nome: grupoFornecedorForm.nome.trim(),
        descricao: grupoFornecedorForm.descricao?.trim() || null,
        fornecedor_principal_id:
          Number(grupoFornecedorForm.fornecedor_principal_id) || fornecedorIds[0],
        fornecedor_ids: fornecedorIds,
        ativo: true,
      };

      if (grupoFornecedorForm.id) {
        await api.patch(`/fornecedor-grupos/${grupoFornecedorForm.id}`, payload);
        toast.success("Grupo de fornecedor atualizado");
      } else {
        await api.post("/fornecedor-grupos/", payload);
        toast.success("Grupo de fornecedor criado");
      }

      setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL);
      await carregarDados();
    } catch (error) {
      console.error("Erro ao salvar grupo de fornecedor:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar grupo de fornecedor");
    } finally {
      setSalvandoGrupoFornecedor(false);
    }
  };

  const excluirGrupoFornecedor = async (grupo) => {
    const confirmar = window.confirm(
      `Excluir o grupo "${grupo.nome}" e liberar os fornecedores vinculados?`,
    );
    if (!confirmar) {
      return;
    }

    try {
      await api.delete(`/fornecedor-grupos/${grupo.id}`);
      toast.success("Grupo de fornecedor excluido");
      if (grupoFornecedorForm.id === grupo.id) {
        setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL);
      }
      await carregarDados();
    } catch (error) {
      console.error("Erro ao excluir grupo de fornecedor:", error);
      toast.error(error.response?.data?.detail || "Erro ao excluir grupo de fornecedor");
    }
  };

  const fecharModalGruposFornecedores = () => {
    setMostrarModalGruposFornecedores(false);
    setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL);
  };

  const iniciarNovoGrupoFornecedor = () => {
    setGrupoFornecedorForm(GRUPO_FORNECEDOR_FORM_INICIAL);
  };

  return {
    mostrarModalGruposFornecedores,
    grupoFornecedorForm,
    setGrupoFornecedorForm,
    salvandoGrupoFornecedor,
    abrirNovoGrupoFornecedor,
    editarGrupoFornecedor,
    alternarFornecedorNoGrupoForm,
    salvarGrupoFornecedor,
    excluirGrupoFornecedor,
    fecharModalGruposFornecedores,
    iniciarNovoGrupoFornecedor,
  };
}
