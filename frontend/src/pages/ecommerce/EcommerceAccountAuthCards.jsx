import PropTypes from "prop-types";

import { ecommerceStylesPropType, fieldErrorPropType } from "./ecommerceAccountPropTypes";
import {
  FieldError,
  PasswordInput,
  checkboxInputStyle,
  checkboxLabelStyle,
  fieldInputStyle,
} from "./EcommerceAccountProfileForm";

export function RegisterCard({
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

export function LoginCard({
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
