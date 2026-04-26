import { useCallback } from "react";

import { vetApi } from "../vetApi";
import { FORM_PARCEIRO_INICIAL } from "./configuracoesConstants";

export function useConfiguracoesParceirosActions({
  carregar,
  mostrarSucesso,
  parceiroForm,
  setErro,
  setMostrarForm,
  setParceiroForm,
  setParceiros,
  setSalvando,
}) {
  const atualizarParceiroForm = useCallback((patch) => {
    setParceiroForm((prev) => ({ ...prev, ...patch }));
  }, [setParceiroForm]);

  const salvarNovoParceiro = useCallback(async () => {
    if (!parceiroForm.vetTenantId) {
      setErro("Selecione o tenant veterinario parceiro.");
      return;
    }

    try {
      setSalvando(true);
      setErro(null);
      await vetApi.criarParceiro({
        vet_tenant_id: parceiroForm.vetTenantId,
        tipo_relacao: parceiroForm.tipoRelacao,
        comissao_empresa_pct: parceiroForm.comissao ? Number.parseFloat(parceiroForm.comissao) : null,
      });
      mostrarSucesso("Parceiro cadastrado com sucesso!");
      setMostrarForm(false);
      setParceiroForm(FORM_PARCEIRO_INICIAL);
      await carregar();
    } catch (e) {
      setErro(e?.response?.data?.detail || "Erro ao cadastrar parceiro.");
    } finally {
      setSalvando(false);
    }
  }, [carregar, mostrarSucesso, parceiroForm, setErro, setMostrarForm, setParceiroForm, setSalvando]);

  const toggleAtivoParceiro = useCallback(async (parceiro) => {
    try {
      await vetApi.atualizarParceiro(parceiro.id, { ativo: !parceiro.ativo });
      setParceiros((prev) =>
        prev.map((item) => (item.id === parceiro.id ? { ...item, ativo: !parceiro.ativo } : item))
      );
    } catch {
      setErro("Nao foi possivel atualizar o parceiro.");
    }
  }, [setErro, setParceiros]);

  const removerParceiro = useCallback(
    async (id) => {
      if (!window.confirm("Tem certeza que deseja remover este vinculo de parceria?")) return;

      try {
        await vetApi.removerParceiro(id);
        setParceiros((prev) => prev.filter((item) => item.id !== id));
        mostrarSucesso("Parceiro removido.");
      } catch {
        setErro("Erro ao remover parceiro.");
      }
    },
    [mostrarSucesso, setErro, setParceiros]
  );

  const cancelarParceiro = useCallback(() => {
    setMostrarForm(false);
    setErro(null);
  }, [setErro, setMostrarForm]);

  return {
    atualizarParceiroForm,
    cancelarParceiro,
    removerParceiro,
    salvarNovoParceiro,
    toggleAtivoParceiro,
  };
}
