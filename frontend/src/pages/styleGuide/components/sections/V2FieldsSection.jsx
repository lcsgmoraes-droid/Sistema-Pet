import { Eye } from "lucide-react";
import { useState } from "react";
import InputCheck from "../../../../components/v2/InputCheck/InputCheck";
import InputCombobox from "../../../../components/v2/InputCombobox/InputCombobox";
import InputComboboxMultiplo from "../../../../components/v2/InputComboboxMultiplo/InputComboboxMultiplo";
import InputCpfCnpj from "../../../../components/v2/InputCpfCnpj/InputCpfCnpj";
import InputData from "../../../../components/v2/InputData/InputData";
import InputDataHora from "../../../../components/v2/InputDataHora/InputDataHora";
import InputMoeda from "../../../../components/v2/InputMoeda/InputMoeda";
import InputPercentual from "../../../../components/v2/InputPercentual/InputPercentual";
import InputPeriodo from "../../../../components/v2/InputPeriodo/InputPeriodo";
import InputQuantidade from "../../../../components/v2/InputQuantidade/InputQuantidade";
import InputRadio from "../../../../components/v2/InputRadio/InputRadio";
import InputSenha from "../../../../components/v2/InputSenha/InputSenha";
import InputTelefone from "../../../../components/v2/InputTelefone/InputTelefone";
import InputTexto from "../../../../components/v2/InputTexto/InputTexto";
import BotaoAjuda from "../../../../components/v2/BotaoAjuda/BotaoAjuda";
import BotaoCancelar from "../../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoExcluir from "../../../../components/v2/BotaoExcluir/BotaoExcluir";
import BotaoInteracao from "../../../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../../../components/v2/BotaoSalva/BotaoSalva";
import StyleGuideExample from "../StyleGuideExample";

const ESPECIES = [
  { value: "cachorro", label: "Cachorro" },
  { value: "gato", label: "Gato" },
  { value: "ave", label: "Ave" },
  { value: "roedor", label: "Roedor" },
];

export default function V2FieldsSection() {
  const [nome, setNome] = useState("");
  const [senha, setSenha] = useState("");
  const [data, setData] = useState("");
  const [dataHora, setDataHora] = useState("");
  const [periodo, setPeriodo] = useState({ inicio: "", fim: "" });
  const [ativo, setAtivo] = useState(true);
  const [porte, setPorte] = useState("medio");
  const [preco, setPreco] = useState(129.9);
  const [quantidade, setQuantidade] = useState(1);
  const [margem, setMargem] = useState(35);
  const [telefone, setTelefone] = useState("");
  const [documento, setDocumento] = useState("");
  const [especie, setEspecie] = useState("");
  const [especiesAtendidas, setEspeciesAtendidas] = useState(["cachorro"]);

  return (
    <>
      <StyleGuideExample label="InputTexto — base de todos os campos de texto (v2)">
        <div className="w-64">
          <InputTexto
            id="v2-nome"
            label="Nome do cliente"
            placeholder="Ex.: Maria Silva"
            value={nome}
            onChange={setNome}
            required
          />
        </div>
      </StyleGuideExample>

      <StyleGuideExample label="InputSenha — reaproveita o InputTexto, adiciona mostrar/ocultar">
        <div className="w-64">
          <InputSenha id="v2-senha" value={senha} onChange={setSenha} />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="InputData / InputDataHora — máscara dd/mm/aaaa, valor exposto em ISO"
        note="Abre um calendário ao focar o campo ou clicar no ícone — digitar continua funcionando normalmente."
      >
        <div className="w-40">
          <InputData id="v2-data" label="Data de nascimento" value={data} onChange={setData} />
        </div>
        <div className="w-56">
          <InputDataHora
            id="v2-data-hora"
            label="Agendamento"
            value={dataHora}
            onChange={setDataHora}
          />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="InputPeriodo — compõe dois InputData (De/Até)"
        note="Cada lado abre seu próprio calendário (herdado do InputData). Um seletor único com sombreado do intervalo é uma evolução futura, não implementada ainda."
      >
        <div className="w-full max-w-sm">
          <InputPeriodo label="Período do relatório" value={periodo} onChange={setPeriodo} />
        </div>
      </StyleGuideExample>

      <StyleGuideExample label="InputCheck / InputRadio">
        <InputCheck id="v2-ativo" label="Cliente ativo" checked={ativo} onChange={setAtivo} />
        <div className="w-full max-w-xs">
          <InputRadio
            label="Porte"
            name="v2-porte"
            value={porte}
            onChange={setPorte}
            opcoes={[
              { value: "pequeno", label: "Pequeno" },
              { value: "medio", label: "Médio" },
              { value: "grande", label: "Grande" },
            ]}
          />
        </div>
      </StyleGuideExample>

      <StyleGuideExample label="InputMoeda / InputQuantidade / InputPercentual">
        <div className="w-36">
          <InputMoeda id="v2-preco" label="Preço" value={preco} onChange={setPreco} />
        </div>
        <div className="w-28">
          <InputQuantidade
            id="v2-qtd"
            label="Quantidade"
            value={quantidade}
            onChange={setQuantidade}
          />
        </div>
        <div className="w-32">
          <InputPercentual id="v2-margem" label="Margem" value={margem} onChange={setMargem} />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="InputTelefone / InputCpfCnpj — máscara progressiva, detecção automática"
        note="InputCpfCnpj já aceita o CNPJ alfanumérico (Receita Federal, 2026) — letras nas 12 primeiras posições, os 2 dígitos verificadores finais continuam numéricos."
      >
        <div className="w-48">
          <InputTelefone
            id="v2-telefone"
            label="Telefone"
            value={telefone}
            onChange={setTelefone}
          />
        </div>
        <div className="w-56">
          <InputCpfCnpj id="v2-doc" value={documento} onChange={setDocumento} />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="InputCombobox — busca, teclado, limpar seleção"
        note='Ghost selection: digite um prefixo (ex.: "cach") e o restante da melhor opção aparece esmaecido — Tab confirma direto, sem precisar abrir a lista.'
      >
        <div className="w-64">
          <InputCombobox label="Espécie" opcoes={ESPECIES} value={especie} onChange={setEspecie} />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="InputComboboxMultiplo — mesma busca, várias seleções em chips"
        note="Backspace com o campo de busca vazio remove o último chip. Sem ghost selection aqui (a fila de chips quebrando linha dificulta alinhar o texto fantasma com precisão)."
      >
        <div className="w-72">
          <InputComboboxMultiplo
            label="Espécies atendidas"
            opcoes={ESPECIES}
            value={especiesAtendidas}
            onChange={setEspeciesAtendidas}
          />
        </div>
      </StyleGuideExample>

      <StyleGuideExample
        label="Botões v2 — um componente por ação, sem prop de cor/tamanho para a página escolher"
        note="BotaoExcluir já pede confirmação (via corepetDialog) antes de chamar onClick — nenhuma tela precisa implementar isso de novo."
      >
        <BotaoSalva onClick={() => {}}>Salvar cliente</BotaoSalva>
        <BotaoCancelar onClick={() => {}} />
        <BotaoExcluir onClick={() => {}} />
        <BotaoInteracao icon={Eye} onClick={() => {}}>
          Ver detalhes
        </BotaoInteracao>
        <BotaoAjuda texto="Ajuda sobre este formulário" />
      </StyleGuideExample>
    </>
  );
}
