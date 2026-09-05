import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, Receipt, Wallet } from "lucide-react";
import api from "../api";
import { formatMoneyBRL } from "../utils/formatters";

const TIPOS = {
  venda_justificada: { titulo: "Vendas justificadas", icone: Receipt },
  diferenca_abertura: { titulo: "Fechamento × abertura", icone: Wallet },
  diferenca_fechamento: { titulo: "Sobras e faltas", icone: AlertTriangle },
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

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro("");
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
        setDados(data);
        setOperadores(data.operadores);
      })
      .catch((error) => {
        if (!ativo) return;
        setDados(null);
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
    };
  }, [filtros, pagina, atualizacao]);

  const filtrar = (campo, valor) => {
    setFiltros((atual) => ({ ...atual, [campo]: valor }));
    setPagina(1);
  };
  const paginas = Math.max(1, Math.ceil((dados?.total || 0) / 30));

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alertas do gestor</h1>
          <p className="mt-1 text-gray-600">
            Confira justificativas e diferenças de caixa da empresa.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setAtualizacao((valor) => valor + 1)}
          disabled={carregando}
          className="flex items-center gap-2 rounded-lg border bg-white px-4 py-2 text-gray-700 disabled:opacity-50"
        >
          <RefreshCw className="h-4 w-4" /> Atualizar
        </button>
      </div>

      <div className="grid gap-3 rounded-xl border bg-white p-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm font-medium text-gray-700">
          De
          <input
            aria-label="Data inicial"
            type="date"
            value={filtros.data_inicio}
            max={filtros.data_fim}
            onChange={(event) => filtrar("data_inicio", event.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          />
        </label>
        <label className="text-sm font-medium text-gray-700">
          Até
          <input
            aria-label="Data final"
            type="date"
            value={filtros.data_fim}
            min={filtros.data_inicio}
            onChange={(event) => filtrar("data_fim", event.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          />
        </label>
        <label className="text-sm font-medium text-gray-700">
          Tipo de alerta
          <select
            value={filtros.tipo}
            onChange={(event) => filtrar("tipo", event.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          >
            <option value="todos">Todos os tipos</option>
            {Object.entries(TIPOS).map(([tipo, info]) => (
              <option key={tipo} value={tipo}>
                {info.titulo}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-gray-700">
          Operador
          <select
            value={filtros.operador_id}
            onChange={(event) => filtrar("operador_id", event.target.value)}
            className="mt-1 w-full rounded-lg border px-3 py-2"
          >
            <option value="">Todos os operadores</option>
            {operadores.map((operador) => (
              <option key={operador.id} value={operador.id}>
                {operador.nome}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {Object.entries(TIPOS).map(([tipo, { titulo, icone: Icone }]) => (
          <button
            key={tipo}
            type="button"
            onClick={() => filtrar("tipo", filtros.tipo === tipo ? "todos" : tipo)}
            aria-pressed={filtros.tipo === tipo}
            className={`rounded-xl border p-4 text-left ${filtros.tipo === tipo ? "border-blue-500 bg-blue-50" : "bg-white"}`}
          >
            <div className="flex items-center justify-between gap-2 text-sm text-gray-600">
              {titulo}
              <Icone className="h-5 w-5" />
            </div>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {carregando ? "…" : (dados?.resumo[tipo] ?? "—")}
            </p>
          </button>
        ))}
      </div>

      <p className="text-sm text-gray-500">
        Os alertas mostram os valores registrados na operação. Uma diferença é um ponto para
        conferência. Consulte períodos de até 93 dias.
      </p>
      {erro && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          {erro}
        </div>
      )}
      {carregando ? (
        <p role="status" className="py-12 text-center text-gray-600">
          Carregando alertas...
        </p>
      ) : !erro && dados?.itens.length === 0 ? (
        <div className="rounded-xl border bg-white p-12 text-center">
          <h2 className="text-lg font-semibold text-gray-900">Nenhum alerta neste filtro</h2>
          <p className="mt-2 text-gray-600">
            Altere o período, o operador ou o tipo para consultar outras ocorrências.
          </p>
        </div>
      ) : (
        !erro && (
          <div className="space-y-3">
            {dados?.itens.map((alerta) => (
              <article key={alerta.id} className="rounded-xl border bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                      {TIPOS[alerta.tipo].titulo}
                    </p>
                    <h2 className="mt-1 text-lg font-semibold text-gray-900">{alerta.titulo}</h2>
                    <p className="mt-1 text-sm text-gray-600">
                      {alerta.operador} · {dataHora(alerta.data)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-xl font-bold ${alerta.diferenca < 0 ? "text-red-700" : "text-amber-700"}`}
                    >
                      {formatMoneyBRL(
                        alerta.diferenca == null
                          ? alerta.valor_informado
                          : Math.abs(alerta.diferenca),
                      )}
                    </p>
                    <p className="text-sm text-gray-600">
                      {alerta.diferenca == null
                        ? "Total da venda"
                        : alerta.diferenca < 0
                          ? "A menos"
                          : "A mais"}
                    </p>
                  </div>
                </div>
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
                <details className="mt-3 text-sm text-gray-700">
                  <summary className="cursor-pointer font-medium">
                    {alerta.tipo === "venda_justificada"
                      ? "Ver justificativa"
                      : "Ver observações da operação"}
                  </summary>
                  <p className="mt-2 whitespace-pre-wrap break-words rounded-lg bg-gray-50 p-3">
                    {alerta.observacoes || "Nenhuma observação informada."}
                  </p>
                </details>
              </article>
            ))}
          </div>
        )
      )}
      {!carregando && !erro && dados?.total > 0 && (
        <div className="flex items-center justify-between gap-3 text-sm text-gray-700">
          <p>
            {dados.total} {dados.total === 1 ? "alerta" : "alertas"} · Página {pagina} de {paginas}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={pagina === 1}
              onClick={() => setPagina((atual) => atual - 1)}
              className="rounded-lg border bg-white px-3 py-2 disabled:opacity-40"
            >
              Anterior
            </button>
            <button
              type="button"
              disabled={pagina >= paginas}
              onClick={() => setPagina((atual) => atual + 1)}
              className="rounded-lg border bg-white px-3 py-2 disabled:opacity-40"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
