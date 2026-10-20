import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Pencil,
  RefreshCw,
  RotateCcw,
  Settings,
} from "lucide-react";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import InputRadio from "../v2/InputRadio/InputRadio";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";
import SeletorOpcoes from "../v2/SeletorOpcoes/SeletorOpcoes";
import { useEscapeToClose } from "../../utils/modalEscape";
import {
  IFOOD_MODALIDADES,
  IFOOD_PENDING_LABELS,
  moedaIfood,
  percentualIfood,
  valorConhecido,
} from "./ifoodPresentation";
import IfoodStatus from "./IfoodStatus";
import useIfoodSimulacaoPreco from "./useIfoodSimulacaoPreco";

const PARCELAS = [
  ["price", "Receita por unidade"],
  ["cost", "Custo do produto no ERP"],
  ["commission", "Comissão da modalidade"],
  ["payment_fee", "Taxa de pagamento"],
  ["tax", "Tributos estimados"],
  ["additional_cost", "Despesa adicional por unidade"],
];

export default function IfoodProdutoDetalhes({
  item,
  modalidade,
  onModalidade,
  onFechar,
  onEditar,
  onConfigurar,
  onPrecoAplicado,
  onSalvandoPreco,
  podeEditar,
  podeConfigurar,
}) {
  const c = useIfoodSimulacaoPreco(item, { podeEditar, onAplicado: onPrecoAplicado });
  useEffect(() => {
    onSalvandoPreco?.(c.salvando);
    return () => onSalvandoPreco?.(false);
  }, [c.salvando, onSalvandoPreco]);
  const [memoriaAberta, setMemoriaAberta] = useState(false);
  useEscapeToClose({ onClose: onFechar, disabled: c.salvando });
  const margem = c.resultado?.margins?.[modalidade];
  const negativa = margem?.calculated && Number(margem.contribution) < 0;
  const fechar = () => {
    if (!c.salvando) onFechar();
  };

  return (
    <ModalPadrao
      titulo={`Calculadora de preço · ${item.name || "Produto"}`}
      tamanho="ampla"
      onFechar={fechar}
      rodape={
        <div className="flex flex-wrap justify-end gap-2">
          <BotaoCancelar disabled={c.salvando} onClick={fechar}>
            Fechar
          </BotaoCancelar>
          {podeEditar ? (
            <BotaoInteracao icon={Pencil} disabled={c.salvando} onClick={onEditar}>
              Editar cadastro completo
            </BotaoInteracao>
          ) : null}
          {podeEditar && c.alterado ? (
            <BotaoSalva type="button" disabled={!c.pronta} loading={c.salvando} onClick={c.aplicar}>
              Aplicar preço ao produto
            </BotaoSalva>
          ) : null}
        </div>
      }
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="v2-texto-ajuda">SKU {item.sku || "não informado"}</p>
          <IfoodStatus status={c.salvo.status} />
        </div>

        <div className="grid items-start gap-5 md:grid-cols-2">
          <div className="min-w-0 space-y-4">
            <section className="rounded-xl bg-slate-50 p-4 dark:bg-slate-950/40">
              <h3 className="v2-rotulo">Oferta atual no cadastro</h3>
              <div className="mt-2 grid grid-cols-2 gap-3">
                <div>
                  <p className="v2-texto-ajuda">Preço vigente iFood</p>
                  <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
                    {moedaIfood(c.salvo.effective_price)}
                  </p>
                  <p className="v2-texto-ajuda">
                    {c.salvo.promotion_active
                      ? "Promoção vigente"
                      : c.salvo.price_source === "especifico"
                        ? "Preço específico do produto"
                        : "Regra geral da loja"}
                  </p>
                </div>
                <div>
                  <p className="v2-texto-ajuda">Preço regular salvo</p>
                  <p className="v2-texto mt-1">{moedaIfood(c.salvo.regular_price)}</p>
                </div>
              </div>
              {c.erroOferta ? (
                <div role="alert" className="mt-3 space-y-2 text-sm text-red-700 dark:text-red-300">
                  <p>{c.erroOferta}</p>
                  <BotaoInteracao icon={RefreshCw} tamanho="pequeno" onClick={c.repetir}>
                    Tentar novamente
                  </BotaoInteracao>
                </div>
              ) : null}
            </section>

            <section className="space-y-4 rounded-xl border border-blue-200 p-4 dark:border-blue-500/30">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="v2-titulo-secao">Experimente outro preço</h3>
                <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-800 dark:bg-blue-500/15 dark:text-blue-200">
                  {c.alterado ? "Simulação não salva" : "Simulação dos valores atuais"}
                </span>
              </div>
              <InputRadio
                name={`ifood-simulacao-preco-${item.product_id}`}
                label="Preço usado na simulação"
                value={c.modo}
                disabled={c.salvando}
                onChange={c.alterarModo}
                opcoes={[
                  { value: "regra_loja", label: "Seguir regra da loja" },
                  { value: "especifico", label: "Preço específico" },
                ]}
                help="Os custos, o estoque e as promoções continuam vindo do cadastro e das regras da loja."
              />
              {c.modo === "especifico" ? (
                <InputMoeda
                  id={`ifood-simulacao-valor-${item.product_id}`}
                  label="Preço específico para simular"
                  disabled={c.salvando}
                  value={c.valor}
                  onChange={c.alterarValor}
                  help="Altere livremente para comparar a contribuição. Digitar não salva no produto."
                />
              ) : (
                <p className="v2-texto-ajuda">
                  Usa o preço normal do ERP com o acréscimo configurado para esta loja. Aplicar esta
                  opção remove o preço específico do iFood.
                </p>
              )}
              <SeletorOpcoes
                opcoes={IFOOD_MODALIDADES}
                rotulo="Simular custos"
                valorSelecionado={modalidade}
                aoSelecionar={onModalidade}
              />
              <BotaoInteracao
                icon={RotateCcw}
                tamanho="pequeno"
                disabled={c.salvando}
                onClick={c.restaurar}
              >
                Restaurar preço salvo
              </BotaoInteracao>
              {!podeEditar ? (
                <p className="v2-texto-ajuda">
                  Você pode simular preços. Para aplicá-los, é necessária permissão de editar
                  produtos.
                </p>
              ) : null}
              {c.sucesso ? (
                <p role="status" className="text-sm text-emerald-700 dark:text-emerald-300">
                  {c.sucesso}
                </p>
              ) : null}
              {c.erroSalvar ? (
                <p role="alert" className="text-sm text-red-700 dark:text-red-300">
                  {c.erroSalvar}
                </p>
              ) : null}
            </section>
          </div>
          <div
            className="min-w-0 space-y-4"
            aria-live="polite"
            aria-busy={!c.pronta && !c.erroSimulacao && !c.erroOferta}
          >
            {c.resultado && !c.pronta && !c.erroOferta ? (
              <div
                role={c.erroSimulacao ? "alert" : "status"}
                className="space-y-2 text-sm text-slate-600 dark:text-slate-300"
              >
                <p>
                  {c.erroSimulacao ||
                    (c.salvando ? "Salvando preço…" : "Atualizando preço, margem e pendências…")}
                </p>
                {c.erroSimulacao ? (
                  <BotaoInteracao icon={RefreshCw} tamanho="pequeno" onClick={c.repetir}>
                    Tentar novamente
                  </BotaoInteracao>
                ) : null}
              </div>
            ) : null}
            {!c.resultado ? (
              c.erroSimulacao ? (
                <div
                  role="alert"
                  className="space-y-2 rounded-xl bg-red-50 p-4 text-sm text-red-800 dark:bg-red-500/10 dark:text-red-200"
                >
                  <p>{c.erroSimulacao}</p>
                  <BotaoInteracao icon={RefreshCw} tamanho="pequeno" onClick={c.repetir}>
                    Tentar novamente
                  </BotaoInteracao>
                </div>
              ) : (
                <p
                  role="status"
                  className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-300"
                >
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  Calculando o preço e as pendências…
                </p>
              )
            ) : (
              <>
                <section
                  className="rounded-xl border border-slate-200 p-4 dark:border-slate-700"
                  aria-label="Resultado da simulação"
                >
                  <p className="v2-rotulo">Resultado da simulação</p>
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                        {moedaIfood(c.resultado.effective_price)}
                      </p>
                      <p className="v2-texto-ajuda">
                        Preço regular simulado: {moedaIfood(c.resultado.regular_price)}
                      </p>
                    </div>
                    <IfoodStatus status={c.resultado.status} />
                  </div>
                  {c.resultado.promotion_active ? (
                    <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
                      A promoção do cadastro está vigente e prevalece no preço e na margem desta
                      simulação. Aplicar o preço regular não altera essa promoção.
                    </p>
                  ) : c.salvo.promotion_active ? (
                    <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200">
                      A promoção salva não foi alterada. Confira as pendências: ela pode não ser
                      válida com o preço regular simulado.
                    </p>
                  ) : null}
                </section>

                <section className="space-y-3">
                  <h3 className="v2-titulo-secao">Contribuição estimada por unidade</h3>
                  {margem ? (
                    <>
                      {margem.calculated ? (
                        <div
                          className={`rounded-xl p-4 ${margem.below_target || negativa ? "bg-amber-50 text-amber-900 dark:bg-amber-500/10 dark:text-amber-200" : "bg-emerald-50 text-emerald-900 dark:bg-emerald-500/10 dark:text-emerald-200"}`}
                        >
                          <p className="font-semibold">
                            Contribuição: {moedaIfood(margem.contribution)} ·{" "}
                            {percentualIfood(margem.percent)}
                          </p>
                          {negativa ? (
                            <p className="mt-1 text-xs">Contribuição negativa nesta simulação.</p>
                          ) : null}
                          {valorConhecido(margem.target_percent) ? (
                            <p className="mt-1 text-xs">
                              Meta da loja: {percentualIfood(margem.target_percent)}
                              {margem.below_target ? " · abaixo da meta" : ""}
                            </p>
                          ) : null}
                        </div>
                      ) : (
                        <div
                          role="status"
                          className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200"
                        >
                          <p className="font-semibold">Margem não calculada</p>
                          <p className="mt-1">
                            {margem.missing?.length
                              ? `Falta informar: ${margem.missing.join(", ")}.`
                              : "Confira o preço, o custo e as taxas da loja."}
                          </p>
                        </div>
                      )}
                      <BotaoInteracao
                        icon={memoriaAberta ? ChevronUp : ChevronDown}
                        tamanho="pequeno"
                        aria-expanded={memoriaAberta}
                        aria-controls={`ifood-memoria-${item.product_id}`}
                        onClick={() => setMemoriaAberta((aberta) => !aberta)}
                      >
                        {memoriaAberta ? "Ocultar memória de cálculo" : "Ver memória de cálculo"}
                      </BotaoInteracao>
                      {memoriaAberta ? (
                        <dl
                          id={`ifood-memoria-${item.product_id}`}
                          className="divide-y divide-slate-100 dark:divide-slate-800"
                        >
                          {PARCELAS.map(([key, label]) => (
                            <div key={key} className="flex justify-between gap-3 py-2 text-sm">
                              <dt className="text-slate-600 dark:text-slate-300">{label}</dt>
                              <dd className="whitespace-nowrap font-medium text-slate-900 dark:text-slate-100">
                                {key === "cost" && Number(margem[key]) <= 0
                                  ? "Não informado"
                                  : moedaIfood(margem[key])}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      ) : null}
                    </>
                  ) : (
                    <p className="v2-texto-ajuda">
                      A estimativa de margem não está disponível para este acesso.
                    </p>
                  )}
                  <p className="v2-texto-ajuda">
                    Estimativa sobre o preço vigente simulado. Não inclui despesas por pedido,
                    mensalidade ou benefícios financiados pela loja. O cenário não altera a
                    logística contratada.
                  </p>
                  {podeConfigurar ? (
                    <BotaoInteracao icon={Settings} disabled={c.salvando} onClick={onConfigurar}>
                      Conferir taxas e regras da loja
                    </BotaoInteracao>
                  ) : null}
                </section>

                <section className="space-y-3">
                  <h3 className="v2-titulo-secao">Pendências da simulação</h3>
                  {c.resultado.pending?.length ? (
                    <ul className="space-y-2">
                      {c.resultado.pending.map((pendencia, index) => (
                        <li
                          key={`${pendencia.code}-${index}`}
                          className="flex gap-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700"
                        >
                          <AlertTriangle
                            className="mt-0.5 h-4 w-4 flex-none text-amber-600 dark:text-amber-300"
                            aria-hidden="true"
                          />
                          <div>
                            <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                              {IFOOD_PENDING_LABELS[pendencia.kind] || "A conferir"}
                            </p>
                            <p className="v2-texto mt-1">{pendencia.message}</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="v2-texto-ajuda">
                      Nenhuma pendência identificada nesta simulação.
                    </p>
                  )}
                </section>
              </>
            )}
          </div>
        </div>
        <p className="v2-texto-ajuda">
          Esta preparação é local. A publicação e a situação do anúncio no iFood ainda não foram
          confirmadas.
        </p>
      </div>
    </ModalPadrao>
  );
}
