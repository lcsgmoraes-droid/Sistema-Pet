import { useCallback, useEffect, useRef, useState } from "react";
import {
  getIfoodRepasses,
  sincronizarIfoodRepasses,
  getIfoodConciliacaoStatus,
  sincronizarIfoodConciliacao,
} from "../../api/ifood";
import { mensagemErroIfood } from "./ifoodPresentation";
import { periodoFinanceiroValido } from "./ifoodFinanceiroNavigation";
import { competenciaValida, periodoFinanceiroHoje } from "./ifoodFinanceiroPresentation";

const PENDENTES = new Set(["created", "enqueue"]);
const LIMITE_TENTATIVAS = 8;
const esperaConciliacao = (job) =>
  Math.max(
    5000,
    Number.isFinite(Number(job?.next_retry_after_seconds))
      ? Number(job.next_retry_after_seconds) * 1000
      : 5000,
  );

export default function useIfoodRepasses({
  enabled = false,
  canSync = false,
  periodoSugerido = null,
} = {}) {
  const [periodo, setPeriodo] = useState(() =>
    periodoFinanceiroValido(periodoSugerido, 90) ? { ...periodoSugerido } : periodoFinanceiroHoje(),
  );
  const [basis, setBasis] = useState("calculation");
  const [competence, setCompetence] = useState(() => periodo.inicio.slice(0, 7));
  const [relatorio, setRelatorio] = useState(null);
  const [jobData, setJobData] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [sincronizando, setSincronizando] = useState(false);
  const [consultandoJob, setConsultandoJob] = useState(false);
  const [seguindo, setSeguindo] = useState(false);
  const [tentativas, setTentativas] = useState(0);
  const [erro, setErro] = useState("");
  const [erroJob, setErroJob] = useState("");
  const [revisao, setRevisao] = useState(0);
  const [revisaoJob, setRevisaoJob] = useState(0);
  const [retryTick, setRetryTick] = useState(0);
  const repasseController = useRef(null);
  const repasseLock = useRef(false);
  const repasseGeracao = useRef(0);
  const jobController = useRef(null);
  const jobLock = useRef(false);
  const jobGeracao = useRef(0);
  const retryAfter = useRef(0);
  const periodoValido = periodoFinanceiroValido(periodo, 90);
  const mesValido = competenciaValida(competence);

  useEffect(() => {
    setSincronizando(false);
    return () => {
      repasseGeracao.current++;
      repasseController.current?.abort();
      repasseLock.current = false;
    };
  }, [enabled, periodo.inicio, periodo.fim, basis, canSync]);

  useEffect(() => {
    if (!enabled || !periodoValido || sincronizando) {
      setCarregando(false);
      return undefined;
    }
    let ativo = true;
    const abort = new AbortController();
    setCarregando(true);
    setErro("");
    getIfoodRepasses(
      { begin_date: periodo.inicio, end_date: periodo.fim, basis },
      { signal: abort.signal },
    )
      .then(({ data }) => {
        if (ativo) setRelatorio(data);
      })
      .catch((error) => {
        if (!ativo) return;
        if (error?.response?.status === 403) setRelatorio(null);
        setErro(
          mensagemErroIfood(error, "Não foi possível consultar os repasses.") +
            " Os últimos dados recebidos foram mantidos; confira o período exibido.",
        );
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
      abort.abort();
    };
  }, [enabled, periodoValido, periodo.inicio, periodo.fim, basis, revisao, sincronizando]);

  useEffect(() => {
    setSeguindo(false);
    setConsultandoJob(false);
    if (!enabled || !mesValido) return undefined;
    const versao = ++jobGeracao.current;
    const abort = new AbortController();
    jobController.current = abort;
    getIfoodConciliacaoStatus({ competence }, { signal: abort.signal })
      .then(({ data }) => {
        if (versao === jobGeracao.current) {
          retryAfter.current = PENDENTES.has(data.job?.status)
            ? Date.now() + esperaConciliacao(data.job)
            : 0;
          setJobData({ ...data, competence });
        }
      })
      .catch((error) => {
        if (versao !== jobGeracao.current) return;
        if (error?.response?.status === 403) setJobData(null);
        setErroJob(
          mensagemErroIfood(error, "Não foi possível consultar o estado local da conciliação."),
        );
      });
    return () => {
      jobGeracao.current++;
      abort.abort();
      jobController.current?.abort();
      jobLock.current = false;
    };
  }, [enabled, mesValido, competence, canSync, revisaoJob]);

  async function sincronizar() {
    if (!enabled || !canSync || !periodoValido || repasseLock.current || carregando) return;
    repasseLock.current = true;
    setSincronizando(true);
    setErro("");
    const versao = repasseGeracao.current;
    const abort = new AbortController();
    repasseController.current = abort;
    try {
      const { data } = await sincronizarIfoodRepasses(
        { begin_date: periodo.inicio, end_date: periodo.fim, basis },
        { signal: abort.signal },
      );
      if (versao === repasseGeracao.current) {
        setRelatorio(data);
        setRevisao((value) => value + 1);
      }
    } catch (error) {
      if (versao === repasseGeracao.current)
        setErro(
          mensagemErroIfood(error, "Não foi possível consultar os títulos no iFood.") +
            " Os dados anteriores foram preservados.",
        );
    } finally {
      if (versao === repasseGeracao.current) {
        repasseLock.current = false;
        setSincronizando(false);
      }
    }
  }

  const consultarConciliacao = useCallback(async () => {
    if (!enabled || !canSync || !mesValido || jobLock.current) return;
    jobLock.current = true;
    jobController.current?.abort();
    const versao = ++jobGeracao.current;
    const abort = new AbortController();
    jobController.current = abort;
    setConsultandoJob(true);
    setErroJob("");
    try {
      const { data } = await sincronizarIfoodConciliacao({ competence }, { signal: abort.signal });
      if (versao !== jobGeracao.current) return;
      retryAfter.current = PENDENTES.has(data.job?.status)
        ? Date.now() + esperaConciliacao(data.job)
        : 0;
      setJobData({ ...data, competence });
      setTentativas((value) => value + 1);
      if (!PENDENTES.has(data.job?.status)) setSeguindo(false);
      if (data.job?.status === "processed") setRevisao((value) => value + 1);
    } catch (error) {
      if (versao !== jobGeracao.current) return;
      retryAfter.current = Date.now() + 5000;
      setSeguindo(false);
      setErroJob(
        mensagemErroIfood(
          error,
          "Não foi possível acompanhar a conciliação. A solicitação e os dados anteriores foram preservados.",
        ),
      );
    } finally {
      if (versao === jobGeracao.current) {
        jobLock.current = false;
        setConsultandoJob(false);
      }
    }
  }, [enabled, canSync, mesValido, competence]);

  const job = jobData?.competence === competence ? jobData.job : null;
  useEffect(() => {
    if (
      !enabled ||
      !canSync ||
      consultandoJob ||
      !PENDENTES.has(job?.status) ||
      (Date.now() >= retryAfter.current && (!seguindo || tentativas >= LIMITE_TENTATIVAS))
    )
      return undefined;
    const delay = Math.min(2147483647, Math.max(0, retryAfter.current - Date.now()));
    const timer = setTimeout(() => {
      setRetryTick((value) => value + 1);
      if (Date.now() >= retryAfter.current && seguindo && tentativas < LIMITE_TENTATIVAS)
        consultarConciliacao();
    }, delay);
    return () => clearTimeout(timer);
  }, [
    enabled,
    canSync,
    seguindo,
    consultandoJob,
    job,
    tentativas,
    consultarConciliacao,
    retryTick,
  ]);

  return {
    periodo,
    alterarPeriodo: setPeriodo,
    periodoValido,
    basis,
    alterarBasis: setBasis,
    competence,
    alterarCompetence: setCompetence,
    mesValido,
    relatorio,
    jobData,
    job,
    carregando,
    sincronizando,
    consultandoJob,
    seguindo: seguindo && tentativas < LIMITE_TENTATIVAS,
    limiteAtingido: seguindo && tentativas >= LIMITE_TENTATIVAS,
    aguardandoRetry: Date.now() < retryAfter.current,
    tentativas,
    erro,
    erroJob,
    atualizar: () => {
      setRevisao((value) => value + 1);
      setRevisaoJob((value) => value + 1);
      setErroJob("");
    },
    sincronizar,
    iniciarConciliacao: () => {
      if (
        !enabled ||
        !canSync ||
        !mesValido ||
        jobLock.current ||
        Date.now() < retryAfter.current ||
        (seguindo && tentativas < LIMITE_TENTATIVAS)
      )
        return;
      setTentativas(0);
      setSeguindo(true);
      consultarConciliacao();
    },
    pausar: () => {
      setSeguindo(false);
      jobGeracao.current++;
      jobController.current?.abort();
      jobLock.current = false;
      setConsultandoJob(false);
    },
  };
}
