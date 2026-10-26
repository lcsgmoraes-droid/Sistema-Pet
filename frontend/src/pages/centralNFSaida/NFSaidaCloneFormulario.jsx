import InputMoeda from "../../components/v2/InputMoeda/InputMoeda";
import InputQuantidade from "../../components/v2/InputQuantidade/InputQuantidade";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import InputTextoLongo from "../../components/v2/InputTextoLongo/InputTextoLongo";
import { formatMoneyBRL } from "../../utils/formatters";
import { totalClonagem } from "./clonagemNotaUtils";

const ROTULOS = {
  razaoSocial: "Nome / razão social",
  nome: "Nome",
  cpf: "CPF",
  cnpj: "CNPJ",
  email: "E-mail",
  telefone: "Telefone",
  inscricaoEstadual: "Inscrição estadual",
  indicadorIe: "Indicador de inscrição estadual",
  endereco: "Endereço",
  logradouro: "Logradouro",
  numero: "Número",
  bairro: "Bairro",
  municipio: "Município",
  codigoMunicipio: "Código IBGE",
  uf: "UF",
  cep: "CEP",
  complemento: "Complemento",
  pais: "País",
  codigoPais: "Código do país",
  frete: "Frete",
  modalidade: "Modalidade do frete",
  valor: "Valor",
  formaPagamento: "Forma de pagamento (código fiscal)",
  tipoIntegracao: "Tipo de integração",
  impostos: "Tributos",
  icms: "ICMS",
  pis: "PIS",
  cofins: "COFINS",
  ipi: "IPI",
  cst: "CST / CSOSN",
  origem: "Origem",
  aliquota: "Alíquota (%)",
  baseCalculo: "Base de cálculo",
  seguro: "Seguro",
  outrasDespesas: "Outras despesas",
  cest: "CEST",
  gtin: "GTIN",
  codigoProduto: "Código do produto",
  unidade: "Unidade",
  ncm: "NCM",
  cfop: "CFOP",
  informacoesFisco: "Informações ao Fisco",
  indicadorPresenca: "Indicador de presença",
  documentosReferenciados: "Documentos referenciados",
};
const MONETARIOS = new Set([
  "valor",
  "baseCalculo",
  "desconto",
  "frete",
  "seguro",
  "outrasDespesas",
]);
const CAMPOS_PRINCIPAIS = new Set([
  "emitente",
  "serie",
  "numero",
  "ambienteCodigo",
  "naturezaOperacao",
  "destinatario",
  "consumidor",
  "produtos",
  "pagamentos",
  "informacoesAdicionais",
]);

function rotulo(campo) {
  return ROTULOS[campo] || campo.replaceAll(/([a-z])([A-Z])/g, "$1 $2");
}

function Campos({ valor, caminho, alterar, disabled }) {
  return Object.entries(valor || {}).map(([campo, conteudo]) => {
    const chave = `${caminho}.${campo}`;
    const label = Array.isArray(valor) ? `Item ${Number(campo) + 1}` : rotulo(campo);
    if (conteudo && typeof conteudo === "object") {
      return (
        <fieldset
          key={chave}
          className="space-y-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700"
        >
          <legend className="px-1 text-sm font-semibold">{label}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campos valor={conteudo} caminho={chave} alterar={alterar} disabled={disabled} />
          </div>
        </fieldset>
      );
    }
    if (typeof conteudo === "number" && MONETARIOS.has(campo)) {
      return (
        <InputMoeda
          key={chave}
          label={label}
          value={conteudo}
          onChange={(novo) => alterar(chave, novo)}
          disabled={disabled}
        />
      );
    }
    return (
      <InputTexto
        key={chave}
        label={label}
        value={conteudo ?? ""}
        onChange={(novo) =>
          alterar(chave, typeof conteudo === "number" ? Number(novo.replace(",", ".")) : novo)
        }
        disabled={disabled}
      />
    );
  });
}

export default function NFSaidaCloneFormulario({ dados, alterar, disabled }) {
  const chaveCliente = dados.destinatario ? "destinatario" : "consumidor";
  const extras = Object.fromEntries(
    Object.entries(dados).filter(([campo]) => !CAMPOS_PRINCIPAIS.has(campo)),
  );
  return (
    <div className="space-y-5">
      <InputTexto
        label="Natureza da operação"
        value={dados.naturezaOperacao}
        onChange={(valor) => alterar("naturezaOperacao", valor)}
        disabled={disabled}
      />
      {dados[chaveCliente] && (
        <section className="space-y-3">
          <h4 className="font-semibold">Destinatário</h4>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campos
              valor={dados[chaveCliente]}
              caminho={chaveCliente}
              alterar={alterar}
              disabled={disabled}
            />
          </div>
        </section>
      )}
      <section className="space-y-3">
        <h4 className="font-semibold">Produtos</h4>
        {(dados.produtos || []).map((item, indice) => (
          <fieldset
            key={indice}
            className="space-y-3 rounded-lg border border-slate-200 p-3 dark:border-slate-700"
          >
            <legend className="px-1 text-sm font-semibold">
              {indice + 1}. {item.descricao}
            </legend>
            <InputTexto
              label={`Descrição do item ${indice + 1}`}
              value={item.descricao}
              onChange={(valor) => alterar(`produtos.${indice}.descricao`, valor)}
              disabled={disabled}
            />
            <div className="grid gap-3 sm:grid-cols-3">
              <InputQuantidade
                label={`Quantidade do item ${indice + 1}`}
                value={item.quantidade}
                onChange={(valor) => alterar(`produtos.${indice}.quantidade`, valor)}
                disabled={disabled}
              />
              <InputMoeda
                label={`Preço unitário do item ${indice + 1}`}
                value={item.valorUnitario}
                onChange={(valor) => alterar(`produtos.${indice}.valorUnitario`, valor)}
                disabled={disabled}
              />
              <InputMoeda
                label={`Desconto do item ${indice + 1}`}
                value={item.desconto || 0}
                onChange={(valor) => alterar(`produtos.${indice}.desconto`, valor)}
                disabled={disabled}
              />
            </div>
            <p className="text-right text-sm">
              Subtotal: {formatMoneyBRL(Number(item.valorTotal || 0) - Number(item.desconto || 0))}
            </p>
            <details className="text-sm">
              <summary className="cursor-pointer font-medium">
                Dados fiscais do item {indice + 1}
              </summary>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <Campos
                  valor={Object.fromEntries(
                    Object.entries(item).filter(
                      ([campo]) =>
                        ![
                          "descricao",
                          "quantidade",
                          "valorUnitario",
                          "valorTotal",
                          "desconto",
                        ].includes(campo),
                    ),
                  )}
                  caminho={`produtos.${indice}`}
                  alterar={alterar}
                  disabled
                />
              </div>
            </details>
          </fieldset>
        ))}
        <p className="text-right font-semibold">
          Total da nota: {formatMoneyBRL(totalClonagem(dados))}
        </p>
      </section>
      <section className="space-y-3">
        <h4 className="font-semibold">Pagamentos</h4>
        <p className="text-xs text-slate-600 dark:text-slate-300">
          Ao alterar o valor da nota, confira os pagamentos. Os tributos serão recalculados ao
          salvar o rascunho.
        </p>
        <Campos
          valor={dados.pagamentos || []}
          caminho="pagamentos"
          alterar={alterar}
          disabled={disabled}
        />
      </section>
      <InputTextoLongo
        label="Informações adicionais"
        value={dados.informacoesAdicionais || ""}
        onChange={(valor) => alterar("informacoesAdicionais", valor)}
        disabled={disabled}
        linhas={3}
      />
      {Object.keys(extras).length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer font-medium">
            Transporte e outros dados fiscais
          </summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {Object.entries(extras).map(([campo, conteudo]) => (
              <Campos
                key={campo}
                valor={{ [campo]: conteudo }}
                caminho=""
                alterar={(caminho, valor) => alterar(caminho.replace(/^\./, ""), valor)}
                disabled
              />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
