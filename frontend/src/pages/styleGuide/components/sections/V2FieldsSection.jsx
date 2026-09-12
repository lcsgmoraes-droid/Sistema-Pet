import { Eye } from "lucide-react";
import { useState } from "react";
import BotaoAjuda from "../../../../components/v2/BotaoAjuda/BotaoAjuda";
import BotaoCancelar from "../../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoExcluir from "../../../../components/v2/BotaoExcluir/BotaoExcluir";
import BotaoInteracao from "../../../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../../../../components/v2/BotaoSalva/BotaoSalva";
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
import StyleGuideExample from "../StyleGuideExample";

const ESPECIES = [
  { value: "cachorro", label: "Cachorro" },
  { value: "gato", label: "Gato" },
  { value: "ave", label: "Ave" },
  { value: "roedor", label: "Roedor" },
];

const MENSAGEM_ERRO = "Este campo é obrigatório.";

function Grupo({ label, note, children }) {
  return (
    <StyleGuideExample label={label} note={note}>
      <div className="grid w-full grid-cols-1 gap-4 sm:grid-cols-3">{children}</div>
    </StyleGuideExample>
  );
}

function Estado({ titulo, children }) {
  return (
    <div>
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
        {titulo}
      </div>
      {children}
    </div>
  );
}

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
      {/* ---------- Botões ---------- */}
      <Grupo
        label="Botões — um componente por ação, sem prop de cor para a página escolher (só tamanho, num enum fechado)"
        note="Ícone-only exige título/aria-label obrigatório para acessibilidade: BotaoAjuda já resolve isso sozinho (prop texto sempre tem um valor); se usar BotaoInteracao só com ícone (sem texto), passe aria-label manualmente."
      >
        <Estado titulo="Ativo">
          <div className="flex flex-wrap items-center gap-2">
            <BotaoSalva onClick={() => {}}>Salvar</BotaoSalva>
            <BotaoCancelar onClick={() => {}} />
            <BotaoExcluir onClick={() => {}} />
            <BotaoInteracao icon={Eye} onClick={() => {}}>
              Ver detalhes
            </BotaoInteracao>
            <BotaoAjuda texto="Ajuda sobre este formulário" />
          </div>
        </Estado>
        <Estado titulo="Desabilitado">
          <div className="flex flex-wrap items-center gap-2">
            <BotaoSalva disabled>Salvar</BotaoSalva>
            <BotaoCancelar disabled />
            <BotaoInteracao icon={Eye} disabled>
              Ver detalhes
            </BotaoInteracao>
          </div>
        </Estado>
        <Estado titulo="Carregando (BotaoSalva)">
          <BotaoSalva loading>Salvando...</BotaoSalva>
        </Estado>
      </Grupo>

      <Grupo
        label='Botões — 3 tamanhos (todo Botao* e BotaoAjuda aceitam tamanho="pequeno"|"normal"|"grande")'
        note='Enum fechado, não é escala livre. "pequeno" fica abaixo do alvo de toque de 44px recomendado — uso pensado para densidade em desktop (barra de ferramentas), não para telas majoritariamente touch.'
      >
        <Estado titulo="Pequeno">
          <div className="flex flex-wrap items-center gap-2">
            <BotaoSalva tamanho="pequeno" onClick={() => {}}>
              Salvar
            </BotaoSalva>
            <BotaoAjuda tamanho="pequeno" texto="Ajuda" />
          </div>
        </Estado>
        <Estado titulo="Normal (padrão)">
          <div className="flex flex-wrap items-center gap-2">
            <BotaoSalva onClick={() => {}}>Salvar</BotaoSalva>
            <BotaoAjuda texto="Ajuda" />
          </div>
        </Estado>
        <Estado titulo="Grande">
          <div className="flex flex-wrap items-center gap-2">
            <BotaoSalva tamanho="grande" onClick={() => {}}>
              Salvar
            </BotaoSalva>
            <BotaoAjuda tamanho="grande" texto="Ajuda" />
          </div>
        </Estado>
        <Estado titulo='Largura total (prop "larguraTotal", usado no botão "Entrar" do Login)'>
          <BotaoInteracao icon={Eye} tamanho="grande" larguraTotal onClick={() => {}}>
            Ocupa toda a largura disponível
          </BotaoInteracao>
        </Estado>
      </Grupo>

      {/* ---------- InputTexto ---------- */}
      <Grupo label="InputTexto — base de todos os campos de texto">
        <Estado titulo="Ativo">
          <InputTexto
            id="v2-nome"
            label="Nome do cliente"
            placeholder="Ex.: Maria Silva"
            value={nome}
            onChange={setNome}
          />
        </Estado>
        <Estado titulo="Com erro">
          <InputTexto
            id="v2-nome-erro"
            label="Nome do cliente"
            value=""
            onChange={() => {}}
            error={MENSAGEM_ERRO}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputTexto
            id="v2-nome-disabled"
            label="Nome do cliente"
            value="Maria Silva"
            onChange={() => {}}
            disabled
          />
        </Estado>
      </Grupo>

      {/* ---------- InputSenha ---------- */}
      <Grupo label="InputSenha — reaproveita o InputTexto, adiciona mostrar/ocultar">
        <Estado titulo="Ativo">
          <InputSenha id="v2-senha" value={senha} onChange={setSenha} />
        </Estado>
        <Estado titulo="Com erro">
          <InputSenha
            id="v2-senha-erro"
            value="123"
            onChange={() => {}}
            error="Senha muito curta."
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputSenha id="v2-senha-disabled" value="••••••••" onChange={() => {}} disabled />
        </Estado>
      </Grupo>

      {/* ---------- InputData / InputDataHora ---------- */}
      <Grupo
        label="InputData / InputDataHora — máscara dd/mm/aaaa, valor exposto em ISO"
        note="Abre um calendário ao focar o campo ou clicar no ícone — digitar continua funcionando normalmente."
      >
        <Estado titulo="Ativo">
          <InputData id="v2-data" label="Data de nascimento" value={data} onChange={setData} />
        </Estado>
        <Estado titulo="Com erro">
          <InputData
            id="v2-data-erro"
            label="Data de nascimento"
            value=""
            onChange={() => {}}
            error={MENSAGEM_ERRO}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputDataHora
            id="v2-data-disabled"
            label="Agendamento"
            value={dataHora || "2026-09-12T09:00"}
            onChange={setDataHora}
            disabled
          />
        </Estado>
      </Grupo>

      {/* ---------- InputPeriodo ---------- */}
      <Grupo
        label="InputPeriodo — um único campo, calendário duplo para escolher início e fim numa tacada só"
        note="Campo somente leitura — clique/foque para abrir; primeiro clique define o início, segundo define o fim, com o intervalo sombreado nos dois meses."
      >
        <Estado titulo="Ativo">
          <InputPeriodo label="Período do relatório" value={periodo} onChange={setPeriodo} />
        </Estado>
        <Estado titulo="Com erro">
          <InputPeriodo
            label="Período do relatório"
            value={{ inicio: "", fim: "" }}
            onChange={() => {}}
            error={MENSAGEM_ERRO}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputPeriodo
            label="Período do relatório"
            value={{ inicio: "2026-09-01", fim: "2026-09-10" }}
            onChange={() => {}}
            disabled
          />
        </Estado>
      </Grupo>

      {/* ---------- InputCheck ---------- */}
      <Grupo label="InputCheck — aparência de botão, label centralizada, mesma altura dos demais campos (h-9)">
        <Estado titulo="Ativo">
          <InputCheck id="v2-ativo" label="Cliente ativo" checked={ativo} onChange={setAtivo} />
        </Estado>
        <Estado titulo="Com erro">
          <InputCheck
            id="v2-ativo-erro"
            label="Cliente ativo"
            checked={false}
            onChange={() => {}}
            error={MENSAGEM_ERRO}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputCheck
            id="v2-ativo-disabled"
            label="Cliente ativo"
            checked
            disabled
            onChange={() => {}}
          />
        </Estado>
      </Grupo>

      {/* ---------- InputRadio ---------- */}
      <Grupo label="InputRadio — aparência de botão, label centralizada, mesma altura dos demais campos (h-9)">
        <Estado titulo="Ativo">
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
        </Estado>
        <Estado titulo="Com erro">
          <InputRadio
            label="Porte"
            name="v2-porte-erro"
            value=""
            onChange={() => {}}
            error={MENSAGEM_ERRO}
            opcoes={[
              { value: "pequeno", label: "Pequeno" },
              { value: "medio", label: "Médio" },
            ]}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputRadio
            label="Porte"
            name="v2-porte-disabled"
            value="medio"
            onChange={() => {}}
            disabled
            opcoes={[
              { value: "pequeno", label: "Pequeno" },
              { value: "medio", label: "Médio" },
            ]}
          />
        </Estado>
      </Grupo>

      {/* ---------- InputMoeda / InputQuantidade / InputPercentual ---------- */}
      <Grupo label="InputMoeda / InputQuantidade / InputPercentual — texto alinhado à direita">
        <Estado titulo="Ativo">
          <div className="flex flex-wrap gap-3">
            <InputMoeda id="v2-preco" label="Preço" value={preco} onChange={setPreco} />
            <InputQuantidade
              id="v2-qtd"
              label="Quantidade"
              value={quantidade}
              onChange={setQuantidade}
            />
            <InputPercentual id="v2-margem" label="Margem" value={margem} onChange={setMargem} />
          </div>
        </Estado>
        <Estado titulo="Com erro">
          <InputMoeda
            id="v2-preco-erro"
            label="Preço"
            value={0}
            onChange={() => {}}
            error={MENSAGEM_ERRO}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputMoeda
            id="v2-preco-disabled"
            label="Preço"
            value={129.9}
            onChange={() => {}}
            disabled
          />
        </Estado>
      </Grupo>

      {/* ---------- InputTelefone / InputCpfCnpj ---------- */}
      <Grupo
        label="InputTelefone / InputCpfCnpj — máscara progressiva, detecção automática"
        note="InputCpfCnpj já aceita o CNPJ alfanumérico (Receita Federal, 2026) — letras nas 12 primeiras posições, os 2 dígitos verificadores finais continuam numéricos."
      >
        <Estado titulo="Ativo">
          <div className="flex flex-wrap gap-3">
            <InputTelefone
              id="v2-telefone"
              label="Telefone"
              value={telefone}
              onChange={setTelefone}
            />
            <InputCpfCnpj id="v2-doc" value={documento} onChange={setDocumento} />
          </div>
        </Estado>
        <Estado titulo="Com erro">
          <InputCpfCnpj id="v2-doc-erro" value="" onChange={() => {}} error={MENSAGEM_ERRO} />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputTelefone
            id="v2-telefone-disabled"
            label="Telefone"
            value="(11) 98888-7777"
            onChange={() => {}}
            disabled
          />
        </Estado>
      </Grupo>

      {/* ---------- InputCombobox ---------- */}
      <Grupo
        label="InputCombobox — busca, teclado, limpar seleção"
        note='Ghost selection: digite um prefixo (ex.: "cach") e o restante da melhor opção aparece esmaecido — Tab confirma direto, sem precisar abrir a lista.'
      >
        <Estado titulo="Ativo">
          <InputCombobox label="Espécie" opcoes={ESPECIES} value={especie} onChange={setEspecie} />
        </Estado>
        <Estado titulo="Com erro">
          <InputCombobox
            label="Espécie"
            opcoes={ESPECIES}
            value=""
            onChange={() => {}}
            error={MENSAGEM_ERRO}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputCombobox
            label="Espécie"
            opcoes={ESPECIES}
            value="cachorro"
            onChange={() => {}}
            disabled
          />
        </Estado>
      </Grupo>

      {/* ---------- InputComboboxMultiplo ---------- */}
      <Grupo
        label="InputComboboxMultiplo — mesma busca, várias seleções em chips"
        note="Ghost selection igual ao InputCombobox — mas aqui Tab adiciona o item como chip e mantém o foco no campo, pronto pro próximo. Backspace com a busca vazia remove o último chip."
      >
        <Estado titulo="Ativo">
          <InputComboboxMultiplo
            label="Espécies atendidas"
            opcoes={ESPECIES}
            value={especiesAtendidas}
            onChange={setEspeciesAtendidas}
          />
        </Estado>
        <Estado titulo="Com erro">
          <InputComboboxMultiplo
            label="Espécies atendidas"
            opcoes={ESPECIES}
            value={[]}
            onChange={() => {}}
            error={MENSAGEM_ERRO}
          />
        </Estado>
        <Estado titulo="Desabilitado">
          <InputComboboxMultiplo
            label="Espécies atendidas"
            opcoes={ESPECIES}
            value={["cachorro", "gato"]}
            onChange={() => {}}
            disabled
          />
        </Estado>
      </Grupo>
    </>
  );
}
