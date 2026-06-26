import { toast } from "react-hot-toast";
import api from "../../api.js";
import { buildCategoriaPayload, buildSubcategoriaDREPayload } from "./categoriasFinanceirasUtils";

export function createCategoriasFinanceirasPersistence({
  carregarDados,
  categorias,
  editando,
  editandoSub,
  formData,
  formSubData,
  getSubcategoriasDREDaCategoria,
  resetForm,
  resetSubForm,
  resolverCategoriaDREId,
  setShowModal,
  setShowSubModal,
}) {
  async function handleSubmit(e) {
    e.preventDefault();

    if (!formData.nome || !formData.tipo) {
      toast.error("Preencha nome e tipo");
      return;
    }

    try {
      let categoriaId;
      if (editando) {
        categoriaId = await atualizarCategoria();
      } else {
        categoriaId = await criarCategoria();
      }

      setShowModal(false);
      resetForm();
      carregarDados();
      return categoriaId;
    } catch (error) {
      console.error("Erro ao salvar:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar categoria");
      return null;
    }
  }

  async function atualizarCategoria() {
    await api.put(`/categorias-financeiras/${editando}`, buildCategoriaPayload(formData));
    const categoriaId = editando;
    await excluirSubcategoriasRemovidas(categoriaId);
    await criarNovasSubcategoriasEditadas(categoriaId);
    toast.success("Categoria atualizada com sucesso!");
    return categoriaId;
  }

  async function excluirSubcategoriasRemovidas(categoriaId) {
    const idsAtuais = new Set(
      formData.novasSubcategorias.filter((subcategoria) => subcategoria.id).map((sub) => sub.id),
    );
    const categoriaAtualParaDelete = categorias.find((categoria) => categoria.id === categoriaId);
    const subsOriginais = getSubcategoriasDREDaCategoria(categoriaAtualParaDelete);
    const subsRemovidas = subsOriginais.filter((subcategoria) => !idsAtuais.has(subcategoria.id));

    for (const subcategoria of subsRemovidas) {
      try {
        await api.delete(`/dre/subcategorias/${subcategoria.id}`);
      } catch (delError) {
        console.error("Erro ao excluir subcategoria:", delError);
        toast.error(`Erro ao excluir subcategoria: ${subcategoria.nome}`);
      }
    }
  }

  async function criarNovasSubcategoriasEditadas(categoriaId) {
    const novasSubs = formData.novasSubcategorias.filter((subcategoria) => {
      return !subcategoria.id && subcategoria.nome?.trim();
    });
    if (novasSubs.length === 0) return;

    const categoriaDREId = resolverCategoriaDREId(categoriaId);
    if (!categoriaDREId) {
      toast.error("Categoria DRE nÃ£o encontrada para vincular subcategoria");
      return;
    }

    let primeiraSubDREIdEdit = null;
    for (const subcategoria of novasSubs) {
      const subId = await criarSubcategoriaDRE({
        categoriaDREId,
        categoriaFinanceiraId: categoriaId,
        nome: subcategoria.nome,
      });
      if (!primeiraSubDREIdEdit && subId) {
        primeiraSubDREIdEdit = subId;
      }
    }

    const categoriaAtual = categorias.find((categoria) => categoria.id === editando);
    if (!categoriaAtual?.dre_subcategoria_id && primeiraSubDREIdEdit) {
      await api.put(`/categorias-financeiras/${editando}`, {
        dre_subcategoria_id: primeiraSubDREIdEdit,
      });
    }

    toast.success(`${novasSubs.length} subcategoria(s) criada(s)!`);
  }

  async function criarCategoria() {
    const response = await api.post("/categorias-financeiras", buildCategoriaPayload(formData));
    const categoriaId = response.data.id;
    toast.success("Categoria criada com sucesso!");

    const primeiraSubDREId = await criarSubcategoriasNovaCategoria(categoriaId);
    if (primeiraSubDREId) {
      try {
        await api.put(`/categorias-financeiras/${categoriaId}`, {
          dre_subcategoria_id: primeiraSubDREId,
        });
      } catch (vinculoError) {
        console.error("Erro ao vincular categoria com DRE:", vinculoError);
      }
    }

    return categoriaId;
  }

  async function criarSubcategoriasNovaCategoria(categoriaId) {
    if (formData.novasSubcategorias.length === 0) return null;

    const subsValidas = formData.novasSubcategorias.filter((subcategoria) => {
      return subcategoria.nome.trim();
    });
    const categoriaDREId = resolverCategoriaDREId(categoriaId);
    if (!categoriaDREId) {
      toast.error("Categoria DRE nÃ£o encontrada para vincular subcategoria");
    }

    let primeiraSubDREId = null;
    for (const subcategoria of subsValidas) {
      if (!categoriaDREId) continue;
      const subId = await criarSubcategoriaDRE({
        categoriaDREId,
        categoriaFinanceiraId: categoriaId,
        nome: subcategoria.nome,
      });
      if (!primeiraSubDREId && subId) {
        primeiraSubDREId = subId;
      }
    }

    if (subsValidas.length > 0) {
      toast.success(`${subsValidas.length} subcategoria(s) criada(s)!`);
    }
    return primeiraSubDREId;
  }

  async function criarSubcategoriaDRE({ categoriaDREId, categoriaFinanceiraId, nome }) {
    try {
      const subResp = await api.post(
        "/dre/subcategorias",
        buildSubcategoriaDREPayload({ categoriaDREId, nome, categoriaFinanceiraId }),
      );
      return subResp?.data?.id || null;
    } catch (subError) {
      console.error("Erro ao criar subcategoria:", subError);
      toast.error(`Erro ao criar subcategoria: ${nome}`);
      return null;
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Deseja realmente excluir esta categoria?")) return;

    try {
      await api.delete(`/categorias-financeiras/${id}`);
      toast.success("Categoria excluÃ­da com sucesso!");
      carregarDados();
    } catch (error) {
      console.error("Erro ao excluir:", error);
      toast.error(error.response?.data?.detail || "Erro ao excluir categoria");
    }
  }

  async function handleQuickTipoCusto(id, novoTipoCusto) {
    try {
      await api.put(`/categorias-financeiras/${id}`, { tipo_custo: novoTipoCusto });
      carregarDados();
    } catch {
      toast.error("Erro ao classificar categoria");
    }
  }

  async function handleQuickCustoPeDRE(subId, novoValor) {
    try {
      await api.put(`/dre/subcategorias/${subId}`, { custo_pe: novoValor });
      carregarDados();
    } catch {
      toast.error("Erro ao classificar subcategoria");
    }
  }

  async function handleSubmitSub(e) {
    e.preventDefault();

    if (!formSubData.categoria_id || !formSubData.nome) {
      toast.error("Preencha categoria e nome");
      return;
    }

    try {
      if (editandoSub) {
        await api.put(`/dre/subcategorias/${editandoSub}`, {
          nome: formSubData.nome,
          ativo: formSubData.ativo,
        });
        toast.success("Subcategoria atualizada!");
      } else {
        await criarSubcategoriaSolta();
      }

      setShowSubModal(false);
      resetSubForm();
      carregarDados();
    } catch (error) {
      console.error("Erro ao salvar:", error);
      toast.error(error.response?.data?.detail || "Erro ao salvar subcategoria");
    }
  }

  async function criarSubcategoriaSolta() {
    const categoriaDREId = resolverCategoriaDREId(formSubData.categoria_id);
    if (!categoriaDREId) {
      toast.error("Categoria DRE nÃ£o encontrada para vincular subcategoria");
      return;
    }

    const subResp = await api.post(
      "/dre/subcategorias",
      buildSubcategoriaDREPayload({
        categoriaDREId,
        nome: formSubData.nome,
        categoriaFinanceiraId: formSubData.categoria_id,
      }),
    );

    const categoriaFinanceira = categorias.find(
      (categoria) => categoria.id === formSubData.categoria_id,
    );
    if (!categoriaFinanceira?.dre_subcategoria_id && subResp?.data?.id) {
      await api.put(`/categorias-financeiras/${formSubData.categoria_id}`, {
        dre_subcategoria_id: subResp.data.id,
      });
    }
    toast.success("Subcategoria criada!");
  }

  return {
    handleDelete,
    handleQuickCustoPeDRE,
    handleQuickTipoCusto,
    handleSubmit,
    handleSubmitSub,
  };
}
