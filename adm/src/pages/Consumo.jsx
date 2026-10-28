import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Lock, Receipt, Tags } from "lucide-react";
import { obter } from "../api/cliente";
import { Aviso, Botao, Carregando, VazioComTexto } from "../components/ui";
import { Selecao } from "../components/formulario";
import { avisosDeCusto, formatarReais, leituraDaDivergencia, ultimosMeses } from "../lib/whatsapp";
import { FaturaModal, FecharMesModal, TarifasModal } from "./ConsumoModais";

export default function Consumo() {
  const meses = useMemo(() => ultimosMeses(12), []);
  const [mes, setMes] = useState(meses[0].value);
  const [versao, setVersao] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const [dados, setDados] = useState(null);
  const [modal, setModal] = useState(null); // { tipo: "tarifas" | "fechar" | "fatura", loja? }

  useEffect(() => {
    let ativo = true;
    (async () => {
      setCarregando(true);
      try {
        const resposta = await obter(`/admin/whatsapp-consumo?mes=${encodeURIComponent(mes)}`);
        if (!ativo) return;
        setDados(resposta);
        setErro("");
      } catch (falha) {
        if (ativo) setErro(falha.message || "Não foi possível carregar o consumo.");
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
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Consumo de WhatsApp</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">
            Mensagens de cada loja, custo estimado com as tarifas da Meta, fechamento do mês para repasse e
            conferência com a fatura real.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Botao variante="secundario" onClick={() => setModal({ tipo: "tarifas" })}>
            <Tags className="h-4 w-4" aria-hidden="true" />
            Tarifas
          </Botao>
          <Botao variante="secundario" onClick={() => setModal({ tipo: "fechar" })}>
            <Lock className="h-4 w-4" aria-hidden="true" />
            Fechar o mês
          </Botao>
        </div>
      </header>

      <div className="max-w-xs">
        <Selecao rotulo="Mês" opcoes={meses} value={mes} onChange={(e) => setMes(e.target.value)} />
      </div>

      {erro ? <Aviso tom="erro">{erro}</Aviso> : null}
      {aviso ? <Aviso tom="ok">{aviso}</Aviso> : null}

      {carregando && !dados ? (
        <Carregando rotulo="Carregando o consumo" />
      ) : dados && lojas.length === 0 ? (
        <VazioComTexto
          icone={Receipt}
          titulo="Nenhuma loja com mensagens neste mês"
          descricao="As lojas aparecem aqui depois do primeiro envio ou recebimento pelo WhatsApp."
        />
      ) : dados ? (
        <>
          <p className="text-sm">
            Total do mês: {dados.totais.enviadas} enviadas · {dados.totais.recebidas} recebidas ·{" "}
            {dados.totais.cobraveis} cobráveis · custo estimado <strong>{formatarReais(dados.totais.custo_estimado)}</strong>{" "}
            · {fechadas} de {lojas.length} loja(s) fechada(s)
          </p>
          {dados.tarifas.length === 0 ? (
            <Aviso tom="atencao">Nenhuma tarifa cadastrada: o custo estimado aparece zerado. Use o botão Tarifas.</Aviso>
          ) : null}

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-400">
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
                    <tr key={loja.loja_id} className="border-b border-slate-100 align-top dark:border-slate-800">
                      <td className="p-3">
                        {fechamento ? (
                          <Botao variante="secundario" onClick={() => setModal({ tipo: "fatura", loja })}>
                            <Receipt className="h-4 w-4" aria-hidden="true" />
                            Fatura da Meta
                          </Botao>
                        ) : (
                          <span className="text-xs text-slate-600 dark:text-slate-400">Mês em aberto</span>
                        )}
                      </td>
                      <td className="p-3 font-medium">
                        {loja.loja_nome}
                        {avisos.map((texto) => (
                          <span
                            key={texto}
                            className="mt-1 flex items-start gap-1 text-xs font-normal text-amber-800 dark:text-amber-300"
                          >
                            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-none" aria-hidden="true" />
                            {texto}
                          </span>
                        ))}
                      </td>
                      <td className="p-3">{loja.totais.enviadas}</td>
                      <td className="p-3">{loja.totais.recebidas}</td>
                      <td className="p-3">{loja.totais.falhas}</td>
                      <td className="p-3">{loja.totais.cobraveis}</td>
                      <td className="p-3">
                        {formatarReais(fechamento ? fechamento.custo_estimado : loja.custo_estimado)}
                      </td>
                      <td className="p-3">
                        {fechamento ? (
                          <>
                            {formatarReais(fechamento.valor_repasse)}
                            <span className="block text-xs text-slate-600 dark:text-slate-400">
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
                              <CheckCircle2 className="mt-0.5 h-4 w-4 flex-none text-emerald-600" aria-hidden="true" />
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
          aoFechar={() => setModal(null)}
          aoAtualizar={(itens) => {
            setDados((atual) => ({ ...atual, tarifas: itens }));
            setAviso("Tarifa cadastrada. Ela vale nas próximas mensagens e no fechamento do mês.");
          }}
        />
      ) : null}
      {modal?.tipo === "fechar" ? (
        <FecharMesModal
          mes={mes}
          margemPadrao={dados?.margem_padrao}
          aoFechar={() => setModal(null)}
          aoFechado={(resultado) => {
            setModal(null);
            setAviso(
              `Mês ${resultado.mes}: ${resultado.fechados_agora} loja(s) fechada(s), ${resultado.ja_fechados} já estavam fechadas.`,
            );
            recarregar();
          }}
        />
      ) : null}
      {modal?.tipo === "fatura" ? (
        <FaturaModal
          loja={modal.loja}
          aoFechar={() => setModal(null)}
          aoSalvo={() => {
            setModal(null);
            setAviso("Fatura registrada.");
            recarregar();
          }}
        />
      ) : null}
    </div>
  );
}
