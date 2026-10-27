import {
  AlertTriangle,
  ArrowDownToLine,
  ArrowUpFromLine,
  CircleDollarSign,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import api from "../../api";
import CartaoIndicador from "../../components/v2/CartaoIndicador/CartaoIndicador";
import CreditosSecao from "./CreditosSecao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import {
  ROTULO_DA_CATEGORIA,
  ROTULO_DA_ORIGEM,
  ROTULO_DO_ESTADO,
  avisosDeCusto,
  formatarQuando,
  formatarReais,
  rotulo,
  ultimosMeses,
} from "../../utils/consumoWhatsapp";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

function ListaDeTotais({ titulo, dados, tabela }) {
  const itens = Object.entries(dados || {});
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <h2 className="text-sm font-bold text-slate-950 dark:text-slate-100">{titulo}</h2>
      {itens.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Nada neste mês.</p>
      ) : (
        <ul className="mt-2 space-y-1 text-sm text-slate-800 dark:text-slate-200">
          {itens.map(([chave, quantidade]) => (
            <li key={chave} className="flex justify-between gap-3">
              <span>{rotulo(tabela, chave)}</span>
              <span className="font-semibold">{quantidade}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// Consumo de mensagens da loja no mês: quantas saíram, quantas custam e quanto isso representa.
export default function ConsumoWhatsAppPage() {
  const meses = useMemo(() => ultimosMeses(12), []);
  const [mes, setMes] = useState(meses[0].value);
  // Um único loading do início até os dados aparecerem.
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [resumo, setResumo] = useState(null);
  const [mensagens, setMensagens] = useState([]);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const [resumoResposta, mensagensResposta] = await Promise.all([
          api.get("/whatsapp/ledger/resumo", { params: { mes } }),
          api.get("/whatsapp/ledger/mensagens", { params: { mes, limite: 100 } }),
        ]);
        if (!ativo) return;
        setResumo(resumoResposta.data);
        setMensagens(mensagensResposta.data.items || []);
        setErro("");
      } catch (error) {
        if (ativo) setErro(mensagemDeErro(error, "Não foi possível carregar o consumo."));
      } finally {
        if (ativo) setCarregando(false);
      }
    })();
    return () => {
      ativo = false;
    };
  }, [mes]);

  const totais = resumo?.totais;
  const avisos = avisosDeCusto(totais);

  return (
    <div className="mx-auto w-full max-w-5xl space-y-4 p-4 sm:p-6">
      <header>
        <LinkPadrao to="/crm/whatsapp">← Voltar ao WhatsApp oficial</LinkPadrao>
        <h1 className="mt-3 text-2xl font-bold text-slate-950 dark:text-slate-100 sm:text-3xl">
          Consumo de mensagens
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Veja quantas mensagens saíram e chegaram pelo WhatsApp oficial e quais têm custo na Meta.
          O custo é uma estimativa feita com as tarifas da Meta; o valor final é o da fatura.
        </p>
      </header>

      <CreditosSecao />

      <div className="max-w-xs">
        <InputCombobox id="consumo-mes" label="Mês" value={mes} opcoes={meses} onChange={setMes} />
      </div>

      {erro ? (
        <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}

      {carregando ? (
        <div role="status" aria-label="Carregando o consumo" className="grid gap-3 sm:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-28 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
            />
          ))}
        </div>
      ) : resumo ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <CartaoIndicador titulo="Enviadas" icone={ArrowUpFromLine} tom="informativo">
              <p className="m-0 text-2xl font-bold">{totais.enviadas}</p>
            </CartaoIndicador>
            <CartaoIndicador titulo="Recebidas" icone={ArrowDownToLine} tom="informativo">
              <p className="m-0 text-2xl font-bold">{totais.recebidas}</p>
            </CartaoIndicador>
            <CartaoIndicador
              titulo="Falharam"
              icone={XCircle}
              tom={totais.falhas > 0 ? "atencao" : "neutro"}
              detalhe={totais.falhas > 0 ? "Veja o motivo na lista abaixo." : undefined}
            >
              <p className="m-0 text-2xl font-bold">{totais.falhas}</p>
            </CartaoIndicador>
            <CartaoIndicador
              titulo="Custo estimado"
              icone={CircleDollarSign}
              tom="neutro"
              detalhe={`${totais.cobraveis} mensagem(ns) cobrável(is)`}
            >
              <p className="m-0 text-2xl font-bold">{formatarReais(resumo.custo_estimado)}</p>
            </CartaoIndicador>
          </div>

          {avisos.map((aviso) => (
            <p
              key={aviso}
              className="flex items-start gap-2 text-sm font-medium text-amber-800 dark:text-amber-300"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
              {aviso}
            </p>
          ))}

          <div className="grid gap-3 md:grid-cols-2">
            <ListaDeTotais
              titulo="Cobráveis por categoria"
              dados={resumo.cobraveis_por_categoria}
              tabela={ROTULO_DA_CATEGORIA}
            />
            <ListaDeTotais
              titulo="Enviadas por origem"
              dados={resumo.enviadas_por_origem}
              tabela={ROTULO_DA_ORIGEM}
            />
          </div>

          <section aria-labelledby="consumo-mensagens">
            <h2
              id="consumo-mensagens"
              className="mb-2 text-base font-bold text-slate-950 dark:text-slate-100"
            >
              Últimas mensagens
            </h2>
            {mensagens.length === 0 ? (
              <EstadoVazio
                icone={ArrowUpFromLine}
                titulo="Nenhuma mensagem neste mês"
                descricao="As mensagens aparecem aqui depois que o WhatsApp oficial for ativado."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                      <th className="py-2 pr-3 font-semibold">Quando</th>
                      <th className="py-2 pr-3 font-semibold">Sentido</th>
                      <th className="py-2 pr-3 font-semibold">Origem</th>
                      <th className="py-2 pr-3 font-semibold">Estado</th>
                      <th className="py-2 pr-3 font-semibold">Cobrança</th>
                      <th className="py-2 font-semibold">Observação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mensagens.map((item) => (
                      <tr
                        key={item.id}
                        className="border-b border-slate-100 align-top dark:border-slate-800"
                      >
                        <td className="whitespace-nowrap py-2 pr-3">
                          {formatarQuando(item.quando)}
                        </td>
                        <td className="py-2 pr-3">
                          {item.direcao === "enviada" ? "Enviada" : "Recebida"}
                        </td>
                        <td className="py-2 pr-3">{rotulo(ROTULO_DA_ORIGEM, item.origem)}</td>
                        <td className="py-2 pr-3">{rotulo(ROTULO_DO_ESTADO, item.estado)}</td>
                        <td className="py-2 pr-3">
                          {item.cobravel === true
                            ? `Cobrável · ${rotulo(ROTULO_DA_CATEGORIA, item.categoria_cobranca || "sem_categoria")}`
                            : item.cobravel === false
                              ? "Sem custo"
                              : "—"}
                        </td>
                        <td className="py-2">
                          {item.erro ||
                            (item.modelo ? `Modelo: ${item.modelo}` : "") ||
                            (item.dentro_da_janela === true ? "Dentro das 24 horas" : "")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
