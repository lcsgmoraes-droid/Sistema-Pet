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
}) {
  const updateProfile = (field) => (e) =>
    setProfileForm((prev) => ({ ...prev, [field]: e.target.value }));

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
            <input
              value={profileForm.nome}
              onChange={updateProfile("nome")}
              placeholder="Nome completo"
              style={S.formInput}
            />
            <input
              value={customer?.email || ""}
              disabled
              placeholder="Email"
              style={{ ...S.formInput, background: "#f8fafc", color: "#9ca3af" }}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <input
              value={profileForm.telefone}
              onChange={updateProfile("telefone")}
              placeholder="Telefone *"
              style={S.formInput}
              required
            />
            <input
              value={profileForm.cpf}
              onChange={updateProfile("cpf")}
              placeholder="CPF"
              style={S.formInput}
            />
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
            value={profileForm.cep}
            onChange={updateProfile("cep")}
            onBlur={onProfileCepBlur}
            placeholder="CEP"
            style={S.formInput}
          />
          <input
            value={profileForm.endereco}
            onChange={updateProfile("endereco")}
            placeholder="Rua / Avenida"
            style={S.formInput}
          />
          <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8 }}>
            <input
              value={profileForm.numero}
              onChange={updateProfile("numero")}
              placeholder="Número"
              style={S.formInput}
            />
            <input
              value={profileForm.complemento}
              onChange={updateProfile("complemento")}
              placeholder="Complemento"
              style={S.formInput}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 100px", gap: 8 }}>
            <input
              value={profileForm.bairro}
              onChange={updateProfile("bairro")}
              placeholder="Bairro"
              style={S.formInput}
            />
            <input
              value={profileForm.cidade}
              onChange={updateProfile("cidade")}
              placeholder="Cidade"
              style={S.formInput}
            />
            <input
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
                value={profileForm.entrega_nome}
                onChange={updateProfile("entrega_nome")}
                placeholder="Nome para entrega"
                style={S.formInput}
              />
              <input
                value={profileForm.entrega_cep}
                onChange={updateProfile("entrega_cep")}
                onBlur={onDeliveryCepBlur}
                placeholder="CEP"
                style={S.formInput}
              />
              <input
                value={profileForm.entrega_endereco}
                onChange={updateProfile("entrega_endereco")}
                placeholder="Rua / Avenida"
                style={S.formInput}
              />
              <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 8 }}>
                <input
                  value={profileForm.entrega_numero}
                  onChange={updateProfile("entrega_numero")}
                  placeholder="Número"
                  style={S.formInput}
                />
                <input
                  value={profileForm.entrega_complemento}
                  onChange={updateProfile("entrega_complemento")}
                  placeholder="Complemento"
                  style={S.formInput}
                />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 100px", gap: 8 }}>
                <input
                  value={profileForm.entrega_bairro}
                  onChange={updateProfile("entrega_bairro")}
                  placeholder="Bairro"
                  style={S.formInput}
                />
                <input
                  value={profileForm.entrega_cidade}
                  onChange={updateProfile("entrega_cidade")}
                  placeholder="Cidade"
                  style={S.formInput}
                />
                <input
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

function RegisterCard({
  authLoading,
  registerForm,
  setRegisterForm,
  showRegisterPassword,
  styles: S,
  onRegister,
  onToggleRegisterPassword,
}) {
  const updateRegister = (field) => (e) =>
    setRegisterForm((prev) => ({ ...prev, [field]: e.target.value }));
  const updateRegisterCheck = (field) => (e) =>
    setRegisterForm((prev) => ({ ...prev, [field]: e.target.checked }));

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
          style={S.formInput}
        />
        <input
          name="ecommerce_register_cpf"
          autoComplete="off"
          value={registerForm.cpf}
          onChange={updateRegister("cpf")}
          placeholder="CPF *  (000.000.000-00)"
          inputMode="numeric"
          style={S.formInput}
          required
        />
        <input
          name="ecommerce_register_telefone"
          autoComplete="off"
          value={registerForm.telefone}
          onChange={updateRegister("telefone")}
          placeholder="Telefone/WhatsApp *"
          inputMode="tel"
          style={S.formInput}
          required
        />
        <input
          name="ecommerce_register_email"
          autoComplete="off"
          value={registerForm.email}
          onChange={updateRegister("email")}
          placeholder="Email"
          type="email"
          style={S.formInput}
        />
        <PasswordInput
          name="ecommerce_register_password"
          value={registerForm.password}
          onChange={updateRegister("password")}
          placeholder="Senha (minimo 8 caracteres)"
          visible={showRegisterPassword}
          onToggle={onToggleRegisterPassword}
          style={S.formInput}
        />
        <label
          style={{
            display: "flex",
            gap: 8,
            alignItems: "flex-start",
            fontSize: 12,
            color: "#57534e",
            lineHeight: 1.45,
          }}
        >
          <input
            type="checkbox"
            checked={registerForm.accepted_terms}
            onChange={updateRegisterCheck("accepted_terms")}
            style={{ marginTop: 2 }}
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
        <label
          style={{
            display: "flex",
            gap: 8,
            alignItems: "flex-start",
            fontSize: 12,
            color: "#57534e",
            lineHeight: 1.45,
          }}
        >
          <input
            type="checkbox"
            checked={registerForm.accepted_privacy}
            onChange={updateRegisterCheck("accepted_privacy")}
            style={{ marginTop: 2 }}
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
        <button type="submit" disabled={authLoading} style={S.saveBtn}>
          {authLoading ? "Criando..." : "Criar minha conta"}
        </button>
      </form>
    </div>
  );
}

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
  profileForm,
  profileSaving,
  recoveryForm,
  recoveryLoading,
  recoveryStep,
  recoveryTokenFromLink,
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
            onRegister={onRegister}
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
