import PropTypes from "prop-types";

import { LoginCard, RegisterCard } from "./EcommerceAccountAuthCards";
import CustomerProfileForm from "./EcommerceAccountProfileForm";
import { ecommerceStylesPropType, fieldErrorPropType } from "./ecommerceAccountPropTypes";

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
