import { useState } from "react";
import { CheckCircle2, Link2, RefreshCw, Send } from "lucide-react";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputRadio from "../v2/InputRadio/InputRadio";
import LinkPadrao from "../v2/LinkPadrao/LinkPadrao";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";
import { useEscapeToClose } from "../../utils/modalEscape";
import { moedaIfood, statusEnvioIfood } from "./ifoodPresentation";
import useIfoodPublicacaoProduto from "./useIfoodPublicacaoProduto";

const dataHora = (value) => {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime())
    ? date.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" })
    : "Data não informada";
};
const quantidade = (value) =>
  value == null ? "Não conferido" : Number(value).toLocaleString("pt-BR");

function Pendencias({ items = [] }) {
  if (!items.length) return null;
  return (
    <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-200">
      {items.map((item, index) => (
        <li key={`${item.code}-${index}`}>{item.message}</li>
      ))}
    </ul>
  );
}

export function ResumoEstoqueAutomatico({ sync, compacto = false }) {
  if (!sync) return null;
  const status =
    {
      queued: "Saldo aguardando envio",
      sending: "Envio de estoque em andamento",
      accepted:
        sync.reference_source === "portal"
          ? "Saldo igual à conferência registrada"
          : "Saldo recebido; resultado externo a conferir",
      backoff: "Aguardando nova tentativa por limite de envios",
      blocked: "Envio bloqueado; confira o vínculo e as pendências",
      uncertain: "Resultado desconhecido; confira antes de reenviar",
    }[sync.status] || "Situação a conferir";
  if (compacto)
    return <p className="v2-texto-ajuda mt-1 max-w-64">Estoque automático DEV: {status}.</p>;
  return (
    <section className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
      <h4 className="v2-titulo-secao">Estoque automático — piloto DEV</h4>
      <p className="v2-texto">{status}.</p>
      <p className="v2-texto-ajuda">
        Saldo disponível atual: {quantidade(sync.desired_stock)} · Último saldo enviado ou
        conferido: {quantidade(sync.last_accepted_stock)}.
      </p>
      {sync.next_attempt_at ? (
        <p className="v2-texto-ajuda">
          Próximo envio permitido a partir de {dataHora(sync.next_attempt_at)}.
        </p>
      ) : null}
      <p className="v2-texto-ajuda">
        {sync.enabled
          ? "Piloto ativo somente para este produto em DEV."
          : "Piloto desativado; histórico preservado."}{" "}
        Este ensaio usa um simulador local. O acompanhamento não comprova aplicação no iFood. Preços
        não fazem parte desta rotina.
      </p>
    </section>
  );
}

export function MemoriaEnvio({ review }) {
  const item = review.payload;
  if (!item) return null;
  return (
    <div className="space-y-3 rounded-lg border border-blue-200 p-3 dark:border-blue-500/30">
      <h4 className="v2-titulo-secao">Revise este único produto</h4>
      <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="v2-texto-ajuda">EAN enviado</dt>
          <dd className="break-all font-medium">{item.barcode}</dd>
        </div>
        {item.name !== undefined ? (
          <div>
            <dt className="v2-texto-ajuda">Nome</dt>
            <dd>{item.name}</dd>
          </div>
        ) : null}
        {item.prices?.price !== undefined ? (
          <div>
            <dt className="v2-texto-ajuda">Preço regular enviado</dt>
            <dd>{moedaIfood(item.prices.price)}</dd>
          </div>
        ) : null}
        {item.inventory?.stock !== undefined ? (
          <div>
            <dt className="v2-texto-ajuda">Estoque disponível enviado</dt>
            <dd>{quantidade(item.inventory.stock)}</dd>
          </div>
        ) : null}
        {Object.hasOwn(item.prices || {}, "promotionPrice") ? (
          <div>
            <dt className="v2-texto-ajuda">Promoção incluída na criação</dt>
            <dd>
              {item.prices.promotionPrice == null
                ? "Sem preço promocional"
                : moedaIfood(item.prices.promotionPrice)}
            </dd>
          </div>
        ) : null}
        {item.details ? (
          <>
            <div>
              <dt className="v2-texto-ajuda">Apresentação</dt>
              <dd>{item.details.unit || "Não informada"}</dd>
            </div>
            <div>
              <dt className="v2-texto-ajuda">Marca / categoria</dt>
              <dd>
                {item.details.brand || "Não informada"} ·{" "}
                {item.details.categorization?.category || "Não informada"}
              </dd>
            </div>
            <div>
              <dt className="v2-texto-ajuda">Foto</dt>
              <dd>{item.details.imageUrl ? "Foto do cadastro incluída" : "Sem foto no envio"}</dd>
            </div>
            <div>
              <dt className="v2-texto-ajuda">Descrição</dt>
              <dd className="whitespace-pre-wrap break-words">
                {item.details.description || "Não informada"}
              </dd>
            </div>
          </>
        ) : null}
      </dl>
      <p className="v2-texto-ajuda">
        {review.operation === "create"
          ? "Criação de um produto com os dados acima, sem substituir o catálogo da loja."
          : "Somente os campos de preço e/ou estoque exibidos serão enviados. Nome, descrição, foto, canais e promoção do iFood serão preservados."}
      </p>
    </div>
  );
}

// Bloco do mesmo cadastro, compartilhado com a central. Não cria outro produto,
// não salva o rascunho nem ativa a automação, configurada separadamente em DEV.
export default function IfoodPublicacaoProduto({ productId, draft = null, imagens, onFechar }) {
  const [localAberto, setLocalAberto] = useState(false);
  const c = useIfoodPublicacaoProduto({ productId, draft, imagens });
  const aberto = Boolean(onFechar) || localAberto;
  const fechar = () => {
    if (!c.busy) {
      setLocalAberto(false);
      onFechar?.();
    }
  };
  useEscapeToClose({ onClose: fechar, disabled: !aberto || Boolean(c.busy) });
  const p = c.publication;
  const last = p?.last_submission;
  const confirmacao = p?.last_confirmation;
  const prefix = `ifood-publicacao-${productId || "novo"}`;

  if (!productId)
    return (
      <p className="v2-texto-ajuda">
        Salve o produto para conferir o vínculo e preparar o primeiro envio.
      </p>
    );

  return (
    <>
      {!onFechar ? (
        <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-700">
          <h4 className="v2-titulo-secao">Vínculo e publicação assistida</h4>
          <p className="v2-texto-ajuda">{statusEnvioIfood(last?.status, last)}</p>
          <ResumoEstoqueAutomatico sync={p?.stock_sync} compacto />
          <BotaoInteracao icon={Link2} tamanho="pequeno" onClick={() => setLocalAberto(true)}>
            Conferir vínculo e envio
          </BotaoInteracao>
        </div>
      ) : null}
      {aberto ? (
        <ModalPadrao
          titulo="Vínculo e publicação de um produto"
          tamanho="grande"
          onFechar={fechar}
          rodape={
            <BotaoCancelar type="button" disabled={Boolean(c.busy)} onClick={fechar}>
              Fechar
            </BotaoCancelar>
          }
        >
          <div className="space-y-5">
            <p className="v2-texto-ajuda">
              {p?.stock_sync?.enabled
                ? "O piloto automático acompanha o estoque salvo deste produto em DEV. Envios manuais estão bloqueados enquanto ele estiver ativo."
                : "Piloto assistido. Preparar ou salvar o cadastro não envia alterações ao iFood. Os dados usados são os da versão salva."}
            </p>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold">{p?.snapshot_saved?.nome || "Produto salvo"}</p>
                <p className="v2-texto-ajuda">
                  SKU {p?.snapshot_saved?.codigo || "não informado"} · EAN{" "}
                  {p?.barcode || "não informado"}
                </p>
              </div>
              <BotaoInteracao
                icon={RefreshCw}
                tamanho="pequeno"
                loading={c.loading}
                disabled={Boolean(c.busy)}
                onClick={c.atualizar}
              >
                Atualizar acompanhamento
              </BotaoInteracao>
            </div>
            {c.loading ? (
              <p role="status" className="v2-texto-ajuda">
                Consultando vínculo, versão salva e histórico…
              </p>
            ) : null}
            {c.error ? (
              <p
                role="alert"
                className="rounded-lg bg-red-50 p-3 text-sm text-red-800 dark:bg-red-500/10 dark:text-red-200"
              >
                {c.error}
              </p>
            ) : null}
            {c.success ? (
              <p role="status" className="text-sm text-emerald-800 dark:text-emerald-200">
                {c.success}
              </p>
            ) : null}
            {p && c.dirty ? (
              <p
                role="status"
                className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200"
              >
                Há campos do cadastro em edição. Salve o cadastro antes de conferir o vínculo ou
                preparar o envio. Seus campos permanecem em edição.
              </p>
            ) : null}
            {c.uncertain ? (
              <p role="alert" className="text-sm text-amber-800 dark:text-amber-200">
                Resultado desconhecido. Não repita o envio; confira o produto no Portal e registre o
                que encontrou.
              </p>
            ) : null}
            <Pendencias items={p?.pending} />
            <ResumoEstoqueAutomatico sync={p?.stock_sync} />

            <section className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h3 className="v2-titulo-secao">1. Confira o mesmo EAN no Portal</h3>
              <LinkPadrao href="https://portal.ifood.com.br" novaJanela>
                Abrir Portal do Parceiro
              </LinkPadrao>
              <p className="v2-texto-ajuda">
                Confira a loja, o EAN e a apresentação. A correspondência não é escolhida
                automaticamente por nome, SKU ou preço.
              </p>
              {p?.link ? (
                <p className="v2-texto">
                  {p.link.stale
                    ? "EAN ou loja alterados — confira novamente o vínculo."
                    : p.link.mode === "existing"
                      ? "Item existente: correspondência declarada no Portal."
                      : "Produto novo: ausência declarada no Portal."}{" "}
                  Conferência em {dataHora(p.link.portal_checked_at)}.
                </p>
              ) : null}
              <InputRadio
                label="Resultado da sua conferência"
                name={`${prefix}-mode`}
                value={c.mode}
                disabled={!c.canLink}
                opcoes={[
                  { value: "existing", label: "Já existe no iFood" },
                  { value: "new", label: "Não encontrei este EAN no Portal" },
                ]}
                onChange={(value) => c.alterar("mode", value)}
              />
              <InputCheckTexto
                id={`${prefix}-checked`}
                checked={c.portalChecked}
                disabled={!c.canLink}
                onChange={(value) => c.alterar("portalChecked", value)}
              >
                {c.mode === "existing"
                  ? "Conferi a loja, o mesmo EAN e a apresentação do produto existente."
                  : "Conferi este EAN nas listas disponíveis do Portal e não localizei o produto; quero preparar uma criação."}
              </InputCheckTexto>
              <BotaoInteracao
                icon={Link2}
                disabled={!c.canLink || !c.portalChecked}
                loading={c.busy === "link"}
                onClick={c.vincular}
              >
                Registrar conferência do EAN
              </BotaoInteracao>
            </section>

            <section className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h3 className="v2-titulo-secao">2. Prepare e revise antes de enviar</h3>
              <p className="v2-texto-ajuda">
                {c.operation === "create"
                  ? "O envio criará somente este produto. O catálogo existente será preservado."
                  : "Escolha o que atualizar no produto vinculado. A promoção atual do iFood será preservada nesta etapa."}
              </p>
              {c.operation === "update" ? (
                <div className="flex flex-wrap gap-4">
                  <InputCheckTexto
                    id={`${prefix}-price`}
                    checked={c.fields.includes("price")}
                    disabled={!c.ready}
                    onChange={(checked) =>
                      c.alterar(
                        "fields",
                        checked
                          ? [...c.fields, "price"]
                          : c.fields.filter((field) => field !== "price"),
                      )
                    }
                  >
                    Preço regular
                  </InputCheckTexto>
                  <InputCheckTexto
                    id={`${prefix}-stock`}
                    checked={c.fields.includes("stock")}
                    disabled={!c.ready}
                    onChange={(checked) =>
                      c.alterar(
                        "fields",
                        checked
                          ? [...c.fields, "stock"]
                          : c.fields.filter((field) => field !== "stock"),
                      )
                    }
                  >
                    Estoque disponível
                  </InputCheckTexto>
                </div>
              ) : null}
              <BotaoInteracao
                icon={RefreshCw}
                disabled={!c.canPrepare}
                loading={c.busy === "prepare"}
                onClick={c.preparar}
              >
                Preparar prévia de um produto
              </BotaoInteracao>
              {c.review ? (
                <>
                  <Pendencias items={c.review.pending} />
                  <MemoriaEnvio review={c.review} />
                  <InputCheckTexto
                    id={`${prefix}-send`}
                    checked={c.confirmSend}
                    disabled={!c.ready || !c.review.eligible}
                    onChange={(value) => c.alterar("confirmSend", value)}
                  >
                    Revisei este produto, o EAN e os campos acima e autorizo enviar esta alteração
                    ao iFood.
                  </InputCheckTexto>
                  {!p?.capabilities?.write_enabled ? (
                    <p className="v2-texto-ajuda">
                      Envios estão desabilitados neste ambiente. A prévia não libera uma publicação.
                    </p>
                  ) : null}
                  <BotaoInteracao
                    icon={Send}
                    disabled={!c.canSend}
                    loading={c.busy === "send"}
                    onClick={c.enviar}
                  >
                    {c.review.operation === "create"
                      ? "Publicar este produto"
                      : "Enviar atualização de preço e/ou estoque"}
                  </BotaoInteracao>
                </>
              ) : null}
            </section>

            <section className="space-y-3 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
              <h3 className="v2-titulo-secao">3. Acompanhe e registre a conferência no Portal</h3>
              <p className="font-medium">{statusEnvioIfood(last?.status, last)}</p>
              {last ? (
                <p className="v2-texto-ajuda">
                  {dataHora(last.finished_at || last.created_at)}
                  {last.message ? ` · ${last.message}` : ""}
                </p>
              ) : null}
              <p className="v2-texto-ajuda">
                Aceite da API não confirma a publicação nem a visibilidade no aplicativo. Confira o
                resultado no Portal.
              </p>
              {confirmacao ? (
                <div className="space-y-1 text-sm">
                  <p>
                    Última conferência manual:{" "}
                    {confirmacao.present ? "produto localizado" : "produto não localizado"}, em{" "}
                    {dataHora(confirmacao.confirmed_at)}.
                  </p>
                  <p>
                    Preço conferido:{" "}
                    {confirmacao.price == null ? "Não conferido" : moedaIfood(confirmacao.price)} ·
                    Estoque conferido: {quantidade(confirmacao.stock)}
                  </p>
                  <p className="v2-texto-ajuda">
                    Esta declaração humana é preservada no histórico e não confirma envios
                    posteriores.
                  </p>
                </div>
              ) : null}
              <InputRadio
                label="O que encontrou no Portal?"
                name={`${prefix}-present`}
                value={c.present ? "yes" : "no"}
                disabled={!c.ready || !p?.capabilities?.can_confirm}
                opcoes={[
                  { value: "yes", label: "Produto localizado" },
                  { value: "no", label: "Produto não localizado" },
                ]}
                onChange={(value) => c.alterar("present", value === "yes")}
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <InputTexto
                  id={`${prefix}-observed-price`}
                  label="Preço conferido no Portal (opcional)"
                  inputMode="decimal"
                  value={c.observedPrice ?? ""}
                  disabled={!c.ready || !p?.capabilities?.can_confirm || !c.present}
                  onChange={(value) => c.alterar("observedPrice", value)}
                  help="Deixe vazio se não conferiu; não copie a estimativa."
                />
                <InputTexto
                  id={`${prefix}-observed-stock`}
                  label="Estoque conferido no Portal (opcional)"
                  inputMode="decimal"
                  value={c.observedStock ?? ""}
                  disabled={!c.ready || !p?.capabilities?.can_confirm || !c.present}
                  onChange={(value) => c.alterar("observedStock", value)}
                  help="Vazio significa não conferido; zero é uma declaração explícita."
                />
              </div>
              <InputCheckTexto
                id={`${prefix}-confirm-portal`}
                checked={c.confirmPortal}
                disabled={!c.ready || !p?.capabilities?.can_confirm}
                onChange={(value) => c.alterar("confirmPortal", value)}
              >
                Conferi agora a loja, o EAN e o resultado acima no Portal do Parceiro.
              </InputCheckTexto>
              <BotaoInteracao
                icon={CheckCircle2}
                disabled={!c.canConfirm}
                loading={c.busy === "confirm"}
                onClick={c.confirmar}
              >
                Registrar conferência manual
              </BotaoInteracao>
            </section>
          </div>
        </ModalPadrao>
      ) : null}
    </>
  );
}
