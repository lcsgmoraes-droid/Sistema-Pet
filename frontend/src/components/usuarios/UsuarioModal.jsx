import { UserCheck, UserPlus } from "lucide-react";
import { useState } from "react";
import api from "../../api";
import { PERFIS_APP } from "../../utils/appAccessProfiles";
import { isBrazilianMobileLogin } from "../../utils/loginPhone";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCheckGroup from "../v2/InputCheckGroup/InputCheckGroup";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputRadio from "../v2/InputRadio/InputRadio";
import InputSenha from "../v2/InputSenha/InputSenha";
import InputTelefone from "../v2/InputTelefone/InputTelefone";
import InputTexto from "../v2/InputTexto/InputTexto";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

const OPCOES_TIPO_PESSOA = [
  { value: "PF", label: "Pessoa Física" },
  { value: "PJ", label: "Pessoa Jurídica" },
];

const CAMPOS_EM_ORDEM = ["nome", "login_phone", "email", "password", "role_id", "app_access_profiles"];

const ID_DO_CAMPO = {
  nome: "novo-usuario-nome",
  login_phone: "novo-usuario-login-phone",
  email: "novo-usuario-email",
  password: "novo-usuario-password",
  role_id: "novo-usuario-role",
  app_access_profiles: "novo-usuario-perfis",
};

function emailPareceValido(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validar(novoUsuario) {
  const erros = {};
  if (!novoUsuario.nome || !novoUsuario.nome.trim()) {
    erros.nome = "Informe o nome da pessoa.";
  }
  if (!isBrazilianMobileLogin(novoUsuario.login_phone)) {
    erros.login_phone = "Informe um celular válido com DDD.";
  }
  const email = (novoUsuario.email || "").trim();
  if (email && !emailPareceValido(email)) {
    erros.email = "Use o formato nome@dominio.com.";
  }
  if ((novoUsuario.password || "").length < 8) {
    erros.password = "Use no mínimo 8 caracteres.";
  }
  if (!novoUsuario.role_id) {
    erros.role_id = "Selecione um perfil de acesso.";
  }
  if (!novoUsuario.app_access_profiles || novoUsuario.app_access_profiles.length === 0) {
    erros.app_access_profiles = "Selecione ao menos um perfil de acesso ao app.";
  }
  return erros;
}

export default function UsuarioModal({
  limparErroServidor,
  novoUsuario,
  onClose,
  onSubmit,
  roles,
  setNovoUsuario,
  showModal,
  usuarioServerErrors = {},
}) {
  const [duplicata, setDuplicata] = useState(null);
  const [pessoaVinculada, setPessoaVinculada] = useState(null);
  const [tocados, setTocados] = useState({});
  const [tentouEnviar, setTentouEnviar] = useState(false);

  if (!showModal) return null;

  const erros = validar(novoUsuario);
  const erroVisivel = (campo) =>
    usuarioServerErrors[campo] || ((tocados[campo] || tentouEnviar) ? erros[campo] : undefined);
  const marcarTocado = (campo) => setTocados((atual) => ({ ...atual, [campo]: true }));

  const verificarDuplicata = async (campo, valor) => {
    if (!valor) return;
    try {
      const { data } = await api.get("/clientes/verificar-duplicata/campo", {
        params: { [campo]: valor },
      });
      if (data.duplicado && data.cliente?.id !== pessoaVinculada?.id) {
        setDuplicata({ campo, cliente: data.cliente });
      }
    } catch (err) {
      console.error("Erro ao verificar pessoa existente:", err);
    }
  };

  const vincularPessoaEncontrada = () => {
    setNovoUsuario({
      ...novoUsuario,
      nome: duplicata.cliente.nome,
      pessoa_id: duplicata.cliente.id,
    });
    setPessoaVinculada({ id: duplicata.cliente.id, nome: duplicata.cliente.nome });
    setDuplicata(null);
  };

  const desvincularPessoa = () => {
    setNovoUsuario({ ...novoUsuario, pessoa_id: null });
    setPessoaVinculada(null);
  };

  const atualizarCampo = (campo, valor) => {
    setNovoUsuario({ ...novoUsuario, [campo]: valor });
    limparErroServidor?.(campo);
  };

  // Nome/celular/e-mail também identificam a pessoa buscada — mudar qualquer um deles depois de
  // um vínculo encontrado invalida o vínculo (os dados não são mais os da pessoa vinculada).
  const alterarIdentificador = (campo, valor) => {
    atualizarCampo(campo, valor);
    if (pessoaVinculada) desvincularPessoa();
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setTentouEnviar(true);
    const errosAtuais = validar(novoUsuario);
    if (Object.keys(errosAtuais).length > 0) {
      const primeiroCampoComErro = CAMPOS_EM_ORDEM.find((campo) => errosAtuais[campo]);
      document
        .getElementById(ID_DO_CAMPO[primeiroCampoComErro])
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    onSubmit();
  };

  return (
    <ModalPadrao
      titulo="Novo usuário"
      tamanho="grande"
      onFechar={onClose}
      rodape={
        <>
          <BotaoCancelar onClick={onClose}>Cancelar</BotaoCancelar>
          <BotaoSalva form="novo-usuario-form" disabled={roles.length === 0} icon={UserPlus}>
            Criar usuário
          </BotaoSalva>
        </>
      }
    >
      <form id="novo-usuario-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Crie o acesso vinculado ao tenant atual.
        </p>

        {!pessoaVinculada ? (
          <InputRadio
            name="novo-usuario-tipo-pessoa"
            label="Tipo de pessoa"
            required
            opcoes={OPCOES_TIPO_PESSOA}
            value={novoUsuario.tipo_pessoa}
            onChange={(tipo_pessoa) => setNovoUsuario({ ...novoUsuario, tipo_pessoa })}
            help="Usado só para criar o cadastro da pessoa vinculada a este login."
          />
        ) : null}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <InputTexto
            id="novo-usuario-nome"
            label="Nome da pessoa"
            required
            autoFocus
            value={novoUsuario.nome}
            error={erroVisivel("nome")}
            onChange={(nome) => alterarIdentificador("nome", nome)}
            onBlur={() => marcarTocado("nome")}
            placeholder="Maria da Silva"
          />

          <InputTexto
            id="novo-usuario-email"
            label="E-mail (opcional)"
            type="email"
            value={novoUsuario.email}
            error={erroVisivel("email")}
            onChange={(email) => alterarIdentificador("email", email)}
            onBlur={(evento) => {
              marcarTocado("email");
              verificarDuplicata("email", evento.target.value);
            }}
            placeholder="Para recuperação por e-mail"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-[200px_minmax(0,1fr)_200px]">
          <InputTelefone
            id="novo-usuario-login-phone"
            label="Celular de acesso"
            required
            tipo="celular"
            value={novoUsuario.login_phone}
            error={erroVisivel("login_phone")}
            onChange={(login_phone) => alterarIdentificador("login_phone", login_phone)}
            onBlur={(evento) => {
              marcarTocado("login_phone");
              verificarDuplicata("celular", evento.target.value);
            }}
            whatsapp={novoUsuario.celular_whatsapp}
            onChangeWhatsapp={(celular_whatsapp) => atualizarCampo("celular_whatsapp", celular_whatsapp)}
            help="Sera o login do usuário"
          />

          <InputCombobox
            id="novo-usuario-role"
            label="Perfil de acesso"
            required
            permitirLimpar={false}
            disabled={roles.length === 0}
            error={erroVisivel("role_id")}
            opcoes={roles.map((role) => ({ value: String(role.role_id), label: role.nome }))}
            value={novoUsuario.role_id ? String(novoUsuario.role_id) : ""}
            onChange={(value) => {
              marcarTocado("role_id");
              atualizarCampo("role_id", value ? Number(value) : null);
            }}
          />

          <InputSenha
            id="novo-usuario-password"
            label="Senha"
            required
            value={novoUsuario.password}
            error={erroVisivel("password")}
            onChange={(password) => atualizarCampo("password", password)}
            onBlur={() => marcarTocado("password")}
            placeholder="Mínimo 8 caracteres"
            autoComplete="new-password"
          />
        </div>

        {duplicata ? (
          <div className="flex flex-col gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-500/30 dark:bg-amber-500/10">
            <p className="font-semibold text-amber-900 dark:text-amber-200">
              Já existe uma pessoa cadastrada com esse {duplicata.campo === "email" ? "e-mail" : "celular"}.
            </p>
            <p className="text-amber-800 dark:text-amber-200">{duplicata.cliente.nome}</p>
            <div className="mt-1 flex flex-wrap gap-2">
              <BotaoCancelar tamanho="pequeno" onClick={() => setDuplicata(null)}>
                Criar pessoa separada
              </BotaoCancelar>
              <BotaoInteracao
                tamanho="pequeno"
                icon={UserCheck}
                onClick={vincularPessoaEncontrada}
              >
                Vincular a esta pessoa
              </BotaoInteracao>
            </div>
          </div>
        ) : null}

        {pessoaVinculada ? (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
            <span className="flex items-center gap-1.5">
              <UserCheck className="h-4 w-4 flex-none" aria-hidden="true" />
              Vinculado a: {pessoaVinculada.nome}
            </span>
            <BotaoCancelar tamanho="pequeno" onClick={desvincularPessoa}>
              Desfazer
            </BotaoCancelar>
          </div>
        ) : null}

        <div id="novo-usuario-perfis">
          <InputCheckGroup
            name="novo-usuario-perfis"
            label="Perfis de acesso ao app (Clique para alternar permissão)"
            required
            error={erroVisivel("app_access_profiles")}
            opcoes={PERFIS_APP}
            value={novoUsuario.app_access_profiles || []}
            onChange={(app_access_profiles) => {
              marcarTocado("app_access_profiles");
              setNovoUsuario({ ...novoUsuario, app_access_profiles });
            }}
          />
        </div>
      </form>
    </ModalPadrao>
  );
}
