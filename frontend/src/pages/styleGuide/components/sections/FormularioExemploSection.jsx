import { useState } from "react";
import Panel from "../../../../components/ui/Panel";
import BotaoCancelar from "../../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../../../components/v2/BotaoSalva/BotaoSalva";
import InputCheck from "../../../../components/v2/InputCheck/InputCheck";
import InputCombobox from "../../../../components/v2/InputCombobox/InputCombobox";
import InputComboboxMultiplo from "../../../../components/v2/InputComboboxMultiplo/InputComboboxMultiplo";
import InputCpfCnpj from "../../../../components/v2/InputCpfCnpj/InputCpfCnpj";
import InputData from "../../../../components/v2/InputData/InputData";
import InputMoeda from "../../../../components/v2/InputMoeda/InputMoeda";
import InputPercentual from "../../../../components/v2/InputPercentual/InputPercentual";
import InputRadio from "../../../../components/v2/InputRadio/InputRadio";
import InputTelefone from "../../../../components/v2/InputTelefone/InputTelefone";
import InputTexto from "../../../../components/v2/InputTexto/InputTexto";

const CATEGORIAS = [
  { value: "varejo", label: "Varejo" },
  { value: "atacado", label: "Atacado" },
  { value: "vip", label: "VIP" },
];

const SERVICOS = [
  { value: "banho_tosa", label: "Banho e tosa" },
  { value: "veterinario", label: "Veterinário" },
  { value: "hotel", label: "Hotel/Creche" },
  { value: "adestramento", label: "Adestramento" },
];

export default function FormularioExemploSection() {
  const [nome, setNome] = useState("");
  const [documento, setDocumento] = useState("");
  const [telefone, setTelefone] = useState("");
  const [nascimento, setNascimento] = useState("");
  const [categoria, setCategoria] = useState("");
  const [servicos, setServicos] = useState(["banho_tosa"]);
  const [limite, setLimite] = useState(500);
  const [desconto, setDesconto] = useState(0);
  const [porte, setPorte] = useState("medio");
  const [ativo, setAtivo] = useState(true);

  return (
    <Panel
      title="Novo cliente"
      subtitle="Formulário de exemplo — só para auditar a distribuição real dos campos v2 lado a lado, não grava nada"
    >
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 md:grid-cols-2">
        <InputTexto
          id="form-exemplo-nome"
          label="Nome completo"
          placeholder="Ex.: Maria Silva"
          value={nome}
          onChange={setNome}
          required
        />
        <InputCpfCnpj id="form-exemplo-doc" value={documento} onChange={setDocumento} />
        <InputTelefone
          id="form-exemplo-telefone"
          label="Telefone"
          value={telefone}
          onChange={setTelefone}
        />
        <InputData
          id="form-exemplo-nascimento"
          label="Data de nascimento"
          value={nascimento}
          onChange={setNascimento}
        />
        <InputCombobox
          label="Categoria"
          opcoes={CATEGORIAS}
          value={categoria}
          onChange={setCategoria}
        />
        <InputComboboxMultiplo
          label="Serviços de interesse"
          opcoes={SERVICOS}
          value={servicos}
          onChange={setServicos}
        />
        <InputMoeda
          id="form-exemplo-limite"
          label="Limite de crédito"
          value={limite}
          onChange={setLimite}
        />
        <InputPercentual
          id="form-exemplo-desconto"
          label="Desconto padrão"
          value={desconto}
          onChange={setDesconto}
        />
        <div className="md:col-span-2">
          <InputRadio
            label="Porte de pet preferido"
            name="form-exemplo-porte"
            value={porte}
            onChange={setPorte}
            opcoes={[
              { value: "pequeno", label: "Pequeno" },
              { value: "medio", label: "Médio" },
              { value: "grande", label: "Grande" },
            ]}
          />
        </div>
        <div className="md:col-span-2">
          <InputCheck
            id="form-exemplo-ativo"
            label="Cliente ativo"
            checked={ativo}
            onChange={setAtivo}
          />
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
        <BotaoCancelar onClick={() => {}} />
        <BotaoSalva onClick={() => {}}>Salvar cliente</BotaoSalva>
      </div>
    </Panel>
  );
}
