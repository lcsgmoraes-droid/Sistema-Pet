import { AlertTriangle, Car, CreditCard, KeyRound, MapPin, Package, Store, Truck, UserRound } from 'lucide-react';
import { formatCurrency } from './ecommerceMvpUtils';

const DELIVERY_OPTIONS = [
  { value: 'entrega', label: 'Entrega', icon: Truck },
  { value: 'retirada', label: 'Retirada na loja', icon: Store },
];

const PICKUP_OPTIONS = [
  { value: 'proprio', label: 'Eu mesmo(a)', icon: UserRound },
  { value: 'terceiro', label: 'Outra pessoa por mim', icon: KeyRound },
];

const PAYMENT_OPTIONS = [
  { key: 'pix', label: 'PIX', icon: CreditCard },
  { key: 'debito', label: 'Debito', icon: CreditCard },
  { key: 'credito', label: 'Credito', icon: CreditCard },
];

const PAYMENT_BRANDS = ['Visa', 'Mastercard', 'Elo', 'Outra'];
const CREDIT_INSTALLMENTS = [1, 2, 3];

function ChoiceLabel({ active, children, icon: Icon, name, onChange, value, styles: S }) {
  return (
    <label style={active ? S.radioLabelActive : S.radioLabel}>
      <input type="radio" name={name} value={value} checked={active} onChange={onChange} style={{ display: 'none' }} />
      {Icon ? <Icon size={15} /> : null}
      {children}
    </label>
  );
}

function CheckoutDeliveryForm({
  addressFields,
  cidadeDestino,
  deliveryMode,
  isDrive,
  tenantContext,
  tipoRetirada,
  styles: S,
  onAddressFieldsChange,
  onCalculateSummary,
  onCheckoutCepBlur,
  onCityChange,
  onDeliveryModeChange,
  onDriveChange,
  onPickupTypeChange,
}) {
  const cityLocked = Boolean(tenantContext?.cidade);

  return (
    <div style={S.formCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 15, color: '#1a1a2e', marginBottom: 12 }}>
        <Package size={17} />
        Como quer receber?
      </div>

      <form onSubmit={onCalculateSummary} style={{ display: 'grid', gap: 10 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {DELIVERY_OPTIONS.map(({ value, label, icon }) => (
            <ChoiceLabel
              key={value}
              active={deliveryMode === value}
              icon={icon}
              name="deliveryMode"
              styles={S}
              value={value}
              onChange={() => onDeliveryModeChange(value)}
            >
              {label}
            </ChoiceLabel>
          ))}
        </div>

        {deliveryMode === 'retirada' && (
          <div style={{ background: '#faf7f4', border: '1px solid #e7e5e4', borderRadius: 10, padding: 14, display: 'grid', gap: 8 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>Quem vai retirar?</div>
            {PICKUP_OPTIONS.map(({ value, label, icon }) => (
              <ChoiceLabel
                key={value}
                active={tipoRetirada === value}
                icon={icon}
                name="tipoRetirada"
                styles={S}
                value={value}
                onChange={() => onPickupTypeChange(value)}
              >
                {label}
              </ChoiceLabel>
            ))}

            {tipoRetirada === 'terceiro' && (
              <div style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, padding: 10, fontSize: 12, color: '#92400e' }}>
                Uma senha secreta de retirada sera gerada. Compartilhe com quem vai buscar.
              </div>
            )}

            {tipoRetirada === 'proprio' && (
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 12px', background: isDrive ? '#fff7ed' : '#f8fafc', border: `1.5px solid ${isDrive ? '#f97316' : '#e5e7eb'}`, borderRadius: 10 }}>
                <input type="checkbox" checked={isDrive} onChange={(event) => onDriveChange(event.target.checked)} style={{ width: 18, height: 18, cursor: 'pointer' }} />
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, fontSize: 13, color: '#1a1a2e' }}>
                    <Car size={14} />
                    Quero usar o Drive
                  </div>
                  <div style={{ fontSize: 11, color: '#6b7280', marginTop: 2 }}>Avise pela loja quando chegar no estacionamento, sem sair do carro.</div>
                </div>
              </label>
            )}
          </div>
        )}

        <input
          value={tenantContext?.cidade || cidadeDestino}
          onChange={(event) => onCityChange(event.target.value)}
          placeholder="Cidade da loja"
          disabled={cityLocked}
          style={{ ...S.formInput, background: cityLocked ? '#f8fafc' : '#fff' }}
        />

        {deliveryMode === 'entrega' && (
          <>
            <input value={addressFields.cep} onChange={(event) => onAddressFieldsChange((prev) => ({ ...prev, cep: event.target.value }))} onBlur={onCheckoutCepBlur} placeholder="CEP" style={S.formInput} />
            <input value={addressFields.endereco} onChange={(event) => onAddressFieldsChange((prev) => ({ ...prev, endereco: event.target.value }))} placeholder="Rua / Avenida" style={S.formInput} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <input value={addressFields.numero} onChange={(event) => onAddressFieldsChange((prev) => ({ ...prev, numero: event.target.value }))} placeholder="Numero" style={S.formInput} />
              <input value={addressFields.complemento} onChange={(event) => onAddressFieldsChange((prev) => ({ ...prev, complemento: event.target.value }))} placeholder="Complemento" style={S.formInput} />
            </div>
            <input value={addressFields.bairro} onChange={(event) => onAddressFieldsChange((prev) => ({ ...prev, bairro: event.target.value }))} placeholder="Bairro" style={S.formInput} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 8 }}>
              <input
                value={addressFields.cidade || tenantContext?.cidade || ''}
                onChange={(event) => onAddressFieldsChange((prev) => ({ ...prev, cidade: event.target.value }))}
                placeholder="Cidade"
                disabled={cityLocked}
                style={{ ...S.formInput, background: cityLocked ? '#f8fafc' : '#fff' }}
              />
              <input value={addressFields.estado || tenantContext?.uf || ''} onChange={(event) => onAddressFieldsChange((prev) => ({ ...prev, estado: event.target.value }))} placeholder="UF" style={S.formInput} />
            </div>
          </>
        )}

        <button type="submit" style={S.payBtn(true)}>
          <MapPin size={15} />
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
  onPaymentBrandChange,
  onPaymentInstallmentsChange,
  onPaymentTypeChange,
}) {
  const needsBrand = pagamentoTipo === 'debito' || pagamentoTipo === 'credito';

  return (
    <div style={S.formCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 15, color: '#1a1a2e', marginBottom: 12 }}>
        <CreditCard size={17} />
        Como vai pagar?
      </div>

      <div style={{ display: 'grid', gap: 10 }}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {PAYMENT_OPTIONS.map(({ key, label, icon }) => (
            <ChoiceLabel
              key={key}
              active={pagamentoTipo === key}
              icon={icon}
              name="pagamentoTipo"
              styles={S}
              value={key}
              onChange={() => onPaymentTypeChange(key)}
            >
              {label}
            </ChoiceLabel>
          ))}
        </div>

        {needsBrand && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: '#6b7280' }}>Bandeira:</span>
            {PAYMENT_BRANDS.map((brand) => (
              <ChoiceLabel
                key={brand}
                active={pagamentoBandeira === brand}
                name="pagamentoBandeira"
                styles={{ ...S, radioLabel: { ...S.radioLabel, padding: '6px 12px', fontSize: 12 } }}
                value={brand}
                onChange={() => onPaymentBrandChange(brand)}
              >
                {brand}
              </ChoiceLabel>
            ))}
          </div>
        )}

        {pagamentoTipo === 'credito' && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 13, color: '#6b7280' }}>Parcelas:</span>
            {CREDIT_INSTALLMENTS.map((installment) => (
              <ChoiceLabel
                key={installment}
                active={pagamentoParcelas === installment}
                name="pagamentoParcelas"
                styles={{ ...S, radioLabel: { ...S.radioLabel, padding: '6px 14px' } }}
                value={installment}
                onChange={() => onPaymentInstallmentsChange(installment)}
              >
                {installment}x
              </ChoiceLabel>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: 10, fontSize: 12, color: '#92400e', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, padding: '8px 10px' }}>
        O carrinho ainda nao e pedido. O pedido so sera liberado apos aprovacao do pagamento online.
      </div>
    </div>
  );
}

function CheckoutSummary({
  cart,
  cartTotal,
  checkoutLoading,
  checkoutResult,
  checkoutResumo,
  cidadeDestino,
  isProfileComplete,
  tenantContext,
  styles: S,
  onFinalizeCheckout,
}) {
  const items = Array.isArray(cart?.itens) ? cart.itens : [];
  const disabled = checkoutLoading || !(tenantContext?.cidade || cidadeDestino) || !items.length || !isProfileComplete;

  return (
    <div style={S.resumoBox}>
      <div style={{ fontWeight: 700, fontSize: 16, color: '#1c1917', marginBottom: 14 }}>Resumo do pedido</div>

      {checkoutResumo ? (
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13, color: '#6b7280' }}>
            <span>Itens ({checkoutResumo.itens_count})</span>
            <span>{formatCurrency(checkoutResumo.subtotal)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13, color: '#6b7280' }}>
            <span>Frete</span>
            <span>{formatCurrency(checkoutResumo?.frete?.valor_frete)}</span>
          </div>
          {checkoutResumo?.cupom?.desconto > 0 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13, color: '#065f46' }}>
              <span>Desconto</span>
              <span>-{formatCurrency(checkoutResumo.cupom.desconto)}</span>
            </div>
          )}
          <div style={S.cartTotalRow}><span>Total</span><span>{formatCurrency(checkoutResumo.total)}</span></div>
        </div>
      ) : items.length ? (
        <div>
          {items.map((item) => (
            <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13, color: '#6b7280', marginBottom: 6 }}>
              <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.nome} x {item.quantidade}</span>
              <span style={{ flexShrink: 0 }}>{formatCurrency(item.preco_unitario * item.quantidade)}</span>
            </div>
          ))}
          <div style={S.cartTotalRow}><span>Total estimado</span><span>{formatCurrency(cartTotal)}</span></div>
        </div>
      ) : null}

      <button onClick={onFinalizeCheckout} disabled={disabled} style={S.finalizarBtn(disabled)}>
        {checkoutLoading ? 'Abrindo pagamento...' : 'Ir para pagamento'}
      </button>

      {!isProfileComplete && (
        <div style={{ display: 'flex', gap: 8, fontSize: 12, color: '#b45309', background: '#fffbeb', borderRadius: 8, padding: '8px 10px', marginTop: 6 }}>
          <AlertTriangle size={14} style={{ flexShrink: 0 }} />
          <span>Complete seu cadastro (nome, telefone, CPF e endereco) na aba Conta para finalizar.</span>
        </div>
      )}

      {checkoutResult?.pedido_id && (
        <div style={{ background: '#ecfdf5', border: '1.5px solid #6ee7b7', borderRadius: 12, padding: 14, marginTop: 8, display: 'grid', gap: 6 }}>
          <div style={{ fontWeight: 700, color: '#065f46', fontSize: 14 }}>Pagamento em analise</div>
          <div style={{ fontSize: 13, color: '#374151' }}>Numero: <strong>{checkoutResult.pedido_id}</strong></div>
          <div style={{ fontSize: 12, color: '#047857' }}>O pedido sera liberado para a loja apos aprovacao do pagamento.</div>

          {checkoutResult.palavra_chave_retirada && (
            <div style={{ background: '#fff7ed', border: '2px solid #f97316', borderRadius: 10, padding: 12, textAlign: 'center', marginTop: 4 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 700, color: '#7c2d12', marginBottom: 4 }}>
                <KeyRound size={13} />
                Senha de retirada
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: 3, color: '#ea580c' }}>{checkoutResult.palavra_chave_retirada}</div>
              <div style={{ fontSize: 11, color: '#92400e', marginTop: 4 }}>Compartilhe com quem vai retirar</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function EcommerceCheckoutPage({
  addressFields,
  cart,
  cartTotal,
  checkoutLoading,
  checkoutResult,
  checkoutResumo,
  cidadeDestino,
  deliveryMode,
  isDrive,
  isProfileComplete,
  pagamentoBandeira,
  pagamentoParcelas,
  pagamentoTipo,
  tenantContext,
  tipoRetirada,
  styles: S,
  onAddressFieldsChange,
  onCalculateSummary,
  onCheckoutCepBlur,
  onCityChange,
  onDeliveryModeChange,
  onDriveChange,
  onFinalizeCheckout,
  onPaymentBrandChange,
  onPaymentInstallmentsChange,
  onPaymentTypeChange,
  onPickupTypeChange,
}) {
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '28px 16px' }}>
      <h2 style={{ margin: '0 0 20px', fontSize: 26, fontWeight: 800, color: '#1c1917' }}>Checkout</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20, alignItems: 'start' }}>
        <div style={{ display: 'grid', gap: 16 }}>
          <CheckoutDeliveryForm
            addressFields={addressFields}
            cidadeDestino={cidadeDestino}
            deliveryMode={deliveryMode}
            isDrive={isDrive}
            tenantContext={tenantContext}
            tipoRetirada={tipoRetirada}
            styles={S}
            onAddressFieldsChange={onAddressFieldsChange}
            onCalculateSummary={onCalculateSummary}
            onCheckoutCepBlur={onCheckoutCepBlur}
            onCityChange={onCityChange}
            onDeliveryModeChange={onDeliveryModeChange}
            onDriveChange={onDriveChange}
            onPickupTypeChange={onPickupTypeChange}
          />

          <CheckoutPaymentForm
            pagamentoBandeira={pagamentoBandeira}
            pagamentoParcelas={pagamentoParcelas}
            pagamentoTipo={pagamentoTipo}
            styles={S}
            onPaymentBrandChange={onPaymentBrandChange}
            onPaymentInstallmentsChange={onPaymentInstallmentsChange}
            onPaymentTypeChange={onPaymentTypeChange}
          />
        </div>

        <CheckoutSummary
          cart={cart}
          cartTotal={cartTotal}
          checkoutLoading={checkoutLoading}
          checkoutResult={checkoutResult}
          checkoutResumo={checkoutResumo}
          cidadeDestino={cidadeDestino}
          isProfileComplete={isProfileComplete}
          tenantContext={tenantContext}
          styles={S}
          onFinalizeCheckout={onFinalizeCheckout}
        />
      </div>
    </div>
  );
}
