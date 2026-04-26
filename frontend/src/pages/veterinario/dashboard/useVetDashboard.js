import { useCallback, useEffect, useMemo, useState } from "react";

import { vetApi } from "../vetApi";
import { montarCardsDashboard } from "./dashboardConfig";

export function useVetDashboard() {
  const [dados, setDados] = useState(null);
  const [relatorio, setRelatorio] = useState(null);
  const [agendamentos, setAgendamentos] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [exportando, setExportando] = useState(false);
  const [erro, setErro] = useState(null);
  const [calendarioMeta, setCalendarioMeta] = useState(null);
  const [mensagemCalendario, setMensagemCalendario] = useState("");

  const carregar = useCallback(async () => {
    try {
      setCarregando(true);
      setErro(null);
      const hoje = new Date().toISOString().slice(0, 10);
      const [dashRes, agRes, relRes] = await Promise.allSettled([
        vetApi.dashboard(),
        vetApi.listarAgendamentos({ data_inicio: hoje, data_fim: hoje }),
        vetApi.relatorioClinico({ dias: 30, top: 5 }),
      ]);

      if (dashRes.status !== "fulfilled" || agRes.status !== "fulfilled") {
        throw new Error("Falha ao carregar dados principais do painel veterinário.");
      }

      setDados(dashRes.value.data);
      setAgendamentos(agRes.value.data?.items ?? agRes.value.data ?? []);
      setRelatorio(relRes.status === "fulfilled" ? relRes.value.data : null);

      vetApi
        .obterCalendarioAgendaMeta()
        .then((res) => setCalendarioMeta(res.data || null))
        .catch(() => setCalendarioMeta(null));
    } catch (e) {
      console.error("Erro ao carregar painel veterinário", e);
      setErro("Não foi possível carregar o painel veterinário.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const cards = useMemo(() => montarCardsDashboard(dados), [dados]);

  const exportarCsvRelatorio = useCallback(async () => {
    try {
      setExportando(true);
      const resposta = await vetApi.exportarRelatorioClinicoCsv({ dias: 30, top: 5 });
      const blob = new Blob([resposta.data], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "relatorio_clinico_veterinario_30d.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Erro ao exportar relatório clínico", e);
      setErro("Não foi possível exportar o relatório clínico.");
    } finally {
      setExportando(false);
    }
  }, []);

  const baixarCalendarioAgenda = useCallback(async () => {
    try {
      setMensagemCalendario("");
      const resposta = await vetApi.baixarCalendarioAgendaIcs();
      const blob = new Blob([resposta.data], { type: "text/calendar;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "agenda-veterinaria.ics";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Erro ao baixar calendario veterinario", e);
      setMensagemCalendario("Nao foi possivel baixar o calendario agora.");
    }
  }, []);

  const copiarLinkCalendario = useCallback(async () => {
    if (!calendarioMeta?.feed_url) return;
    try {
      await navigator.clipboard.writeText(calendarioMeta.feed_url);
      setMensagemCalendario("Link privado copiado para assinar a agenda no celular.");
    } catch (e) {
      console.error("Erro ao copiar link do calendario", e);
      setMensagemCalendario("Nao foi possivel copiar o link automaticamente.");
    }
  }, [calendarioMeta?.feed_url]);

  return {
    agendamentos,
    baixarCalendarioAgenda,
    calendarioMeta,
    cards,
    carregando,
    copiarLinkCalendario,
    dados,
    erro,
    exportando,
    exportarCsvRelatorio,
    mensagemCalendario,
    relatorio,
  };
}
