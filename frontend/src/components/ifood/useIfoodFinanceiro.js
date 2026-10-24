import { useEffect, useRef, useState } from "react";
import {
  getIfoodFinanceiroRelatorio,
  getIfoodFinanceiroStatus,
  salvarIfoodCustosPedido,
  sincronizarIfoodFinanceiro,
} from "../../api/ifood";
import { mensagemErroIfood } from "./ifoodPresentation";

const CAMPOS_CUSTOS = ["revenue", "cmv", "tax", "other_costs"];
const VAZIO = { revenue: null, cmv: null, tax: null, other_costs: null, source_note: "" };

function periodoInicial() {
  const agora = new Date();
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(agora);
  const parte = (tipo) => partes.find((item) => item.type === tipo)?.value;
  const dia = `${parte("year")}-${parte("month")}-${parte("day")}`;
  return { inicio: dia, fim: dia };
}

export default function useIfoodFinanceiro({ enabled = false } = {}) {
  const [periodo, setPeriodo] = useState(periodoInicial);
  const [status, setStatus] = useState(null);
  const [relatorio, setRelatorio] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");
  const [sucesso, setSucesso] = useState("");
  const [revisao, setRevisao] = useState(0);
  const [pedido, setPedido] = useState(null);
  const [rascunho, setRascunho] = useState(VAZIO);
  const [erroCustos, setErroCustos] = useState("");
  const trava = useRef(false);
  const montado = useRef(true);
  const periodoValido = Boolean(periodo.inicio && periodo.fim && periodo.inicio <= periodo.fim);
  const params = { begin_date: periodo.inicio, end_date: periodo.fim };

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  useEffect(() => {
    if (!enabled || !periodoValido || ocupado) {
      setCarregando(false);
      return undefined;
    }
    let ativo = true;
    const abort = new AbortController();
    setCarregando(true);
    setErro("");
    (async () => {
      const resultados = await Promise.allSettled([
        getIfoodFinanceiroStatus({ signal: abort.signal }),
        getIfoodFinanceiroRelatorio(
          { begin_date: periodo.inicio, end_date: periodo.fim },
          { signal: abort.signal },
        ),
      ]);
      if (!ativo) return;
      setStatus(resultados[0].status === "fulfilled" ? resultados[0].value.data : null);
      if (resultados[1].status === "fulfilled") setRelatorio(resultados[1].value.data);
      const falha = resultados.find((resultado) => resultado.status === "rejected");
      if (
        resultados.some(
          (resultado) =>
            resultado.status === "rejected" && resultado.reason?.response?.status === 403,
        )
      ) {
        setRelatorio(null);
      }
      if (falha)
        setErro(
          mensagemErroIfood(falha.reason, "Não foi possível consultar o financeiro.") +
            " Os últimos dados recebidos foram mantidos; confira o período e a atualização exibidos.",
        );
      setCarregando(false);
    })();
    return () => {
      ativo = false;
      abort.abort();
    };
  }, [enabled, periodoValido, periodo.inicio, periodo.fim, revisao, ocupado]);

  async function sincronizar() {
    if (!enabled || !status?.can_sync || !periodoValido || trava.current || carregando) return;
    trava.current = true;
    setOcupado(true);
    setErro("");
    setSucesso("");
    try {
      const response = await sincronizarIfoodFinanceiro(params);
      if (montado.current) {
        setRelatorio(response.data);
        setSucesso("Consulta de eventos concluída. Conferindo os dados locais…");
        setRevisao((atual) => atual + 1);
      }
    } catch (error) {
      if (montado.current)
        setErro(
          mensagemErroIfood(error, "Não foi possível consultar os eventos no iFood.") +
            " Os dados anteriores e os custos em edição foram preservados.",
        );
    } finally {
      trava.current = false;
      if (montado.current) setOcupado(false);
    }
  }

  function abrirCustos(orderId, custos = null) {
    if (trava.current) return;
    setPedido(orderId);
    setRascunho({
      ...VAZIO,
      ...Object.fromEntries(
        Object.keys(VAZIO).map((campo) => [campo, custos?.[campo] ?? VAZIO[campo]]),
      ),
    });
    setErroCustos("");
  }

  async function salvarCustos() {
    if (!pedido || trava.current || !enabled || !status?.can_edit_costs) return;
    if (rascunho.source_note.trim().length < 5 || rascunho.source_note.trim().length > 1000) {
      setErroCustos("Informe a fonte e a justificativa desta venda com 5 a 1.000 caracteres.");
      return;
    }
    if (
      CAMPOS_CUSTOS.some(
        (campo) =>
          rascunho[campo] !== null &&
          (!Number.isFinite(Number(rascunho[campo])) || Number(rascunho[campo]) < 0),
      )
    ) {
      setErroCustos(
        "Informe valores válidos, sem negativos. Valor desconhecido deve ficar sem informar.",
      );
      return;
    }
    trava.current = true;
    setOcupado(true);
    setErroCustos("");
    try {
      const response = await salvarIfoodCustosPedido(pedido, {
        ...Object.fromEntries(
          CAMPOS_CUSTOS.map((campo) => [
            campo,
            rascunho[campo] === null ? null : Number(rascunho[campo]),
          ]),
        ),
        source_note: rascunho.source_note.trim(),
      });
      if (montado.current) {
        setRelatorio((atual) =>
          atual
            ? {
                ...atual,
                orders: atual.orders.map((order) =>
                  order.order_id === pedido ? { ...order, ...response.data } : order,
                ),
              }
            : atual,
        );
        setPedido(null);
        setSucesso("Versão dos custos desta venda salva. Os eventos do iFood foram preservados.");
        setRevisao((atual) => atual + 1);
      }
    } catch (error) {
      if (montado.current)
        setErroCustos(
          mensagemErroIfood(error, "Não foi possível salvar os custos. Seu rascunho foi mantido."),
        );
    } finally {
      trava.current = false;
      if (montado.current) setOcupado(false);
    }
  }

  return {
    periodo,
    alterarPeriodo: setPeriodo,
    periodoValido,
    status,
    relatorio,
    carregando,
    ocupado,
    erro,
    sucesso,
    atualizar: () => setRevisao((atual) => atual + 1),
    sincronizar,
    pedido,
    rascunho,
    erroCustos,
    abrirCustos,
    salvarCustos,
    alterarCusto: (campo, valor) => setRascunho((atual) => ({ ...atual, [campo]: valor })),
    fecharCustos: () => {
      if (!trava.current) setPedido(null);
    },
  };
}
