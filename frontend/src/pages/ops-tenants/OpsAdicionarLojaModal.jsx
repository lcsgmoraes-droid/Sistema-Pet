import { useState } from "react";

import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import platformApi from "../../platformApi";
import { PLAN_EDIT_OPTIONS } from "./opsTenantsConstants";

const OPCOES_PLANO = [{ value: "", label: "Padrao do cadastro" }, ...PLAN_EDIT_OPTIONS];

function extrairErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

export default function OpsAdicionarLojaModal({ grupo, onClose, onCreated }) {
  const [nomeLoja, setNomeLoja] = useState("");
  const [plan, setPlan] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const [erroNomeLoja, setErroNomeLoja] = useState("");
  const [resultado, setResultado] = useState(null);

  function handleNomeLojaChange(valor) {
    setNomeLoja(valor);
    if (erroNomeLoja) setErroNomeLoja("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (nomeLoja.trim().length < 2) {
      setErroNomeLoja("Informe o nome da loja (pelo menos 2 caracteres).");
      return;
    }
    setErroNomeLoja("");
    setErro("");
    setEnviando(true);
    try {
      const { data } = await platformApi.post(
        `/admin/grupos-comerciais/${grupo.grupoId}/lojas`,
        {
          nome_loja: nomeLoja.trim(),
          plan: plan || undefined,
        },
      );
      setResultado(data);
      setNomeLoja("");
      setPlan("");
      onCreated?.();
    } catch (error) {
      setErro(extrairErro(error, "Nao foi possivel provisionar a loja. Tente novamente."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <ModalPadrao
      titulo="Adicionar loja"
      tamanho="pequena"
      onFechar={onClose}
      rodape={
        resultado ? (
          <BotaoCancelar onClick={onClose}>Fechar</BotaoCancelar>
        ) : (
          <>
            <BotaoCancelar onClick={onClose}>Cancelar</BotaoCancelar>
            <BotaoSalva form="adicionar-loja-form" loading={enviando}>
              {enviando ? "Criando..." : "Criar loja"}
            </BotaoSalva>
          </>
        )
      }
    >
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Nova loja dentro do grupo <span className="font-semibold">{grupo.nome}</span>. Sem trial
        gratuito — cliente ja pagante negociando uma loja a mais.
      </p>

      {resultado ? (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300">
          <p className="font-semibold">Loja "{resultado.nome}" criada e anexada ao grupo.</p>
          <p className="mt-1">
            Login: {resultado.login_name} · tenant {resultado.tenant_id}
          </p>
        </div>
      ) : (
        <form
          id="adicionar-loja-form"
          onSubmit={handleSubmit}
          noValidate
          className="mt-4 space-y-4"
        >
          <InputTexto
            id="adicionar-loja-nome"
            label="Nome da loja"
            autoFocus
            required
            value={nomeLoja}
            onChange={handleNomeLojaChange}
            placeholder="Ex.: Pet Feliz - Unidade Centro"
            maxLength={150}
            error={erroNomeLoja}
          />
          <InputCombobox
            id="adicionar-loja-plano"
            label="Plano negociado"
            opcoes={OPCOES_PLANO}
            value={plan}
            onChange={setPlan}
            permitirLimpar={false}
          />

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
