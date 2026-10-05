import { toast } from "react-hot-toast";
import api from "../../api.js";
import { buildCategoriaPayload, buildSubcategoriaDREPayload } from "./categoriasFinanceirasUtils";
import { confirmarCorePet } from "../../services/corepetDialog";
import {
  garantirCategoriaDRE,
  prevalidarSubcategoriasDRE,
} from "../../utils/dreCategoriaFinanceira";

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
    const categoriaOriginal = categorias.find((categoria) => categoria.id === editando);
    if (categoriaOriginal && formData.tipo !== categoriaOriginal.tipo) {
      toast.error("O tipo da categoria não pode ser alterado após a criação.");
      return;
    }

    let categoriaId;
    try {
      await prevalidarSubcategoriasDRE(api, {
        nomeCategoria: formData.nome,
        tipoCategoria: formData.tipo,
        categoriaFinanceiraId: editando,
        categoriaDREId: editando ? resolverCategoriaDREId(editando) : null,
        subcategorias: formData.novasSubcategorias,
      });

      if (editando) {
        categoriaId = await atualizarCategoria();
      } else {
        categoriaId = await criarCategoria();
        const primeiraSubDREId = await criarSubcategoriasNovaCategoria(categoriaId);
        if (primeiraSubDREId) {
          await api.put(`/categorias-financeiras/${categoriaId}`, {
            dre_subcategoria_id: primeiraSubDREId,
          });
        }
      }

      toast.success(
        editando ? "Categoria atualizada com sucesso!" : "Categoria criada com sucesso!",
      );
      setShowModal(false);
      resetForm();
      carregarDados();
      return categoriaId;
    } catch (error) {
      console.error("Erro ao salvar:", error);
      toast.error(
        categoriaId && !editando
          ? "Categoria criada, mas houve erro nas subcategorias. Reabra a categoria para concluir."
          : error.response?.data?.detail || error.message || "Erro ao salvar categoria",
      );
      if (categoriaId) carregarDados();
      return null;
    }
  }

  async function atualizarCategoria() {
    await api.put(`/categorias-financeiras/${editando}`, buildCategoriaPayload(formData));
    const categoriaId = editando;
    const primeiraNovaSubId = await criarNovasSubcategoriasEditadas(categoriaId);
    await atualizarSubcategoriasExistentes(categoriaId);
    await excluirSubcategoriasRemovidas(categoriaId, primeiraNovaSubId);
    return categoriaId;
  }

  async function atualizarSubcategoriasExistentes(categoriaId) {
    const originais = getSubcategoriasDREDaCategoria(
      categorias.find((categoria) => categoria.id === categoriaId),
    );
    for (const subcategoria of formData.novasSubcategorias) {
      if (!subcategoria.id) continue;
      const original = originais.find((item) => item.id === subcategoria.id);
      if (
        original?.categoria_financeira_id === categoriaId &&
        subcategoria.nome?.trim() &&
        subcategoria.nome.trim() !== original.nome
      ) {
        await api.put(`/dre/subcategorias/${subcategoria.id}`, {
          nome: subcategoria.nome.trim(),
        });
      }
    }
  }

  async function excluirSubcategoriasRemovidas(categoriaId, primeiraNovaSubId = null) {
    const idsAtuais = new Set(
      formData.novasSubcategorias.filter((subcategoria) => subcategoria.id).map((sub) => sub.id),
    );
    const categoriaAtualParaDelete = categorias.find((categoria) => categoria.id === categoriaId);
    const subsOriginais = getSubcategoriasDREDaCategoria(categoriaAtualParaDelete);
    if (
      categoriaAtualParaDelete?.dre_subcategoria_id &&
      !idsAtuais.has(categoriaAtualParaDelete.dre_subcategoria_id)
    ) {
      await api.put(`/categorias-financeiras/${categoriaId}`, {
        dre_subcategoria_id: [...idsAtuais][0] || primeiraNovaSubId || null,
      });
    }
    const subsRemovidas = subsOriginais.filter(
      (subcategoria) =>
        subcategoria.categoria_financeira_id === categoriaId && !idsAtuais.has(subcategoria.id),
    );

    for (const subcategoria of subsRemovidas) {
      await api.delete(`/dre/subcategorias/${subcategoria.id}`);
    }
  }

  async function criarNovasSubcategoriasEditadas(categoriaId) {
    const novasSubs = formData.novasSubcategorias.filter((subcategoria) => {
      return !subcategoria.id && subcategoria.nome?.trim();
    });
    if (novasSubs.length === 0) return null;

    const categoriaAtual = categorias.find((categoria) => categoria.id === categoriaId);
    const categoriaDREId =
      resolverCategoriaDREId(categoriaId) ||
      (await garantirCategoriaDRE(api, {
        nome: formData.nome,
        tipo: formData.tipo,
      }));

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

    if (!categoriaAtual?.dre_subcategoria_id && primeiraSubDREIdEdit) {
      await api.put(`/categorias-financeiras/${editando}`, {
        dre_subcategoria_id: primeiraSubDREIdEdit,
      });
    }
    return primeiraSubDREIdEdit;
  }

  async function criarCategoria() {
    const response = await api.post("/categorias-financeiras", buildCategoriaPayload(formData));
    return response.data.id;
  }

  async function criarSubcategoriasNovaCategoria(categoriaId) {
    if (formData.novasSubcategorias.length === 0) return null;

    const subsValidas = formData.novasSubcategorias.filter((subcategoria) => {
      return subcategoria.nome.trim();
    });
    if (subsValidas.length === 0) return null;
    const categoriaDREId = await garantirCategoriaDRE(api, {
      nome: formData.nome,
      tipo: formData.tipo,
    });

    let primeiraSubDREId = null;
    for (const subcategoria of subsValidas) {
      const subId = await criarSubcategoriaDRE({
        categoriaDREId,
        categoriaFinanceiraId: categoriaId,
        nome: subcategoria.nome,
      });
      if (!primeiraSubDREId && subId) {
        primeiraSubDREId = subId;
      }
    }

    return primeiraSubDREId;
  }

  async function criarSubcategoriaDRE({ categoriaDREId, categoriaFinanceiraId, nome }) {
    const subResp = await api.post(
      "/dre/subcategorias",
      buildSubcategoriaDREPayload({ categoriaDREId, nome, categoriaFinanceiraId }),
    );
    return subResp?.data?.id || null;
  }

  async function handleDelete(id) {
    if (!(await confirmarCorePet("Deseja realmente excluir esta categoria?"))) return;

    try {
      await api.delete(`/categorias-financeiras/${id}`);
      toast.success("Categoria excluída com sucesso!");
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
    const categoriaFinanceira = categorias.find(
      (categoria) => categoria.id === formSubData.categoria_id,
    );
    const categoriaDREId =
      resolverCategoriaDREId(formSubData.categoria_id) ||
      (await garantirCategoriaDRE(api, {
        nome: categoriaFinanceira.nome,
        tipo: categoriaFinanceira.tipo,
      }));

    const subResp = await api.post(
      "/dre/subcategorias",
      buildSubcategoriaDREPayload({
        categoriaDREId,
        nome: formSubData.nome,
        categoriaFinanceiraId: formSubData.categoria_id,
      }),
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
