import { useCallback, useEffect, useState } from "react";
import { vetApi } from "../vetApi";
import {
  buildMedicamentoPayload,
  FORM_MEDICAMENTO_INICIAL,
  mapMedicamentoParaForm,
} from "./medicamentosForm";

export function useCatMedicamentos() {
  const [lista, setLista] = useState([]);
  const [busca, setBusca] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [removendoId, setRemovendoId] = useState(null);
  const [form, setForm] = useState(FORM_MEDICAMENTO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setBuscando(true);
    setErro("");
    try {
      const response = await vetApi.listarMedicamentos(busca || undefined);
      setLista(Array.isArray(response.data) ? response.data : response.data?.items ?? []);
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao carregar medicamentos.");
    } finally {
      setBuscando(false);
    }
  }, [busca]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function abrirNovo() {
    setEditando(null);
    setForm(FORM_MEDICAMENTO_INICIAL);
    setModalAberto(true);
    setErro("");
  }

  function abrirEdicao(item) {
    setEditando(item);
    setForm(mapMedicamentoParaForm(item));
    setModalAberto(true);
    setErro("");
  }

  function fecharModal() {
    setModalAberto(false);
  }

  function setCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  async function salvar() {
    if (!form.nome.trim()) return;
    setSalvando(true);
    setErro("");
    try {
      const payload = buildMedicamentoPayload(form);
      if (editando?.id) {
        await vetApi.atualizarMedicamento(editando.id, payload);
      } else {
        await vetApi.criarMedicamento(payload);
      }
      setModalAberto(false);
      setEditando(null);
      setForm(FORM_MEDICAMENTO_INICIAL);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao salvar medicamento.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item) {
    if (!window.confirm(`Deseja excluir o medicamento "${item.nome}"?`)) return;
    setRemovendoId(item.id);
    setErro("");
    try {
      await vetApi.removerMedicamento(item.id);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao excluir medicamento.");
    } finally {
      setRemovendoId(null);
    }
  }

  return {
    abrirEdicao,
    abrirNovo,
    busca,
    buscando,
    editando,
    erro,
    excluir,
    fecharModal,
    form,
    lista,
    modalAberto,
    removendoId,
    salvando,
    salvar,
    setBusca,
    setCampo,
  };
}
