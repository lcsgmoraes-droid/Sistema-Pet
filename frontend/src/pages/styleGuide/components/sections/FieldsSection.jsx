import { useState } from "react";
import AutocompleteSelect from "../../../../components/ui/AutocompleteSelect";
import CurrencyInput from "../../../../components/CurrencyInput";
import { CheckboxField, SelectField, TextField } from "../../../../components/ui/FormField";
import QuantidadeInput from "../../../../components/QuantidadeInput";
import StyleGuideExample from "../StyleGuideExample";

const OPCOES_EXEMPLO = [
  { value: "cachorro", label: "Cachorro" },
  { value: "gato", label: "Gato" },
  { value: "ave", label: "Ave" },
];

export default function FieldsSection() {
  const [texto, setTexto] = useState("");
  const [selecao, setSelecao] = useState("");
  const [marcado, setMarcado] = useState(false);
  const [valorMonetario, setValorMonetario] = useState(0);
  const [quantidade, setQuantidade] = useState(1);
  const [combo, setCombo] = useState("");

  return (
    <>
      <StyleGuideExample
        label="TextField / SelectField / CheckboxField — components/ui/FormField.jsx (legado, ver progresso)"
        note="Já resolvem label, erro e help — mas ainda não são a base de nenhum campo mais específico."
      >
        <TextField
          label="Nome do cliente"
          placeholder="Ex.: Maria Silva"
          value={texto}
          onChange={setTexto}
          help="Campo padrão de texto com FormField por trás"
        />
        <SelectField label="Espécie" value={selecao} onChange={setSelecao}>
          <option value="">Selecione...</option>
          {OPCOES_EXEMPLO.map((opcao) => (
            <option key={opcao.value} value={opcao.value}>
              {opcao.label}
            </option>
          ))}
        </SelectField>
        <CheckboxField label="Cliente ativo" checked={marcado} onChange={setMarcado} />
      </StyleGuideExample>

      <StyleGuideExample
        label="CurrencyInput — futuro MoneyField (legado, ver progresso)"
        note="Máscara da direita para a esquerda, padrão brasileiro (1.234,56). Ainda sem label/erro padronizados."
      >
        <CurrencyInput
          aria-label="Valor de exemplo"
          value={valorMonetario}
          onChange={setValorMonetario}
          className="w-40 rounded-lg border border-slate-300 px-3 py-2 text-right text-sm dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
        />
      </StyleGuideExample>

      <StyleGuideExample
        label="QuantidadeInput — futuro QuantityField (legado, ver progresso)"
        note="Aceita vírgula ou ponto, permite digitar valores decimais livremente (ex.: 0,587)."
      >
        <label className="block">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
            Quantidade de exemplo
          </span>
          <QuantidadeInput
            value={quantidade}
            onChange={setQuantidade}
            className="mt-1 block w-28 rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
          />
        </label>
      </StyleGuideExample>

      <StyleGuideExample
        label="AutocompleteSelect — futuro ComboboxField (legado, ver progresso)"
        note="O mais completo dos campos já existentes: busca, criação de opção, limpar seleção."
      >
        <div className="w-64">
          <AutocompleteSelect
            label="Espécie (com busca)"
            options={OPCOES_EXEMPLO}
            value={combo}
            onChange={setCombo}
          />
        </div>
      </StyleGuideExample>
    </>
  );
}
