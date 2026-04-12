import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { PawPrint } from 'lucide-react';
import { FiAlertCircle, FiEye, FiEyeOff, FiLock, FiMail } from 'react-icons/fi';
import api from '../api';

const INITIAL_FORM = {
  email: '',
  token: '',
  novaSenha: '',
  confirmarSenha: '',
};

export default function ForgotPassword() {
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState('request');
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  useEffect(() => {
    const email = (searchParams.get('email') || '').trim();
    const token = (searchParams.get('token') || '').trim();

    if (!email && !token) {
      return;
    }

    setForm((prev) => ({
      ...prev,
      email: email || prev.email,
      token: token || prev.token,
    }));
    setStep('reset');
  }, [searchParams]);

  async function handleRequestSubmit(event) {
    event.preventDefault();
    const normalizedEmail = form.email.trim().toLowerCase();

    if (!normalizedEmail) {
      setError('Informe o e-mail da conta para continuar.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await api.post('/auth/forgot-password', { email: normalizedEmail });
      const minutes = response?.data?.expires_in_minutes;
      setStep('reset');
      setForm((prev) => ({
        ...prev,
        email: normalizedEmail,
        token: '',
        novaSenha: '',
        confirmarSenha: '',
      }));
      setSuccess(
        minutes
          ? `Se o e-mail existir, enviamos as instruções. O token expira em ${minutes} minutos.`
          : 'Se o e-mail existir, enviamos as instruções de recuperação.'
      );
    } catch (err) {
      setError(err?.response?.data?.detail || 'Não foi possível iniciar a recuperação agora.');
    } finally {
      setLoading(false);
    }
  }

  async function handleResetSubmit(event) {
    event.preventDefault();
    const normalizedEmail = form.email.trim().toLowerCase();
    const token = form.token.trim();

    if (!normalizedEmail || !token) {
      setError('Preencha o e-mail e o token recebido.');
      return;
    }

    if (form.novaSenha.length < 6) {
      setError('A nova senha deve ter pelo menos 6 caracteres.');
      return;
    }

    if (form.novaSenha !== form.confirmarSenha) {
      setError('A confirmação da senha não confere.');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await api.post('/auth/reset-password', {
        email: normalizedEmail,
        token,
        nova_senha: form.novaSenha,
      });

      setSuccess('Senha atualizada com sucesso. Você já pode entrar com a nova senha.');
      setStep('request');
      setForm({
        email: normalizedEmail,
        token: '',
        novaSenha: '',
        confirmarSenha: '',
      });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Não foi possível redefinir a senha.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-purple-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8 animate-fade-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-100 rounded-full mb-4">
            <PawPrint className="w-8 h-8 text-purple-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Recuperar Senha</h1>
          <p className="text-gray-600 mt-2">
            {step === 'request'
              ? 'Vamos enviar as instruções para o e-mail da conta.'
              : 'Cole o token recebido e defina sua nova senha.'}
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
            <FiAlertCircle className="flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
            {success}
          </div>
        )}

        <form
          onSubmit={step === 'request' ? handleRequestSubmit : handleResetSubmit}
          className="space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <div className="relative">
              <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
                placeholder="seu@email.com"
                required
              />
            </div>
          </div>

          {step === 'reset' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Token</label>
                <input
                  type="text"
                  value={form.token}
                  onChange={(e) => setForm((prev) => ({ ...prev, token: e.target.value }))}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
                  placeholder="Cole o token recebido por e-mail"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nova senha</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={form.novaSenha}
                    onChange={(e) => setForm((prev) => ({ ...prev, novaSenha: e.target.value }))}
                    className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
                    placeholder="Mínimo de 6 caracteres"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition"
                  >
                    {showPassword ? <FiEyeOff /> : <FiEye />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Confirmar nova senha</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={form.confirmarSenha}
                    onChange={(e) => setForm((prev) => ({ ...prev, confirmarSenha: e.target.value }))}
                    className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
                    placeholder="Repita a nova senha"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition"
                  >
                    {showConfirmPassword ? <FiEyeOff /> : <FiEye />}
                  </button>
                </div>
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading
              ? 'Processando...'
              : step === 'request'
                ? 'Enviar instruções'
                : 'Salvar nova senha'}
          </button>
        </form>

        <div className="mt-6 flex flex-col gap-3 text-center">
          {step === 'request' ? (
            <button
              type="button"
              onClick={() => {
                setStep('reset');
                setError('');
                setSuccess('');
              }}
              className="text-sm text-purple-600 hover:text-purple-700 font-semibold"
            >
              Já tenho um token
            </button>
          ) : (
            <button
              type="button"
              onClick={() => {
                setStep('request');
                setError('');
                setSuccess('');
              }}
              className="text-sm text-purple-600 hover:text-purple-700 font-semibold"
            >
              Solicitar um novo token
            </button>
          )}

          <Link to="/login" className="text-sm text-gray-600 hover:text-gray-800">
            Voltar para o login
          </Link>
        </div>
      </div>
    </div>
  );
}
