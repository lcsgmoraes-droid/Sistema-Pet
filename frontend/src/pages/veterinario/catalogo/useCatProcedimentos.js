import { useEffect, useMemo, useState } from "react";
import { vetApi } from "../vetApi";
import { parseNumero } from "./shared";
import {
  buildProcedimentoPayload,
  FORM_PROCEDIMENTO_INICIAL,
  mapProcedimentoParaForm,
} from "./procedimentosForm";

export function useCatProcedimentos() {
  const [lista, setLista] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(FORM_PROCEDIMENTO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [removendoId, setRemovendoId] = useState(null);
  const [erro, setErro] = useState("");

  async function carregar() {
    setCarregando(true);
    setErro("");
    try {
      const [procedimentosResponse, produtosResponse] = await Promise.all([
        vetApi.listarCatalogoProcedimentos(),
        vetApi.listarProdutosEstoque(),
      ]);
      setLista(
        Array.isArray(procedimentosResponse.data)
          ? procedimentosResponse.data
          : procedimentosResponse.data?.items ?? []
      );
      setProdutos(Array.isArray(produtosResponse.data) ? produtosResponse.data : produtosResponse.data?.items ?? []);
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao carregar procedimentos.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  function setCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function abrirNovo() {
    setEditando(null);
    setForm(FORM_PROCEDIMENTO_INICIAL);
    setModalAberto(true);
    setErro("");
  }

  function abrirEdicao(item) {
    setEditando(item);
    setForm(mapProcedimentoParaForm(item));
    setModalAberto(true);
    setErro("");
  }

  function fecharModal() {
    setModalAberto(false);
  }

  function atualizarInsumo(index, campo, valor) {
    setForm((prev) => {
      const insumos = [...prev.insumos];
      insumos[index] = { ...insumos[index], [campo]: valor };
      return { ...prev, insumos };
    });
  }

  function adicionarInsumo() {
    setForm((prev) => ({
      ...prev,
      insumos: [...prev.insumos, { produto_id: "", quantidade: "1", baixar_estoque: true }],
    }));
  }

  function removerInsumo(index) {
    setForm((prev) => ({
      ...prev,
      insumos: prev.insumos.filter((_, currentIndex) => currentIndex !== index),
    }));
  }

  const resumoMargem = useMemo(() => {
    const custoEstimadoForm = form.insumos.reduce((total, item) => {
      const produto = produtos.find((produtoAtual) => String(produtoAtual.id) === String(item.produto_id));
      return total + Number(produto?.preco_custo || 0) * (parseNumero(item.quantidade) || 0);
    }, 0);
    const precoSugeridoForm = parseNumero(form.preco) || 0;
    const margemEstimadaForm = precoSugeridoForm - custoEstimadoForm;
    const margemPercentualForm = precoSugeridoForm > 0 ? (margemEstimadaForm / precoSugeridoForm) * 100 : 0;

    return {
      custoEstimadoForm,
      margemEstimadaForm,
      margemPercentualForm,
      precoSugeridoForm,
    };
  }, [form.insumos, form.preco, produtos]);

  async function salvar() {
    if (!form.nome.trim()) return;
    setSalvando(true);
    setErro("");
    try {
      const payload = buildProcedimentoPayload(form);

      if (editando?.id) {
        await vetApi.atualizarCatalogoProcedimento(editando.id, payload);
      } else {
        await vetApi.criarCatalogoProcedimento(payload);
      }
      setModalAberto(false);
      setEditando(null);
      setForm(FORM_PROCEDIMENTO_INICIAL);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao salvar procedimento.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item) {
    if (!window.confirm(`Deseja excluir o procedimento "${item.nome}"?`)) return;
    setRemovendoId(item.id);
    setErro("");
    try {
      await vetApi.removerCatalogoProcedimento(item.id);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao excluir procedimento.");
    } finally {
      setRemovendoId(null);
    }
  }

  return {
    adicionarInsumo,
    abrirEdicao,
    abrirNovo,
    atualizarInsumo,
    carregando,
    editando,
    erro,
    excluir,
    fecharModal,
    form,
    lista,
    modalAberto,
    produtos,
    removerInsumo,
    removendoId,
    resumoMargem,
    salvando,
    salvar,
    setCampo,
  };
}
