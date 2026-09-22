import ClienteOrigemSelect from "./ClienteOrigemSelect";
import InputCpfCnpj from "../v2/InputCpfCnpj/InputCpfCnpj";
import InputData from "../v2/InputData/InputData";
import InputRadio from "../v2/InputRadio/InputRadio";
import InputTexto from "../v2/InputTexto/InputTexto";

const OPCOES_TIPO_CADASTRO = [
  { value: "cliente", label: "Cliente" },
  { value: "fornecedor", label: "Fornecedor" },
  { value: "veterinario", label: "Veterinário" },
  { value: "funcionario", label: "Funcionário" },
];

const OPCOES_TIPO_PESSOA = [
  { value: "PF", label: "Pessoa Física" },
  { value: "PJ", label: "Pessoa Jurídica" },
];

export default function ClientePessoaDadosGeraisTab({
  erros = {},
  formData,
  onBlurCampo,
  setFormData,
}) {
  const selecionarTipoCadastro = (tipoCadastro) => {
    setFormData((prev) => {
      const perfis = new Set(prev.app_access_profiles || []);
      if (["cliente", "funcionario", "veterinario"].includes(prev.tipo_cadastro)) {
        perfis.delete(prev.tipo_cadastro);
      }
      if (["cliente", "funcionario", "veterinario"].includes(tipoCadastro)) {
        perfis.add(tipoCadastro);
      }
      return { ...prev, tipo_cadastro: tipoCadastro, app_access_profiles: Array.from(perfis) };
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="w-full sm:w-[70%]">
          <InputRadio
            name="tipo_cadastro"
            label="Tipo de cadastro"
            required
            opcoes={OPCOES_TIPO_CADASTRO}
            value={formData.tipo_cadastro}
            onChange={selecionarTipoCadastro}
          />
        </div>

        <div className="w-full sm:w-[30%]">
          <InputRadio
            name="tipo_pessoa"
            label="Tipo de pessoa"
            required
            opcoes={OPCOES_TIPO_PESSOA}
            value={formData.tipo_pessoa}
            onChange={(tipo_pessoa) => setFormData((prev) => ({ ...prev, tipo_pessoa }))}
          />
        </div>
      </div>

      {formData.tipo_pessoa === "PF" ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(220px,1fr)_200px_180px]">
            <InputTexto
              id="pessoa-nome"
              label="Nome completo"
              required
              value={formData.nome}
              error={erros.nome}
              onChange={(nome) => setFormData((prev) => ({ ...prev, nome }))}
              onBlur={() => onBlurCampo?.("nome")}
              placeholder="Digite o nome completo"
            />

            <InputCpfCnpj
              id="pessoa-cpf"
              label="CPF"
              value={formData.cpf}
              onChange={(cpf) => setFormData((prev) => ({ ...prev, cpf }))}
            />

            <InputData
              id="pessoa-data-nascimento"
              label="Data de nascimento"
              help=""
              value={formData.data_nascimento || ""}
              onChange={(data_nascimento) =>
                setFormData((prev) => ({ ...prev, data_nascimento }))
              }
            />
          </div>

          {formData.tipo_cadastro === "veterinario" ? (
            <div className="w-full max-w-[220px]">
              <InputTexto
                id="pessoa-crmv"
                label="CRMV"
                required
                value={formData.crmv}
                error={erros.crmv}
                onChange={(crmv) => setFormData((prev) => ({ ...prev, crmv }))}
                onBlur={() => onBlurCampo?.("crmv")}
                maxLength={20}
                placeholder="CRMV XX 1234"
                help="Informe o número com UF."
              />
            </div>
          ) : null}
        </>
      ) : (
        <>
          <InputTexto
            id="pessoa-razao-social"
            label="Razão social"
            required
            value={formData.razao_social}
            error={erros.razao_social}
            onChange={(razao_social) => setFormData((prev) => ({ ...prev, razao_social }))}
            onBlur={() => onBlurCampo?.("razao_social")}
            placeholder="Razão social da empresa"
          />

          <InputTexto
            id="pessoa-nome-fantasia"
            label="Nome fantasia"
            required
            value={formData.nome}
            error={erros.nome}
            onChange={(nome) => setFormData((prev) => ({ ...prev, nome }))}
            onBlur={() => onBlurCampo?.("nome")}
            placeholder="Nome fantasia da empresa"
          />

          <div className="flex flex-wrap gap-4">
            <div className="w-full max-w-[220px]">
              <InputCpfCnpj
                id="pessoa-cnpj"
                label="CNPJ"
                required
                value={formData.cnpj}
                error={erros.cnpj}
                onChange={(cnpj) => setFormData((prev) => ({ ...prev, cnpj }))}
                onBlur={() => onBlurCampo?.("cnpj")}
              />
            </div>

            <div className="w-full max-w-[200px]">
              <InputTexto
                id="pessoa-inscricao-estadual"
                label="Inscrição estadual"
                value={formData.inscricao_estadual}
                onChange={(inscricao_estadual) =>
                  setFormData((prev) => ({ ...prev, inscricao_estadual }))
                }
                placeholder="IE"
              />
            </div>

            <div className="w-full max-w-xs">
              <InputTexto
                id="pessoa-responsavel"
                label="Responsável / contato"
                value={formData.responsavel}
                onChange={(responsavel) => setFormData((prev) => ({ ...prev, responsavel }))}
                placeholder="Nome do responsável ou contato"
              />
            </div>
          </div>
        </>
      )}

      {formData.tipo_cadastro === "cliente" ? (
        <ClienteOrigemSelect
          value={formData.origem_cliente}
          onChange={(origem_cliente) => setFormData((prev) => ({ ...prev, origem_cliente }))}
        />
      ) : null}
    </div>
  );
}
