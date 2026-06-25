import {
  CheckCircle2,
  ExternalLink,
  FileText,
  PackageMinus,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import CurrencyInput from "../../components/CurrencyInput";
import ActionButton from "../../components/ui/ActionButton";
import { ChannelBadge } from "../../components/ui/ChannelBadges";
import Panel from "../../components/ui/Panel";
import { CANAIS_FULL, formatarQuantidade } from "./estoqueFullNFUtils";

export default function EstoqueFullNFLancamentoPanel({ controller }) {
  const {
    numeroNF,
    plataforma,
    setPlataforma,
    dataVencimentoTarifa,
    setDataVencimentoTarifa,
    observacao,
    setObservacao,
    adicionarLinha,
    xmlInputKey,
    setArquivoXml,
    lendoXml,
    importarItensDoXml,
    problemasEstoque,
    validandoEstoque,
    revalidarEstoque,
    podeLancarNegativo,
    salvando,
    lancarNegativo,
    abrirCorrecaoEstoque,
    problemaDaLinha,
    itens,
    atualizarLinha,
    removerLinha,
    tarifaEnvio,
    setTarifaEnvio,
    categoriaTarifaId,
    setCategoriaTarifaId,
    categoriasDespesa,
    categoriaTarifaSelecionada,
    processar,
  } = controller;

  return (
    <>
      <Panel className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">
              Numero da NF (automatico via XML)
            </div>
            <input
              id="numero-nf"
              aria-label="Numero da NF"
              type="text"
              value={numeroNF}
              readOnly
              placeholder="Selecione um XML para preencher"
              className="w-full border border-amber-300 bg-amber-50 rounded-lg px-3 py-2 text-gray-900"
            />
          </div>

          <div>
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="block text-sm font-medium text-gray-700">Canal / origem *</div>
              {plataforma && <ChannelBadge channel={plataforma} />}
            </div>
            <select
              id="plataforma-full"
              aria-label="Canal ou origem"
              value={plataforma}
              onChange={(e) => setPlataforma(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">Selecione o canal</option>
              {CANAIS_FULL.map((canal) => (
                <option key={canal.value} value={canal.value}>
                  {canal.label}
                </option>
              ))}
            </select>
            {!plataforma && (
              <p className="mt-1 text-xs text-amber-700">
                Obrigatorio para direcionar a despesa na DRE correta.
              </p>
            )}
          </div>

          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">
              Data vencimento tarifa
            </div>
            <input
              id="vencimento-tarifa"
              aria-label="Data vencimento tarifa"
              type="date"
              value={dataVencimentoTarifa}
              onChange={(e) => setDataVencimentoTarifa(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            />
          </div>
        </div>

        <div>
          <div className="block text-sm font-medium text-gray-700 mb-1">Observacao (opcional)</div>
          <input
            id="obs-full"
            aria-label="Observacao"
            type="text"
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            placeholder="Ex: lote de pedidos da semana"
            className="w-full border border-gray-300 rounded-lg px-3 py-2"
          />
        </div>
      </Panel>

      <Panel
        className="space-y-3"
        title="Itens da NF (baixa de estoque)"
        actions={
          <ActionButton icon={Plus} intent="create" onClick={adicionarLinha}>
            Adicionar item
          </ActionButton>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end bg-slate-50 border border-slate-200 rounded-xl p-3 md:p-4">
          <div className="md:col-span-8">
            <div className="block text-sm font-medium text-slate-700 mb-1">
              Escolher XML da NF (preenche numero e itens)
            </div>
            <input
              key={xmlInputKey}
              type="file"
              accept=".xml,text/xml,application/xml"
              onChange={(e) => setArquivoXml(e.target.files?.[0] || null)}
              className="w-full border border-slate-300 bg-white rounded-lg px-3 py-2"
            />
          </div>
          <div className="md:col-span-4">
            <ActionButton
              className="w-full"
              icon={FileText}
              intent="edit"
              loading={lendoXml}
              onClick={importarItensDoXml}
              size="md"
            >
              Ler XML e preencher
            </ActionButton>
          </div>
        </div>

        {problemasEstoque.length > 0 && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h3 className="font-semibold">
                  Estoque insuficiente em {problemasEstoque.length} item(ns)
                </h3>
                <p className="mt-1 text-red-800">
                  Corrija o estoque dos produtos marcados em uma nova aba e depois revalide sem
                  perder esta NF.
                </p>
              </div>
              <ActionButton
                icon={RefreshCw}
                intent="warning"
                loading={validandoEstoque}
                onClick={revalidarEstoque}
                tone="soft"
              >
                Revalidar estoque
              </ActionButton>
              {podeLancarNegativo && (
                <ActionButton
                  icon={PackageMinus}
                  intent="delete"
                  loading={salvando}
                  onClick={lancarNegativo}
                  tone="soft"
                >
                  Lancar negativo
                </ActionButton>
              )}
            </div>
            <div className="mt-3 grid gap-2">
              {problemasEstoque.map((problema) => (
                <div
                  key={`${problema.entrada_sku || problema.sku}-${problema.produto_id || "sem-produto"}`}
                  className="flex flex-col gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <p className="font-semibold">{problema.nome || "Produto nao identificado"}</p>
                    <p className="text-xs text-red-700">
                      SKU {problema.sku || problema.entrada_sku || "-"} | Disponivel:{" "}
                      {formatarQuantidade(problema.disponivel)} | NF pede:{" "}
                      {formatarQuantidade(problema.solicitado)} | Falta:{" "}
                      {formatarQuantidade(problema.faltante)}
                    </p>
                  </div>
                  {problema.url_correcao && (
                    <ActionButton
                      icon={ExternalLink}
                      intent="delete"
                      onClick={() => abrirCorrecaoEstoque(problema)}
                      size="xs"
                    >
                      Corrigir estoque
                    </ActionButton>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          {itens.map((item) => {
            const problema = problemaDaLinha(item);
            return (
              <div
                key={item.id}
                className={`grid grid-cols-1 gap-2 rounded-xl md:grid-cols-12 ${
                  problema ? "border border-red-300 bg-red-50 p-2" : ""
                }`}
              >
                <div className="md:col-span-7">
                  <input
                    id={`sku-${item.id}`}
                    aria-label={`SKU ${item.id}`}
                    type="text"
                    value={item.sku}
                    onChange={(e) => atualizarLinha(item.id, "sku", e.target.value)}
                    placeholder="SKU do produto"
                    className={`w-full rounded-lg border px-3 py-2 ${
                      problema ? "border-red-300 bg-white text-red-900" : "border-gray-300"
                    }`}
                  />
                </div>
                <div className="md:col-span-3">
                  <input
                    id={`qtd-${item.id}`}
                    aria-label={`Quantidade ${item.id}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={item.quantidade}
                    onChange={(e) => atualizarLinha(item.id, "quantidade", e.target.value)}
                    placeholder="Quantidade"
                    className={`w-full rounded-lg border px-3 py-2 ${
                      problema ? "border-red-300 bg-white text-red-900" : "border-gray-300"
                    }`}
                  />
                </div>
                <div className="md:col-span-2">
                  <ActionButton
                    className="w-full"
                    icon={Trash2}
                    intent="delete"
                    onClick={() => removerLinha(item.id)}
                    tone="soft"
                  >
                    Remover
                  </ActionButton>
                </div>
                {problema && (
                  <div className="md:col-span-12 flex flex-col gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 text-xs text-red-800 md:flex-row md:items-center md:justify-between">
                    <span>
                      {problema.nome}: disponivel {formatarQuantidade(problema.disponivel)},
                      solicitado {formatarQuantidade(problema.solicitado)}, falta{" "}
                      {formatarQuantidade(problema.faltante)}.
                    </span>
                    {problema.url_correcao && (
                      <ActionButton
                        icon={ExternalLink}
                        intent="delete"
                        onClick={() => abrirCorrecaoEstoque(problema)}
                        size="xs"
                        tone="soft"
                      >
                        Abrir ajuste de estoque
                      </ActionButton>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel
        className="space-y-4"
        title="Tarifa de envio (financeiro)"
        subtitle="Se preencher esta parte, o sistema cria uma conta a pagar so da tarifa de envio. Se deixar zero, nao cria nada no financeiro."
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">Valor da tarifa</div>
            <CurrencyInput
              id="valor-tarifa"
              aria-label="Valor da tarifa"
              value={tarifaEnvio}
              onChange={setTarifaEnvio}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
              placeholder="0,00"
            />
          </div>

          <div>
            <div className="block text-sm font-medium text-gray-700 mb-1">
              Categoria de despesa {tarifaEnvio > 0 ? "(obrigatoria)" : "(opcional)"}
            </div>
            <select
              id="categoria-tarifa"
              aria-label="Categoria da tarifa"
              value={categoriaTarifaId}
              onChange={(e) => setCategoriaTarifaId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">Sem categoria</option>
              {categoriasDespesa.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.caminho_completo || cat.nome}
                </option>
              ))}
            </select>
            {tarifaEnvio > 0 && !categoriaTarifaId && (
              <p className="mt-1 text-xs text-amber-700">
                Para gerar o contas a pagar da tarifa, selecione uma categoria com DRE vinculada.
              </p>
            )}
            {tarifaEnvio > 0 &&
              categoriaTarifaId &&
              !categoriaTarifaSelecionada?.dre_subcategoria_id && (
                <p className="mt-1 text-xs text-red-700">
                  Esta categoria ainda nao tem vinculo DRE. Ajuste o cadastro da categoria antes de
                  confirmar.
                </p>
              )}
            {tarifaEnvio > 0 && categoriaTarifaSelecionada?.dre_subcategoria_id && (
              <p className="mt-1 text-xs text-emerald-700">
                A despesa sera lancada na DRE do canal/origem selecionado.
              </p>
            )}
          </div>
        </div>
      </Panel>

      <div className="flex flex-wrap gap-3">
        <ActionButton
          icon={CheckCircle2}
          intent="create"
          loading={salvando}
          onClick={() => processar()}
          size="lg"
        >
          Confirmar baixa por NF
        </ActionButton>
      </div>
    </>
  );
}
