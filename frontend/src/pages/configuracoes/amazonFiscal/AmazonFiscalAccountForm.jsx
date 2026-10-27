import { useState } from "react";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../../components/v2/BotaoSalva/BotaoSalva";
import InputCheck from "../../../components/v2/InputCheck/InputCheck";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import InputCpfCnpj from "../../../components/v2/InputCpfCnpj/InputCpfCnpj";
import InputTexto from "../../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../../components/v2/ModalPadrao/ModalPadrao";
import { formatFiscalDate } from "./amazonFiscalUtils";

export default function AmazonFiscalAccountForm({
  account,
  busy,
  error,
  onSave,
  onClose,
  hasFiscalScopes = true,
}) {
  const [form, setForm] = useState(() => ({
    seller_id: "",
    emitter_cnpj: "",
    auto_issue_enabled: false,
    upload_enabled: false,
    discount_policy: "source_discounts",
    active: false,
    ...account,
    discount_consent: account?.discount_policy === "buyer_payment_total",
  }));
  const change = (field, value) => setForm((current) => ({ ...current, [field]: value }));
  return (
    <ModalPadrao
      titulo={account?.id ? "Configurar conta Amazon" : "Cadastrar conta fiscal Amazon"}
      onFechar={() => {
        if (!busy) onClose();
      }}
      rodape={
        <>
          <BotaoCancelar disabled={busy} onClick={onClose}>
            Voltar
          </BotaoCancelar>
          <BotaoSalva type="button" loading={busy} onClick={() => onSave(form)}>
            Salvar configuração
          </BotaoSalva>
        </>
      }
    >
      <div className="space-y-4 text-slate-800 dark:text-slate-100">
        {error && (
          <p
            role="alert"
            className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300"
          >
            {error}
          </p>
        )}
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Configure aqui o Seller ID, o CNPJ emitente, os produtos e a política de descontos desta
          conta Amazon. A ativação vale somente para esta empresa e esta conta.
        </p>
        <InputTexto
          label="Seller ID da conta Amazon"
          value={form.seller_id}
          onChange={(value) => change("seller_id", value)}
          required
          disabled={busy || Boolean(account?.id)}
          maxLength={80}
        />
        <InputCpfCnpj
          label="CNPJ do emitente CorePet"
          value={form.emitter_cnpj}
          onChange={(value) => change("emitter_cnpj", value)}
          required
          disabled={busy}
        />
        <InputCombobox
          id="amazon-fiscal-discount-policy"
          label="Política de descontos"
          value={form.discount_policy}
          disabled={busy}
          permitirLimpar={false}
          opcoes={[
            { value: "source_discounts", label: "Somente descontos explícitos do pedido" },
            { value: "buyer_payment_total", label: "Ajustar total ao pagamento documentado" },
          ]}
          onChange={(value) =>
            setForm((current) => ({ ...current, discount_policy: value, discount_consent: false }))
          }
          help="Na política padrão, diferenças entre o total e os pagamentos aparecem como pendência para revisão."
        />
        {form.discount_policy === "buyer_payment_total" && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/20">
            <p className="mb-2 text-sm text-amber-900 dark:text-amber-200">
              A diferença positiva será rateada como desconto adicional nos itens, com registro da
              política e dos valores de origem.
            </p>
            <InputCheck
              id="amazon-discount-consent"
              label="Autorizo ajustar o desconto ao pagamento documentado"
              checked={form.discount_consent}
              onChange={(value) => change("discount_consent", value)}
              disabled={busy}
            />
          </div>
        )}
        <InputCheck
          id="amazon-fiscal-account-active"
          label="Ativar fluxo de pedidos Amazon com EcommerceAI nesta empresa"
          checked={form.active}
          onChange={(value) =>
            setForm((current) => ({
              ...current,
              active: value,
              auto_issue_enabled: value && current.auto_issue_enabled,
              upload_enabled: value && current.upload_enabled,
            }))
          }
          disabled={busy || (!hasFiscalScopes && !form.active)}
          help="Começa desativado. Ao ativar e salvar, o EcommerceAI busca e prepara os novos pedidos desta conta. A emissão exige confirmação humana enquanto a opção de emissão automática estiver desligada. Pedidos anteriores exigem revisão explícita."
        />
        <InputCheck
          id="amazon-auto-issue-consent"
          label="Emitir NF-e automaticamente após as validações"
          checked={form.auto_issue_enabled}
          onChange={(value) => change("auto_issue_enabled", value)}
          disabled={busy || !form.active || (!hasFiscalScopes && !form.auto_issue_enabled)}
          help="Começa desativada. Autoriza o CorePet a emitir os pedidos elegíveis desta conta sem confirmação por pedido, após validar destinatário, produtos e pagamentos, acompanhando o mesmo pedido para evitar notas duplicadas."
        />
        <p className="text-sm">
          Corte registrado para novos pedidos:{" "}
          <strong>{formatFiscalDate(account?.activated_at)}</strong>
        </p>
        <InputCheck
          id="amazon-upload-consent"
          label="Autorizar envio automático do XML à Amazon quando permitido"
          checked={form.upload_enabled}
          onChange={(value) => change("upload_enabled", value)}
          disabled={busy || !form.active || (!hasFiscalScopes && !form.upload_enabled)}
          help="Começa desativado. O EcommerceAI envia o XML autorizado somente quando a Amazon permitir. A emissão na SEFAZ e o aceite da Amazon são acompanhados separadamente."
        />
        {!hasFiscalScopes && (
          <p role="status" className="text-sm text-amber-800 dark:text-amber-200">
            A conexão ainda precisa das permissões fiscais aprovadas. O fluxo aguarda essa
            autorização antes de operar; configurar esta conta não concede novas permissões.
          </p>
        )}
        <p className="text-sm text-slate-600 dark:text-slate-300">
          A configuração fiscal é feita somente aqui no CorePet; o EcommerceAI acompanha os pedidos
          e o envio do XML. Vincule os SKUs exatos em “Mapear SKUs” antes da emissão. As demais
          empresas e os fluxos já usados pelo Bling mantêm suas configurações atuais.
        </p>
      </div>
    </ModalPadrao>
  );
}
