import BuscaProduto from "../../components/v2/BuscaProduto/BuscaProduto";
import { RefreshCw } from "lucide-react";
import ProductIdentity from "../../components/ui/ProductIdentity";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoLink from "../../components/v2/BotaoLink/BotaoLink";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../components/v2/InputData/InputData";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../../components/v2/SeletorOpcoes/SeletorOpcoes";
import { PERIODOS } from "./produtosRelatorioConstants";

const OPCOES_QUANTIDADE = [
  { value: "", label: "Todas as quantidades" },
  { value: "acima_de", label: "Acima de" },
  { value: "abaixo_de", label: "Abaixo de" },
  { value: "igual_a", label: "Igual a" },
];

const OPCOES_MOVIMENTACAO = [
  { value: "", label: "Todos os tipos" },
  { value: "entrada", label: "Entrada" },
  { value: "saida", label: "Saída" },
  { value: "transferencia", label: "Transferência" },
];

const OPCOES_PAGINA = [20, 50, 100].map((value) => ({ value, label: String(value) }));
const OPCOES_PERIODO = PERIODOS.map((periodo) => ({
  valor: periodo.value,
  rotulo: periodo.label,
}));

export default function ProdutosRelatorioFiltros({
  periodoSelecionado,
  filtrosForm,
  produtoSelecionado,
  buscaProduto,
  sugestoesProdutos,
  dropdownAberto,
  loadingBuscaProduto,
  buscaRef,
  erroQuantidade = "",
  onSubmit,
  onPeriodoChange,
  onDataInicioChange,
  onDataFimChange,
  onFiltroChange,
  onBuscaProdutoChange,
  onBuscaProdutoFocus,
  onLimparBuscaProduto: _onLimparBuscaProduto,
  onSelecionarProduto,
  onLimparProduto,
  onLimparFiltros,
}) {
  const unidade = produtoSelecionado?.unidade || produtoSelecionado?.unidade_medida;
  const unidadeLabel = unidade ? String(unidade).toLowerCase() : "unidade do produto";

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <SeletorOpcoes
        rotulo="Período"
        opcoes={OPCOES_PERIODO}
        valorSelecionado={periodoSelecionado}
        aoSelecionar={(valor) =>
          onPeriodoChange(PERIODOS.find((periodo) => periodo.value === valor))
        }
      />

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <InputData
          id="relatorio-data-inicio"
          label="Data início"
          value={filtrosForm.data_inicio}
          onChange={onDataInicioChange}
        />

        <InputData
          id="relatorio-data-fim"
          label="Data fim"
          value={filtrosForm.data_fim}
          onChange={onDataFimChange}
        />

        <div className="relative md:col-span-2" ref={buscaRef}>
          {produtoSelecionado ? (
            <div>
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                Produto
              </span>
              <div className="mt-1 flex min-h-9 items-center gap-3 rounded-lg border border-blue-300 bg-blue-50 px-3 py-1 dark:border-blue-700 dark:bg-blue-950">
                <div className="min-w-0 flex-1">
                  <ProductIdentity
                    product={produtoSelecionado}
                    className="max-w-full"
                    nameClassName="text-sm font-semibold text-gray-900 dark:text-slate-100"
                    codeClassName="text-xs text-gray-600 dark:text-slate-400"
                  />
                </div>
                <BotaoLink onClick={onLimparProduto}>Limpar</BotaoLink>
              </div>
            </div>
          ) : (
            <BuscaProduto
              id="relatorio-busca-produto"
              label="Produto"
              value={buscaProduto}
              onChange={onBuscaProdutoChange}
              onFocus={onBuscaProdutoFocus}
              suggestions={sugestoesProdutos}
              showSuggestions={dropdownAberto}
              loading={loadingBuscaProduto}
              onSelect={onSelecionarProduto}
              placeholder="Buscar por nome, código, SKU ou código de barras"
            />
          )}
        </div>

        <InputCombobox
          id="relatorio-tipo-movimentacao"
          label="Tipo da movimentação"
          value={filtrosForm.tipo_movimentacao}
          opcoes={OPCOES_MOVIMENTACAO}
          permitirLimpar={false}
          onChange={(value) => onFiltroChange("tipo_movimentacao", value)}
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <InputCombobox
          id="relatorio-quantidade-operador"
          label="Quantidade por item / movimentação"
          value={filtrosForm.quantidade_operador || ""}
          opcoes={OPCOES_QUANTIDADE}
          permitirLimpar={false}
          onChange={(value) => onFiltroChange("quantidade_operador", value)}
        />
        <InputTexto
          id="relatorio-quantidade-valor"
          label={`Quantidade (${unidadeLabel})`}
          inputMode="decimal"
          value={filtrosForm.quantidade_valor ?? ""}
          onChange={(value) => onFiltroChange("quantidade_valor", value)}
          disabled={!filtrosForm.quantidade_operador}
          placeholder="Ex.: 1 ou 0,5"
          error={erroQuantidade}
          help={
            unidadeLabel === "kg"
              ? "1 kg = 1. Para 500 g, informe 0,5."
              : "Informe na unidade de cadastro do produto."
          }
        />
        <p className="self-center text-xs text-slate-500 dark:text-slate-400 md:col-span-2 xl:col-span-3">
          Acima e abaixo não incluem o valor informado. Use Igual a para a quantidade exata. Para
          consultar o fracionamento vendido, veja o histórico de vendas e as movimentações de saída.
        </p>
      </div>

      <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="w-full md:w-40">
          <InputCombobox
            id="relatorio-itens-pagina"
            label="Itens por página"
            value={filtrosForm.page_size}
            opcoes={OPCOES_PAGINA}
            permitirLimpar={false}
            onChange={(value) => onFiltroChange("page_size", Number(value))}
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <BotaoCancelar onClick={onLimparFiltros}>Limpar filtros</BotaoCancelar>
          <BotaoInteracao type="submit" icon={RefreshCw}>
            Atualizar painel
          </BotaoInteracao>
        </div>
      </div>
    </form>
  );
}
