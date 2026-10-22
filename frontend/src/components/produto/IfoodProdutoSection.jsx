import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, RefreshCw } from "lucide-react";
import { previewIfoodProduto } from "../../api/ifood";
import useIfoodPromotionRefresh from "../../hooks/useIfoodPromotionRefresh";
import { formatBRL, formatMoneyBRL, formatPercent } from "../../utils/formatters";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoLink from "../v2/BotaoLink/BotaoLink";
import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import InputRadio from "../v2/InputRadio/InputRadio";
import LinkPadrao from "../v2/LinkPadrao/LinkPadrao";
import PromocaoFields from "./PromocaoFields";
import { serializarDataHoraIfood } from "./ifoodProdutoDates";

const STATUS = {
  nao_selecionado: "Não selecionado",
  pendente: "Com pendências",
  pausado: "Pausado no CorePet",
  sem_estoque: "Sem estoque disponível",
  pronto_para_envio: "Cadastro pronto para envio",
};

const TIPOS_PENDENCIA = {
  bloqueio: "Impede o envio",
  operacional: "Operação",
  rentabilidade: "Margem",
  recomendacao: "Recomendação",
};

const numeroOpcional = (value) =>
  value === "" || value === null || value === undefined ? null : Number(value);

// Domínio do cadastro canônico: não salva um segundo produto nem publica no iFood.
export default function IfoodProdutoSection({ formData, handleChange, imagens = [], onCorrigir }) {
  const [modalidade, setModalidade] = useState("MERCHANT");
  const [resultado, setResultado] = useState(null);
  const [payloadCalculado, setPayloadCalculado] = useState(null);
  const [calculando, setCalculando] = useState(true);
  const [erro, setErro] = useState("");
  const [tentativa, setTentativa] = useState(0);
  const especifico = numeroOpcional(formData.preco_ifood) !== null;
  const selecionado = Boolean(formData.anunciar_ifood);
  const compartilhado = Boolean(formData.estoque_compartilhado);
  const produtoComComposicao =
    formData.tipo_produto === "KIT" ||
    (formData.tipo_produto === "VARIACAO" && Boolean(formData.tipo_kit));

  const payload = JSON.stringify({
    modalidade,
    produto: {
      id: formData.id || undefined,
      codigo: formData.codigo || formData.sku,
      sku: formData.sku || formData.codigo,
      nome: formData.nome,
      tipo: formData.tipo,
      tipo_produto: formData.tipo_produto,
      e_granel: Boolean(formData.e_granel),
      tipo_kit: produtoComComposicao ? (formData.e_kit_fisico ? "FISICO" : "VIRTUAL") : null,
      ...(produtoComComposicao
        ? {
            composicao_kit: (formData.composicao_kit || []).map((item) => ({
              produto_componente_id: Number(item.produto_componente_id || item.produto_id),
              quantidade: Number(item.quantidade || 1),
              opcional: Boolean(item.opcional),
            })),
          }
        : {}),
      unidade: formData.unidade,
      descricao_curta: formData.descricao || "",
      descricao_completa: formData.descricao_completa || null,
      imagem_principal:
        imagens.find((imagem) => imagem.e_principal || imagem.principal)?.url ||
        imagens[0]?.url ||
        formData.imagem_principal ||
        null,
      ativo: formData.ativo !== false,
      situacao: formData.situacao !== false,
      preco_custo: numeroOpcional(formData.preco_custo),
      preco_venda: numeroOpcional(formData.preco_venda),
      codigo_barras: formData.codigo_barras || null,
      gtin_ean: formData.gtin_ean || null,
      anunciar_ifood: selecionado,
      ifood_pausado: Boolean(formData.ifood_pausado),
      preco_ifood: numeroOpcional(formData.preco_ifood),
      preco_ifood_promo: numeroOpcional(formData.preco_ifood_promo),
      preco_ifood_promo_inicio: serializarDataHoraIfood(formData.preco_ifood_promo_inicio),
      preco_ifood_promo_fim: serializarDataHoraIfood(formData.preco_ifood_promo_fim),
    },
  });

  // A virada consulta o rascunho atual, sem carregar outro cadastro nem salvar
  // campos. O escopo cancela o agendamento quando o usuario altera o formulario.
  useIfoodPromotionRefresh(resultado, () => setTentativa((atual) => atual + 1), {
    enabled: selecionado && !compartilhado && !calculando && payloadCalculado === payload,
    scopeKey: payload,
  });

  useEffect(() => {
    if (compartilhado) {
      setCalculando(false);
      return undefined;
    }
    let ativo = true;
    const controller = new AbortController();
    setCalculando(true);
    setErro("");
    const timer = setTimeout(async () => {
      try {
        const { data } = await previewIfoodProduto(JSON.parse(payload), {
          signal: controller.signal,
        });
        if (ativo) {
          setResultado(data);
          setPayloadCalculado(payload);
        }
      } catch (error) {
        if (ativo && error.code !== "ERR_CANCELED") {
          setErro(
            "Não foi possível atualizar a estimativa e as pendências. Os últimos valores consultados podem estar desatualizados. Tente novamente.",
          );
        }
      } finally {
        if (ativo) setCalculando(false);
      }
    }, 350);
    return () => {
      ativo = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [payload, tentativa, compartilhado]);

  if (compartilhado) {
    return (
      <div className="space-y-2 border-t border-slate-200 pt-5 dark:border-slate-700">
        <h3 className="v2-titulo-secao">iFood</h3>
        <p className="v2-texto-ajuda">
          Este cadastro pertence a {formData.estoque_origem_nome || "outra loja do grupo"}. Cadastre
          o produto nesta loja para configurar preço, margem e publicação no iFood.
        </p>
        {formData.id && formData.estoque_origem_empresa_id ? (
          <LinkPadrao
            to={`/produtos/novo?pre_cadastro_grupo=${formData.id}&tenant_origem=${encodeURIComponent(formData.estoque_origem_empresa_id)}`}
          >
            Cadastrar nesta loja
          </LinkPadrao>
        ) : null}
      </div>
    );
  }

  const margem = resultado?.margins?.[modalidade];
  const pendencias = resultado?.pending || [];

  return (
    <div
      id="produto-canal-ifood"
      className="space-y-4 border-t border-slate-200 pt-5 dark:border-slate-700"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="v2-titulo-secao">iFood</h3>
          <p className="v2-texto-ajuda mt-1">
            Reaproveita os dados deste cadastro, com preço e seleção por loja.
          </p>
        </div>
        <LinkPadrao to="/ifood">Abrir central do iFood</LinkPadrao>
      </div>

      <InputCheckTexto
        id="produto-anunciar-ifood"
        checked={selecionado}
        onChange={(checked) => handleChange("anunciar_ifood", checked)}
      >
        Vender no iFood
      </InputCheckTexto>

      {selecionado ? (
        <>
          <InputRadio
            label="Preço do iFood"
            name="produto-ifood-modo-preco"
            value={especifico ? "especifico" : "regra_loja"}
            opcoes={[
              { value: "regra_loja", label: "Seguir regra da loja" },
              { value: "especifico", label: "Preço específico" },
            ]}
            onChange={(modo) =>
              handleChange(
                "preco_ifood",
                modo === "regra_loja"
                  ? null
                  : (resultado?.regular_price ?? Number(formData.preco_venda || 0)),
              )
            }
            help={
              especifico
                ? "Este valor é fixo. Alterar o custo ou o preço do ERP recalcula a margem, sem mudar o preço específico."
                : "Usa o preço de venda regular do ERP e o acréscimo configurado para o iFood. Não herda promoções de outros canais."
            }
          />
          {especifico ? (
            <InputMoeda
              id="produto-preco-ifood"
              label="Preço específico do iFood (R$)"
              value={formData.preco_ifood}
              onChange={(value) => handleChange("preco_ifood", value)}
              help="Preço zero gera pendência no canal e pode ser salvo para corrigir depois."
            />
          ) : null}

          <details className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
            <summary className="cursor-pointer text-sm font-medium text-slate-700 dark:text-slate-200">
              Promoção exclusiva do iFood (opcional)
            </summary>
            <div className="mt-3 space-y-3">
              <InputCheckTexto
                id="produto-ifood-usar-promocao"
                checked={numeroOpcional(formData.preco_ifood_promo) !== null}
                onChange={(checked) => {
                  handleChange(
                    "preco_ifood_promo",
                    checked ? (resultado?.regular_price ?? 0) : null,
                  );
                  if (!checked) {
                    handleChange("preco_ifood_promo_inicio", "");
                    handleChange("preco_ifood_promo_fim", "");
                  }
                }}
              >
                Usar preço promocional no iFood
              </InputCheckTexto>
              {numeroOpcional(formData.preco_ifood_promo) !== null ? (
                <PromocaoFields
                  title="Período e preço da promoção"
                  startId="produto-ifood-promo-inicio"
                  endId="produto-ifood-promo-fim"
                  description="A estimativa considera o preço promocional durante o período informado."
                  priceControl={
                    <InputMoeda
                      id="produto-preco-ifood-promo"
                      label="Preço promocional (R$)"
                      value={formData.preco_ifood_promo}
                      onChange={(value) => handleChange("preco_ifood_promo", value)}
                    />
                  }
                  startValue={formData.preco_ifood_promo_inicio}
                  endValue={formData.preco_ifood_promo_fim}
                  onStartChange={(value) => handleChange("preco_ifood_promo_inicio", value)}
                  onEndChange={(value) => handleChange("preco_ifood_promo_fim", value)}
                />
              ) : null}
            </div>
          </details>

          <InputCheckTexto
            id="produto-ifood-pausado"
            checked={Boolean(formData.ifood_pausado)}
            onChange={(checked) => handleChange("ifood_pausado", checked)}
          >
            Manter pausado no iFood, mesmo quando houver reposição de estoque
          </InputCheckTexto>

          <InputRadio
            label="Cenário para estimar a margem"
            name="produto-ifood-modalidade"
            value={modalidade}
            opcoes={[
              { value: "MERCHANT", label: "Entrega própria" },
              { value: "IFOOD", label: "Entrega iFood" },
            ]}
            onChange={setModalidade}
            help="Simula as condições comerciais de cada modalidade. A modalidade efetiva vem no pedido e depende da habilitação da loja."
          />
        </>
      ) : null}

      <div role="status" aria-live="polite" className="text-sm text-slate-600 dark:text-slate-300">
        {calculando
          ? "Atualizando preço, margem e pendências…"
          : erro || STATUS[resultado?.status] || "Estimativa indisponível"}
      </div>
      {erro ? (
        <BotaoInteracao
          icon={RefreshCw}
          tamanho="pequeno"
          onClick={() => setTentativa((value) => value + 1)}
        >
          Tentar novamente
        </BotaoInteracao>
      ) : null}

      {resultado && payloadCalculado === payload && selecionado ? (
        <>
          <dl aria-busy={calculando} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-white p-3 dark:bg-slate-900">
              <dt className="v2-texto-ajuda">
                Preço efetivo {resultado.promotion_active ? "em promoção" : "estimado"}
              </dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
                {resultado.effective_price == null
                  ? "Não definido"
                  : formatMoneyBRL(resultado.effective_price)}
              </dd>
              <dd className="v2-texto-ajuda">
                {resultado.price_source === "especifico" ? "Preço específico" : "Regra da loja"}
                {resultado.promotion_active
                  ? ` · Regular ${formatMoneyBRL(resultado.regular_price)}`
                  : ""}
              </dd>
            </div>
            <div className="rounded-lg bg-white p-3 dark:bg-slate-900">
              <dt className="v2-texto-ajuda">Contribuição estimada / unidade</dt>
              <dd
                className={`mt-1 text-lg font-semibold ${margem?.calculated && (margem.below_target || margem.contribution < 0) ? "text-amber-700 dark:text-amber-300" : "text-slate-900 dark:text-slate-100"}`}
              >
                {margem?.calculated
                  ? `${formatMoneyBRL(margem.contribution)} · ${formatPercent(margem.percent)}`
                  : "Margem não calculada"}
              </dd>
              <dd className="v2-texto-ajuda">
                {margem?.calculated && margem.contribution < 0
                  ? "Contribuição negativa"
                  : margem?.below_target
                    ? "Abaixo da meta da loja"
                    : "Após os custos informados"}
              </dd>
            </div>
            <div className="rounded-lg bg-white p-3 dark:bg-slate-900">
              <dt className="v2-texto-ajuda">Estoque disponível</dt>
              <dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
                {resultado.available_stock == null
                  ? "Após salvar o produto"
                  : `${formatBRL(resultado.available_stock)} ${formData.unidade || "UN"}`}
              </dd>
              <dd className="v2-texto-ajuda">Calculado pelo ERP, considerando reservas.</dd>
            </div>
          </dl>

          {!margem?.calculated ? (
            <div className="space-y-1 text-sm text-slate-600 dark:text-slate-300">
              <p>
                Falta informar:{" "}
                {(margem?.missing || []).join(", ") || "custo e condições comerciais da loja"}.
              </p>
              <LinkPadrao to="/ifood">Conferir taxas e regra de preço da loja</LinkPadrao>
            </div>
          ) : null}

          {margem?.calculated ? (
            <details className="text-sm text-slate-600 dark:text-slate-300">
              <summary className="cursor-pointer font-medium">Ver composição da margem</summary>
              <dl className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
                {[
                  ["Receita", margem.price],
                  ["Custo do produto", margem.cost],
                  ["Comissão", margem.commission],
                  ["Taxa de pagamento", margem.payment_fee],
                  ["Tributos estimados", margem.tax],
                  ["Outros custos unitários", margem.additional_cost],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="v2-texto-ajuda">{label}</dt>
                    <dd>{formatMoneyBRL(value)}</dd>
                  </div>
                ))}
              </dl>
              <p className="v2-texto-ajuda mt-2">
                Contribuição ÷ receita do item. Despesas por pedido, mensalidade, subsídios e
                valores do repasse precisam ser conferidos no resultado da venda.
              </p>
            </details>
          ) : null}

          <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Pendências e recomendações
            </h4>
            {pendencias.length ? (
              <ul className="mt-2 space-y-2">
                {pendencias.map((pendencia, index) => (
                  <li
                    key={`${pendencia.code}-${index}`}
                    className="flex items-start justify-between gap-3 text-sm text-slate-700 dark:text-slate-300"
                  >
                    <div className="flex gap-2">
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                      <span>
                        <strong className="text-xs">
                          {TIPOS_PENDENCIA[pendencia.kind] || "Revisar"}:{" "}
                        </strong>
                        {pendencia.message}
                      </span>
                    </div>
                    {pendencia.field && onCorrigir ? (
                      <BotaoLink onClick={() => onCorrigir(pendencia.field)}>Revisar</BotaoLink>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-300">
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                Sem pendências de cadastro.
              </p>
            )}
          </div>
        </>
      ) : null}
      <p className="v2-texto-ajuda">
        Salvar mantém a intenção de venda e as pendências no CorePet. A publicação no iFood é uma
        ação separada.
      </p>
    </div>
  );
}
