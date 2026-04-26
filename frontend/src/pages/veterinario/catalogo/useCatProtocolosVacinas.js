import { useCallback, useEffect, useState } from "react";

import { vetApi } from "../vetApi";
import {
  buildProtocoloPayload,
  FORM_PROTOCOLO_INICIAL,
  mapProtocoloParaForm,
} from "./protocolosVacinasForm";

export function useCatProtocolosVacinas() {
  const [lista, setLista] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState(FORM_PROTOCOLO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [removendoId, setRemovendoId] = useState(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro("");
    try {
      const response = await vetApi.listarProtocolosVacinas();
      setLista(Array.isArray(response.data) ? response.data : response.data?.items ?? []);
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao carregar protocolos.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function abrirNovo() {
    setEditando(null);
    setForm(FORM_PROTOCOLO_INICIAL);
    setModalAberto(true);
    setErro("");
  }

  function abrirEdicao(item) {
    setEditando(item);
    setForm(mapProtocoloParaForm(item));
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
    if (!form.nome.trim() || !form.especie.trim()) return;
    setSalvando(true);
    setErro("");
    try {
      const payload = buildProtocoloPayload(form);
      if (editando?.id) {
        await vetApi.atualizarProtocoloVacina(editando.id, payload);
      } else {
        await vetApi.criarProtocoloVacina(payload);
      }
      setModalAberto(false);
      setEditando(null);
      setForm(FORM_PROTOCOLO_INICIAL);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao salvar protocolo.");
    } finally {
      setSalvando(false);
    }
  }

  async function excluir(item) {
    if (!window.confirm(`Deseja excluir o protocolo "${item.nome}"?`)) return;
    setRemovendoId(item.id);
    setErro("");
    try {
      await vetApi.removerProtocoloVacina(item.id);
      await carregar();
    } catch (err) {
      setErro(err?.response?.data?.detail || "Erro ao excluir protocolo.");
    } finally {
      setRemovendoId(null);
    }
  }

  return {
    abrirEdicao,
    abrirNovo,
    carregando,
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
    setCampo,
  };
}
