import { AlertTriangle, CheckCircle2, Package, RefreshCw, ShieldCheck } from "lucide-react";
import BotaoExcluir from "../../components/v2/BotaoExcluir/BotaoExcluir";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import Etiqueta from "../../components/v2/Etiqueta/Etiqueta";
import EstadoVazio from "../../components/v2/EstadoVazio/EstadoVazio";
import FaixaAviso from "../../components/v2/FaixaAviso/FaixaAviso";
import { formatarDataValidade, formatarMoeda } from "./lembretesFormatters";

export default function LembretesValidadeSection({ controller }) {
  return (
    <div className="grid gap-5">
      {controller.validadeInativa && <ValidadeInativa controller={controller} />}
      {controller.validadeAtivaSemPendencias && <ValidadeAtiva controller={controller} />}
      {controller.validadePendencias.length > 0 && <ValidadePendencias controller={controller} />}
      {!controller.validadeInativa &&
        !controller.validadeAtivaSemPendencias &&
        controller.validadePendencias.length === 0 && (
          <EstadoVazio icone={CheckCircle2} titulo="Nenhuma pendência de validade no momento." />
        )}
    </div>
  );
}

function ValidadeInativa({ controller }) {
  return (
    <FaixaAviso
      acoes={
        <BotaoInteracao onClick={controller.irConfiguracoesEstoque}>
          Abrir configurações
        </BotaoInteracao>
      }
      icone={AlertTriangle}
      titulo="Proteção por validade desativada"
      tom="atencao"
    >
      Ative a proteção para retirar automaticamente os lotes que vencem em até{" "}
      {controller.validadeConfig.dias || 15} dia(s) e gerar pendências aqui.
    </FaixaAviso>
  );
}

function ValidadeAtiva({ controller }) {
  return (
    <FaixaAviso
      acoes={<VerificarValidadeButton controller={controller} />}
      icone={ShieldCheck}
      titulo="Proteção por validade ativa"
      tom="sucesso"
    >
      A busca automática considera lotes que vencem em até {controller.validadeConfig.dias || 15}{" "}
      dia(s).
    </FaixaAviso>
  );
}

function ValidadePendencias({ controller }) {
  return (
    <section className="grid gap-3">
      <FaixaAviso
        acoes={<VerificarValidadeButton controller={controller} />}
        icone={AlertTriangle}
        titulo="Produtos removidos por validade"
        tom="atencao"
      >
        <span className="mr-2">Revise cada item e registre a decisão.</span>
        <Etiqueta tom="atencao">{controller.validadePendencias.length} itens</Etiqueta>
      </FaixaAviso>
      {controller.validadePendencias.map((item) => (
        <ValidadePendenciaCard key={item.id} item={item} onResolver={controller.resolverValidade} />
      ))}
    </section>
  );
}

function VerificarValidadeButton({ controller }) {
  return (
    <BotaoInteracao
      icon={RefreshCw}
      loading={controller.processandoValidade}
      onClick={() => controller.carregarValidadePendencias({ processar: true, mostrarToast: true })}
    >
      {controller.processandoValidade ? "Verificando..." : "Verificar validade agora"}
    </BotaoInteracao>
  );
}

function ValidadePendenciaCard({ item, onResolver }) {
  return (
    <article className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="m-0 font-semibold text-slate-900 dark:text-slate-100">
            {item.produto_nome || "Produto sem nome"}
          </p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Lote {item.lote_nome || item.lote_id} - vence em{" "}
            {formatarDataValidade(item.data_validade)}
          </p>
        </div>
        <div className="sm:text-right">
          <p className="m-0 font-semibold text-slate-900 dark:text-slate-100">
            {Number(item.quantidade_bloqueada || 0).toLocaleString("pt-BR")} un.
          </p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Custo estimado: {formatarMoeda(item.custo_total_estimado)}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3 dark:border-slate-800">
        <BotaoExcluir
          mensagemConfirmacao="Registrar este lote como descartado e prejuízo?"
          onClick={() => onResolver(item, "descartar")}
        >
          Descartar
        </BotaoExcluir>
        <BotaoInteracao icon={Package} onClick={() => onResolver(item, "trocar")}>
          Registrar troca
        </BotaoInteracao>
        <BotaoInteracao icon={RefreshCw} onClick={() => onResolver(item, "retornar")}>
          Retornar ao estoque
        </BotaoInteracao>
      </div>
    </article>
  );
}
