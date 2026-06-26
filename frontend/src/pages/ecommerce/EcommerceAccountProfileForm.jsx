import PropTypes from "prop-types";

const fieldErrorPropType = PropTypes.shape({
  field: PropTypes.string,
  message: PropTypes.string,
});

const ecommerceStylesPropType = PropTypes.shape({
  accountCard: PropTypes.object,
  formInput: PropTypes.object,
  saveBtn: PropTypes.object,
});

export function fieldInputStyle(baseStyle, fieldError, field) {
  if (fieldError?.field !== field) return baseStyle;
  return {
    ...baseStyle,
    borderColor: "#dc2626",
    boxShadow: "0 0 0 3px rgba(220, 38, 38, 0.14)",
    background: "#fff7f7",
  };
}

export function checkboxInputStyle(fieldError, field) {
  if (fieldError?.field !== field) return { marginTop: 2 };
  return {
    marginTop: 2,
    outline: "3px solid rgba(220, 38, 38, 0.18)",
    outlineOffset: 3,
  };
}

export function checkboxLabelStyle(fieldError, field) {
  const base = {
    display: "flex",
    gap: 8,
    alignItems: "flex-start",
    fontSize: 12,
    color: "#57534e",
    lineHeight: 1.45,
  };

  if (fieldError?.field !== field) return base;
  return {
    ...base,
    border: "1px solid #fecaca",
    background: "#fff7f7",
    borderRadius: 8,
    padding: "8px 10px",
  };
}

export function FieldError({ field, fieldError }) {
  if (fieldError?.field !== field || !fieldError?.message) return null;

  return (
    <div
      role="alert"
      style={{
        color: "#b91c1c",
        fontSize: 12,
        fontWeight: 700,
        marginTop: 5,
      }}
    >
      {fieldError.message}
    </div>
  );
}

FieldError.propTypes = {
  field: PropTypes.string.isRequired,
  fieldError: fieldErrorPropType,
};

export function PasswordInput({ name, value, onChange, placeholder, visible, onToggle, style }) {
  return (
    <div style={{ position: "relative" }}>
      <input
        name={name}
        autoComplete="new-password"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        type={visible ? "text" : "password"}
        style={{ ...style, paddingRight: 80, width: "100%", boxSizing: "border-box" }}
      />
      <button
        type="button"
        onClick={onToggle}
        style={{
          position: "absolute",
          right: 10,
          top: "50%",
          transform: "translateY(-50%)",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        {visible ? "Ocultar" : "👁 Ver"}
      </button>
    </div>
  );
}

export default function CustomerProfileForm({
  customer,
  profileForm,
  setProfileForm,
  wishlistCount,
  notifyRequestsCount,
  profileSaving,
  styles: S,
  onDeliveryCepBlur,
  onLogout,
  onProfileCepBlur,
  onSaveProfile,
  profileFieldError,
  onClearProfileFieldError,
}) {
  const updateProfile = (field) => (e) => {
    onClearProfileFieldError(field);
    setProfileForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={S.accountCard}>
        <div style={{ fontWeight: 700, fontSize: 15, color: "#1a1a2e", marginBottom: 4 }}>
          Olá, {customer?.nome || profileForm.nome || "cliente"}! 👋
        </div>
        <div style={{ fontSize: 13, color: "#9ca3af", marginBottom: 14 }}>
          {customer?.email} • Lista de desejos: {wishlistCount} • Avisos: {notifyRequestsCount}
        </div>

        <form onSubmit={onSaveProfile} style={{ display: "grid", gap: 10 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: "#374151", marginBottom: 2 }}>
            Dados pessoais
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div>
              <input
                name="ecommerce_profile_nome"
                value={profileForm.nome}
                onChange={updateProfile("nome")}
                placeholder="Nome completo"
                style={fieldInputStyle(S.formInput, profileFieldError, "nome")}
              />
              <FieldError field="nome" fieldError={profileFieldError} />
            </div>
            <input
              value={customer?.email || ""}
              disabled
              placeholder="Email"
              style={{ ...S.formInput, background: "#f8fafc", color: "#9ca3af" }}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div>
              <input
                name="ecommerce_profile_telefone"
                value={profileForm.telefone}
                onChange={updateProfile("telefone")}
                placeholder="Telefone *"
                style={fieldInputStyle(S.formInput, profileFieldError, "telefone")}
                required
              />
              <FieldError field="telefone" fieldError={profileFieldError} />
            </div>
            <div>
              <input
                name="ecommerce_profile_cpf"
                value={profileForm.cpf}
                onChange={updateProfile("cpf")}
                placeholder="CPF"
                style={fieldInputStyle(S.formInput, profileFieldError, "cpf")}
              />
              <FieldError field="cpf" fieldError={profileFieldError} />
            </div>
          </div>

          <div
            style={{
              fontWeight: 600,
              fontSize: 13,
              color: "#374151",
              marginTop: 6,
              marginBottom: 2,
            }}
          >
            Endereço principal
          </div>
          <input
            name="ecommerce_profile_cep"
            value={profileForm.cep}
            onChange={updateProfile("cep")}
            onBlur={onProfileCepBlur}
            placeholder="CEP"
            style={S.formInput}
          />
          <input
            name="ecommerce_profile_endereco"
            value={profileForm.endereco}
            onChange={updateProfile("endereco")}
            placeholder="Rua / Avenida"
            style={fieldInputStyle(S.formInput, profileFieldError, "endereco")}
          />
          <FieldError field="endereco" fieldError={profileFieldError} />
          <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8 }}>
            <input
              name="ecommerce_profile_numero"
              value={profileForm.numero}
              onChange={updateProfile("numero")}
              placeholder="Número"
              style={S.formInput}
            />
            <input
              name="ecommerce_profile_complemento"
              value={profileForm.complemento}
              onChange={updateProfile("complemento")}
              placeholder="Complemento"
              style={S.formInput}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 100px", gap: 8 }}>
            <input
              name="ecommerce_profile_bairro"
              value={profileForm.bairro}
              onChange={updateProfile("bairro")}
              placeholder="Bairro"
              style={S.formInput}
            />
            <input
              name="ecommerce_profile_cidade"
              value={profileForm.cidade}
              onChange={updateProfile("cidade")}
              placeholder="Cidade"
              style={S.formInput}
            />
            <input
              name="ecommerce_profile_estado"
              value={profileForm.estado}
              onChange={updateProfile("estado")}
              placeholder="UF"
              style={S.formInput}
            />
          </div>

          <button
            type="button"
            onClick={() =>
              setProfileForm((prev) => ({
                ...prev,
                usar_endereco_entrega_diferente: !prev.usar_endereco_entrega_diferente,
              }))
            }
            style={{
              justifySelf: "start",
              background: "transparent",
              border: "1.5px solid #e7e5e4",
              color: "#f97316",
              borderRadius: 8,
              padding: "8px 14px",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {profileForm.usar_endereco_entrega_diferente
              ? "− Remover endereço alternativo"
              : "+ Adicionar endereço de entrega diferente"}
          </button>

          {profileForm.usar_endereco_entrega_diferente && (
            <div
              style={{
                display: "grid",
                gap: 8,
                background: "#faf7f4",
                border: "1px solid #e7e5e4",
                borderRadius: 12,
                padding: 14,
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 13, color: "#374151" }}>
                Endereço de entrega alternativo
              </div>
              <input
                name="ecommerce_profile_entrega_nome"
                value={profileForm.entrega_nome}
                onChange={updateProfile("entrega_nome")}
                placeholder="Nome para entrega"
                style={fieldInputStyle(S.formInput, profileFieldError, "entrega_nome")}
              />
              <FieldError field="entrega_nome" fieldError={profileFieldError} />
              <input
                name="ecommerce_profile_entrega_cep"
                value={profileForm.entrega_cep}
                onChange={updateProfile("entrega_cep")}
                onBlur={onDeliveryCepBlur}
                placeholder="CEP"
                style={S.formInput}
              />
              <input
                name="ecommerce_profile_entrega_endereco"
                value={profileForm.entrega_endereco}
                onChange={updateProfile("entrega_endereco")}
                placeholder="Rua / Avenida"
                style={fieldInputStyle(S.formInput, profileFieldError, "entrega_endereco")}
              />
              <FieldError field="entrega_endereco" fieldError={profileFieldError} />
              <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8 }}>
                <input
                  name="ecommerce_profile_entrega_numero"
                  value={profileForm.entrega_numero}
                  onChange={updateProfile("entrega_numero")}
                  placeholder="Número"
                  style={S.formInput}
                />
                <input
                  name="ecommerce_profile_entrega_complemento"
                  value={profileForm.entrega_complemento}
                  onChange={updateProfile("entrega_complemento")}
                  placeholder="Complemento"
                  style={S.formInput}
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 100px", gap: 8 }}>
                <input
                  name="ecommerce_profile_entrega_bairro"
                  value={profileForm.entrega_bairro}
                  onChange={updateProfile("entrega_bairro")}
                  placeholder="Bairro"
                  style={S.formInput}
                />
                <input
                  name="ecommerce_profile_entrega_cidade"
                  value={profileForm.entrega_cidade}
                  onChange={updateProfile("entrega_cidade")}
                  placeholder="Cidade"
                  style={S.formInput}
                />
                <input
                  name="ecommerce_profile_entrega_estado"
                  value={profileForm.entrega_estado}
                  onChange={updateProfile("entrega_estado")}
                  placeholder="UF"
                  style={S.formInput}
                />
              </div>
            </div>
          )}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="submit" disabled={profileSaving} style={S.saveBtn}>
              {profileSaving ? "Salvando..." : "✓ Salvar cadastro"}
            </button>
            <button
              type="button"
              onClick={onLogout}
              style={{
                background: "#f1f5f9",
                border: "1.5px solid #e5e7eb",
                color: "#ef4444",
                borderRadius: 10,
                padding: "10px 20px",
                fontWeight: 600,
                fontSize: 14,
                cursor: "pointer",
              }}
            >
              Sair da conta
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

CustomerProfileForm.propTypes = {
  customer: PropTypes.object,
  profileForm: PropTypes.object.isRequired,
  setProfileForm: PropTypes.func.isRequired,
  wishlistCount: PropTypes.number.isRequired,
  notifyRequestsCount: PropTypes.number.isRequired,
  profileSaving: PropTypes.bool.isRequired,
  styles: ecommerceStylesPropType.isRequired,
  onDeliveryCepBlur: PropTypes.func.isRequired,
  onLogout: PropTypes.func.isRequired,
  onProfileCepBlur: PropTypes.func.isRequired,
  onSaveProfile: PropTypes.func.isRequired,
  profileFieldError: fieldErrorPropType,
  onClearProfileFieldError: PropTypes.func.isRequired,
};
