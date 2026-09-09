import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import * as Updates from "expo-updates";

const INTERVALO_VERIFICACAO = 15 * 60 * 1000;
type Etapa = "idle" | "checking" | "downloading" | "ready" | "restarting" | "current";

export function useAppUpdates() {
  const nativo = Updates.useUpdates();
  const enabled = !__DEV__ && Updates.isEnabled;
  const [etapa, setEtapa] = useState<Etapa>("idle");
  const [erro, setErro] = useState<string | null>(null);
  const emCurso = useRef(false);
  const ultimaTentativa = useRef(0);
  const prontoLocal = useRef(false);
  const atual = useRef(nativo);
  atual.current = nativo;

  const verificar = useCallback(async (manual = false) => {
    const estado = atual.current;
    if (!enabled || emCurso.current || estado.isStartupProcedureRunning || estado.isChecking || estado.isDownloading || estado.isRestarting) return;
    if (prontoLocal.current || estado.isUpdatePending) return;
    const ultima = Math.max(ultimaTentativa.current, estado.lastCheckForUpdateTimeSinceRestart?.getTime() ?? 0);
    if (!manual && Date.now() - ultima < INTERVALO_VERIFICACAO) return;

    emCurso.current = true;
    ultimaTentativa.current = Date.now();
    setErro(null);
    setEtapa("checking");
    try {
      const resultado = await Updates.checkForUpdateAsync();
      if (resultado.isAvailable || resultado.isRollBackToEmbedded) {
        setEtapa("downloading");
        const download = await Updates.fetchUpdateAsync();
        if (!download.isNew && !download.isRollBackToEmbedded) {
          throw new Error("download_indisponivel");
        }
        prontoLocal.current = true;
        setEtapa("ready");
      } else if (resultado.reason === Updates.UpdateCheckResultNotAvailableReason.UPDATE_PREVIOUSLY_FAILED) {
        setEtapa("idle");
        setErro("A última atualização não conseguiu iniciar neste aparelho. Entre em contato com o suporte.");
      } else {
        setEtapa("current");
      }
    } catch {
      setEtapa("idle");
      setErro("Não foi possível verificar ou baixar a atualização. Confira a internet e tente novamente.");
    } finally {
      emCurso.current = false;
    }
  }, [enabled]);

  // A inicialização nativa já consulta o servidor. Também verificamos ao voltar
  // ao app, pois sair da tela no Android pode manter o mesmo processo vivo.
  useEffect(() => {
    if (AppState.currentState === "active") void verificar();
  }, [verificar, nativo.isStartupProcedureRunning]);

  useEffect(() => {
    let anterior = AppState.currentState;
    const listener = AppState.addEventListener("change", (proximo) => {
      if (proximo === "active" && anterior !== "active") void verificar();
      anterior = proximo;
    });
    return () => listener.remove();
  }, [verificar]);

  useEffect(() => {
    if (!enabled) return;
    // Evidência do pacote executado; não contém usuário, token ou dados do ERP.
    console.info("[CorePetUpdate]", JSON.stringify({
      updateId: Updates.updateId,
      runtimeVersion: Updates.runtimeVersion,
      channel: Updates.channel,
      isEmbeddedLaunch: Updates.isEmbeddedLaunch,
      isEmergencyLaunch: Updates.isEmergencyLaunch,
    }));
  }, [enabled]);

  const aplicar = useCallback(async () => {
    if (!enabled || emCurso.current || (!prontoLocal.current && !atual.current.isUpdatePending)) return;
    emCurso.current = true;
    setErro(null);
    setEtapa("restarting");
    try {
      await Updates.reloadAsync();
    } catch {
      emCurso.current = false;
      setEtapa("ready");
      setErro("Não foi possível reiniciar o app. Tente aplicar a atualização novamente.");
    }
  }, [enabled]);

  const reiniciando = etapa === "restarting" || nativo.isRestarting;
  const baixando = etapa === "downloading" || nativo.isDownloading;
  const verificando = etapa === "checking" || nativo.isChecking || nativo.isStartupProcedureRunning;
  const pronto = prontoLocal.current || nativo.isUpdatePending;
  const erroNativo = nativo.checkError || nativo.downloadError;
  const erroExibido = erro ?? (!pronto && !verificando && !baixando && erroNativo
    ? "Não foi possível buscar a atualização. Confira a internet e tente novamente."
    : null);

  return {
    enabled, verificar, aplicar, pronto, reiniciando,
    ocupado: reiniciando || baixando || verificando,
    erro: erroExibido,
    status: reiniciando ? "Reiniciando o app…"
      : baixando ? "Baixando atualização…"
      : verificando ? "Verificando atualização…"
      : pronto ? "Atualização pronta para aplicar"
      : erroExibido ? "Não foi possível atualizar"
      : nativo.currentlyRunning.isEmergencyLaunch ? "O app abriu uma versão de recuperação"
      : etapa === "current" || nativo.lastCheckForUpdateTimeSinceRestart ? "Nenhuma atualização disponível"
      : "Verifique se há uma atualização",
    versao: nativo.currentlyRunning,
  };
}
