import { useState } from "react";
import BotaoCancelar from "../../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../../components/v2/BotaoSalva/BotaoSalva";
import InputCheck from "../../../components/v2/InputCheck/InputCheck";
import InputCombobox from "../../../components/v2/InputCombobox/InputCombobox";
import InputCpfCnpj from "../../../components/v2/InputCpfCnpj/InputCpfCnpj";
import InputTexto from "../../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../../components/v2/ModalPadrao/ModalPadrao";
import { formatFiscalDate } from "./amazonFiscalUtils";

export default function AmazonFiscalAccountForm({ account, busy, error, onSave, onClose }) {
  const [form, setForm] = useState(() => ({
    seller_id: "",
    emitter_cnpj: "",
    auto_issue_enabled: false,
    discount_policy: "source_discounts",
    active: true,
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
          Confira o Seller ID da loja Amazon e o CNPJ do emitente desta empresa. A configuração não
          cria vendas nem movimentos de estoque.
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
          id="amazon-auto-issue-consent"
          label="Autorizo emissão automática de novos pedidos desta loja"
          checked={form.auto_issue_enabled}
          onChange={(value) => change("auto_issue_enabled", value)}
          disabled={busy}
          help="Começa desativada. Ao ativar e salvar, o sistema registra o momento de corte. Pedidos anteriores exigem revisão explícita."
        />
        <p className="text-sm">
          Corte registrado para emissão automática:{" "}
          <strong>{formatFiscalDate(account?.activated_at)}</strong>
        </p>
        <InputCheck
          id="amazon-fiscal-account-active"
          label="Conta fiscal ativa"
          checked={form.active}
          onChange={(value) => change("active", value)}
          disabled={busy}
        />
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Configure também a fila fiscal da mesma conta no EcommerceAI. O envio à Amazon depende das
          permissões da Amazon e é acompanhado no EcommerceAI.
        </p>
      </div>
    </ModalPadrao>
  );
}
