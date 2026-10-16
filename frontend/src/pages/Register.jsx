import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PawPrint, UserPlus } from "lucide-react";
import { FiAlertCircle } from "react-icons/fi";
import { useAuth } from "../contexts/AuthContext";
import { findPublicPlan, planOrganizationTypes } from "../data/publicPlans";
import InputTexto from "../components/v2/InputTexto/InputTexto";
import InputSenha from "../components/v2/InputSenha/InputSenha";
import InputCombobox from "../components/v2/InputCombobox/InputCombobox";
import InputCheckTexto from "../components/v2/InputCheckTexto/InputCheckTexto";
import BotaoInteracao from "../components/v2/BotaoInteracao/BotaoInteracao";
import LinkPadrao from "../components/v2/LinkPadrao/LinkPadrao";

const FORM_ID = "register-form";
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Ordem visual dos campos (topo do formulário até o rodapé fixo) — usada só se o envio for
// bloqueado por algum caminho que não passe pelo botão (ele já vem desabilitado até tudo válido).
const CAMPOS_EM_ORDEM = [
  "nome",
  "nomeLoja",
  "nomeAcesso",
  "email",
  "password",
  "confirmPassword",
  "acceptedTerms",
  "acceptedPrivacy",
];

const ID_DO_CAMPO = {
  nome: "register-nome",
  nomeLoja: "register-nome-loja",
  nomeAcesso: "register-nome-acesso",
  email: "register-email",
  password: "register-password",
  confirmPassword: "register-confirm-password",
  acceptedTerms: "register-accepted-terms",
  acceptedPrivacy: "register-accepted-privacy",
};

const Register = () => {
  const [nome, setNome] = useState("");
  const [nomeLoja, setNomeLoja] = useState("");
  const [nomeAcesso, setNomeAcesso] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  // Um campo só mostra erro depois que o usuário passou por ele (blur/alteração) — evita a tela
  // inteira nascer vermelha antes de qualquer interação.
  const [tocados, setTocados] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedPlan = (searchParams.get("plan") || "pet-start").trim().toLowerCase();
  const selectedPlanData = findPublicPlan(requestedPlan) || findPublicPlan("pet-start");
  const selectedPlan = selectedPlanData.id;
  const requestedOrganization = (searchParams.get("organization_type") || "").trim().toLowerCase();
  const defaultOrganization =
    requestedOrganization || planOrganizationTypes[selectedPlanData.segment] || "petshop";
  const [organizationType, setOrganizationType] = useState(defaultOrganization);
  const organizationOptions =
    selectedPlanData.segment === "vet"
      ? [
          { value: "veterinary_clinic", label: "Clinica Veterinaria" },
          { value: "hospital", label: "Hospital Veterinario" },
        ]
      : selectedPlanData.segment === "grooming"
        ? [{ value: "grooming", label: "Banho e Tosa" }]
        : [{ value: "petshop", label: "Pet Shop" }];
  // Só existe escolha de verdade quando o segmento tem mais de um tipo (hoje, só o veterinario).
  // Com uma opcao so, ela e a resposta certa por definicao — nao faz sentido pedir pro usuario
  // confirmar algo que nao e uma decisao, entao o campo nem aparece e o valor vai direto no envio.
  const opcaoOrganizacaoUnica =
    organizationOptions.length === 1 ? organizationOptions[0].value : null;
  const organizationTypeEfetivo = opcaoOrganizacaoUnica || organizationType;

  // Recalculado a cada render a partir dos valores atuais — nunca fica desatualizado, e é o que
  // decide se o botão de enviar pode ficar ativo (não depende de nenhum clique prévio).
  const validar = () => {
    const novosErros = {};

    if (!nome.trim()) novosErros.nome = "Informe seu nome.";
    if (!nomeLoja.trim()) novosErros.nomeLoja = "Informe o nome da empresa.";

    if (!nomeAcesso.trim()) {
      novosErros.nomeAcesso = "Informe o nome de acesso da loja.";
    } else if (nomeAcesso.trim().length < 3) {
      novosErros.nomeAcesso = "O nome de acesso da loja deve ter pelo menos 3 caracteres.";
    }

    if (!email.trim()) {
      novosErros.email = "Informe seu email.";
    } else if (!EMAIL_REGEX.test(email.trim())) {
      novosErros.email = "Informe um email valido.";
    }

    if (!password) {
      novosErros.password = "Informe uma senha.";
    } else if (password.length < 8) {
      novosErros.password = "A senha deve ter no minimo 8 caracteres.";
    }

    if (!confirmPassword) {
      novosErros.confirmPassword = "Repita a senha.";
    } else if (confirmPassword !== password) {
      novosErros.confirmPassword = "As senhas nao coincidem.";
    }

    if (!acceptedTerms) novosErros.acceptedTerms = "E preciso aceitar os Termos de Uso.";
    if (!acceptedPrivacy) {
      novosErros.acceptedPrivacy = "E preciso confirmar a leitura da Politica de Privacidade.";
    }

    return novosErros;
  };

  const erros = validar();
  const formValido = Object.keys(erros).length === 0;
  const erroVisivel = (campo) => (tocados[campo] ? erros[campo] : undefined);
  const marcarTocado = (campo) => setTocados((atual) => ({ ...atual, [campo]: true }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    // O botão já vem desabilitado enquanto `formValido` for falso — este bloqueio é só uma rede
    // de segurança (ex.: envio disparado por Enter num navegador que ignore o atributo disabled).
    if (!formValido) {
      setTocados(Object.fromEntries(CAMPOS_EM_ORDEM.map((campo) => [campo, true])));
      const primeiroCampoComErro = CAMPOS_EM_ORDEM.find((campo) => erros[campo]);
      document
        .getElementById(ID_DO_CAMPO[primeiroCampoComErro])
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    setLoading(true);
    const result = await register({
      email,
      password,
      nome,
      nome_loja: nomeLoja,
      nome_acesso: nomeAcesso.trim(),
      plan: selectedPlan,
      organization_type: organizationTypeEfetivo,
      accepted_terms: acceptedTerms,
      accepted_privacy: acceptedPrivacy,
    });

    if (result.success && result.requiresEmailVerification) {
      navigate(`/verificar-email?email=${encodeURIComponent(email)}`);
    } else if (result.success) {
      navigate("/dashboard");
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-purple-900 flex items-center justify-center p-4 py-10">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl p-6 sm:p-8 animate-fade-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-100 rounded-full mb-4">
            <PawPrint className="w-8 h-8 text-purple-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Criar empresa</h1>
          <p className="text-gray-600 mt-2">Comece com 30 dias de acesso completo ao CorePet</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
            <FiAlertCircle className="flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <aside className="lg:sticky lg:top-6 lg:self-start">
            <div className="space-y-4">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                <p className="mb-2 font-black">
                  Plano escolhido: {selectedPlanData.name} — R$ {selectedPlanData.price}/mes
                </p>
                <p className="font-semibold">Experiência CorePet Completa por 30 dias</p>
                <p className="mt-1">
                  Durante o período gratuito, sua empresa poderá conhecer todos os módulos do
                  CorePet. Depois, nossa equipe ajuda você a escolher e configurar o plano que faz
                  sentido para a sua operação.
                </p>
                <p className="mt-2 text-xs font-semibold">
                  Condição de lançamento com acompanhamento humano para as 20 primeiras empresas.
                </p>
              </div>

              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-3">
                <InputCheckTexto
                  id="register-accepted-terms"
                  checked={acceptedTerms}
                  error={erroVisivel("acceptedTerms")}
                  onChange={(value) => {
                    setAcceptedTerms(value);
                    marcarTocado("acceptedTerms");
                  }}
                >
                  Li e aceito os{" "}
                  <LinkPadrao to="/termos" novaJanela tamanho="text-sm">
                    Termos de Uso
                  </LinkPadrao>
                  .
                </InputCheckTexto>
                <InputCheckTexto
                  id="register-accepted-privacy"
                  checked={acceptedPrivacy}
                  error={erroVisivel("acceptedPrivacy")}
                  onChange={(value) => {
                    setAcceptedPrivacy(value);
                    marcarTocado("acceptedPrivacy");
                  }}
                >
                  Li e confirmo que estou ciente da{" "}
                  <LinkPadrao to="/privacidade" novaJanela tamanho="text-sm">
                    Politica de Privacidade
                  </LinkPadrao>
                  .
                </InputCheckTexto>
              </div>

              <div>
                <BotaoInteracao
                  type="submit"
                  form={FORM_ID}
                  icon={UserPlus}
                  disabled={loading || !formValido}
                  loading={loading}
                  tamanho="grande"
                  larguraTotal
                >
                  {loading ? "Criando conta..." : "Criar conta"}
                </BotaoInteracao>
                {!formValido && !loading ? (
                  <p className="mt-2 text-center text-xs font-medium text-amber-700">
                    Preencha os campos obrigatórios e aceite os termos para continuar.
                  </p>
                ) : null}
              </div>

              <p className="text-center text-sm text-gray-600">
                Ja tem uma conta?{" "}
                <LinkPadrao to="/login" tamanho="text-sm">
                  Fazer login
                </LinkPadrao>
              </p>
            </div>
          </aside>

          <form id={FORM_ID} onSubmit={handleSubmit} noValidate className="space-y-3">
            <InputTexto
              id="register-nome"
              label="Seu nome"
              value={nome}
              error={erroVisivel("nome")}
              onChange={setNome}
              onBlur={() => marcarTocado("nome")}
              placeholder="Nome do responsavel"
              required
            />

            <InputTexto
              id="register-nome-loja"
              label="Nome da empresa"
              value={nomeLoja}
              error={erroVisivel("nomeLoja")}
              onChange={setNomeLoja}
              onBlur={() => marcarTocado("nomeLoja")}
              placeholder="Ex: CorePet"
              required
            />

            <InputTexto
              id="register-nome-acesso"
              label="Nome de acesso da loja"
              value={nomeAcesso}
              error={erroVisivel("nomeAcesso")}
              help={
                erroVisivel("nomeAcesso")
                  ? undefined
                  : "Deve ser unico no CorePet. Seus colaboradores usarao este nome para entrar."
              }
              onChange={setNomeAcesso}
              onBlur={() => marcarTocado("nomeAcesso")}
              maxLength={120}
              placeholder="Ex: Vira Latas"
              required
            />

            {opcaoOrganizacaoUnica ? null : (
              <InputCombobox
                id="register-organization-type"
                label="Tipo de empresa"
                opcoes={organizationOptions}
                value={organizationType}
                onChange={(value) => setOrganizationType(value)}
                permitirLimpar={false}
              />
            )}

            <InputTexto
              id="register-email"
              label="Email"
              type="email"
              value={email}
              error={erroVisivel("email")}
              autoComplete="email"
              onChange={setEmail}
              onBlur={() => marcarTocado("email")}
              placeholder="seu@email.com"
              required
            />

            <InputSenha
              id="register-password"
              label="Senha"
              value={password}
              error={erroVisivel("password")}
              autoComplete="new-password"
              onChange={setPassword}
              onBlur={() => marcarTocado("password")}
              placeholder="Minimo 8 caracteres"
              required
            />

            <InputSenha
              id="register-confirm-password"
              label="Confirmar senha"
              value={confirmPassword}
              error={erroVisivel("confirmPassword")}
              autoComplete="new-password"
              onChange={setConfirmPassword}
              onBlur={() => marcarTocado("confirmPassword")}
              placeholder="Repita a senha"
              required
            />
          </form>
        </div>
      </div>
    </div>
  );
};

export default Register;
