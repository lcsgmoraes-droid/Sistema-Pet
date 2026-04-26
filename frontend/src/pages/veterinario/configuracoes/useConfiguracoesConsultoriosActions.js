import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { FORM_CONSULTORIO_INICIAL } from "./configuracoesConstants";

export function useConfiguracoesConsultoriosActions({
  carregar,
  consultorioForm,
  mostrarSucesso,
  setConsultorioForm,
  setConsultorios,
  setErro,
  setMostrarFormConsultorio,
  setSalvando,
}) {
  const atualizarConsultorioForm = useCallback((patch) => {
    setConsultorioForm((prev) => ({ ...prev, ...patch }));
  }, [setConsultorioForm]);

  const salvarNovoConsultorio = useCallback(async () => {
    if (!consultorioForm.nome.trim()) {
      setErro("Informe o nome do consultorio.");
      return;
    }

    try {
      setSalvando(true);
      setErro(null);
      await vetApi.criarConsultorio({
        nome: consultorioForm.nome.trim(),
        descricao: consultorioForm.descricao.trim() || undefined,
        ordem: consultorioForm.ordem ? Number.parseInt(consultorioForm.ordem, 10) : undefined,
      });
      mostrarSucesso("Consultorio cadastrado com sucesso!");
      setMostrarFormConsultorio(false);
      setConsultorioForm(FORM_CONSULTORIO_INICIAL);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao cadastrar consultorio.");
    } finally {
      setSalvando(false);
    }
  }, [
    carregar,
    consultorioForm,
    mostrarSucesso,
    setConsultorioForm,
    setErro,
    setMostrarFormConsultorio,
    setSalvando,
  ]);

  const toggleAtivoConsultorio = useCallback(async (consultorio) => {
    try {
      await vetApi.atualizarConsultorio(consultorio.id, { ativo: !consultorio.ativo });
      setConsultorios((prev) =>
        prev.map((item) =>
          item.id === consultorio.id ? { ...item, ativo: !consultorio.ativo } : item
        )
      );
    } catch (e) {
      setErro(e?.response?.data?.detail || "Nao foi possivel atualizar o consultorio.");
    }
  }, [setConsultorios, setErro]);

  const removerConsultorio = useCallback(
    async (consultorio) => {
      if (!window.confirm(`Deseja remover o consultorio "${consultorio.nome}"?`)) return;

      try {
        await vetApi.removerConsultorio(consultorio.id);
        setConsultorios((prev) => prev.filter((item) => item.id !== consultorio.id));
        mostrarSucesso("Consultorio removido.");
      } catch (e) {
        setErro(e?.response?.data?.detail || "Erro ao remover consultorio.");
      }
    },
    [mostrarSucesso, setConsultorios, setErro]
  );

  const cancelarConsultorio = useCallback(() => {
    setMostrarFormConsultorio(false);
    setConsultorioForm(FORM_CONSULTORIO_INICIAL);
  }, [setConsultorioForm, setMostrarFormConsultorio]);

  return {
    atualizarConsultorioForm,
    cancelarConsultorio,
    removerConsultorio,
    salvarNovoConsultorio,
    toggleAtivoConsultorio,
  };
}
