import { Plus } from "lucide-react";
import { useState } from "react";

import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoExcluir from "../../components/v2/BotaoExcluir/BotaoExcluir";
import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import BotaoLink from "../../components/v2/BotaoLink/BotaoLink";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCheckTexto from "../../components/v2/InputCheckTexto/InputCheckTexto";
import InputCpfCnpj from "../../components/v2/InputCpfCnpj/InputCpfCnpj";
import InputRadio from "../../components/v2/InputRadio/InputRadio";
import InputTelefone from "../../components/v2/InputTelefone/InputTelefone";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import platformApi from "../../platformApi";

const OPCOES_TITULAR_TIPO_PESSOA = [
  { value: "PF", label: "Pessoa Física" },
  { value: "PJ", label: "Pessoa Jurídica" },
];

function novaLojaVazia() {
  return { nome_loja: "" };
}

function extrairErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

export default function OpsGrupoComercialOnboardingModal({ onClose, onCreated, onDefinirProposta }) {
  const [titularEmail, setTitularEmail] = useState("");
  const [titularNome, setTitularNome] = useState("");
  const [titularTipoPessoa, setTitularTipoPessoa] = useState("PF");
  const [titularTelefone, setTitularTelefone] = useState("");
  const [titularCpfCnpj, setTitularCpfCnpj] = useState("");
  const [semTrial, setSemTrial] = useState(false);
  const [lojas, setLojas] = useState([novaLojaVazia()]);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [erroTitularEmail, setErroTitularEmail] = useState("");
  const [erroTitularCpfCnpj, setErroTitularCpfCnpj] = useState("");
  const [errosNomeLoja, setErrosNomeLoja] = useState({});
  const [resultado, setResultado] = useState(null);

  function handleTitularEmailChange(valor) {
    setTitularEmail(valor);
    if (erroTitularEmail) setErroTitularEmail("");
  }

  function handleTitularCpfCnpjChange(valor) {
    setTitularCpfCnpj(valor);
    if (erroTitularCpfCnpj) setErroTitularCpfCnpj("");
  }

  function atualizarLoja(indice, campo, valor) {
    setLojas((atual) =>
      atual.map((loja, i) => (i === indice ? { ...loja, [campo]: valor } : loja)),
    );
    if (campo === "nome_loja" && errosNomeLoja[indice]) {
      setErrosNomeLoja((atual) => {
        const { [indice]: _removido, ...resto } = atual;
        return resto;
      });
    }
  }

  function adicionarLoja() {
    setLojas((atual) => [...atual, novaLojaVazia()]);
  }

  function removerLoja(indice) {
    setLojas((atual) => atual.filter((_, i) => i !== indice));
    setErrosNomeLoja({});
  }

  // Validação em tela (borda vermelha + mensagem abaixo do campo) — o
  // formulário usa `noValidate` pra desligar o balão nativo do navegador,
  // então essa função é a única checagem que roda antes de enviar.
  function validarCampos() {
    const novoErroEmail =
      !titularEmail.trim() || !titularEmail.includes("@")
        ? "Informe um e-mail válido para o titular."
        : "";
    const digitosDocumento = titularCpfCnpj.replace(/\D/g, "");
    const tamanhoEsperado = titularTipoPessoa === "PJ" ? 14 : 11;
    const novoErroCpfCnpj =
      digitosDocumento.length !== tamanhoEsperado
        ? `Informe um ${titularTipoPessoa === "PJ" ? "CNPJ" : "CPF"} válido do titular.`
        : "";
    const novosErrosNomeLoja = {};
    lojas.forEach((loja, indice) => {
      if (loja.nome_loja.trim().length < 2) {
        novosErrosNomeLoja[indice] = "Informe um nome com pelo menos 2 caracteres.";
      }
    });
    setErroTitularEmail(novoErroEmail);
    setErroTitularCpfCnpj(novoErroCpfCnpj);
    setErrosNomeLoja(novosErrosNomeLoja);
    return !novoErroEmail && !novoErroCpfCnpj && Object.keys(novosErrosNomeLoja).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!validarCampos()) {
      setErro("Revise os campos destacados.");
      return;
    }
    setErro("");
    setResultado(null);
    setEnviando(true);
    try {
      const { data } = await platformApi.post("/admin/grupos-comerciais/onboarding", {
        titular_email: titularEmail.trim().toLowerCase(),
        titular_nome: titularNome.trim() || undefined,
        titular_tipo_pessoa: titularTipoPessoa,
        titular_telefone: titularTelefone.trim() || undefined,
        titular_cpf_cnpj: titularCpfCnpj.trim(),
        grant_trial: !semTrial,
        lojas: lojas.map((loja) => ({
          nome_loja: loja.nome_loja.trim(),
        })),
      });
      setResultado(data);
      onCreated?.();
    } catch (error) {
      setErro(extrairErro(error, "Nao foi possivel concluir o onboarding. Tente novamente."));
    } finally {
      setEnviando(false);
    }
  }

  function handleDefinirProposta(tenantId) {
    onDefinirProposta?.(tenantId);
    onClose?.();
  }

  return (
    <ModalPadrao
      titulo="Novo grupo comercial"
      tamanho="normal"
      onFechar={onClose}
      rodape={
        resultado ? (
          <BotaoCancelar onClick={onClose}>Fechar</BotaoCancelar>
        ) : (
          <>
            <BotaoCancelar onClick={onClose}>Cancelar</BotaoCancelar>
            <BotaoSalva form="grupo-comercial-onboarding-form" loading={enviando}>
              {enviando ? "Criando..." : "Criar grupo comercial"}
            </BotaoSalva>
          </>
        )
      }
    >
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
        Esta etapa só cria as lojas. Depois de criadas, defina o plano e o valor de cada uma
        individualmente pela "Proposta comercial" — o link aparece ao lado de cada loja assim que
        o grupo é criado.
      </p>

      {resultado ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
          <p className="font-semibold">
            Grupo comercial #{resultado.grupo_id} criado com {resultado.lojas.length} loja(s).
          </p>
          {resultado.aviso ? (
            <p className="mt-1 font-semibold text-amber-800 dark:text-amber-200">
              {resultado.aviso} Isso já aparece marcado como "Critico" na lista de tenants.
            </p>
          ) : (
            <p className="mt-1">
              Um e-mail para definir a senha foi enviado para {resultado.titular_email}.
            </p>
          )}
          <p className="mt-1">
            Próximo passo: defina o plano e o valor de cada loja pela proposta comercial.
          </p>
          <ul className="mt-2 list-disc space-y-0.5 pl-5">
            {resultado.lojas.map((loja) => (
              <li key={loja.tenant_id}>
                {loja.nome} — login: {loja.login_name}{" "}
                <BotaoLink onClick={() => handleDefinirProposta(loja.tenant_id)}>
                  Definir proposta comercial
                </BotaoLink>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <form
          id="grupo-comercial-onboarding-form"
          onSubmit={handleSubmit}
          noValidate
          className="mt-4 space-y-4"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <InputTexto
              id="titular-email"
              type="email"
              label="E-mail do titular"
              autoComplete="email"
              autoFocus
              value={titularEmail}
              onChange={handleTitularEmailChange}
              placeholder="dono@empresa.com"
              required
              error={erroTitularEmail}
            />
            <InputTexto
              id="titular-nome"
              label="Nome do titular (opcional)"
              autoComplete="name"
              value={titularNome}
              onChange={setTitularNome}
              placeholder="Ex.: Maria Silva"
              maxLength={160}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-[auto_1fr_1fr]">
            <InputRadio
              name="titular-tipo-pessoa"
              label="Tipo de pessoa"
              opcoes={OPCOES_TITULAR_TIPO_PESSOA}
              value={titularTipoPessoa}
              onChange={setTitularTipoPessoa}
            />
            <InputCpfCnpj
              id="titular-cpf-cnpj"
              label={titularTipoPessoa === "PJ" ? "CNPJ do titular" : "CPF do titular"}
              value={titularCpfCnpj}
              onChange={handleTitularCpfCnpjChange}
              required
              error={erroTitularCpfCnpj}
            />
            <InputTelefone
              id="titular-telefone"
              label="Telefone do titular (opcional)"
              value={titularTelefone}
              onChange={setTitularTelefone}
            />
          </div>
          <InputCheckTexto id="sem-trial" checked={semTrial} onChange={setSemTrial}>
            Cliente já pagante — não conceder os 30 dias de teste gratuito
          </InputCheckTexto>

          <div className="space-y-3">
            <span className="v2-rotulo">Lojas</span>
            <ul className="space-y-3">
              {lojas.map((loja, indice) => (
                <li
                  key={indice}
                  className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800 sm:flex-row sm:items-end"
                >
                  <div className="min-w-0 flex-1">
                    <InputTexto
                      id={`loja-${indice}-nome`}
                      label={`Nome da loja ${indice + 1}`}
                      value={loja.nome_loja}
                      onChange={(valor) => atualizarLoja(indice, "nome_loja", valor)}
                      placeholder="Ex.: Loja Centro"
                      maxLength={150}
                      required
                      error={errosNomeLoja[indice] || ""}
                    />
                  </div>
                  {lojas.length > 1 ? (
                    <BotaoExcluir
                      tamanho="normal"
                      mensagemConfirmacao="Remover esta loja do formulário?"
                      onClick={() => removerLoja(indice)}
                    >
                      Remover
                    </BotaoExcluir>
                  ) : null}
                </li>
              ))}
            </ul>
            <BotaoInteracao icon={Plus} onClick={adicionarLoja}>
              Adicionar outra loja
            </BotaoInteracao>
          </div>

          {erro ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-300">
              {erro}
            </div>
          ) : null}
        </form>
      )}
    </ModalPadrao>
  );
}
