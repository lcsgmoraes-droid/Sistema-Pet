import { formatCurrency } from "./ecommerceMvpUtils";

const DELIVERY_OPTIONS = [
  { value: "entrega", label: "🚚 Entrega" },
  { value: "retirada", label: "🏪 Retirada na loja" },
];

const PICKUP_OPTIONS = [
  { value: "proprio", label: "🙋 Eu mesmo(a)" },
  { value: "terceiro", label: "🤝 Outra pessoa por mim" },
];

const PAYMENT_OPTIONS = [
  { key: "pix", label: "PIX", icon: "📱" },
  { key: "debito", label: "Débito", icon: "💳" },
  { key: "credito", label: "Crédito", icon: "💳" },
];

const CARD_BRANDS = ["Visa", "Mastercard", "Elo", "Outra"];
const CREDIT_INSTALLMENTS = [1, 2, 3];

function CheckoutDeliveryForm({
  addressFields,
  cidadeDestino,
  deliveryMode,
  isDrive,
  setAddressFields,
  styles: S,
  tenantContext,
  tipoRetirada,
  onCalculateSummary,
  onCheckoutCepBlur,
  onCidadeDestinoChange,
  onDeliveryModeChange,
  onIsDriveChange,
  onTipoRetiradaChange,
}) {
  const updateAddress = (field) => (e) =>
    setAddressFields((prev) => ({ ...prev, [field]: e.target.value }));
  const hasTenantCity = Boolean(tenantContext?.cidade);

  return (
    <div style={S.formCard}>
      <div style={{ fontWeight: 700, fontSize: 15, color: "#1a1a2e", marginBottom: 12 }}>
        📦 Como quer receber?
      </div>
      <form onSubmit={onCalculateSummary} style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", gap: 10 }}>
          {DELIVERY_OPTIONS.map(({ value, label }) => (
            <label key={value} style={deliveryMode === value ? S.radioLabelActive : S.radioLabel}>
              <input
                type="radio"
                name="deliveryMode"
                value={value}
                checked={deliveryMode === value}
                onChange={() => onDeliveryModeChange(value)}
                style={{ display: "none" }}
              />
              {label}
            </label>
          ))}
        </div>

        {deliveryMode === "retirada" && (
          <div
            style={{
              background: "#faf7f4",
              border: "1px solid #e7e5e4",
              borderRadius: 10,
              padding: 14,
              display: "grid",
              gap: 8,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 13, color: "#374151" }}>Quem vai retirar?</div>
            {PICKUP_OPTIONS.map(({ value, label }) => (
              <label key={value} style={tipoRetirada === value ? S.radioLabelActive : S.radioLabel}>
                <input
                  type="radio"
                  name="tipoRetirada"
                  value={value}
                  checked={tipoRetirada === value}
                  onChange={() => onTipoRetiradaChange(value)}
                  style={{ display: "none" }}
                />
                {label}
              </label>
            ))}
            {tipoRetirada === "terceiro" && (
              <div
                style={{
                  background: "#fff7ed",
                  border: "1px solid #fed7aa",
                  borderRadius: 8,
                  padding: 10,
                  fontSize: 12,
                  color: "#92400e",
                }}
              >
                ℹ️ Uma <strong>senha secreta de retirada</strong> será gerada. Compartilhe com quem
                vai buscar.
              </div>
            )}
            {tipoRetirada === "proprio" && (
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  cursor: "pointer",
                  padding: "10px 12px",
                  background: isDrive ? "#fff7ed" : "#f8fafc",
                  border: `1.5px solid ${isDrive ? "#f97316" : "#e5e7eb"}`,
                  borderRadius: 10,
                }}
              >
                <input
                  type="checkbox"
                  checked={isDrive}
                  onChange={(e) => onIsDriveChange(e.target.checked)}
                  style={{ width: 18, height: 18, cursor: "pointer" }}
                />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13, color: "#1a1a2e" }}>
                    🚗 Quero usar o Drive
                  </div>
                  <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
                    Avise pela loja quando chegar no estacionamento — sem sair do carro!
                  </div>
                </div>
              </label>
            )}
          </div>
        )}

        <input
          value={tenantContext?.cidade || cidadeDestino}
          onChange={(e) => onCidadeDestinoChange(e.target.value)}
          placeholder="Cidade da loja"
          disabled={hasTenantCity}
          style={{ ...S.formInput, background: hasTenantCity ? "#f8fafc" : "#fff" }}
        />

        {deliveryMode === "entrega" && (
          <>
            <input
              value={addressFields.cep}
              onChange={updateAddress("cep")}
              onBlur={onCheckoutCepBlur}
              placeholder="CEP"
              style={S.formInput}
            />
            <input
              value={addressFields.endereco}
              onChange={updateAddress("endereco")}
              placeholder="Rua / Avenida"
              style={S.formInput}
            />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <input
                value={addressFields.numero}
                onChange={updateAddress("numero")}
                placeholder="Número"
                style={S.formInput}
              />
              <input
                value={addressFields.complemento}
                onChange={updateAddress("complemento")}
                placeholder="Complemento"
                style={S.formInput}
              />
            </div>
            <input
              value={addressFields.bairro}
              onChange={updateAddress("bairro")}
              placeholder="Bairro"
              style={S.formInput}
            />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 8 }}>
              <input
                value={addressFields.cidade || tenantContext?.cidade || ""}
                onChange={updateAddress("cidade")}
                placeholder="Cidade"
                disabled={hasTenantCity}
                style={{ ...S.formInput, background: hasTenantCity ? "#f8fafc" : "#fff" }}
              />
              <input
                value={addressFields.estado || tenantContext?.uf || ""}
                onChange={updateAddress("estado")}
                placeholder="UF"
                style={S.formInput}
              />
            </div>
          </>
        )}
        <button type="submit" style={S.payBtn(true)}>
          Calcular resumo
        </button>
      </form>
    </div>
  );
}

function CheckoutPaymentForm({
  pagamentoBandeira,
  pagamentoParcelas,
  pagamentoTipo,
  styles: S,
  onPagamentoBandeiraChange,
  onPagamentoParcelasChange,
  onPagamentoTipoChange,
}) {
  return (
    <div style={S.formCard}>
      <div style={{ fontWeight: 700, fontSize: 15, color: "#1a1a2e", marginBottom: 12 }}>
        💳 Como vai pagar?
      </div>
      <div style={{ display: "grid", gap: 10 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {PAYMENT_OPTIONS.map((option) => (
            <label
              key={option.key}
              style={pagamentoTipo === option.key ? S.radioLabelActive : S.radioLabel}
            >
              <input
                type="radio"
                name="pagamentoTipo"
                value={option.key}
                checked={pagamentoTipo === option.key}
                onChange={() => onPagamentoTipoChange(option.key)}
                style={{ display: "none" }}
              />
              {option.icon} {option.label}
            </label>
          ))}
        </div>
        {(pagamentoTipo === "debito" || pagamentoTipo === "credito") && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontSize: 13, color: "#6b7280" }}>Bandeira:</span>
            {CARD_BRANDS.map((brand) => (
              <label
                key={brand}
                style={
                  pagamentoBandeira === brand
                    ? S.radioLabelActive
                    : { ...S.radioLabel, padding: "6px 12px", fontSize: 12 }
                }
              >
                <input
                  type="radio"
                  checked={pagamentoBandeira === brand}
                  onChange={() => onPagamentoBandeiraChange(brand)}
                  style={{ display: "none" }}
                />{" "}
                {brand}
              </label>
            ))}
          </div>
        )}
        {pagamentoTipo === "credito" && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 13, color: "#6b7280" }}>Parcelas:</span>
            {CREDIT_INSTALLMENTS.map((installment) => (
              <label
                key={installment}
                style={
                  pagamentoParcelas === installment
                    ? S.radioLabelActive
                    : { ...S.radioLabel, padding: "6px 14px" }
                }
              >
                <input
                  type="radio"
                  checked={pagamentoParcelas === installment}
                  onChange={() => onPagamentoParcelasChange(installment)}
                  style={{ display: "none" }}
                />{" "}
                {installment}x
              </label>
            ))}
          </div>
        )}
      </div>
      <div
        style={{
          marginTop: 10,
          fontSize: 12,
          color: "#92400e",
          background: "#fff7ed",
          border: "1px solid #fed7aa",
          borderRadius: 8,
          padding: "8px 10px",
        }}
      >
        O carrinho ainda nao e pedido. O pedido so sera liberado apos aprovacao do pagamento online.
      </div>
    </div>
  );
}

function CheckoutResult({ result }) {
  if (!result?.pedido_id) return null;

  return (
    <div
      style={{
        background: "#ecfdf5",
        border: "1.5px solid #6ee7b7",
        borderRadius: 12,
        padding: 14,
        marginTop: 8,
        display: "grid",
        gap: 6,
      }}
    >
      <div style={{ fontWeight: 700, color: "#065f46", fontSize: 14 }}>Pagamento em analise</div>
      <div style={{ fontSize: 13, color: "#374151" }}>
        Número: <strong>{result.pedido_id}</strong>
      </div>
      <div style={{ fontSize: 12, color: "#047857" }}>
        O pedido sera liberado para a loja apos aprovacao do pagamento.
      </div>
      {result.palavra_chave_retirada && (
        <div
          style={{
            background: "#fff7ed",
            border: "2px solid #f97316",
            borderRadius: 10,
            padding: 12,
            textAlign: "center",
            marginTop: 4,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 700, color: "#7c2d12", marginBottom: 4 }}>
            🔑 SENHA DE RETIRADA
          </div>
          <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: 3, color: "#ea580c" }}>
            {result.palavra_chave_retirada}
          </div>
          <div style={{ fontSize: 11, color: "#92400e", marginTop: 4 }}>
            Compartilhe com quem vai retirar
          </div>
        </div>
      )}
    </div>
  );
}

function CheckoutSummary({
  cart,
  cartTotal,
  checkoutLoading,
  checkoutResumo,
  checkoutResult,
  finalizeDisabled,
  isProfileComplete,
  styles: S,
  onFinalizeCheckout,
}) {
  return (
    <div style={S.resumoBox}>
      <div style={{ fontWeight: 700, fontSize: 16, color: "#1c1917", marginBottom: 14 }}>
        Resumo do pedido
      </div>
      {checkoutResumo ? (
        <div style={{ display: "grid", gap: 8 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 13,
              color: "#6b7280",
            }}
          >
            <span>Itens ({checkoutResumo.itens_count})</span>
            <span>{formatCurrency(checkoutResumo.subtotal)}</span>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 13,
              color: "#6b7280",
            }}
          >
            <span>Frete</span>
            <span>{formatCurrency(checkoutResumo?.frete?.valor_frete)}</span>
          </div>
          {checkoutResumo?.cupom?.desconto > 0 && (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 13,
                color: "#065f46",
              }}
            >
              <span>Desconto</span>
              <span>-{formatCurrency(checkoutResumo.cupom.desconto)}</span>
            </div>
          )}
          <div style={S.cartTotalRow}>
            <span>Total</span>
            <span>{formatCurrency(checkoutResumo.total)}</span>
          </div>
        </div>
      ) : cart?.itens?.length ? (
        <div>
          {cart.itens.map((item) => (
            <div
              key={item.item_id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 13,
                color: "#6b7280",
                marginBottom: 6,
              }}
            >
              <span>
                {item.nome} × {item.quantidade}
              </span>
              <span>{formatCurrency(item.preco_unitario * item.quantidade)}</span>
            </div>
          ))}
          <div style={S.cartTotalRow}>
            <span>Total estimado</span>
            <span>{formatCurrency(cartTotal)}</span>
          </div>
        </div>
      ) : null}

      <button
        onClick={onFinalizeCheckout}
        disabled={finalizeDisabled}
        style={S.finalizarBtn(finalizeDisabled)}
      >
        {checkoutLoading ? "Abrindo pagamento..." : "Ir para pagamento"}
      </button>

      {!isProfileComplete && (
        <div
          style={{
            fontSize: 12,
            color: "#b45309",
            background: "#fffbeb",
            borderRadius: 8,
            padding: "8px 10px",
            marginTop: 6,
          }}
        >
          ⚠️ Complete seu cadastro (nome, telefone, CPF e endereço) na aba Conta para finalizar.
        </div>
      )}

      <CheckoutResult result={checkoutResult} />
    </div>
  );
}

export default function EcommerceCheckoutPage({
  addressFields,
  cart,
  cartTotal,
  checkoutLoading,
  checkoutResumo,
  checkoutResult,
  cidadeDestino,
  deliveryMode,
  isDrive,
  isProfileComplete,
  pagamentoBandeira,
  pagamentoParcelas,
  pagamentoTipo,
  setAddressFields,
  styles: S,
  tenantContext,
  tipoRetirada,
  onCalculateSummary,
  onCheckoutCepBlur,
  onCidadeDestinoChange,
  onDeliveryModeChange,
  onFinalizeCheckout,
  onIsDriveChange,
  onPagamentoBandeiraChange,
  onPagamentoParcelasChange,
  onPagamentoTipoChange,
  onTipoRetiradaChange,
}) {
  const finalizeDisabled =
    checkoutLoading ||
    !(tenantContext?.cidade || cidadeDestino) ||
    !cart?.itens?.length ||
    !isProfileComplete;

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "28px 16px" }}>
      <h2 style={{ margin: "0 0 20px", fontSize: 26, fontWeight: 800, color: "#1c1917" }}>
        Checkout
      </h2>
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 20, alignItems: "start" }}
      >
        <div style={{ display: "grid", gap: 16 }}>
          <CheckoutDeliveryForm
            addressFields={addressFields}
            cidadeDestino={cidadeDestino}
            deliveryMode={deliveryMode}
            isDrive={isDrive}
            setAddressFields={setAddressFields}
            styles={S}
            tenantContext={tenantContext}
            tipoRetirada={tipoRetirada}
            onCalculateSummary={onCalculateSummary}
            onCheckoutCepBlur={onCheckoutCepBlur}
            onCidadeDestinoChange={onCidadeDestinoChange}
            onDeliveryModeChange={onDeliveryModeChange}
            onIsDriveChange={onIsDriveChange}
            onTipoRetiradaChange={onTipoRetiradaChange}
          />
          <CheckoutPaymentForm
            pagamentoBandeira={pagamentoBandeira}
            pagamentoParcelas={pagamentoParcelas}
            pagamentoTipo={pagamentoTipo}
            styles={S}
            onPagamentoBandeiraChange={onPagamentoBandeiraChange}
            onPagamentoParcelasChange={onPagamentoParcelasChange}
            onPagamentoTipoChange={onPagamentoTipoChange}
          />
        </div>

        <CheckoutSummary
          cart={cart}
          cartTotal={cartTotal}
          checkoutLoading={checkoutLoading}
          checkoutResumo={checkoutResumo}
          checkoutResult={checkoutResult}
          finalizeDisabled={finalizeDisabled}
          isProfileComplete={isProfileComplete}
          styles={S}
          onFinalizeCheckout={onFinalizeCheckout}
        />
      </div>
    </div>
  );
}
