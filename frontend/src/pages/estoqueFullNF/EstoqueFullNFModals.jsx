import { CheckCircle2, Edit3, History, Link as LinkIcon, X } from "lucide-react";
import ActionButton from "../../components/ui/ActionButton";
import { ChannelBadge, getChannelConfig } from "../../components/ui/ChannelBadges";
import IconActionButton from "../../components/ui/IconActionButton";
import { formatMoneyBRL } from "../../utils/formatters";
import { CANAIS_FULL, contarBaixas, contarLancamentosFinanceiros } from "./estoqueFullNFUtils";

export default function EstoqueFullNFModals({ controller }) {
  const {
    modalConclusao,
    corrigirCanalDoResultado,
    fecharModalConclusao,
    modalEditarCanal,
    fecharModalEditarCanal,
    salvandoCanal,
    setModalEditarCanal,
    salvarCanalLancamento,
    modalDre,
    fecharModalDre,
    dreSubcategoriaId,
    setDreSubcategoriaId,
    carregandoDre,
    dreSubcategoriasDespesa,
    salvandoVinculoDre,
    vincularDreEContinuar,
  } = controller;

  return (
    <>
      {modalConclusao.aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-2xl">
            <div className="border-b border-slate-200 px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
                Processamento concluido
              </p>
              <h3 className="mt-1 text-lg font-semibold text-slate-900">Baixa por NF finalizada</h3>
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                <div>
                  <p className="text-xs text-slate-500">NF</p>
                  <p className="text-base font-semibold text-slate-900">
                    {modalConclusao.resultado?.numero_nf}
                  </p>
                </div>
                <ChannelBadge
                  channel={modalConclusao.resultado?.plataforma}
                  label={modalConclusao.resultado?.plataforma_label}
                />
              </div>

              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <p className="font-semibold">Confirme a loja/canal antes de seguir.</p>
                <p className="mt-1">
                  Esta baixa ficou registrada em{" "}
                  <strong>
                    {
                      getChannelConfig(
                        modalConclusao.resultado?.plataforma,
                        modalConclusao.resultado?.plataforma_label,
                      ).label
                    }
                  </strong>
                  . Se estiver errado, corrija agora para manter estoque, financeiro e DRE na origem
                  certa.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase text-emerald-700">Baixas feitas</p>
                  <p className="mt-1 text-2xl font-bold text-emerald-900">
                    {contarBaixas(modalConclusao.resultado)}
                  </p>
                </div>
                <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase text-blue-700">Financeiro</p>
                  <p className="mt-1 text-2xl font-bold text-blue-900">
                    {contarLancamentosFinanceiros(modalConclusao.resultado)}
                  </p>
                </div>
              </div>

              {modalConclusao.resultado?.estoque_ja_baixado && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  O estoque desta NF ja estava baixado. O sistema nao baixou novamente e executou
                  apenas o que ainda estava pendente.
                </div>
              )}

              {modalConclusao.resultado?.tarifa_envio?.conta_pagar_id && (
                <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                  Conta a pagar gerada:{" "}
                  <strong>#{modalConclusao.resultado.tarifa_envio.conta_pagar_id}</strong> no valor
                  de <strong>{formatMoneyBRL(modalConclusao.resultado.tarifa_envio.valor)}</strong>.
                </div>
              )}
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
              <ActionButton
                icon={Edit3}
                intent="warning"
                onClick={corrigirCanalDoResultado}
                tone="soft"
              >
                Corrigir canal
              </ActionButton>
              <ActionButton icon={History} onClick={() => fecharModalConclusao(true)} tone="soft">
                Ver historico
              </ActionButton>
              <ActionButton
                icon={CheckCircle2}
                intent="create"
                onClick={() => fecharModalConclusao(false)}
              >
                OK, novo lancamento
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {modalEditarCanal.aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                  Correcao de canal
                </p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">
                  Editar loja/canal da NF {modalEditarCanal.lancamento?.numero_nf}
                </h3>
              </div>
              <IconActionButton
                aria-label="Fechar"
                onClick={fecharModalEditarCanal}
                disabled={salvandoCanal}
                icon={X}
                intent="neutral"
                tone="ghost"
              />
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <p>
                  Canal atual:{" "}
                  <ChannelBadge
                    channel={modalEditarCanal.lancamento?.plataforma}
                    label={modalEditarCanal.lancamento?.plataforma_label}
                  />
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  A correcao atualiza a baixa de estoque e a conta a pagar da tarifa desta NF.
                </p>
              </div>

              <div>
                <label
                  className="mb-1 block text-sm font-medium text-slate-700"
                  htmlFor="editar-canal-full"
                >
                  Loja / canal correto
                </label>
                <select
                  id="editar-canal-full"
                  value={modalEditarCanal.canal}
                  onChange={(event) =>
                    setModalEditarCanal((prev) => ({
                      ...prev,
                      canal: event.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                >
                  <option value="">Selecione o canal</option>
                  {CANAIS_FULL.map((canal) => (
                    <option key={canal.value} value={canal.value}>
                      {canal.label}
                    </option>
                  ))}
                </select>
              </div>

              {modalEditarCanal.canal &&
                modalEditarCanal.canal !== modalEditarCanal.lancamento?.plataforma && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    Vou mover esta NF para{" "}
                    <strong>{getChannelConfig(modalEditarCanal.canal).label}</strong>. Confira antes
                    de salvar.
                  </div>
                )}
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
              <ActionButton onClick={fecharModalEditarCanal} disabled={salvandoCanal} tone="soft">
                Cancelar
              </ActionButton>
              <ActionButton
                icon={CheckCircle2}
                intent="edit"
                onClick={salvarCanalLancamento}
                disabled={!modalEditarCanal.canal}
                loading={salvandoCanal}
              >
                Salvar canal
              </ActionButton>
            </div>
          </div>
        </div>
      )}

      {modalDre.aberto && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 px-4">
          <div className="w-full max-w-xl rounded-xl bg-white shadow-2xl border border-slate-200">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                  Acao necessaria
                </p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">
                  Vincular categoria a DRE
                </h3>
              </div>
              <IconActionButton
                aria-label="Fechar"
                onClick={fecharModalDre}
                icon={X}
                intent="neutral"
                tone="ghost"
              />
            </div>

            <div className="space-y-4 px-5 py-4">
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                A categoria{" "}
                <strong>{modalDre.categoria?.caminho_completo || modalDre.categoria?.nome}</strong>{" "}
                ainda nao tem vinculo contabil. Para gerar a conta a pagar e jogar a despesa na DRE
                do canal selecionado, escolha abaixo onde essa despesa deve entrar.
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Subcategoria DRE de despesa
                </label>
                <select
                  value={dreSubcategoriaId}
                  onChange={(e) => setDreSubcategoriaId(e.target.value)}
                  disabled={carregandoDre}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 disabled:bg-slate-100"
                >
                  <option value="">
                    {carregandoDre
                      ? "Carregando opcoes..."
                      : "Selecione onde classificar esta despesa"}
                  </option>
                  {dreSubcategoriasDespesa.map((sub) => (
                    <option key={sub.id} value={sub.id}>
                      {sub.categoria_nome} &gt; {sub.nome}
                    </option>
                  ))}
                </select>
                {!carregandoDre && !dreSubcategoriasDespesa.length && (
                  <p className="mt-2 text-xs text-red-700">
                    Nenhuma subcategoria DRE de despesa ativa foi encontrada. Cadastre o plano DRE
                    antes de continuar.
                  </p>
                )}
              </div>

              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
                Esse vinculo fica salvo na categoria financeira. Nas proximas baixas com a mesma
                categoria, o sistema ja segue direto.
              </div>
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-200 px-5 py-4 sm:flex-row sm:justify-end">
              <ActionButton onClick={fecharModalDre} disabled={salvandoVinculoDre} tone="soft">
                Resolver depois
              </ActionButton>
              <ActionButton
                icon={LinkIcon}
                intent="create"
                onClick={vincularDreEContinuar}
                disabled={carregandoDre || !dreSubcategoriasDespesa.length}
                loading={salvandoVinculoDre}
              >
                Vincular e continuar
              </ActionButton>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
