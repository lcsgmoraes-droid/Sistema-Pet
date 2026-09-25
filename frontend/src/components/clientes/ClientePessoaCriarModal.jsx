import { useEffect, useState } from "react";
import { FiX } from "react-icons/fi";
import toast from "react-hot-toast";
import api from "../../api";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCheckGroup from "../v2/InputCheckGroup/InputCheckGroup";
import InputCpfCnpj from "../v2/InputCpfCnpj/InputCpfCnpj";
import InputRadio from "../v2/InputRadio/InputRadio";
import InputTelefone from "../v2/InputTelefone/InputTelefone";
import InputTexto from "../v2/InputTexto/InputTexto";

const OPCOES_TIPO_CADASTRO = [
  { value: "cliente", label: "Cliente" },
  { value: "fornecedor", label: "Fornecedor" },
  { value: "veterinario", label: "Veterinário" },
  { value: "funcionario", label: "Funcionário" },
];

const FLAG_POR_TIPO = {
  cliente: "is_cliente",
  fornecedor: "is_fornecedor",
  veterinario: "is_veterinario",
  funcionario: "is_funcionario",
};

const OPCOES_TIPO_PESSOA = [
  { value: "PF", label: "Pessoa Física" },
  { value: "PJ", label: "Pessoa Jurídica" },
];

const CAMPOS_EM_ORDEM = ["tipos_cadastro", "nome", "razao_social", "cnpj", "crmv", "celular"];

const ID_DO_CAMPO = {
  tipos_cadastro: "pessoa-criar-tipos-cadastro",
  nome: "pessoa-criar-nome",
  razao_social: "pessoa-criar-razao-social",
  cnpj: "pessoa-criar-cnpj",
  crmv: "pessoa-criar-crmv",
  celular: "pessoa-criar-celular",
};

function formDataInicial(tipoCadastro) {
  const tipoValido = FLAG_POR_TIPO[tipoCadastro] ? tipoCadastro : "cliente";
  return {
    is_cliente: tipoValido === "cliente",
    is_fornecedor: tipoValido === "fornecedor",
    is_veterinario: tipoValido === "veterinario",
    is_funcionario: tipoValido === "funcionario",
    tipo_pessoa: "PF",
    nome: "",
    cpf: "",
    cnpj: "",
    razao_social: "",
    inscricao_estadual: "",
    responsavel: "",
    crmv: "",
    telefone: "",
    celular: "",
    celular_whatsapp: true,
  };
}

function validar(formData) {
  const erros = {};
  if (!formData.nome.trim()) erros.nome = "Informe o nome.";

  if (formData.tipo_pessoa === "PJ") {
    if (!formData.cnpj.trim()) erros.cnpj = "Informe o CNPJ.";
    if (!formData.razao_social.trim()) erros.razao_social = "Informe a razão social.";
  }

  if (formData.is_veterinario && !formData.crmv.trim()) {
    erros.crmv = "Informe o CRMV.";
  }

  if (formData.is_cliente) {
    const digitos = `${formData.telefone}${formData.celular}`.replace(/\D/g, "");
    if (digitos.length < 10) erros.celular = "Informe telefone ou celular.";
  }

  if (
    !formData.is_cliente &&
    !formData.is_fornecedor &&
    !formData.is_veterinario &&
    !formData.is_funcionario
  ) {
    erros.tipos_cadastro = "Selecione ao menos um tipo de cadastro.";
  }

  return erros;
}

export default function ClientePessoaCriarModal({ aberto, tipoInicial, onCriado, onFechar }) {
  const [formData, setFormData] = useState(() => formDataInicial(tipoInicial));
  const [tocados, setTocados] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [duplicado, setDuplicado] = useState(null);

  useEffect(() => {
    if (aberto) {
      setFormData(formDataInicial(tipoInicial));
      setTocados({});
      setDuplicado(null);
    }
  }, [aberto, tipoInicial]);

  if (!aberto) return null;

  const erros = validar(formData);
  const formValido = Object.keys(erros).length === 0;
  const erroVisivel = (campo) => (tocados[campo] ? erros[campo] : undefined);
  const marcarTocado = (campo) => setTocados((atual) => ({ ...atual, [campo]: true }));

  const selecionarTiposCadastro = (valoresSelecionados) => {
    setFormData((prev) => ({
      ...prev,
      is_cliente: valoresSelecionados.includes("cliente"),
      is_fornecedor: valoresSelecionados.includes("fornecedor"),
      is_veterinario: valoresSelecionados.includes("veterinario"),
      is_funcionario: valoresSelecionados.includes("funcionario"),
    }));
  };

  const criarCliente = async () => {
    setEnviando(true);
    try {
      const payload = { ...formData };
      Object.keys(payload).forEach((campo) => {
        if (payload[campo] === "") payload[campo] = null;
      });

      const { data } = await api.post("/clientes/", payload);
      toast.success("Cadastro criado. Agora complete os demais dados.");
      onCriado(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Não foi possível criar o cadastro.");
    } finally {
      setEnviando(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!formValido) {
      setTocados(Object.fromEntries(CAMPOS_EM_ORDEM.map((campo) => [campo, true])));
      const primeiroCampoComErro = CAMPOS_EM_ORDEM.find((campo) => erros[campo]);
      document
        .getElementById(ID_DO_CAMPO[primeiroCampoComErro])
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    setEnviando(true);
    try {
      const params = new URLSearchParams();
      if (formData.cpf) params.append("cpf", formData.cpf);
      if (formData.cnpj) params.append("cnpj", formData.cnpj);
      if (formData.telefone) params.append("telefone", formData.telefone);
      if (formData.celular) params.append("celular", formData.celular);
      if (formData.crmv) params.append("crmv", formData.crmv);

      if (params.toString()) {
        const { data } = await api.get(`/clientes/verificar-duplicata/campo?${params.toString()}`);
        if (data?.duplicado) {
          setDuplicado(data);
          setEnviando(false);
          return;
        }
      }
    } catch (err) {
      console.error("Erro ao verificar duplicidade:", err);
    }

    await criarCliente();
  };

  const campoCelular = (
    <InputTelefone
      id="pessoa-criar-celular"
      label="Celular"
      tipo="celular"
      required={formData.is_cliente}
      value={formData.celular}
      error={erroVisivel("celular")}
      onChange={(celular) => setFormData((prev) => ({ ...prev, celular }))}
      onBlur={() => marcarTocado("celular")}
      whatsapp={formData.celular_whatsapp}
      onChangeWhatsapp={(celular_whatsapp) =>
        setFormData((prev) => ({ ...prev, celular_whatsapp }))
      }
      help={
        formData.is_cliente
          ? "Obrigatório para clientes do app, e-commerce e loja física."
          : "Opcional — pode ser preenchido depois, na tela de edição."
      }
    />
  );

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
          <h3 className="text-xl font-bold text-gray-900">Nova pessoa</h3>
          <button
            type="button"
            onClick={onFechar}
            className="text-gray-400 transition-colors hover:text-gray-600"
            aria-label="Fechar"
          >
            <FiX className="h-6 w-6" />
          </button>
        </div>

        <form id="pessoa-criar-form" onSubmit={handleSubmit} noValidate className="space-y-4 p-6">
          <p className="text-sm font-medium text-gray-600">Cadastro básico</p>

          {duplicado ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-semibold">Já existe um cadastro com dados parecidos.</p>
              <p className="mt-1">{duplicado.cliente?.nome}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <BotaoCancelar tamanho="pequeno" onClick={() => setDuplicado(null)}>
                  Revisar dados
                </BotaoCancelar>
                <BotaoSalva
                  type="button"
                  tamanho="pequeno"
                  loading={enviando}
                  onClick={() => {
                    setDuplicado(null);
                    criarCliente();
                  }}
                >
                  Criar mesmo assim
                </BotaoSalva>
              </div>
            </div>
          ) : null}

          <div id="pessoa-criar-tipos-cadastro">
            <InputCheckGroup
              name="pessoa-criar-tipos-cadastro"
              label="Tipo de cadastro"
              required
              error={tocados.tipos_cadastro ? erros.tipos_cadastro : undefined}
              opcoes={OPCOES_TIPO_CADASTRO}
              value={Object.entries(FLAG_POR_TIPO)
                .filter(([, flag]) => formData[flag])
                .map(([tipo]) => tipo)}
              onChange={(valores) => {
                marcarTocado("tipos_cadastro");
                selecionarTiposCadastro(valores);
              }}
            />
          </div>

          <InputRadio
            name="tipo_pessoa"
            label="Tipo de pessoa"
            required
            opcoes={OPCOES_TIPO_PESSOA}
            value={formData.tipo_pessoa}
            onChange={(tipo_pessoa) => setFormData((prev) => ({ ...prev, tipo_pessoa }))}
          />

          {formData.tipo_pessoa === "PF" ? (
            <>
              <InputTexto
                id="pessoa-criar-nome"
                label="Nome completo"
                required
                value={formData.nome}
                error={erroVisivel("nome")}
                onChange={(nome) => setFormData((prev) => ({ ...prev, nome }))}
                onBlur={() => marcarTocado("nome")}
                placeholder="Digite o nome completo"
              />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <InputCpfCnpj
                  id="pessoa-criar-cpf"
                  label="CPF"
                  value={formData.cpf}
                  onChange={(cpf) => setFormData((prev) => ({ ...prev, cpf }))}
                />

                {campoCelular}
              </div>

              {formData.is_veterinario ? (
                <InputTexto
                  id="pessoa-criar-crmv"
                  label="CRMV"
                  required
                  value={formData.crmv}
                  error={erroVisivel("crmv")}
                  onChange={(crmv) => setFormData((prev) => ({ ...prev, crmv }))}
                  onBlur={() => marcarTocado("crmv")}
                  maxLength={20}
                  placeholder="CRMV XX 1234"
                />
              ) : null}
            </>
          ) : (
            <>
              <InputTexto
                id="pessoa-criar-razao-social"
                label="Razão social"
                required
                value={formData.razao_social}
                error={erroVisivel("razao_social")}
                onChange={(razao_social) => setFormData((prev) => ({ ...prev, razao_social }))}
                onBlur={() => marcarTocado("razao_social")}
                placeholder="Razão social da empresa"
              />

              <InputTexto
                id="pessoa-criar-nome"
                label="Nome fantasia"
                required
                value={formData.nome}
                error={erroVisivel("nome")}
                onChange={(nome) => setFormData((prev) => ({ ...prev, nome }))}
                onBlur={() => marcarTocado("nome")}
                placeholder="Nome fantasia da empresa"
              />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <InputCpfCnpj
                  id="pessoa-criar-cnpj"
                  label="CNPJ"
                  required
                  value={formData.cnpj}
                  error={erroVisivel("cnpj")}
                  onChange={(cnpj) => setFormData((prev) => ({ ...prev, cnpj }))}
                  onBlur={() => marcarTocado("cnpj")}
                />

                {campoCelular}
              </div>
            </>
          )}
        </form>

        <div className="sticky bottom-0 flex justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
          <BotaoCancelar onClick={onFechar}>Cancelar</BotaoCancelar>
          <BotaoSalva form="pessoa-criar-form" loading={enviando} disabled={enviando}>
            Criar cadastro
          </BotaoSalva>
        </div>
      </div>
    </div>
  );
}
