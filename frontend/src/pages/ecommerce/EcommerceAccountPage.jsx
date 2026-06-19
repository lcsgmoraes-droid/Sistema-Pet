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

function fieldInputStyle(baseStyle, fieldError, field) {
  if (fieldError?.field !== field) return baseStyle;
  return {
    ...baseStyle,
    borderColor: "#dc2626",
    boxShadow: "0 0 0 3px rgba(220, 38, 38, 0.14)",
    background: "#fff7f7",
  };
}

function checkboxInputStyle(fieldError, field) {
  if (fieldError?.field !== field) return { marginTop: 2 };
  return {
    marginTop: 2,
    outline: "3px solid rgba(220, 38, 38, 0.18)",
    outlineOffset: 3,
  };
}

function checkboxLabelStyle(fieldError, field) {
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

function FieldError({ field, fieldError }) {
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

function PasswordInput({ name, value, onChange, placeholder, visible, onToggle, style }) {
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

function CustomerProfileForm({
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

function RegisterCard({
  authLoading,
  registerForm,
  setRegisterForm,
  showRegisterPassword,
  styles: S,
  registerFieldError,
  onRegister,
  onClearRegisterFieldError,
  onToggleRegisterPassword,
}) {
  const updateRegister = (field) => (e) => {
    onClearRegisterFieldError(field);
    setRegisterForm((prev) => ({ ...prev, [field]: e.target.value }));
  };
  const updateRegisterCheck = (field) => (e) => {
    onClearRegisterFieldError(field);
    setRegisterForm((prev) => ({ ...prev, [field]: e.target.checked }));
  };

  return (
    <div style={S.accountCard}>
      <div style={{ fontWeight: 800, fontSize: 20, color: "#1c1917", marginBottom: 14 }}>
        Criar conta
      </div>
      <form onSubmit={onRegister} autoComplete="off" style={{ display: "grid", gap: 10 }}>
        <input
          name="ecommerce_register_nome"
          autoComplete="off"
          value={registerForm.nome}
          onChange={updateRegister("nome")}
          placeholder="Nome completo"
          style={fieldInputStyle(S.formInput, registerFieldError, "nome")}
        />
        <FieldError field="nome" fieldError={registerFieldError} />
        <input
          name="ecommerce_register_cpf"
          autoComplete="off"
          value={registerForm.cpf}
          onChange={updateRegister("cpf")}
          placeholder="CPF *  (000.000.000-00)"
          inputMode="numeric"
          style={fieldInputStyle(S.formInput, registerFieldError, "cpf")}
          required
        />
        <FieldError field="cpf" fieldError={registerFieldError} />
        <input
          name="ecommerce_register_telefone"
          autoComplete="off"
          value={registerForm.telefone}
          onChange={updateRegister("telefone")}
          placeholder="Telefone/WhatsApp *"
          inputMode="tel"
          style={fieldInputStyle(S.formInput, registerFieldError, "telefone")}
          required
        />
        <FieldError field="telefone" fieldError={registerFieldError} />
        <input
          name="ecommerce_register_email"
          autoComplete="off"
          value={registerForm.email}
          onChange={updateRegister("email")}
          placeholder="Email"
          type="email"
          style={fieldInputStyle(S.formInput, registerFieldError, "email")}
        />
        <FieldError field="email" fieldError={registerFieldError} />
        <PasswordInput
          name="ecommerce_register_password"
          value={registerForm.password}
          onChange={updateRegister("password")}
          placeholder="Senha (minimo 8 caracteres)"
          visible={showRegisterPassword}
          onToggle={onToggleRegisterPassword}
          style={fieldInputStyle(S.formInput, registerFieldError, "senha")}
        />
        <FieldError field="senha" fieldError={registerFieldError} />
        <label style={checkboxLabelStyle(registerFieldError, "accepted_terms")}>
          <input
            name="ecommerce_register_accepted_terms"
            type="checkbox"
            checked={registerForm.accepted_terms}
            onChange={updateRegisterCheck("accepted_terms")}
            style={checkboxInputStyle(registerFieldError, "accepted_terms")}
          />
          <span>
            Li e aceito os{" "}
            <a
              href="/termos"
              target="_blank"
              rel="noreferrer"
              style={{ color: "#7c3aed", fontWeight: 700 }}
            >
              Termos de Uso
            </a>
            .
          </span>
        </label>
        <FieldError field="accepted_terms" fieldError={registerFieldError} />
        <label style={checkboxLabelStyle(registerFieldError, "accepted_privacy")}>
          <input
            name="ecommerce_register_accepted_privacy"
            type="checkbox"
            checked={registerForm.accepted_privacy}
            onChange={updateRegisterCheck("accepted_privacy")}
            style={checkboxInputStyle(registerFieldError, "accepted_privacy")}
          />
          <span>
            Li e aceito a{" "}
            <a
              href="/privacidade"
              target="_blank"
              rel="noreferrer"
              style={{ color: "#7c3aed", fontWeight: 700 }}
            >
              Politica de Privacidade
            </a>
            .
          </span>
        </label>
        <FieldError field="accepted_privacy" fieldError={registerFieldError} />
        <button type="submit" disabled={authLoading} style={S.saveBtn}>
          {authLoading ? "Criando..." : "Criar minha conta"}
        </button>
      </form>
    </div>
  );
}

RegisterCard.propTypes = {
  authLoading: PropTypes.bool.isRequired,
  registerForm: PropTypes.shape({
    accepted_privacy: PropTypes.bool,
    accepted_terms: PropTypes.bool,
    cpf: PropTypes.string,
    email: PropTypes.string,
    nome: PropTypes.string,
    password: PropTypes.string,
    telefone: PropTypes.string,
  }).isRequired,
  setRegisterForm: PropTypes.func.isRequired,
  showRegisterPassword: PropTypes.bool.isRequired,
  styles: ecommerceStylesPropType.isRequired,
  registerFieldError: fieldErrorPropType,
  onRegister: PropTypes.func.isRequired,
  onClearRegisterFieldError: PropTypes.func.isRequired,
  onToggleRegisterPassword: PropTypes.func.isRequired,
};

function PasswordRecoveryForm({
  recoveryForm,
  recoveryLoading,
  recoveryStep,
  recoveryTokenFromLink,
  setRecoveryForm,
  showRecoveryConfirmPassword,
  showRecoveryPassword,
  styles: S,
  onClosePasswordRecovery,
  onPasswordRecoveryRequest,
  onPasswordRecoveryReset,
  onSwitchRecoveryToRequest,
  onSwitchRecoveryToReset,
  onToggleRecoveryConfirmPassword,
  onToggleRecoveryPassword,
}) {
  const updateRecovery = (field) => (e) =>
    setRecoveryForm((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <form
      onSubmit={recoveryStep === "request" ? onPasswordRecoveryRequest : onPasswordRecoveryReset}
      autoComplete="off"
      style={{ display: "grid", gap: 10 }}
    >
      <input
        name="ecommerce_recovery_email"
        autoComplete="off"
        value={recoveryForm.email}
        onChange={updateRecovery("email")}
        placeholder="Email"
        type="email"
        style={S.formInput}
      />

      {recoveryStep === "reset" && (
        <>
          {recoveryTokenFromLink ? (
            <div
              style={{
                border: "1px solid #ddd6fe",
                background: "#f5f3ff",
                color: "#5b21b6",
                borderRadius: 10,
                padding: "10px 12px",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              Link de recuperacao carregado. Basta cadastrar a nova senha.
            </div>
          ) : (
            <input
              name="ecommerce_recovery_token"
              autoComplete="off"
              inputMode="numeric"
              value={recoveryForm.token}
              onChange={updateRecovery("token")}
              placeholder="Codigo de recuperacao"
              type="text"
              style={S.formInput}
            />
          )}
          <PasswordInput
            name="ecommerce_recovery_password"
            value={recoveryForm.novaSenha}
            onChange={updateRecovery("novaSenha")}
            placeholder="Nova senha"
            visible={showRecoveryPassword}
            onToggle={onToggleRecoveryPassword}
            style={S.formInput}
          />
          <PasswordInput
            name="ecommerce_recovery_password_confirm"
            value={recoveryForm.confirmarSenha}
            onChange={updateRecovery("confirmarSenha")}
            placeholder="Confirmar nova senha"
            visible={showRecoveryConfirmPassword}
            onToggle={onToggleRecoveryConfirmPassword}
            style={S.formInput}
          />
        </>
      )}

      <button type="submit" disabled={recoveryLoading} style={S.saveBtn}>
        {recoveryLoading
          ? "Processando..."
          : recoveryStep === "request"
            ? "Enviar instruções"
            : "Salvar nova senha"}
      </button>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {recoveryStep === "request" ? (
          <button
            type="button"
            onClick={onSwitchRecoveryToReset}
            style={{
              background: "#fff",
              border: "1.5px solid #d1d5db",
              color: "#374151",
              borderRadius: 10,
              padding: "10px 16px",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Ja tenho o codigo
          </button>
        ) : (
          <button
            type="button"
            onClick={onSwitchRecoveryToRequest}
            style={{
              background: "#fff",
              border: "1.5px solid #d1d5db",
              color: "#374151",
              borderRadius: 10,
              padding: "10px 16px",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Solicitar novo link
          </button>
        )}

        <button
          type="button"
          onClick={onClosePasswordRecovery}
          style={{
            background: "transparent",
            border: "none",
            color: "#2563eb",
            fontWeight: 700,
            fontSize: 13,
            cursor: "pointer",
            padding: "10px 0",
          }}
        >
          Voltar para login
        </button>
      </div>
    </form>
  );
}

function LoginCard({
  authLoading,
  loginForm,
  passwordRecoveryMode,
  recoveryForm,
  recoveryLoading,
  recoveryStep,
  recoveryTokenFromLink,
  setLoginForm,
  setRecoveryForm,
  showLoginPassword,
  showRecoveryConfirmPassword,
  showRecoveryPassword,
  styles: S,
  onClosePasswordRecovery,
  onLogin,
  onOpenPasswordRecovery,
  onPasswordRecoveryRequest,
  onPasswordRecoveryReset,
  onSwitchRecoveryToRequest,
  onSwitchRecoveryToReset,
  onToggleLoginPassword,
  onToggleRecoveryConfirmPassword,
  onToggleRecoveryPassword,
}) {
  const updateLogin = (field) => (e) =>
    setLoginForm((prev) => ({ ...prev, [field]: e.target.value }));

  return (
    <div style={S.accountCard}>
      <div style={{ fontWeight: 800, fontSize: 20, color: "#1c1917", marginBottom: 10 }}>
        {passwordRecoveryMode ? "Recuperar senha" : "Entrar"}
      </div>
      <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 14 }}>
        {passwordRecoveryMode
          ? recoveryStep === "request"
            ? "Informe o e-mail da conta e enviaremos as instruções."
            : recoveryTokenFromLink
              ? "Link seguro carregado. Escolha uma nova senha."
              : "Digite o codigo recebido e escolha uma nova senha."
          : "Acesse sua conta para acompanhar pedidos e finalizar a compra mais rápido."}
      </div>

      {passwordRecoveryMode ? (
        <PasswordRecoveryForm
          recoveryForm={recoveryForm}
          recoveryLoading={recoveryLoading}
          recoveryStep={recoveryStep}
          recoveryTokenFromLink={recoveryTokenFromLink}
          setRecoveryForm={setRecoveryForm}
          showRecoveryConfirmPassword={showRecoveryConfirmPassword}
          showRecoveryPassword={showRecoveryPassword}
          styles={S}
          onClosePasswordRecovery={onClosePasswordRecovery}
          onPasswordRecoveryRequest={onPasswordRecoveryRequest}
          onPasswordRecoveryReset={onPasswordRecoveryReset}
          onSwitchRecoveryToRequest={onSwitchRecoveryToRequest}
          onSwitchRecoveryToReset={onSwitchRecoveryToReset}
          onToggleRecoveryConfirmPassword={onToggleRecoveryConfirmPassword}
          onToggleRecoveryPassword={onToggleRecoveryPassword}
        />
      ) : (
        <form onSubmit={onLogin} autoComplete="off" style={{ display: "grid", gap: 10 }}>
          <input
            name="ecommerce_login_email"
            autoComplete="off"
            value={loginForm.email}
            onChange={updateLogin("email")}
            placeholder="Email"
            type="email"
            style={S.formInput}
          />
          <PasswordInput
            name="ecommerce_login_password"
            value={loginForm.password}
            onChange={updateLogin("password")}
            placeholder="Senha"
            visible={showLoginPassword}
            onToggle={onToggleLoginPassword}
            style={S.formInput}
          />
          <button type="submit" disabled={authLoading} style={S.saveBtn}>
            {authLoading ? "Entrando..." : "Entrar"}
          </button>
          <button
            type="button"
            onClick={() => onOpenPasswordRecovery("request")}
            style={{
              background: "transparent",
              border: "none",
              color: "#2563eb",
              fontWeight: 700,
              fontSize: 13,
              cursor: "pointer",
              justifySelf: "start",
              padding: 0,
            }}
          >
            Esqueci minha senha
          </button>
        </form>
      )}
    </div>
  );
}

export default function EcommerceAccountPage({
  authLoading,
  customer,
  customerToken,
  isMobile,
  loginForm,
  notifyRequestsCount,
  passwordRecoveryMode,
  profileFieldError,
  profileForm,
  profileSaving,
  recoveryForm,
  recoveryLoading,
  recoveryStep,
  recoveryTokenFromLink,
  registerFieldError,
  registerForm,
  setLoginForm,
  setProfileForm,
  setRecoveryForm,
  setRegisterForm,
  showLoginPassword,
  showRecoveryConfirmPassword,
  showRecoveryPassword,
  showRegisterPassword,
  styles: S,
  wishlistCount,
  onClosePasswordRecovery,
  onClearProfileFieldError,
  onClearRegisterFieldError,
  onDeliveryCepBlur,
  onLogin,
  onLogout,
  onOpenPasswordRecovery,
  onPasswordRecoveryRequest,
  onPasswordRecoveryReset,
  onProfileCepBlur,
  onRegister,
  onSaveProfile,
  onSwitchRecoveryToRequest,
  onSwitchRecoveryToReset,
  onToggleLoginPassword,
  onToggleRecoveryConfirmPassword,
  onToggleRecoveryPassword,
  onToggleRegisterPassword,
}) {
  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "28px 16px" }}>
      <h2 style={{ margin: "0 0 20px", fontSize: 26, fontWeight: 800, color: "#1c1917" }}>
        Minha Conta
      </h2>
      {customerToken ? (
        <CustomerProfileForm
          customer={customer}
          profileForm={profileForm}
          profileSaving={profileSaving}
          setProfileForm={setProfileForm}
          styles={S}
          wishlistCount={wishlistCount}
          notifyRequestsCount={notifyRequestsCount}
          onDeliveryCepBlur={onDeliveryCepBlur}
          onLogout={onLogout}
          onProfileCepBlur={onProfileCepBlur}
          onSaveProfile={onSaveProfile}
          profileFieldError={profileFieldError}
          onClearProfileFieldError={onClearProfileFieldError}
        />
      ) : (
        <div
          style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 20 }}
        >
          <RegisterCard
            authLoading={authLoading}
            registerForm={registerForm}
            setRegisterForm={setRegisterForm}
            showRegisterPassword={showRegisterPassword}
            styles={S}
            registerFieldError={registerFieldError}
            onRegister={onRegister}
            onClearRegisterFieldError={onClearRegisterFieldError}
            onToggleRegisterPassword={onToggleRegisterPassword}
          />
          <LoginCard
            authLoading={authLoading}
            loginForm={loginForm}
            passwordRecoveryMode={passwordRecoveryMode}
            recoveryForm={recoveryForm}
            recoveryLoading={recoveryLoading}
            recoveryStep={recoveryStep}
            recoveryTokenFromLink={recoveryTokenFromLink}
            setLoginForm={setLoginForm}
            setRecoveryForm={setRecoveryForm}
            showLoginPassword={showLoginPassword}
            showRecoveryConfirmPassword={showRecoveryConfirmPassword}
            showRecoveryPassword={showRecoveryPassword}
            styles={S}
            onClosePasswordRecovery={onClosePasswordRecovery}
            onLogin={onLogin}
            onOpenPasswordRecovery={onOpenPasswordRecovery}
            onPasswordRecoveryRequest={onPasswordRecoveryRequest}
            onPasswordRecoveryReset={onPasswordRecoveryReset}
            onSwitchRecoveryToRequest={onSwitchRecoveryToRequest}
            onSwitchRecoveryToReset={onSwitchRecoveryToReset}
            onToggleLoginPassword={onToggleLoginPassword}
            onToggleRecoveryConfirmPassword={onToggleRecoveryConfirmPassword}
            onToggleRecoveryPassword={onToggleRecoveryPassword}
          />
        </div>
      )}
    </div>
  );
}

EcommerceAccountPage.propTypes = {
  authLoading: PropTypes.bool.isRequired,
  customer: PropTypes.object,
  customerToken: PropTypes.string,
  isMobile: PropTypes.bool.isRequired,
  loginForm: PropTypes.object.isRequired,
  notifyRequestsCount: PropTypes.number.isRequired,
  passwordRecoveryMode: PropTypes.bool.isRequired,
  profileFieldError: fieldErrorPropType,
  profileForm: PropTypes.object.isRequired,
  profileSaving: PropTypes.bool.isRequired,
  recoveryForm: PropTypes.object.isRequired,
  recoveryLoading: PropTypes.bool.isRequired,
  recoveryStep: PropTypes.string.isRequired,
  recoveryTokenFromLink: PropTypes.bool.isRequired,
  registerFieldError: fieldErrorPropType,
  registerForm: PropTypes.object.isRequired,
  setLoginForm: PropTypes.func.isRequired,
  setProfileForm: PropTypes.func.isRequired,
  setRecoveryForm: PropTypes.func.isRequired,
  setRegisterForm: PropTypes.func.isRequired,
  showLoginPassword: PropTypes.bool.isRequired,
  showRecoveryConfirmPassword: PropTypes.bool.isRequired,
  showRecoveryPassword: PropTypes.bool.isRequired,
  showRegisterPassword: PropTypes.bool.isRequired,
  styles: ecommerceStylesPropType.isRequired,
  wishlistCount: PropTypes.number.isRequired,
  onClosePasswordRecovery: PropTypes.func.isRequired,
  onClearProfileFieldError: PropTypes.func.isRequired,
  onClearRegisterFieldError: PropTypes.func.isRequired,
  onDeliveryCepBlur: PropTypes.func.isRequired,
  onLogin: PropTypes.func.isRequired,
  onLogout: PropTypes.func.isRequired,
  onOpenPasswordRecovery: PropTypes.func.isRequired,
  onPasswordRecoveryRequest: PropTypes.func.isRequired,
  onPasswordRecoveryReset: PropTypes.func.isRequired,
  onProfileCepBlur: PropTypes.func.isRequired,
  onRegister: PropTypes.func.isRequired,
  onSaveProfile: PropTypes.func.isRequired,
  onSwitchRecoveryToRequest: PropTypes.func.isRequired,
  onSwitchRecoveryToReset: PropTypes.func.isRequired,
  onToggleLoginPassword: PropTypes.func.isRequired,
  onToggleRecoveryConfirmPassword: PropTypes.func.isRequired,
  onToggleRecoveryPassword: PropTypes.func.isRequired,
  onToggleRegisterPassword: PropTypes.func.isRequired,
};
