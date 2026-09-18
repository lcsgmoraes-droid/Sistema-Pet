import { useState } from "react";
import { toast } from "react-hot-toast";
import BotaoCancelar from "../../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoExcluir from "../../../../components/v2/BotaoExcluir/BotaoExcluir";
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
  const [servicos, setServicos] = useState([]);
  const [limite, setLimite] = useState(500);
  const [desconto, setDesconto] = useState(0);
  const [porte, setPorte] = useState("medio");
  const [ativo, setAtivo] = useState(true);
  const [erros, setErros] = useState({});

  const validar = () => {
    const novosErros = {};
    if (!nome.trim()) novosErros.nome = "Informe o nome completo.";
    if (!documento.trim()) novosErros.documento = "Informe um CPF ou CNPJ.";
    if (!telefone.trim()) novosErros.telefone = "Informe um telefone de contato.";
    if (!nascimento) novosErros.nascimento = "Informe a data de nascimento.";
    if (!categoria) novosErros.categoria = "Selecione uma categoria.";
    if (servicos.length === 0) novosErros.servicos = "Selecione pelo menos um serviço.";
    return novosErros;
  };

  const aoSalvar = () => {
    const novosErros = validar();
    setErros(novosErros);
    if (Object.keys(novosErros).length > 0) {
      toast.error("Corrija os campos destacados antes de salvar.");
      return;
    }
    toast.success("Cliente salvo (exemplo — nada foi gravado de verdade).");
  };

  const aoCancelar = () => {
    setErros({});
    toast("Alterações descartadas (exemplo).", { icon: "↩️" });
  };

  const aoExcluir = () => {
    toast.success("Cliente excluído (exemplo — nada foi apagado de verdade).");
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-4">
        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Novo cliente</h3>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Formulário de exemplo — não grava nada de verdade. Clique em "Salvar cliente" vazio para
          ver o estado de erro de cada campo obrigatório.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-x-6 gap-y-4 md:grid-cols-2">
        <InputTexto
          id="form-exemplo-nome"
          label="Nome completo"
          placeholder="Ex.: Maria Silva"
          value={nome}
          onChange={setNome}
          error={erros.nome}
          required
        />
        <InputCpfCnpj
          id="form-exemplo-doc"
          value={documento}
          onChange={setDocumento}
          error={erros.documento}
          required
        />
        <InputTelefone
          id="form-exemplo-telefone"
          label="Telefone"
          value={telefone}
          onChange={setTelefone}
          error={erros.telefone}
          required
        />
        <InputData
          id="form-exemplo-nascimento"
          label="Data de nascimento"
          value={nascimento}
          onChange={setNascimento}
          error={erros.nascimento}
          required
        />
        <InputCombobox
          label="Categoria"
          opcoes={CATEGORIAS}
          value={categoria}
          onChange={setCategoria}
          error={erros.categoria}
          required
        />
        <InputComboboxMultiplo
          label="Serviços de interesse"
          opcoes={SERVICOS}
          value={servicos}
          onChange={setServicos}
          error={erros.servicos}
          required
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

      <div className="mt-6 flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
        <BotaoExcluir onClick={aoExcluir} />
        <BotaoCancelar onClick={aoCancelar} />
        <BotaoSalva onClick={aoSalvar}>Salvar cliente</BotaoSalva>
      </div>
    </div>
  );
}
