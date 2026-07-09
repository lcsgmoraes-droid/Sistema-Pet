import { useEffect, useState } from "react";

import { FORM_CONSULTORIO_INICIAL, FORM_PARCEIRO_INICIAL } from "./configuracoesConstants";
import { vetApi } from "../vetApi";
import { useConfiguracoesConsultoriosActions } from "./useConfiguracoesConsultoriosActions";
import { useConfiguracoesData } from "./useConfiguracoesData";
import { useConfiguracoesFeedback } from "./useConfiguracoesFeedback";
import { useConfiguracoesParceirosActions } from "./useConfiguracoesParceirosActions";

export function useVetConfiguracoes() {
  const data = useConfiguracoesData();
  const { mostrarSucesso, sucesso } = useConfiguracoesFeedback();
  const [mostrarForm, setMostrarForm] = useState(false);
  const [parceiroForm, setParceiroForm] = useState(FORM_PARCEIRO_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [mostrarFormConsultorio, setMostrarFormConsultorio] = useState(false);
  const [consultorioForm, setConsultorioForm] = useState(FORM_CONSULTORIO_INICIAL);
  const [lembretesForm, setLembretesForm] = useState(null);

  useEffect(() => {
    if (!data.lembretesConfig) return;
    setLembretesForm({
      lembretes_agendamento_ativos: data.lembretesConfig.lembretes_agendamento_ativos ?? true,
      lembrete_agendamento_1d_ativo: data.lembretesConfig.lembrete_agendamento_1d_ativo ?? true,
      lembrete_agendamento_horas_ativo:
        data.lembretesConfig.lembrete_agendamento_horas_ativo ?? true,
      lembrete_agendamento_horas_antes: String(
        data.lembretesConfig.lembrete_agendamento_horas_antes ?? 1,
      ),
    });
  }, [data.lembretesConfig]);

  function atualizarLembretesForm(patch) {
    setLembretesForm((prev) => ({ ...(prev || {}), ...patch }));
  }

  async function salvarLembretes() {
    if (!lembretesForm) return;
    setSalvando(true);
    data.setErro(null);
    try {
      const response = await vetApi.atualizarConfigLembretes({
        lembretes_agendamento_ativos: Boolean(lembretesForm.lembretes_agendamento_ativos),
        lembrete_agendamento_1d_ativo: Boolean(lembretesForm.lembrete_agendamento_1d_ativo),
        lembrete_agendamento_horas_ativo: Boolean(lembretesForm.lembrete_agendamento_horas_ativo),
        lembrete_agendamento_horas_antes: Number(
          lembretesForm.lembrete_agendamento_horas_antes || 1,
        ),
      });
      data.setLembretesConfig(response.data);
      mostrarSucesso("Lembretes salvos.");
    } catch {
      data.setErro("Nao foi possivel salvar os lembretes.");
    } finally {
      setSalvando(false);
    }
  }

  const parceirosActions = useConfiguracoesParceirosActions({
    carregar: data.carregar,
    mostrarSucesso,
    parceiroForm,
    setErro: data.setErro,
    setMostrarForm,
    setParceiroForm,
    setParceiros: data.setParceiros,
    setSalvando,
  });
  const consultoriosActions = useConfiguracoesConsultoriosActions({
    carregar: data.carregar,
    consultorioForm,
    mostrarSucesso,
    setConsultorioForm,
    setConsultorios: data.setConsultorios,
    setErro: data.setErro,
    setMostrarFormConsultorio,
    setSalvando,
  });

  return {
    ...consultoriosActions,
    ...parceirosActions,
    carregar: data.carregar,
    carregando: data.carregando,
    consultorioForm,
    consultorios: data.consultorios,
    erro: data.erro,
    lembretesForm,
    mostrarForm,
    mostrarFormConsultorio,
    parceiroForm,
    parceiros: data.parceiros,
    salvando,
    setErro: data.setErro,
    setMostrarForm,
    setMostrarFormConsultorio,
    salvarLembretes,
    sucesso,
    tenantsVet: data.tenantsVet,
    atualizarLembretesForm,
  };
}
