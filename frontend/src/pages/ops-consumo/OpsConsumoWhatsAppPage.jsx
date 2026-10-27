import { AlertTriangle, CheckCircle2, Lock, Receipt, Tags } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import api from "../../platformApi";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import {
  avisosDeCusto,
  formatarReais,
  leituraDaDivergencia,
  ultimosMeses,
} from "../../utils/consumoWhatsapp";
import { FaturaModal, FecharMesModal, TarifasModal } from "./OpsConsumoModais";

function mensagemDeErro(error, padrao) {
  const detalhe = error?.response?.data?.detail;
  return typeof detalhe === "string" ? detalhe : padrao;
}

export default function OpsConsumoWhatsAppPage() {
  const meses = useMemo(() => ultimosMeses(12), []);
  const [mes, setMes] = useState(meses[0].value);
  const [versao, setVersao] = useState(0);
  // Um único loading do início até os dados aparecerem.
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [dados, setDados] = useState(null);
  const [modal, setModal] = useState(null); // { tipo: "tarifas" | "fechar" | "fatura", loja? }

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const { data } = await api.get("/admin/whatsapp-consumo", { params: { mes } });
        if (!ativo) return;
        setDados(data);
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
  }, [mes, versao]);

  const recarregar = () => setVersao((atual) => atual + 1);
  const lojas = dados?.lojas || [];
  const fechadas = lojas.filter((loja) => loja.fechamento).length;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 p-4 sm:p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="m-0 text-xs font-bold uppercase tracking-[0.18em] text-teal-700 dark:text-teal-300">
            Plataforma
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950 dark:text-slate-100 sm:text-3xl">
            Consumo de WhatsApp
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
            Mensagens de cada loja, custo estimado com as tarifas da Meta, fechamento do mês para
            repasse e conferência com a fatura real.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <BotaoInteracao icon={Tags} onClick={() => setModal({ tipo: "tarifas" })}>
            Tarifas
          </BotaoInteracao>
          <BotaoInteracao icon={Lock} onClick={() => setModal({ tipo: "fechar" })}>
            Fechar o mês
          </BotaoInteracao>
        </div>
      </header>

      <div className="max-w-xs">
        <InputCombobox
          id="ops-consumo-mes"
          label="Mês"
          value={mes}
          opcoes={meses}
          onChange={setMes}
        />
      </div>

      {erro ? (
        <p role="alert" className="text-sm font-medium text-red-700 dark:text-red-300">
          {erro}
        </p>
      ) : null}

      {carregando ? (
        <div
          role="status"
          aria-label="Carregando o consumo"
          className="h-40 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900"
        />
      ) : dados && lojas.length === 0 ? (
        <EstadoVazio
          icone={Receipt}
          titulo="Nenhuma loja com mensagens neste mês"
          descricao="As lojas aparecem aqui depois do primeiro envio ou recebimento pelo WhatsApp."
        />
      ) : dados ? (
        <>
          <p className="text-sm text-slate-700 dark:text-slate-200">
            Total do mês: {dados.totais.enviadas} enviadas · {dados.totais.recebidas} recebidas ·{" "}
            {dados.totais.cobraveis} cobráveis · custo estimado{" "}
            <strong>{formatarReais(dados.totais.custo_estimado)}</strong> · {fechadas} de{" "}
            {lojas.length} loja(s) fechada(s)
          </p>
          {dados.tarifas.length === 0 ? (
            <p className="flex items-start gap-2 text-sm font-medium text-amber-800 dark:text-amber-300">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
              Nenhuma tarifa cadastrada: o custo estimado aparece zerado. Use o botão Tarifas.
            </p>
          ) : null}

          <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-700">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                  <th className="p-3 font-semibold">Ações</th>
                  <th className="p-3 font-semibold">Loja</th>
                  <th className="p-3 font-semibold">Enviadas</th>
                  <th className="p-3 font-semibold">Recebidas</th>
                  <th className="p-3 font-semibold">Falhas</th>
                  <th className="p-3 font-semibold">Cobráveis</th>
                  <th className="p-3 font-semibold">Custo estimado</th>
                  <th className="p-3 font-semibold">Repasse</th>
                  <th className="p-3 font-semibold">Conferência</th>
                </tr>
              </thead>
              <tbody>
                {lojas.map((loja) => {
                  const fechamento = loja.fechamento;
                  const leitura = fechamento ? leituraDaDivergencia(fechamento.divergencia) : null;
                  const avisos = avisosDeCusto(loja.totais);
                  return (
                    <tr
                      key={loja.loja_id}
                      className="border-b border-slate-100 align-top dark:border-slate-800"
                    >
                      <td className="p-3">
                        {fechamento ? (
                          <BotaoInteracao
                            icon={Receipt}
                            tamanho="pequeno"
                            onClick={() => setModal({ tipo: "fatura", loja })}
                          >
                            Fatura da Meta
                          </BotaoInteracao>
                        ) : (
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            Mês em aberto
                          </span>
                        )}
                      </td>
                      <td className="p-3 font-medium">
                        {loja.loja_nome}
                        {avisos.map((aviso) => (
                          <span
                            key={aviso}
                            className="mt-1 flex items-start gap-1 text-xs font-normal text-amber-800 dark:text-amber-300"
                          >
                            <AlertTriangle
                              className="mt-0.5 h-3.5 w-3.5 flex-none"
                              aria-hidden="true"
                            />
                            {aviso}
                          </span>
                        ))}
                      </td>
                      <td className="p-3">{loja.totais.enviadas}</td>
                      <td className="p-3">{loja.totais.recebidas}</td>
                      <td className="p-3">{loja.totais.falhas}</td>
                      <td className="p-3">{loja.totais.cobraveis}</td>
                      <td className="p-3">
                        {formatarReais(
                          fechamento ? fechamento.custo_estimado : loja.custo_estimado,
                        )}
                      </td>
                      <td className="p-3">
                        {fechamento ? (
                          <>
                            {formatarReais(fechamento.valor_repasse)}
                            <span className="block text-xs text-slate-500 dark:text-slate-400">
                              margem {fechamento.margem_percentual}%
                            </span>
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="p-3">
                        {leitura ? (
                          <span className="flex items-start gap-1">
                            {leitura.tom === "ok" ? (
                              <CheckCircle2
                                className="mt-0.5 h-4 w-4 flex-none text-emerald-600"
                                aria-hidden="true"
                              />
                            ) : null}
                            {leitura.texto}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      ) : null}

      {modal?.tipo === "tarifas" ? (
        <TarifasModal
          tarifas={dados?.tarifas || []}
          onFechar={() => setModal(null)}
          onAtualizado={(itens) => {
            setDados((atual) => ({ ...atual, tarifas: itens }));
            toast.success(
              "Tarifa cadastrada. Ela vale nas próximas mensagens e no fechamento do mês.",
            );
          }}
        />
      ) : null}
      {modal?.tipo === "fechar" ? (
        <FecharMesModal
          mes={mes}
          margemPadrao={dados?.margem_padrao}
          onFechar={() => setModal(null)}
          onFechado={(resultado) => {
            setModal(null);
            toast.success(
              `Mês ${resultado.mes}: ${resultado.fechados_agora} loja(s) fechada(s), ${resultado.ja_fechados} já estavam fechadas.`,
            );
            recarregar();
          }}
        />
      ) : null}
      {modal?.tipo === "fatura" ? (
        <FaturaModal
          loja={modal.loja}
          onFechar={() => setModal(null)}
          onSalvo={() => {
            setModal(null);
            toast.success("Fatura registrada.");
            recarregar();
          }}
        />
      ) : null}
    </div>
  );
}
