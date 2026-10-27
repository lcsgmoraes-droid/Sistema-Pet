import { Plus } from "lucide-react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCheck from "../../components/v2/InputCheck/InputCheck";
import InputMoeda from "../../components/v2/InputMoeda/InputMoeda";
import InputPercentual from "../../components/v2/InputPercentual/InputPercentual";
import InputRadio from "../../components/v2/InputRadio/InputRadio";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import { COMMISSION_ITEM_ICONS } from "./comissoesConstants";

export default function ComissaoSelectedItemPanel({
  adicionarConfiguracao,
  itemSelecionado,
  salvarItem,
  setItemSelecionado,
  ocultarAdicionar = false,
  salvando = false,
}) {
  if (!itemSelecionado) {
    return (
      <div className="rounded-lg border p-8 text-center text-slate-500 dark:border-slate-700 dark:text-slate-300">
        Selecione a regra geral, uma categoria, subcategoria ou produto ao lado para configurar
      </div>
    );
  }
  const atualizar = (campo, valor) => setItemSelecionado({ ...itemSelecionado, [campo]: valor });
  return (
    <div className="space-y-4 rounded-lg border p-4 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">
      <h4 className="font-medium">
        {COMMISSION_ITEM_ICONS[itemSelecionado.tipo]} {itemSelecionado.nome}
      </h4>
      <InputRadio
        name="tipo-comissao"
        label="Tipo de Comissão"
        value={itemSelecionado.tipo_calculo}
        opcoes={[
          { value: "percentual", label: "Percentual sobre venda" },
          { value: "lucro", label: "Divisão de lucro" },
          { value: "fixo", label: "Valor fixo por unidade" },
        ]}
        onChange={(valor) => atualizar("tipo_calculo", valor)}
      />
      {itemSelecionado.tipo_calculo === "fixo" ? (
        <InputMoeda
          id="comissao-valor-fixo"
          label="Valor por unidade vendida (R$)"
          value={itemSelecionado.valor_fixo}
          onChange={(valor) => atualizar("valor_fixo", valor)}
          help="Multiplicado pela quantidade vendida. Quantidades fracionadas e pagamentos parciais são proporcionais; taxas não reduzem este valor."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <InputPercentual
            id="comissao-percentual"
            label={itemSelecionado.tipo_calculo === "lucro" ? "Parceiro (%)" : "Percentual"}
            value={itemSelecionado.percentual}
            onChange={(valor) =>
              setItemSelecionado({
                ...itemSelecionado,
                percentual: valor,
                percentual_loja: 100 - valor,
              })
            }
          />
          {itemSelecionado.tipo_calculo === "lucro" && (
            <InputPercentual
              id="comissao-loja"
              label="Loja (%)"
              value={itemSelecionado.percentual_loja}
              disabled
              help="Preço − descontos − taxas − impostos − custo = lucro."
            />
          )}
        </div>
      )}
      {itemSelecionado.tipo_calculo !== "fixo" && (
        <InputCheck
          id="comissao-edicao-venda"
          label="Permitir editar percentual na venda"
          checked={itemSelecionado.permite_edicao_venda}
          onChange={(valor) => atualizar("permite_edicao_venda", valor)}
        />
      )}
      <InputTextoLongo
        id="comissao-observacoes"
        label="Observações"
        value={itemSelecionado.observacoes}
        onChange={(valor) => atualizar("observacoes", valor)}
        linhas={3}
      />
      <div className="flex flex-wrap gap-2">
        {!ocultarAdicionar && (
          <BotaoInteracao icon={Plus} onClick={adicionarConfiguracao} disabled={salvando}>
            Adicionar à lista
          </BotaoInteracao>
        )}
        <BotaoSalva type="button" onClick={salvarItem} disabled={salvando} loading={salvando}>
          Salvar agora
        </BotaoSalva>
      </div>
    </div>
  );
}
