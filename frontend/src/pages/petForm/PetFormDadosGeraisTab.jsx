import BuscaPessoa from "../../components/v2/BuscaPessoa/BuscaPessoa";
import useBuscaEntidadeLocal from "../../components/v2/BuscaEntidade/useBuscaEntidadeLocal";
import { Plus } from "lucide-react";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCheckTexto from "../../components/v2/InputCheckTexto/InputCheckTexto";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputData from "../../components/v2/InputData/InputData";
import InputRadio from "../../components/v2/InputRadio/InputRadio";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";

const OPCOES_SEXO = [
  { value: "Macho", label: "Macho" },
  { value: "Fêmea", label: "Fêmea" },
];

export default function PetFormDadosGeraisTab({
  abrirQuickAdd,
  clientes,
  clienteIdPreSelecionado,
  erros,
  especies,
  especieSelecionadaAtual,
  formData,
  handleEspecieChange,
  isEditing,
  onChangeCastrado,
  racas,
  setField,
}) {
  const buscaTutor = useBuscaEntidadeLocal({
    itens: clientes,
    valueId: formData.cliente_id,
    onChangeId: setField("cliente_id"),
    tipo: "pessoa",
  });
  const opcoesEspecies = especies.map((especie) => ({
    value: String(especie.id),
    label: especie.nome,
  }));
  const opcoesRacas = racas.map((raca) => ({ value: raca.nome, label: raca.nome }));
  // Cadastros antigos podem ter uma raça que não está mais no catálogo ativo.
  // O combobox precisa dessa opção para exibir o valor que o pet já possui.
  if (formData.raca && !opcoesRacas.some((opcao) => opcao.value === formData.raca)) {
    opcoesRacas.unshift({ value: formData.raca, label: formData.raca });
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
        <div className="w-full sm:max-w-sm">
          <BuscaPessoa
            {...buscaTutor}
            id="pet-cliente"
            label="Cliente (Tutor)"
            placeholder="Selecione o tutor..."
            required
            error={erros.cliente_id}
          />
          {clienteIdPreSelecionado && (
            <p className="mt-1 text-xs text-blue-600">Tutor selecionado automaticamente</p>
          )}
        </div>

        <div className="w-full sm:max-w-[220px]">
          <InputTexto
            id="pet-nome"
            label="Nome do Pet"
            value={formData.nome}
            onChange={setField("nome")}
            required
            error={erros.nome}
            placeholder="Ex: Rex, Miau, Totó"
          />
        </div>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-start">
        <div className="w-full sm:max-w-[200px]">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <InputCombobox
                id="pet-especie"
                label="Espécie"
                opcoes={opcoesEspecies}
                value={formData.especie}
                onChange={handleEspecieChange}
                placeholder="Selecione..."
                required
                error={erros.especie}
              />
            </div>
            <BotaoInteracao
              icon={Plus}
              onClick={() => abrirQuickAdd("especie")}
              tamanho="normal"
              aria-label="Nova espécie"
            >
              Nova
            </BotaoInteracao>
          </div>
          {especies.length === 0 && (
            <p className="mt-1 text-xs text-amber-800">
              Nenhuma espécie cadastrada. Cadastre em Cadastros → Espécies e Raças.
            </p>
          )}
        </div>

        <div className="w-full sm:max-w-[200px]">
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <InputCombobox
                id="pet-raca"
                label="Raça"
                opcoes={opcoesRacas}
                value={formData.raca}
                onChange={setField("raca")}
                placeholder={
                  !formData.especie ? "Selecione uma espécie primeiro" : "Selecione uma raça..."
                }
                disabled={!formData.especie}
              />
            </div>
            <BotaoInteracao
              icon={Plus}
              onClick={() => abrirQuickAdd("raca")}
              tamanho="normal"
              disabled={!formData.especie}
              aria-label="Nova raça"
            >
              Nova
            </BotaoInteracao>
          </div>
          {formData.especie && racas.length === 0 && (
            <p className="mt-1 text-xs text-amber-800">
              Nenhuma raça cadastrada para{" "}
              {especieSelecionadaAtual?.nome || "a espécie selecionada"}.
            </p>
          )}
        </div>

        <div className="w-full sm:w-auto">
          <InputRadio
            name="sexo"
            label="Sexo"
            opcoes={OPCOES_SEXO}
            value={formData.sexo}
            onChange={setField("sexo")}
          />
        </div>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
        <InputCheckTexto id="pet-castrado" checked={formData.castrado} onChange={onChangeCastrado}>
          Pet castrado
        </InputCheckTexto>

        {formData.castrado && (
          <div className="w-full sm:max-w-[180px]">
            <InputData
              id="pet-castrado-data"
              label="Data da castração"
              value={formData.castrado_data}
              onChange={setField("castrado_data")}
            />
          </div>
        )}
      </div>

      <InputTextoLongo
        id="pet-observacoes"
        label="Observações Gerais"
        value={formData.observacoes}
        onChange={setField("observacoes")}
        linhas={4}
        placeholder="Informações adicionais, comportamento, preferências, etc"
      />

      {isEditing && (
        <InputCheckTexto id="pet-ativo" checked={formData.ativo} onChange={setField("ativo")}>
          Pet ativo no sistema
        </InputCheckTexto>
      )}
    </div>
  );
}
