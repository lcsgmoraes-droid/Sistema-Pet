import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import api from "../../api.js";
import {
  CATEGORY_COLORS,
  CATEGORY_ICONS,
  DEFAULT_CATEGORIA_FORM,
  DEFAULT_SUBCATEGORIA_FORM,
} from "./categoriasFinanceirasConstants";
import { createCategoriasFinanceirasPersistence } from "./categoriasFinanceirasPersistence";
import {
  buildSubcategoriasExistentes,
  countCategoriasByTipo,
  filterCategoriasRaiz,
  getSubcategoriasDREDaCategoria as selectSubcategoriasDRE,
  normalizeDisplayText,
  normalizeIcon,
  resolverCategoriaDREId as resolveCategoriaDREId,
} from "./categoriasFinanceirasUtils";

function createCategoriaForm() {
  return {
    ...DEFAULT_CATEGORIA_FORM,
    novasSubcategorias: [],
  };
}

function createSubcategoriaForm() {
  return { ...DEFAULT_SUBCATEGORIA_FORM };
}

export function useCategoriasFinanceirasController() {
  const [categorias, setCategorias] = useState([]);
  const [subcategoriasDRE, setSubcategoriasDRE] = useState([]);
  const [dreCategorias, setDreCategorias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showSubModal, setShowSubModal] = useState(false);
  const [editando, setEditando] = useState(null);
  const [editandoSub, setEditandoSub] = useState(null);
  const [categoriaExpandida, setCategoriaExpandida] = useState(new Set());
  const [filtroTipo, setFiltroTipo] = useState("todos");
  const [formData, setFormData] = useState(createCategoriaForm);
  const [formSubData, setFormSubData] = useState(createSubcategoriaForm);

  async function carregarDados() {
    setLoading(true);
    try {
      await Promise.all([
        carregarCategorias(),
        carregarSubcategoriasDRE(),
        carregarCategoriasDRE(),
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function carregarCategoriasDRE() {
    try {
      const response = await api.get("/dre/categorias");
      setDreCategorias(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error("Erro ao carregar categorias DRE:", error);
      setDreCategorias([]);
    }
  }

  async function carregarCategorias() {
    try {
      const response = await api.get("/categorias-financeiras");
      setCategorias(response.data);
    } catch (error) {
      console.error("Erro ao carregar categorias:", error);
      toast.error(error.response?.data?.detail || "Erro ao carregar categorias financeiras");
    }
  }

  async function carregarSubcategoriasDRE() {
    try {
      const response = await api.get("/dre/subcategorias");
      setSubcategoriasDRE(response.data);
    } catch (error) {
      console.error("Erro ao carregar subcategorias DRE:", error);
      setSubcategoriasDRE([]);
    }
  }

  useEffect(() => {
    carregarDados();
  }, []);

  function getSubcategoriasDREDaCategoria(categoria) {
    return selectSubcategoriasDRE(categoria, subcategoriasDRE);
  }

  function resolverCategoriaDREId(categoriaFinanceiraId) {
    return resolveCategoriaDREId({
      categoriaFinanceiraId,
      categorias,
      subcategoriasDRE,
      dreCategorias,
    });
  }

  function toggleExpansao(categoriaId) {
    const novasExpandidas = new Set(categoriaExpandida);
    if (novasExpandidas.has(categoriaId)) {
      novasExpandidas.delete(categoriaId);
    } else {
      novasExpandidas.add(categoriaId);
    }
    setCategoriaExpandida(novasExpandidas);
  }

  function handleEdit(categoria) {
    const subsExistentes = buildSubcategoriasExistentes(
      getSubcategoriasDREDaCategoria(categoria),
      categoria.id,
    );
    setFormData({
      nome: normalizeDisplayText(categoria.nome),
      tipo: categoria.tipo,
      cor: categoria.cor || "#6366f1",
      icone: normalizeIcon(categoria.icone),
      descricao: normalizeDisplayText(categoria.descricao || ""),
      ativo: categoria.ativo,
      tipo_custo: categoria.tipo_custo || null,
      novasSubcategorias: subsExistentes,
    });
    setEditando(categoria.id);
    setShowModal(true);
  }

  function resetForm() {
    setFormData(createCategoriaForm());
    setEditando(null);
  }

  function adicionarSubcategoriaNova(nome = "") {
    setFormData((atual) => ({
      ...atual,
      novasSubcategorias: [...atual.novasSubcategorias, { nome, descricao: "", ativo: true }],
    }));
  }

  function atualizarSubcategoriaNova(index, field, value) {
    setFormData((atual) => ({
      ...atual,
      novasSubcategorias: atual.novasSubcategorias.map((subcategoria, subIndex) =>
        subIndex === index ? { ...subcategoria, [field]: value } : subcategoria,
      ),
    }));
  }

  function removerSubcategoriaNova(index) {
    setFormData((atual) => ({
      ...atual,
      novasSubcategorias: atual.novasSubcategorias.filter((_, subIndex) => subIndex !== index),
    }));
  }

  function handleKeyDownSubcategoria(e, index) {
    if (e.key === "Tab" && !e.shiftKey && index === formData.novasSubcategorias.length - 1) {
      e.preventDefault();
      adicionarSubcategoriaNova();
    }
  }

  function resetSubForm() {
    setFormSubData(createSubcategoriaForm());
    setEditandoSub(null);
  }

  function openCategoriaModal() {
    resetForm();
    setShowModal(true);
  }

  function closeCategoriaModal() {
    setShowModal(false);
    resetForm();
  }

  function closeSubcategoriaModal() {
    setShowSubModal(false);
    resetSubForm();
  }

  const persistence = createCategoriasFinanceirasPersistence({
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
  });

  return {
    categorias,
    categoriasFiltradas: filterCategoriasRaiz(categorias, filtroTipo),
    categoriaExpandida,
    colors: CATEGORY_COLORS,
    countDespesas: countCategoriasByTipo(categorias, "despesa"),
    countReceitas: countCategoriasByTipo(categorias, "receita"),
    editando,
    editandoSub,
    filtroTipo,
    formData,
    formSubData,
    getSubcategoriasDREDaCategoria,
    handleDelete: persistence.handleDelete,
    handleEdit,
    handleKeyDownSubcategoria,
    handleQuickCustoPeDRE: persistence.handleQuickCustoPeDRE,
    handleQuickTipoCusto: persistence.handleQuickTipoCusto,
    handleSubmit: persistence.handleSubmit,
    handleSubmitSub: persistence.handleSubmitSub,
    icons: CATEGORY_ICONS,
    loading,
    showModal,
    showSubModal,
    adicionarSubcategoriaNova,
    atualizarSubcategoriaNova,
    closeCategoriaModal,
    closeSubcategoriaModal,
    openCategoriaModal,
    removerSubcategoriaNova,
    resetForm,
    resetSubForm,
    setFiltroTipo,
    setFormData,
    setFormSubData,
    toggleExpansao,
  };
}
