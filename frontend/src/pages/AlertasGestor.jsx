import { useEffect, useRef, useState } from "react";
import { AlertTriangle, ExternalLink, RefreshCw, Receipt, Wallet } from "lucide-react";
import api from "../api";
import { formatMoneyBRL } from "../utils/formatters";
import BotaoInteracao from "../components/v2/BotaoInteracao/BotaoInteracao";
import CartaoIndicador from "../components/v2/CartaoIndicador/CartaoIndicador";
import InputData from "../components/v2/InputData/InputData";
import InputCombobox from "../components/v2/InputCombobox/InputCombobox";
import IdentificacaoPixItem from "../components/caixa/IdentificacaoPixItem";
import { urlConsultaVendaPdv } from "../utils/conferenciaFechamentoUtils";
import { pixDoAlerta } from "./alertasGestorPix";

const TIPOS = {
  venda_justificada: { titulo: "Vendas justificadas", icone: Receipt },
  diferenca_abertura: { titulo: "Fechamento × abertura", icone: Wallet },
  diferenca_fechamento: { titulo: "Sobras e faltas", icone: AlertTriangle },
  pix_nao_identificado: { titulo: "Pix não identificado", icone: AlertTriangle },
};
const dataLocal = (data) =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(data);
const dataHora = (data) =>
  new Date(data).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });

export default function AlertasGestor() {
  const [filtros, setFiltros] = useState(() => ({
    data_inicio: dataLocal(new Date(Date.now() - 6 * 86400000)),
    data_fim: dataLocal(new Date()),
    tipo: "todos",
    operador_id: "",
  }));
  const [pagina, setPagina] = useState(1);
  const [atualizacao, setAtualizacao] = useState(0);
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [operadores, setOperadores] = useState([]);
  const [salvandoPix, setSalvandoPix] = useState(false);
  const [pixDesatualizado, setPixDesatualizado] = useState(false);
  const cicloRef = useRef(0);
  const envioPixRef = useRef(false);
  const montadoRef = useRef(false);
  const consultaCarregadaRef = useRef(null);
  const chaveConsulta = JSON.stringify([filtros, pagina]);
  const params = {
    ...filtros,
    operador_id: filtros.operador_id || undefined,
    pagina,
    por_pagina: 30,
  };

  useEffect(() => {
    montadoRef.current = true;
    return () => {
      montadoRef.current = false;
    };
  }, []);

  useEffect(() => {
    let ativo = true;
    cicloRef.current += 1;
    const mudouConsulta = consultaCarregadaRef.current !== chaveConsulta;
    if (mudouConsulta) setDados(null);
    setCarregando(true);
    setErro("");
    if (!filtros.data_inicio || !filtros.data_fim || filtros.data_fim < filtros.data_inicio) {
      setCarregando(false);
      setErro("Informe a data inicial e a data final em ordem para consultar os alertas.");
      return () => {
        ativo = false;
        cicloRef.current += 1;
      };
    }
    api
      .get("/alertas-gestor", {
        params: {
          ...filtros,
          operador_id: filtros.operador_id || undefined,
          pagina,
          por_pagina: 30,
        },
      })
      .then(({ data }) => {
        if (!ativo) return;
        consultaCarregadaRef.current = chaveConsulta;
        setDados(data);
        setOperadores(data.operadores || []);
        setPixDesatualizado(false);
      })
      .catch((error) => {
        if (!ativo) return;
        if (mudouConsulta) setDados(null);
        else setPixDesatualizado(true);
        const detalhe = error.response?.data?.detail;
        setErro(
          error.response?.status === 403
            ? "Você precisa de acesso aos relatórios gerenciais para consultar estes alertas."
            : typeof detalhe === "string"
              ? detalhe
              : "Não foi possível carregar os alertas. Tente novamente.",
        );
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
      cicloRef.current += 1;
    };
  }, [filtros, pagina, atualizacao, chaveConsulta]);

  const salvarIdentificacaoPix = async (item, estado, justificativa) => {
    const alerta = dados?.itens?.find(
      (linha) => linha.tipo === "pix_nao_identificado" && linha.pagamento_id === item.id,
    );
    const original = alerta && pixDoAlerta(alerta);
    const nota = String(justificativa || "").trim();
    if (
      !original ||
      envioPixRef.current ||
      carregando ||
      pixDesatualizado ||
      !nota ||
      nota.length > 1000 ||
      !["identificado", "nao_identificado"].includes(estado) ||
      original.identificacao_pix.estado === estado ||
      original.assinatura !== item.assinatura ||
      original.identificacao_pix.registro_id !== item.identificacao_pix?.registro_id
    )
      return false;
    const ciclo = cicloRef.current;
    envioPixRef.current = true;
    setSalvandoPix(true);
    setErro("");
    const reler = async () => {
      const { data } = await api.get("/alertas-gestor", { params });
      if (ciclo !== cicloRef.current) return false;
      const ultimaPagina = Math.max(1, Math.ceil((data.total || 0) / 30));
      if (pagina > ultimaPagina) {
        setPagina(ultimaPagina);
        return true;
      }
      consultaCarregadaRef.current = chaveConsulta;
      setDados(data);
      setOperadores(data.operadores || []);
      setPixDesatualizado(false);
      return true;
    };
    try {
      await api.post(`/alertas-gestor/pix/${original.id}/identificacao`, {
        pagamento_id: original.id,
        assinatura: original.assinatura,
        registro_id: original.identificacao_pix.registro_id ?? null,
        estado,
        justificativa: nota,
      });
      try {
        return await reler();
      } catch {
        if (ciclo === cicloRef.current) {
          setPixDesatualizado(true);
          setErro(
            "Identificação salva, mas a atualização dos alertas falhou. Atualize para conferir o resultado.",
          );
        }
        return false;
      }
    } catch (error) {
      if (ciclo !== cicloRef.current) return false;
      try {
        await reler();
      } catch {
        setPixDesatualizado(true);
      }
      if (ciclo === cicloRef.current)
        setErro(
          error.response?.status === 409
            ? "O Pix foi atualizado por outra pessoa. Confira o estado atual antes de confirmar novamente."
            : typeof error.response?.data?.detail === "string"
              ? error.response.data.detail
              : "Não foi possível salvar a identificação do Pix. O motivo foi preservado.",
        );
      return false;
    } finally {
      envioPixRef.current = false;
      if (montadoRef.current) setSalvandoPix(false);
    }
  };

  const filtrar = (campo, valor) => {
    if (envioPixRef.current) return;
    setFiltros((atual) => ({ ...atual, [campo]: valor }));
    setPagina(1);
  };
  const paginas = Math.max(1, Math.ceil((dados?.total || 0) / 30));

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="v2-titulo-pagina">Alertas do gestor</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-300">
            Confira justificativas, diferenças de caixa e Pix ainda não identificados.
          </p>
        </div>
        <BotaoInteracao
          icon={RefreshCw}
          onClick={() => setAtualizacao((valor) => valor + 1)}
          disabled={carregando || salvandoPix}
        >
          Atualizar
        </BotaoInteracao>
      </div>

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900 sm:grid-cols-2 lg:grid-cols-4">
        <InputData
          id="alertas-data-inicial"
          label="Data inicial"
          value={filtros.data_inicio}
          disabled={salvandoPix}
          onChange={(valor) => filtrar("data_inicio", valor)}
        />
        <InputData
          id="alertas-data-final"
          label="Data final"
          value={filtros.data_fim}
          disabled={salvandoPix}
          onChange={(valor) => filtrar("data_fim", valor)}
        />
        <InputCombobox
          id="alertas-tipo"
          label="Tipo de alerta"
          value={filtros.tipo}
          disabled={salvandoPix}
          permitirLimpar={false}
          onChange={(valor) => filtrar("tipo", valor)}
          opcoes={[
            { value: "todos", label: "Todos os tipos" },
            ...Object.entries(TIPOS).map(([value, info]) => ({ value, label: info.titulo })),
          ]}
        />
        <InputCombobox
          id="alertas-operador"
          label="Operador"
          value={filtros.operador_id}
          disabled={salvandoPix}
          permitirLimpar={false}
          onChange={(valor) => filtrar("operador_id", valor)}
          opcoes={[
            { value: "", label: "Todos os operadores" },
            ...operadores.map((operador) => ({ value: operador.id, label: operador.nome })),
          ]}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Object.entries(TIPOS).map(([tipo, { titulo, icone: Icone }]) => (
          <CartaoIndicador
            key={tipo}
            titulo={titulo}
            icone={Icone}
            tom={tipo === "pix_nao_identificado" ? "atencao" : "informativo"}
            detalhe={filtros.tipo === tipo ? "Filtro selecionado" : "Filtrar este tipo de alerta"}
            aoClicar={
              salvandoPix
                ? undefined
                : () => filtrar("tipo", filtros.tipo === tipo ? "todos" : tipo)
            }
          >
            <p className="text-3xl font-bold text-slate-900 dark:text-slate-100">
              {carregando ? "…" : (dados?.resumo[tipo] ?? "—")}
            </p>
          </CartaoIndicador>
        ))}
      </div>

      <p className="text-sm text-slate-500 dark:text-slate-400">
        Os alertas mostram os valores registrados na operação. Uma diferença é um ponto para
        conferência. Consulte períodos de até 93 dias. Pix não identificado continua pendente até
        ser resolvido, mesmo fora do período selecionado.
      </p>
      {erro && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          {erro}
        </div>
      )}
      {(carregando && !dados) || (!erro && consultaCarregadaRef.current !== chaveConsulta) ? (
        <p role="status" className="py-12 text-center text-gray-600">
          Carregando alertas...
        </p>
      ) : dados?.itens.length === 0 ? (
        <div className="rounded-xl border bg-white p-12 text-center">
          <h2 className="text-lg font-semibold text-gray-900">Nenhum alerta neste filtro</h2>
          <p className="mt-2 text-gray-600">
            Altere o período, o operador ou o tipo para consultar outras ocorrências.
          </p>
        </div>
      ) : (
        dados && (
          <div className="space-y-3">
            {dados?.itens.map((alerta) => (
              <article
                key={alerta.id}
                className={`rounded-xl border p-5 ${alerta.tipo === "pix_nao_identificado" ? "border-amber-300 bg-amber-50/50 dark:border-amber-700 dark:bg-amber-950/20" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-cyan-300">
                      {TIPOS[alerta.tipo]?.titulo || "Alerta"}
                    </p>
                    <h2 className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
                      {alerta.titulo}
                    </h2>
                    <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                      {alerta.operador} ·{" "}
                      {dataHora(
                        alerta.data || alerta.data_identificacao || alerta.dataidentificacao,
                      )}
                    </p>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-xl font-bold ${alerta.diferenca < 0 ? "text-red-700" : "text-amber-700"}`}
                    >
                      {formatMoneyBRL(
                        alerta.diferenca == null
                          ? (alerta.valor ?? alerta.valor_informado)
                          : Math.abs(alerta.diferenca),
                      )}
                    </p>
                    <p className="text-sm text-gray-600">
                      {alerta.tipo === "pix_nao_identificado"
                        ? "Pix a identificar"
                        : alerta.diferenca == null
                          ? "Total da venda"
                          : alerta.diferenca < 0
                            ? "A menos"
                            : "A mais"}
                    </p>
                  </div>
                </div>
                {alerta.tipo === "pix_nao_identificado" && (
                  <div className="mt-3 space-y-3">
                    <div className="flex flex-wrap gap-2">
                      {alerta.caixa_id && (
                        <span className="text-xs text-slate-600 dark:text-slate-300">
                          Caixa #{alerta.numero_caixa || alerta.caixa_id}
                        </span>
                      )}
                      {urlConsultaVendaPdv(alerta.venda_id) && (
                        <BotaoInteracao
                          tamanho="pequeno"
                          icon={ExternalLink}
                          onClick={() =>
                            window.open(
                              urlConsultaVendaPdv(alerta.venda_id),
                              "_blank",
                              "noopener,noreferrer",
                            )
                          }
                        >
                          Abrir venda {alerta.numero_venda ? `#${alerta.numero_venda}` : "no PDV"}
                        </BotaoInteracao>
                      )}
                    </div>
                    <IdentificacaoPixItem
                      item={pixDoAlerta(alerta)}
                      salvando={salvandoPix}
                      bloqueado={pixDesatualizado || carregando}
                      onSalvar={salvarIdentificacaoPix}
                    />
                  </div>
                )}
                {alerta.diferenca != null && (
                  <div className="mt-4 grid gap-2 rounded-lg bg-gray-50 p-3 text-sm text-gray-700 sm:grid-cols-2">
                    <p>
                      {alerta.tipo === "diferenca_abertura"
                        ? `Fechamento de referência (#${alerta.referencia.numero_caixa})`
                        : "Saldo esperado registrado"}
                      : <strong>{formatMoneyBRL(alerta.valor_referencia)}</strong>
                    </p>
                    <p>
                      {alerta.tipo === "diferenca_abertura"
                        ? "Valor da abertura"
                        : "Dinheiro contado"}
                      : <strong>{formatMoneyBRL(alerta.valor_informado)}</strong>
                    </p>
                  </div>
                )}
                {alerta.origem === "observacao_historica" && (
                  <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
                    Comparação histórica: esta referência foi registrada pelo sistema antigo e pode
                    precisar de revisão.
                  </p>
                )}
                {alerta.tipo === "venda_justificada" && (
                  <p className="mt-3 text-sm text-gray-600">
                    Desconto na venda: {formatMoneyBRL(alerta.desconto)}
                  </p>
                )}
                {alerta.tipo !== "pix_nao_identificado" && (
                  <details className="mt-3 text-sm text-slate-700 dark:text-slate-300">
                    <summary className="cursor-pointer font-medium">
                      {alerta.tipo === "venda_justificada"
                        ? "Ver justificativa"
                        : "Ver observações da operação"}
                    </summary>
                    <p className="mt-2 whitespace-pre-wrap break-words rounded-lg bg-gray-50 p-3">
                      {alerta.observacoes || "Nenhuma observação informada."}
                    </p>
                  </details>
                )}
              </article>
            ))}
          </div>
        )
      )}
      {!carregando && dados?.total > 0 && (
        <div className="flex items-center justify-between gap-3 text-sm text-gray-700">
          <p>
            {dados.total} {dados.total === 1 ? "alerta" : "alertas"} · Página {pagina} de {paginas}
          </p>
          <div className="flex gap-2">
            <BotaoInteracao
              disabled={pagina === 1 || salvandoPix}
              onClick={() => setPagina((atual) => atual - 1)}
            >
              Anterior
            </BotaoInteracao>
            <BotaoInteracao
              disabled={pagina >= paginas || salvandoPix}
              onClick={() => setPagina((atual) => atual + 1)}
            >
              Próxima
            </BotaoInteracao>
          </div>
        </div>
      )}
    </div>
  );
}
