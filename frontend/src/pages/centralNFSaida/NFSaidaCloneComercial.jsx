import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputCpfCnpj from "../../components/v2/InputCpfCnpj/InputCpfCnpj";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import { canalComercialClone, CNPJ_PUBLICO_AMAZON, FONTE_CNPJ_AMAZON } from "./clonagemNotaUtils";

export default function NFSaidaCloneComercial({ dados, modelo, alterar, alterarCanal, disabled }) {
  if (Number(modelo) !== 55) return null;
  const canal = canalComercialClone(dados);
  const opcoes = [
    { value: "loja_fisica", label: "PDV / loja física" },
    { value: "venda_direta_online", label: "Venda direta pela internet" },
    { value: "amazon", label: "Amazon" },
  ];
  if (canal === "preservar")
    opcoes.push({ value: canal, label: "Preservar presença da nota original" });
  if (canal === "intermediacao_existente")
    opcoes.push({ value: canal, label: "Outro intermediador / dados atuais" });
  return (
    <fieldset className="space-y-4 rounded-lg border border-slate-200 p-4 dark:border-slate-700">
      <legend className="px-1 font-semibold">Operação e intermediador da cópia</legend>
      <InputCombobox
        id="clone-canal-operacao"
        label="Canal da cópia"
        value={canal}
        opcoes={opcoes}
        permitirLimpar={false}
        onChange={alterarCanal}
        disabled={disabled}
      />
      <p className="text-xs text-slate-600 dark:text-slate-300">
        A opção Amazon configura uma operação pela internet. Confira o intermediador e o cadastro da
        sua loja antes de emitir.
      </p>
      {dados.intermediador && (
        <div className="space-y-3">
          <InputCpfCnpj
            label="CNPJ do intermediador da cópia"
            value={dados.intermediador.cnpj || ""}
            onChange={(valor) => alterar("intermediador.cnpj", valor)}
            disabled={disabled}
            required
            help="O CNPJ sugerido é público e pode ser ajustado conforme a operação."
          />
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <BotaoInteracao
              tamanho="pequeno"
              onClick={() => alterar("intermediador.cnpj", CNPJ_PUBLICO_AMAZON)}
              disabled={disabled}
            >
              Usar CNPJ público da Amazon
            </BotaoInteracao>
            <LinkPadrao href={FONTE_CNPJ_AMAZON} novaJanela>
              Fonte do CNPJ público
            </LinkPadrao>
          </div>
          <InputTexto
            label="Identificação da loja ou vendedor no intermediador"
            value={dados.intermediador.identificadorCadastro || ""}
            onChange={(valor) => alterar("intermediador.identificadorCadastro", valor)}
            disabled={disabled}
            required
            maxLength={60}
            help="Informe o código de cadastro da loja ou vendedor (Seller ID). Este campo corresponde ao idCadIntTran e é diferente do número do pedido."
          />
        </div>
      )}
    </fieldset>
  );
}
