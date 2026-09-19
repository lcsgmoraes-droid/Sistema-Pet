import { useEffect, useState } from "react";
import { Pencil, Search, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getProdutos } from "../../api/produtos";
import ProductIdentity from "../../components/ui/ProductIdentity";
import ProdutosRelatorioCurvaVendas30Dias from "../produtos-relatorio/ProdutosRelatorioCurvaVendas30Dias";
import ProdutosRelatorioHistoricoVendas from "../produtos-relatorio/ProdutosRelatorioHistoricoVendas";
import ProdutosRelatorioJanelaVendaCard from "../produtos-relatorio/ProdutosRelatorioJanelaVendaCard";
import ProdutosRelatorioResumoCard from "../produtos-relatorio/ProdutosRelatorioResumoCard";
import {
  extrairListaProdutos,
  formatarData,
  formatarQuantidade,
} from "../produtos-relatorio/produtosRelatorioFormatters";

function formatarDataFiltro(valor) {
  if (!valor) return "-";
  const [ano, mes, dia] = valor.split("-");
  return `${dia}/${mes}/${ano}`;
}

function BuscaProduto({ selecionado, onSelecionar, onLimpar }) {
  const [termo, setTermo] = useState("");
  const [sugestoes, setSugestoes] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [aberto, setAberto] = useState(false);

  useEffect(() => {
    if (selecionado || termo.trim().length < 2) {
      setSugestoes([]);
      return undefined;
    }
    const timer = setTimeout(async () => {
      try {
        setCarregando(true);
        const response = await getProdutos({
          busca: termo.trim(),
          page: 1,
          page_size: 8,
          include_variations: true,
        });
        setSugestoes(extrairListaProdutos(response?.data));
      } catch (error) {
        console.error("Erro ao buscar produtos:", error);
        setSugestoes([]);
      } finally {
        setCarregando(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [selecionado, termo]);

  if (selecionado) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
        <div className="min-w-0 flex-1">
          <ProductIdentity
            product={selecionado}
            nameClassName="font-semibold text-slate-900"
            codeClassName="text-xs text-slate-500"
          />
        </div>
        <button
          type="button"
          onClick={onLimpar}
          className="rounded-lg p-2 text-slate-500 hover:bg-white hover:text-rose-600"
          aria-label="Limpar produto"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <Search className="absolute left-3 top-3.5 h-4 w-4 text-slate-400" aria-hidden="true" />
      <input
        value={termo}
        onChange={(event) => {
          setTermo(event.target.value);
          setAberto(true);
        }}
        onFocus={() => setAberto(true)}
        placeholder="Digite nome, código, SKU ou código de barras"
        className="w-full rounded-xl border border-slate-300 py-3 pl-10 pr-4 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
      />
      {aberto && termo.trim().length >= 2 && (
        <div className="absolute z-20 mt-2 max-h-80 w-full overflow-auto rounded-xl border border-slate-200 bg-white shadow-xl">
          {carregando ? (
            <p className="p-4 text-sm text-slate-500">Buscando produtos...</p>
          ) : sugestoes.length ? (
            sugestoes.map((produto) => (
              <button
                key={produto.id}
                type="button"
                onMouseDown={() => {
                  onSelecionar(produto);
                  setTermo("");
                  setAberto(false);
                }}
                className="flex w-full items-center justify-between gap-4 border-b border-slate-100 px-4 py-3 text-left last:border-0 hover:bg-blue-50"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-slate-900">
                    {produto.nome}
                  </span>
                  <span className="block truncate text-xs text-slate-500">
                    {[produto.codigo, produto.sku, produto.codigo_barras]
                      .filter(Boolean)
                      .join(" · ")}
                  </span>
                </span>
                <span className="shrink-0 text-xs text-slate-500">
                  Estoque {formatarQuantidade(produto.estoque_atual)}
                </span>
              </button>
            ))
          ) : (
            <p className="p-4 text-sm text-slate-500">Nenhum produto encontrado.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function AnaliseProdutoEspecifico({
  produtoSelecionado,
  dadosProduto,
  carregando,
  filtrosAplicados,
  pagina,
  onSelecionar,
  onLimpar,
  onPaginaChange,
}) {
  const navigate = useNavigate();
  const totalPaginas = dadosProduto?.historico_pages || 0;

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl flex-1">
            <label className="mb-2 block text-sm font-semibold text-slate-800">
              Produto para análise detalhada
            </label>
            <BuscaProduto
              selecionado={produtoSelecionado}
              onSelecionar={onSelecionar}
              onLimpar={onLimpar}
            />
            <p className="mt-2 text-xs text-slate-500">
              Histórico entre {formatarDataFiltro(filtrosAplicados.data_inicio)} e{" "}
              {formatarDataFiltro(filtrosAplicados.data_fim)}. Para mudar as datas, use os filtros
              acima.
            </p>
          </div>
          {produtoSelecionado && (
            <button
              type="button"
              onClick={() => navigate(`/produtos/${produtoSelecionado.id}/editar`)}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              <Pencil className="h-4 w-4" />
              Editar produto
            </button>
          )}
        </div>
      </div>

      {!produtoSelecionado ? (
        <div className="rounded-2xl border border-dashed border-blue-200 bg-blue-50 px-6 py-14 text-center dark:border-blue-800 dark:bg-blue-950/50">
          <p className="text-lg font-bold text-blue-950 dark:text-blue-100">
            Pesquise um produto para abrir a visão completa
          </p>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-blue-800 dark:text-blue-200">
            Você verá estoque, cobertura, médias de giro, janelas de 7 a 90 dias, ritmo diário e
            cada venda do item.
          </p>
        </div>
      ) : carregando ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-sm text-slate-500 shadow-sm">
          Carregando o desempenho do produto...
        </div>
      ) : !dadosProduto ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-sm text-slate-500">
          Não foi possível montar a análise deste produto.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <ProdutosRelatorioResumoCard
              titulo="Estoque atual"
              valor={formatarQuantidade(dadosProduto.produto?.estoque_atual)}
              descricao={`Mínimo: ${formatarQuantidade(dadosProduto.produto?.estoque_minimo)}`}
              destaque="blue"
            />
            <ProdutosRelatorioResumoCard
              titulo="Cobertura estimada"
              valor={
                dadosProduto.resumo?.ruptura_ativa
                  ? "Ruptura"
                  : dadosProduto.resumo?.cobertura_estimada_dias != null
                    ? `${formatarQuantidade(dadosProduto.resumo.cobertura_estimada_dias)} dias`
                    : "Sem base"
              }
              descricao="Calculada pelo giro médio dos últimos 30 dias."
              destaque={dadosProduto.resumo?.ruptura_ativa ? "rose" : "amber"}
            />
            <ProdutosRelatorioResumoCard
              titulo="Média diária (30 dias)"
              valor={formatarQuantidade(dadosProduto.resumo?.media_diaria_30)}
              descricao={`${formatarQuantidade(dadosProduto.resumo?.quantidade_vendida_30)} unidades vendidas`}
              destaque="emerald"
            />
            <ProdutosRelatorioResumoCard
              titulo="Última venda"
              valor={formatarData(dadosProduto.resumo?.ultima_venda?.data_venda)}
              descricao={
                dadosProduto.resumo?.dias_sem_vender != null
                  ? `${dadosProduto.resumo.dias_sem_vender} dia(s) sem vender`
                  : "Sem histórico de venda"
              }
              destaque="violet"
            />
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
            {(dadosProduto.janelas || []).map((janela) => (
              <ProdutosRelatorioJanelaVendaCard key={janela.dias} janela={janela} ativa={false} />
            ))}
          </div>
          {(dadosProduto.curva_30_dias || []).length > 0 && (
            <ProdutosRelatorioCurvaVendas30Dias pontos={dadosProduto.curva_30_dias} />
          )}
          <ProdutosRelatorioHistoricoVendas
            dadosProduto={{ ...dadosProduto, historico_page: pagina }}
            totalPaginasHistorico={totalPaginas}
            onPaginaChange={onPaginaChange}
          />
        </>
      )}
    </div>
  );
}
