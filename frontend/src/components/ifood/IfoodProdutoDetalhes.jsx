import { AlertTriangle, Pencil, Settings } from "lucide-react";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
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
  podeEditar,
  podeConfigurar,
}) {
  useEscapeToClose({ onClose: onFechar });
  const margem = item.margins?.[modalidade];
  const negativa = margem?.calculated && Number(margem.contribution) < 0;
  return (
    <ModalPadrao
      titulo={item.name || "Detalhes do produto"}
      tamanho="grande"
      onFechar={onFechar}
      rodape={
        <>
          <BotaoCancelar onClick={onFechar}>Fechar</BotaoCancelar>
          {podeEditar ? (
            <BotaoInteracao icon={Pencil} onClick={onEditar}>
              Editar no cadastro
            </BotaoInteracao>
          ) : null}
        </>
      }
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="v2-texto-ajuda">SKU {item.sku || "não informado"}</p>
          <IfoodStatus status={item.status} />
        </div>
        <div className="grid grid-cols-2 gap-3 rounded-xl bg-slate-50 p-4 dark:bg-slate-950/40">
          <div>
            <p className="v2-rotulo">Preço vigente iFood</p>
            <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
              {moedaIfood(item.effective_price)}
            </p>
            <p className="v2-texto-ajuda">
              {item.price_source === "especifico"
                ? "Preço específico do produto"
                : "Regra geral da loja"}
            </p>
          </div>
          <div>
            <p className="v2-rotulo">Preço regular</p>
            <p className="mt-1 v2-texto">{moedaIfood(item.regular_price)}</p>
            {item.promotion_active ? (
              <p className="v2-texto-ajuda">Promoção vigente aplicada ao cálculo.</p>
            ) : null}
          </div>
        </div>

        <section className="space-y-3">
          <h3 className="v2-titulo-secao">Pendências e orientações</h3>
          {item.pending?.length ? (
            <ul className="space-y-2">
              {item.pending.map((pendencia, index) => (
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
            <p className="v2-texto-ajuda">Nenhuma pendência identificada na preparação local.</p>
          )}
        </section>

        <section className="space-y-3">
          <h3 className="v2-titulo-secao">Contribuição estimada por unidade</h3>
          <SeletorOpcoes
            opcoes={IFOOD_MODALIDADES}
            rotulo="Simular custos"
            valorSelecionado={modalidade}
            aoSelecionar={onModalidade}
          />
          {margem ? (
            <>
              <dl className="divide-y divide-slate-100 dark:divide-slate-800">
                {PARCELAS.map(([key, label]) => (
                  <div key={key} className="flex justify-between gap-3 py-2 text-sm">
                    <dt className="text-slate-600 dark:text-slate-300">{label}</dt>
                    <dd className="whitespace-nowrap font-medium text-slate-900 dark:text-slate-100">
                      {moedaIfood(margem[key])}
                    </dd>
                  </div>
                ))}
              </dl>
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
            </>
          ) : (
            <p className="v2-texto-ajuda">
              A estimativa de margem não está disponível para este acesso.
            </p>
          )}
          <p className="v2-texto-ajuda">
            Estimativa sobre o preço vigente do item. Não inclui despesas por pedido, mensalidade ou
            benefícios financiados pela loja. O cenário não altera a logística contratada.
          </p>
          {podeConfigurar ? (
            <BotaoInteracao icon={Settings} onClick={onConfigurar}>
              Conferir taxas e regras da loja
            </BotaoInteracao>
          ) : null}
        </section>
        <p className="v2-texto-ajuda">
          Esta preparação é local. A publicação e a situação do anúncio no iFood ainda não foram
          confirmadas.
        </p>
      </div>
    </ModalPadrao>
  );
}
