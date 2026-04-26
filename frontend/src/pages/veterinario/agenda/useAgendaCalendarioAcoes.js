import { useCallback } from "react";

import { vetApi } from "../vetApi";

export function useAgendaCalendarioAcoes({ calendarioMeta, setMensagemCalendario }) {
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
    } catch {
      setMensagemCalendario("Nao foi possivel baixar o calendario agora.");
    }
  }, [setMensagemCalendario]);

  const copiarLinkCalendario = useCallback(async () => {
    if (!calendarioMeta?.feed_url) return;
    try {
      await navigator.clipboard.writeText(calendarioMeta.feed_url);
      setMensagemCalendario("Link privado copiado. Agora voce pode assinar no calendario do celular.");
    } catch {
      setMensagemCalendario("Nao foi possivel copiar o link automaticamente.");
    }
  }, [calendarioMeta?.feed_url, setMensagemCalendario]);

  return {
    baixarCalendarioAgenda,
    copiarLinkCalendario,
  };
}
