import { Filter, RotateCcw, Search } from "lucide-react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../components/v2/InputData/InputData";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import SeletorOpcoes from "../../components/v2/SeletorOpcoes/SeletorOpcoes";
import { CANAIS_VENDA, PERIODOS_ANALISE } from "./analiseProdutosUtils";

const OPCOES_PERIODO = PERIODOS_ANALISE.map((periodo) => ({
  valor: periodo.id,
  rotulo: periodo.label,
}));

function opcoesCatalogo(itens, todos) {
  return [
    { value: "", label: todos },
    ...(itens || []).map((item) => ({
      value: String(item.id),
      label: item.nome || item.razao_social || item.nome_fantasia || `Registro ${item.id}`,
    })),
  ];
}

export default function AnaliseProdutosFiltros({
  catalogos,
  periodoAtivo,
  filtros,
  onPeriodoChange,
  onChange,
  onSubmit,
  onLimpar,
}) {
  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <SeletorOpcoes
          rotulo="Períodos rápidos"
          opcoes={OPCOES_PERIODO}
          valorSelecionado={periodoAtivo}
          aoSelecionar={(valor) =>
            onPeriodoChange(PERIODOS_ANALISE.find((periodo) => periodo.id === valor))
          }
        />
        <p className="text-xs text-slate-500 dark:text-slate-400">
          A comparação usa o período anterior com a mesma quantidade de dias.
        </p>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <InputData
          id="analise-produtos-data-inicio"
          label="Data inicial"
          value={filtros.data_inicio}
          onChange={(valor) => onChange("data_inicio", valor)}
        />
        <InputData
          id="analise-produtos-data-fim"
          label="Data final"
          value={filtros.data_fim}
          onChange={(valor) => onChange("data_fim", valor)}
        />
        <InputCombobox
          id="analise-produtos-categoria"
          label="Categoria"
          value={filtros.categoria_id}
          opcoes={opcoesCatalogo(catalogos.categorias, "Todas as categorias")}
          placeholder="Todas as categorias"
          onChange={(valor) => onChange("categoria_id", valor)}
        />
        <InputCombobox
          id="analise-produtos-marca"
          label="Marca"
          value={filtros.marca_id}
          opcoes={opcoesCatalogo(catalogos.marcas, "Todas as marcas")}
          placeholder="Todas as marcas"
          onChange={(valor) => onChange("marca_id", valor)}
        />
        <InputCombobox
          id="analise-produtos-departamento"
          label="Departamento"
          value={filtros.departamento_id}
          opcoes={opcoesCatalogo(catalogos.departamentos, "Todos os departamentos")}
          placeholder="Todos os departamentos"
          onChange={(valor) => onChange("departamento_id", valor)}
        />
        <InputCombobox
          id="analise-produtos-fornecedor"
          label="Fornecedor"
          value={filtros.fornecedor_id}
          opcoes={opcoesCatalogo(catalogos.fornecedores, "Todos os fornecedores")}
          placeholder="Todos os fornecedores"
          onChange={(valor) => onChange("fornecedor_id", valor)}
        />
        <InputCombobox
          id="analise-produtos-canal"
          label="Canal de venda"
          value={filtros.canal}
          opcoes={CANAIS_VENDA}
          placeholder="Todos os canais"
          onChange={(valor) => onChange("canal", valor)}
        />
        <InputTexto
          id="analise-produtos-busca"
          type="search"
          label="Produto"
          value={filtros.busca}
          onChange={(valor) => onChange("busca", valor)}
          placeholder="Nome, código ou código de barras"
          left={<Search className="h-4 w-4" aria-hidden="true" />}
        />
      </div>

      <div className="mt-5 flex flex-wrap justify-end gap-3">
        <BotaoInteracao icon={RotateCcw} onClick={onLimpar}>
          Limpar
        </BotaoInteracao>
        <BotaoInteracao type="submit" icon={Filter}>
          Aplicar filtros
        </BotaoInteracao>
      </div>
    </form>
  );
}
