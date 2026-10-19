import { useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  History,
  RotateCcw,
} from "lucide-react";
import { toast } from "react-hot-toast";
import api from "../../api";
import { formatMoneyBRL } from "../../utils/formatters";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../v2/EstadoVazio/EstadoVazio";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

const POR_PAGINA = 10;
const FORMAS_PAGAMENTO = {
  dinheiro: "Dinheiro",
  pix: "Pix",
  debito: "Cartão de débito",
  credito: "Cartão de crédito",
  transferencia: "Transferência",
};

function formatarData(value) {
  if (!value) return "—";
  const data = new Date(value);
  return Number.isNaN(data.getTime()) ? "—" : data.toLocaleString("pt-BR");
}

function mensagemErro(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return (
      detail
        .map((item) => item.msg)
        .filter(Boolean)
        .join(" · ") || fallback
    );
  return fallback;
}

export default function ClienteBaixasLotePanel({ clienteId, onAtualizado }) {
  const [itens, setItens] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [versao, setVersao] = useState(0);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState("");
  const [expandido, setExpandido] = useState(null);
  const [loteEstorno, setLoteEstorno] = useState(null);
  const [motivo, setMotivo] = useState("");
  const [erroEstorno, setErroEstorno] = useState("");
  const [estornando, setEstornando] = useState(false);
  const envioEmAndamento = useRef(false);

  useEffect(() => {
    let ativo = true;
    setLoading(true);
    setErro("");
    api
      .get(`/clientes/${clienteId}/baixas-lote`, { params: { page, per_page: POR_PAGINA } })
      .then(({ data }) => {
        if (!ativo) return;
        setItens(data.itens || []);
        setTotal(data.total || 0);
      })
      .catch((error) => {
        if (ativo) setErro(mensagemErro(error, "Não foi possível carregar as baixas em lote."));
      })
      .finally(() => {
        if (ativo) setLoading(false);
      });
    return () => {
      ativo = false;
    };
  }, [clienteId, page, versao]);

  function abrirEstorno(lote) {
    setLoteEstorno(lote);
    setMotivo("");
    setErroEstorno("");
  }

  function fecharEstorno() {
    if (!envioEmAndamento.current) setLoteEstorno(null);
  }

  async function estornar() {
    if (envioEmAndamento.current || !loteEstorno) return;
    const motivoLimpo = motivo.trim();
    if (motivoLimpo.length < 5) {
      setErroEstorno("Descreva o motivo com pelo menos 5 caracteres.");
      return;
    }
    envioEmAndamento.current = true;
    setEstornando(true);
    setErroEstorno("");
    try {
      await api.post(`/clientes/${clienteId}/baixas-lote/${loteEstorno.id}/estornar`, {
        motivo: motivoLimpo,
      });
    } catch (error) {
      setErroEstorno(mensagemErro(error, "Não foi possível estornar a baixa. Tente novamente."));
      return;
    } finally {
      envioEmAndamento.current = false;
      setEstornando(false);
    }
    setLoteEstorno(null);
    setVersao((anterior) => anterior + 1);
    toast.success("Baixa em lote estornada. Os valores podem ser corrigidos.");
    try {
      await onAtualizado?.();
    } catch {
      toast.error("O estorno foi concluído. Atualize a tela para consultar os saldos.");
    }
  }

  const totalPaginas = Math.max(1, Math.ceil(total / POR_PAGINA));

  return (
    <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
      <div>
        <h3 className="v2-titulo-secao flex items-center gap-2">
          <History className="h-5 w-5" aria-hidden="true" />
          Baixas em lote
        </h3>
        <p className="v2-texto-ajuda mt-1">
          Cada pagamento aparece uma vez. Nos detalhes, consulte como ele foi distribuído entre as
          vendas.
        </p>
      </div>

      {loading ? (
        <p role="status" className="py-8 text-center text-sm text-slate-500 dark:text-slate-400">
          Carregando baixas em lote...
        </p>
      ) : erro ? (
        <div className="space-y-3">
          <p role="alert" className="text-sm text-red-700 dark:text-red-400">
            {erro}
          </p>
          <BotaoInteracao onClick={() => setVersao((anterior) => anterior + 1)} tamanho="pequeno">
            Tentar novamente
          </BotaoInteracao>
        </div>
      ) : itens.length === 0 ? (
        <EstadoVazio icone={History} titulo="Nenhuma baixa em lote neste histórico" />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-700 dark:text-slate-200">
              <thead className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <tr>
                  <th className="px-3 py-3">Ações</th>
                  <th className="px-3 py-3">Lançamento</th>
                  <th className="px-3 py-3">Pagamento</th>
                  <th className="px-3 py-3 text-right">Valor</th>
                  <th className="px-3 py-3">Situação</th>
                </tr>
              </thead>
              {itens.map((lote) => {
                const estornado = lote.status === "estornado";
                const aberto = expandido === lote.id;
                return (
                  <tbody key={lote.id} className="border-b border-slate-100 dark:border-slate-800">
                    <tr>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-2">
                          <BotaoInteracao
                            tamanho="pequeno"
                            icon={aberto ? ChevronUp : ChevronDown}
                            aria-expanded={aberto}
                            onClick={() => setExpandido(aberto ? null : lote.id)}
                          >
                            Detalhes
                          </BotaoInteracao>
                          {!estornado ? (
                            <BotaoInteracao
                              tamanho="pequeno"
                              icon={RotateCcw}
                              onClick={() => abrirEstorno(lote)}
                            >
                              Estornar
                            </BotaoInteracao>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <p className="font-semibold">Baixa #{lote.id}</p>
                        <p>{formatarData(lote.data)}</p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {lote.usuario_nome || "Usuário não informado"}
                        </p>
                      </td>
                      <td className="px-3 py-3">
                        {FORMAS_PAGAMENTO[lote.forma_pagamento] || lote.forma_pagamento}
                        {lote.numero_transacao ? (
                          <p className="break-all text-xs">Transação: {lote.numero_transacao}</p>
                        ) : null}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 text-right font-semibold">
                        {formatMoneyBRL(lote.valor_total)}
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={
                            estornado
                              ? "text-red-700 dark:text-red-400"
                              : "text-emerald-700 dark:text-emerald-400"
                          }
                        >
                          {estornado ? "Estornado" : "Confirmado"}
                        </span>
                      </td>
                    </tr>
                    {aberto ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="space-y-3 bg-slate-50 px-4 py-4 dark:bg-slate-950/40"
                        >
                          <p className="font-medium">Distribuição do pagamento</p>
                          <ul className="space-y-1">
                            {(lote.vendas || []).map((venda) => (
                              <li key={venda.venda_id} className="flex justify-between gap-4">
                                <span>Venda {venda.numero_venda || `#${venda.venda_id}`}</span>
                                <span>{formatMoneyBRL(venda.valor_baixado)}</span>
                              </li>
                            ))}
                          </ul>
                          {lote.observacoes ? (
                            <p className="whitespace-pre-wrap">Observações: {lote.observacoes}</p>
                          ) : null}
                          {estornado ? (
                            <div className="space-y-1 text-red-800 dark:text-red-300">
                              <p>
                                Estornado em {formatarData(lote.estornado_em)}
                                {lote.estornado_por_nome ? ` por ${lote.estornado_por_nome}` : ""}.
                              </p>
                              <p className="whitespace-pre-wrap">
                                Motivo: {lote.motivo_estorno || "Não informado"}
                              </p>
                            </div>
                          ) : null}
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                );
              })}
            </table>
          </div>
          {totalPaginas > 1 ? (
            <div className="flex items-center justify-end gap-3 text-sm text-slate-600 dark:text-slate-300">
              <BotaoInteracao
                icon={ChevronLeft}
                tamanho="pequeno"
                disabled={page <= 1}
                onClick={() => setPage((anterior) => anterior - 1)}
              >
                Anterior
              </BotaoInteracao>
              <span>
                Página {page} de {totalPaginas}
              </span>
              <BotaoInteracao
                icon={ChevronRight}
                tamanho="pequeno"
                disabled={page >= totalPaginas}
                onClick={() => setPage((anterior) => anterior + 1)}
              >
                Próxima
              </BotaoInteracao>
            </div>
          ) : null}
        </>
      )}
      <p className="v2-texto-ajuda">
        Baixas anteriores a este histórico precisam de conferência para serem vinculadas.
      </p>

      {loteEstorno ? (
        <ModalPadrao
          titulo={`Estornar baixa #${loteEstorno.id}`}
          onFechar={fecharEstorno}
          tamanho="pequena"
          rodape={
            <>
              <BotaoCancelar disabled={estornando} onClick={fecharEstorno} />
              <BotaoInteracao icon={RotateCcw} loading={estornando} onClick={estornar}>
                Confirmar estorno
              </BotaoInteracao>
            </>
          }
        >
          <div className="space-y-4">
            <p className="text-sm text-slate-700 dark:text-slate-200">
              O estorno de {formatMoneyBRL(loteEstorno.valor_total)} reverte os efeitos vinculados a
              este pagamento e libera os valores para correção.
            </p>
            <p className="v2-texto-ajuda">
              É necessário ter um caixa aberto para estornar. O histórico do caixa original será
              preservado.
            </p>
            <InputTextoLongo
              id={`motivo-estorno-${loteEstorno.id}`}
              label="Motivo do estorno"
              required
              maxLength={500}
              value={motivo}
              onChange={setMotivo}
              disabled={estornando}
              help="Explique o que precisa ser corrigido (5 a 500 caracteres)."
            />
            {erroEstorno ? (
              <p
                role="alert"
                className="whitespace-pre-wrap text-sm text-red-700 dark:text-red-400"
              >
                {erroEstorno}
              </p>
            ) : null}
          </div>
        </ModalPadrao>
      ) : null}
    </section>
  );
}
