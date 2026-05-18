import {
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
  LogOut,
  Mail,
  MapPin,
  Minus,
  Plus,
  RotateCcw,
  Save,
  ShieldCheck,
  UserPlus,
  UserRound,
} from 'lucide-react';

function FieldGrid({ children, columns = '1fr 1fr', isMobile }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : columns, gap: 8 }}>
      {children}
    </div>
  );
}

function SectionTitle({ children, icon: Icon }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontWeight: 600, fontSize: 13, color: '#374151', marginTop: 6, marginBottom: 2 }}>
      {Icon ? <Icon size={15} /> : null}
      {children}
    </div>
  );
}

function PasswordInput({
  autoComplete = 'new-password',
  name,
  placeholder,
  show,
  style,
  value,
  onChange,
  onToggle,
}) {
  const ToggleIcon = show ? EyeOff : Eye;

  return (
    <div style={{ position: 'relative' }}>
      <input
        name={name}
        autoComplete={autoComplete}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        type={show ? 'text' : 'password'}
        style={{ ...style, paddingRight: 88, width: '100%', boxSizing: 'border-box' }}
      />
      <button
        type="button"
        aria-label={show ? 'Ocultar senha' : 'Ver senha'}
        onClick={onToggle}
        style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: '#6b7280', display: 'inline-flex', alignItems: 'center', gap: 4 }}
      >
        <ToggleIcon size={14} />
        {show ? 'Ocultar' : 'Ver'}
      </button>
    </div>
  );
}

function AccountProfileForm({
  customer,
  isMobile,
  notifyRequestsCount,
  profileForm,
  profileSaving,
  styles: S,
  wishlistCount,
  onDeliveryCepBlur,
  onLogout,
  onProfileCepBlur,
  onProfileFormChange,
  onSaveProfile,
}) {
  const updateProfile = (field, value) => onProfileFormChange((prev) => ({ ...prev, [field]: value }));

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={S.accountCard}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 15, color: '#1a1a2e', marginBottom: 4 }}>
          <UserRound size={17} />
          Ola, {customer?.nome || profileForm.nome || 'cliente'}!
        </div>
        <div style={{ fontSize: 13, color: '#9ca3af', marginBottom: 14 }}>
          {customer?.email} | Lista de desejos: {wishlistCount} | Avisos: {notifyRequestsCount}
        </div>

        <form onSubmit={onSaveProfile} style={{ display: 'grid', gap: 10 }}>
          <SectionTitle icon={UserRound}>Dados pessoais</SectionTitle>
          <FieldGrid isMobile={isMobile}>
            <input value={profileForm.nome} onChange={(event) => updateProfile('nome', event.target.value)} placeholder="Nome completo" style={S.formInput} />
            <input value={customer?.email || ''} disabled placeholder="Email" style={{ ...S.formInput, background: '#f8fafc', color: '#9ca3af' }} />
          </FieldGrid>
          <FieldGrid isMobile={isMobile}>
            <input value={profileForm.telefone} onChange={(event) => updateProfile('telefone', event.target.value)} placeholder="Telefone *" style={S.formInput} required />
            <input value={profileForm.cpf} onChange={(event) => updateProfile('cpf', event.target.value)} placeholder="CPF" style={S.formInput} />
          </FieldGrid>

          <SectionTitle icon={MapPin}>Endereco principal</SectionTitle>
          <input value={profileForm.cep} onChange={(event) => updateProfile('cep', event.target.value)} onBlur={onProfileCepBlur} placeholder="CEP" style={S.formInput} />
          <input value={profileForm.endereco} onChange={(event) => updateProfile('endereco', event.target.value)} placeholder="Rua / Avenida" style={S.formInput} />
          <FieldGrid columns="140px 1fr" isMobile={isMobile}>
            <input value={profileForm.numero} onChange={(event) => updateProfile('numero', event.target.value)} placeholder="Numero" style={S.formInput} />
            <input value={profileForm.complemento} onChange={(event) => updateProfile('complemento', event.target.value)} placeholder="Complemento" style={S.formInput} />
          </FieldGrid>
          <FieldGrid columns="1fr 1fr 100px" isMobile={isMobile}>
            <input value={profileForm.bairro} onChange={(event) => updateProfile('bairro', event.target.value)} placeholder="Bairro" style={S.formInput} />
            <input value={profileForm.cidade} onChange={(event) => updateProfile('cidade', event.target.value)} placeholder="Cidade" style={S.formInput} />
            <input value={profileForm.estado} onChange={(event) => updateProfile('estado', event.target.value)} placeholder="UF" style={S.formInput} />
          </FieldGrid>

          <button
            type="button"
            onClick={() => onProfileFormChange((prev) => ({ ...prev, usar_endereco_entrega_diferente: !prev.usar_endereco_entrega_diferente }))}
            style={{ justifySelf: 'start', background: 'transparent', border: '1.5px solid #e7e5e4', color: '#f97316', borderRadius: 8, padding: '8px 14px', fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            {profileForm.usar_endereco_entrega_diferente ? <Minus size={14} /> : <Plus size={14} />}
            {profileForm.usar_endereco_entrega_diferente ? 'Remover endereco alternativo' : 'Adicionar endereco de entrega diferente'}
          </button>

          {profileForm.usar_endereco_entrega_diferente && (
            <div style={{ display: 'grid', gap: 8, background: '#faf7f4', border: '1px solid #e7e5e4', borderRadius: 12, padding: 14 }}>
              <SectionTitle icon={MapPin}>Endereco de entrega alternativo</SectionTitle>
              <input value={profileForm.entrega_nome} onChange={(event) => updateProfile('entrega_nome', event.target.value)} placeholder="Nome para entrega" style={S.formInput} />
              <input value={profileForm.entrega_cep} onChange={(event) => updateProfile('entrega_cep', event.target.value)} onBlur={onDeliveryCepBlur} placeholder="CEP" style={S.formInput} />
              <input value={profileForm.entrega_endereco} onChange={(event) => updateProfile('entrega_endereco', event.target.value)} placeholder="Rua / Avenida" style={S.formInput} />
              <FieldGrid columns="140px 1fr" isMobile={isMobile}>
                <input value={profileForm.entrega_numero} onChange={(event) => updateProfile('entrega_numero', event.target.value)} placeholder="Numero" style={S.formInput} />
                <input value={profileForm.entrega_complemento} onChange={(event) => updateProfile('entrega_complemento', event.target.value)} placeholder="Complemento" style={S.formInput} />
              </FieldGrid>
              <FieldGrid columns="1fr 1fr 100px" isMobile={isMobile}>
                <input value={profileForm.entrega_bairro} onChange={(event) => updateProfile('entrega_bairro', event.target.value)} placeholder="Bairro" style={S.formInput} />
                <input value={profileForm.entrega_cidade} onChange={(event) => updateProfile('entrega_cidade', event.target.value)} placeholder="Cidade" style={S.formInput} />
                <input value={profileForm.entrega_estado} onChange={(event) => updateProfile('entrega_estado', event.target.value)} placeholder="UF" style={S.formInput} />
              </FieldGrid>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="submit" disabled={profileSaving} style={{ ...S.saveBtn, display: 'inline-flex', alignItems: 'center', gap: 7 }}>
              <Save size={15} />
              {profileSaving ? 'Salvando...' : 'Salvar cadastro'}
            </button>
            <button type="button" onClick={onLogout} style={{ background: '#f1f5f9', border: '1.5px solid #e5e7eb', color: '#ef4444', borderRadius: 10, padding: '10px 20px', fontWeight: 600, fontSize: 14, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 7 }}>
              <LogOut size={15} />
              Sair da conta
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RegisterPanel({
  authLoading,
  registerForm,
  showRegisterPassword,
  styles: S,
  onRegister,
  onRegisterFormChange,
  onToggleRegisterPassword,
}) {
  const updateRegister = (field, value) => onRegisterFormChange((prev) => ({ ...prev, [field]: value }));

  return (
    <div style={S.accountCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 800, fontSize: 20, color: '#1c1917', marginBottom: 14 }}>
        <UserPlus size={20} />
        Criar conta
      </div>
      <form onSubmit={onRegister} autoComplete="off" style={{ display: 'grid', gap: 10 }}>
        <input name="ecommerce_register_nome" autoComplete="off" value={registerForm.nome} onChange={(event) => updateRegister('nome', event.target.value)} placeholder="Nome completo" style={S.formInput} />
        <input name="ecommerce_register_cpf" autoComplete="off" value={registerForm.cpf} onChange={(event) => updateRegister('cpf', event.target.value)} placeholder="CPF *  (000.000.000-00)" inputMode="numeric" style={S.formInput} required />
        <input name="ecommerce_register_telefone" autoComplete="off" value={registerForm.telefone} onChange={(event) => updateRegister('telefone', event.target.value)} placeholder="Telefone/WhatsApp *" inputMode="tel" style={S.formInput} required />
        <input name="ecommerce_register_email" autoComplete="off" value={registerForm.email} onChange={(event) => updateRegister('email', event.target.value)} placeholder="Email" type="email" style={S.formInput} />
        <PasswordInput
          name="ecommerce_register_password"
          value={registerForm.password}
          show={showRegisterPassword}
          placeholder="Senha (minimo 8 caracteres)"
          style={S.formInput}
          onChange={(event) => updateRegister('password', event.target.value)}
          onToggle={onToggleRegisterPassword}
        />
        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: '#57534e', lineHeight: 1.45 }}>
          <input type="checkbox" checked={registerForm.accepted_terms} onChange={(event) => updateRegister('accepted_terms', event.target.checked)} style={{ marginTop: 2 }} />
          <span>Li e aceito os <a href="/termos" target="_blank" rel="noreferrer" style={{ color: '#7c3aed', fontWeight: 700 }}>Termos de Uso</a>.</span>
        </label>
        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: '#57534e', lineHeight: 1.45 }}>
          <input type="checkbox" checked={registerForm.accepted_privacy} onChange={(event) => updateRegister('accepted_privacy', event.target.checked)} style={{ marginTop: 2 }} />
          <span>Li e aceito a <a href="/privacidade" target="_blank" rel="noreferrer" style={{ color: '#7c3aed', fontWeight: 700 }}>Politica de Privacidade</a>.</span>
        </label>
        <button type="submit" disabled={authLoading} style={{ ...S.saveBtn, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
          <ShieldCheck size={15} />
          {authLoading ? 'Criando...' : 'Criar minha conta'}
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
  showRecoveryConfirmPassword,
  showRecoveryPassword,
  styles: S,
  onClosePasswordRecovery,
  onPasswordRecoveryRequest,
  onPasswordRecoveryReset,
  onRecoveryFormChange,
  onRequestNewRecoveryLink,
  onToggleRecoveryConfirmPassword,
  onToggleRecoveryPassword,
  onUseRecoveryCode,
}) {
  const updateRecovery = (field, value) => onRecoveryFormChange((prev) => ({ ...prev, [field]: value }));

  return (
    <form
      onSubmit={recoveryStep === 'request' ? onPasswordRecoveryRequest : onPasswordRecoveryReset}
      autoComplete="off"
      style={{ display: 'grid', gap: 10 }}
    >
      <input
        name="ecommerce_recovery_email"
        autoComplete="off"
        value={recoveryForm.email}
        onChange={(event) => updateRecovery('email', event.target.value)}
        placeholder="Email"
        type="email"
        style={S.formInput}
      />

      {recoveryStep === 'reset' && (
        <>
          {recoveryTokenFromLink ? (
            <div style={{ border: '1px solid #ddd6fe', background: '#f5f3ff', color: '#5b21b6', borderRadius: 10, padding: '10px 12px', fontSize: 13, fontWeight: 600 }}>
              Link de recuperacao carregado. Basta cadastrar a nova senha.
            </div>
          ) : (
            <input
              name="ecommerce_recovery_token"
              autoComplete="off"
              inputMode="numeric"
              value={recoveryForm.token}
              onChange={(event) => updateRecovery('token', event.target.value)}
              placeholder="Codigo de recuperacao"
              type="text"
              style={S.formInput}
            />
          )}
          <PasswordInput
            name="ecommerce_recovery_password"
            value={recoveryForm.novaSenha}
            show={showRecoveryPassword}
            placeholder="Nova senha"
            style={S.formInput}
            onChange={(event) => updateRecovery('novaSenha', event.target.value)}
            onToggle={onToggleRecoveryPassword}
          />
          <PasswordInput
            name="ecommerce_recovery_password_confirm"
            value={recoveryForm.confirmarSenha}
            show={showRecoveryConfirmPassword}
            placeholder="Confirmar nova senha"
            style={S.formInput}
            onChange={(event) => updateRecovery('confirmarSenha', event.target.value)}
            onToggle={onToggleRecoveryConfirmPassword}
          />
        </>
      )}

      <button type="submit" disabled={recoveryLoading} style={{ ...S.saveBtn, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
        <RotateCcw size={15} />
        {recoveryLoading ? 'Processando...' : recoveryStep === 'request' ? 'Enviar instrucoes' : 'Salvar nova senha'}
      </button>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {recoveryStep === 'request' ? (
          <button type="button" onClick={onUseRecoveryCode} style={{ background: '#fff', border: '1.5px solid #d1d5db', color: '#374151', borderRadius: 10, padding: '10px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <KeyRound size={14} />
            Ja tenho o codigo
          </button>
        ) : (
          <button type="button" onClick={onRequestNewRecoveryLink} style={{ background: '#fff', border: '1.5px solid #d1d5db', color: '#374151', borderRadius: 10, padding: '10px 16px', fontWeight: 600, fontSize: 13, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Mail size={14} />
            Solicitar novo link
          </button>
        )}

        <button type="button" onClick={onClosePasswordRecovery} style={{ background: 'transparent', border: 'none', color: '#2563eb', fontWeight: 700, fontSize: 13, cursor: 'pointer', padding: '10px 0' }}>
          Voltar para login
        </button>
      </div>
    </form>
  );
}

function LoginPanel({
  authLoading,
  loginForm,
  passwordRecoveryMode,
  recoveryForm,
  recoveryLoading,
  recoveryStep,
  recoveryTokenFromLink,
  showLoginPassword,
  showRecoveryConfirmPassword,
  showRecoveryPassword,
  styles: S,
  onClosePasswordRecovery,
  onLogin,
  onLoginFormChange,
  onOpenPasswordRecovery,
  onPasswordRecoveryRequest,
  onPasswordRecoveryReset,
  onRecoveryFormChange,
  onRequestNewRecoveryLink,
  onToggleLoginPassword,
  onToggleRecoveryConfirmPassword,
  onToggleRecoveryPassword,
  onUseRecoveryCode,
}) {
  const updateLogin = (field, value) => onLoginFormChange((prev) => ({ ...prev, [field]: value }));

  return (
    <div style={S.accountCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 800, fontSize: 20, color: '#1c1917', marginBottom: 10 }}>
        {passwordRecoveryMode ? <KeyRound size={20} /> : <LockKeyhole size={20} />}
        {passwordRecoveryMode ? 'Recuperar senha' : 'Entrar'}
      </div>
      <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 14 }}>
        {passwordRecoveryMode
          ? (recoveryStep === 'request'
              ? 'Informe o e-mail da conta e enviaremos as instrucoes.'
              : recoveryTokenFromLink
                ? 'Link seguro carregado. Escolha uma nova senha.'
                : 'Digite o codigo recebido e escolha uma nova senha.')
          : 'Acesse sua conta para acompanhar pedidos e finalizar a compra mais rapido.'}
      </div>

      {passwordRecoveryMode ? (
        <PasswordRecoveryForm
          recoveryForm={recoveryForm}
          recoveryLoading={recoveryLoading}
          recoveryStep={recoveryStep}
          recoveryTokenFromLink={recoveryTokenFromLink}
          showRecoveryConfirmPassword={showRecoveryConfirmPassword}
          showRecoveryPassword={showRecoveryPassword}
          styles={S}
          onClosePasswordRecovery={onClosePasswordRecovery}
          onPasswordRecoveryRequest={onPasswordRecoveryRequest}
          onPasswordRecoveryReset={onPasswordRecoveryReset}
          onRecoveryFormChange={onRecoveryFormChange}
          onRequestNewRecoveryLink={onRequestNewRecoveryLink}
          onToggleRecoveryConfirmPassword={onToggleRecoveryConfirmPassword}
          onToggleRecoveryPassword={onToggleRecoveryPassword}
          onUseRecoveryCode={onUseRecoveryCode}
        />
      ) : (
        <form onSubmit={onLogin} autoComplete="off" style={{ display: 'grid', gap: 10 }}>
          <input name="ecommerce_login_email" autoComplete="off" value={loginForm.email} onChange={(event) => updateLogin('email', event.target.value)} placeholder="Email" type="email" style={S.formInput} />
          <PasswordInput
            name="ecommerce_login_password"
            value={loginForm.password}
            show={showLoginPassword}
            placeholder="Senha"
            style={S.formInput}
            onChange={(event) => updateLogin('password', event.target.value)}
            onToggle={onToggleLoginPassword}
          />
          <button type="submit" disabled={authLoading} style={{ ...S.saveBtn, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
            <LockKeyhole size={15} />
            {authLoading ? 'Entrando...' : 'Entrar'}
          </button>
          <button
            type="button"
            onClick={() => onOpenPasswordRecovery('request')}
            style={{ background: 'transparent', border: 'none', color: '#2563eb', fontWeight: 700, fontSize: 13, cursor: 'pointer', justifySelf: 'start', padding: 0 }}
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
  showLoginPassword,
  showRecoveryConfirmPassword,
  showRecoveryPassword,
  showRegisterPassword,
  styles: S,
  wishlistCount,
  onClosePasswordRecovery,
  onDeliveryCepBlur,
  onLogin,
  onLoginFormChange,
  onLogout,
  onOpenPasswordRecovery,
  onPasswordRecoveryRequest,
  onPasswordRecoveryReset,
  onProfileCepBlur,
  onProfileFormChange,
  onRegister,
  onRegisterFormChange,
  onRecoveryFormChange,
  onRequestNewRecoveryLink,
  onSaveProfile,
  onToggleLoginPassword,
  onToggleRecoveryConfirmPassword,
  onToggleRecoveryPassword,
  onToggleRegisterPassword,
  onUseRecoveryCode,
}) {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 16px' }}>
      <h2 style={{ margin: '0 0 20px', fontSize: 26, fontWeight: 800, color: '#1c1917' }}>Minha Conta</h2>

      {customerToken ? (
        <AccountProfileForm
          customer={customer}
          isMobile={isMobile}
          notifyRequestsCount={notifyRequestsCount}
          profileForm={profileForm}
          profileSaving={profileSaving}
          styles={S}
          wishlistCount={wishlistCount}
          onDeliveryCepBlur={onDeliveryCepBlur}
          onLogout={onLogout}
          onProfileCepBlur={onProfileCepBlur}
          onProfileFormChange={onProfileFormChange}
          onSaveProfile={onSaveProfile}
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 20 }}>
          <RegisterPanel
            authLoading={authLoading}
            registerForm={registerForm}
            showRegisterPassword={showRegisterPassword}
            styles={S}
            onRegister={onRegister}
            onRegisterFormChange={onRegisterFormChange}
            onToggleRegisterPassword={onToggleRegisterPassword}
          />

          <LoginPanel
            authLoading={authLoading}
            loginForm={loginForm}
            passwordRecoveryMode={passwordRecoveryMode}
            recoveryForm={recoveryForm}
            recoveryLoading={recoveryLoading}
            recoveryStep={recoveryStep}
            recoveryTokenFromLink={recoveryTokenFromLink}
            showLoginPassword={showLoginPassword}
            showRecoveryConfirmPassword={showRecoveryConfirmPassword}
            showRecoveryPassword={showRecoveryPassword}
            styles={S}
            onClosePasswordRecovery={onClosePasswordRecovery}
            onLogin={onLogin}
            onLoginFormChange={onLoginFormChange}
            onOpenPasswordRecovery={onOpenPasswordRecovery}
            onPasswordRecoveryRequest={onPasswordRecoveryRequest}
            onPasswordRecoveryReset={onPasswordRecoveryReset}
            onRecoveryFormChange={onRecoveryFormChange}
            onRequestNewRecoveryLink={onRequestNewRecoveryLink}
            onToggleLoginPassword={onToggleLoginPassword}
            onToggleRecoveryConfirmPassword={onToggleRecoveryConfirmPassword}
            onToggleRecoveryPassword={onToggleRecoveryPassword}
            onUseRecoveryCode={onUseRecoveryCode}
          />
        </div>
      )}
    </div>
  );
}
