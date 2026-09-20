import { useCallback, useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { FiUserMinus, FiUserPlus } from "react-icons/fi";
import ActionButton from "../../components/ui/ActionButton";
import EmptyState from "../../components/ui/EmptyState";
import { SelectField } from "../../components/ui/FormField";
import LoadingState from "../../components/ui/LoadingState";
import { confirmarCorePet } from "../../services/corepetDialog";
import { useAuth } from "../../contexts/AuthContext";
import api from "../../api";
import {
  concederGestorGrupo,
  listarGestoresGrupo,
  revogarGestorGrupo,
} from "../../services/gruposComerciais";

function mensagemErro(error, padrao) {
  return error?.response?.data?.detail || padrao;
}

function formatarData(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(new Date(value));
}

export default function GrupoComercialAcessos({ grupoId }) {
  const { user } = useAuth();
  const [gestores, setGestores] = useState([]);
  const [usuariosDaLoja, setUsuariosDaLoja] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [novoGestorId, setNovoGestorId] = useState("");
  const [acao, setAcao] = useState("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [listaGestores, respostaUsuarios] = await Promise.all([
        listarGestoresGrupo(grupoId),
        api.get("/usuarios"),
      ]);
      setGestores(listaGestores);
      setUsuariosDaLoja(respostaUsuarios.data);
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível carregar os acessos do grupo."));
    } finally {
      setCarregando(false);
    }
  }, [grupoId]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const candidatos = useMemo(() => {
    const idsComAcesso = new Set(gestores.map((gestor) => gestor.user_id));
    idsComAcesso.add(user?.id);
    return usuariosDaLoja.filter((usuario) => !idsComAcesso.has(usuario.user_id));
  }, [gestores, usuariosDaLoja, user?.id]);

  async function conceder(event) {
    event.preventDefault();
    if (!novoGestorId) {
      toast.error("Escolha um usuário para dar acesso.");
      return;
    }
    setAcao(`conceder-${novoGestorId}`);
    try {
      await concederGestorGrupo(grupoId, Number(novoGestorId));
      toast.success("Acesso concedido.");
      setNovoGestorId("");
      await carregar();
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível conceder este acesso."));
    } finally {
      setAcao("");
    }
  }

  async function revogar(gestor) {
    if (!(await confirmarCorePet(`Revogar o acesso de gestão de ${gestor.nome || gestor.email}?`))) {
      return;
    }
    setAcao(`revogar-${gestor.user_id}`);
    try {
      await revogarGestorGrupo(grupoId, gestor.user_id);
      toast.success("Acesso revogado.");
      await carregar();
    } catch (error) {
      toast.error(mensagemErro(error, "Não foi possível revogar este acesso."));
    } finally {
      setAcao("");
    }
  }

  if (carregando) {
    return <LoadingState label="Carregando acessos do grupo..." />;
  }

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-sm font-semibold text-slate-800">Quem tem acesso à gestão do grupo</h3>
        <p className="mt-1 text-xs text-slate-500">
          Só quem está nesta lista (além de você, como master) consegue ver e gerenciar este
          grupo — adicionar/remover loja, ver a cobrança das lojas.
        </p>
        {gestores.length === 0 ? (
          <EmptyState
            className="mt-3"
            title="Ninguém além de você tem acesso ainda"
            description="Use o formulário abaixo para dar acesso a outro usuário."
          />
        ) : (
          <div className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">
            {gestores.map((gestor) => (
              <div
                key={gestor.user_id}
                className="flex items-center justify-between gap-3 px-3 py-2.5"
              >
                <div>
                  <div className="text-sm font-medium text-slate-900">
                    {gestor.nome || gestor.email}
                  </div>
                  <div className="text-xs text-slate-500">
                    Acesso concedido em {formatarData(gestor.concedido_em)}
                  </div>
                </div>
                <ActionButton
                  icon={FiUserMinus}
                  intent="danger"
                  tone="ghost"
                  size="xs"
                  loading={acao === `revogar-${gestor.user_id}`}
                  onClick={() => revogar(gestor)}
                >
                  Revogar
                </ActionButton>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-800">Dar acesso a outro usuário</h3>
        <p className="mt-1 text-xs text-slate-500">
          Lista os usuários da sua loja. A pessoa não vira master — só ganha acesso a esta tela,
          e você pode revogar quando quiser.
        </p>
        <form className="mt-2 flex flex-col gap-2 sm:flex-row" onSubmit={conceder}>
          <SelectField
            className="min-w-0 flex-1"
            value={novoGestorId}
            onChange={setNovoGestorId}
          >
            <option value="">Selecione um usuário</option>
            {candidatos.map((usuario) => (
              <option key={usuario.user_id} value={usuario.user_id}>
                {usuario.nome || usuario.email || usuario.username}
              </option>
            ))}
          </SelectField>
          <ActionButton
            type="submit"
            icon={FiUserPlus}
            intent="success"
            loading={acao === `conceder-${novoGestorId}`}
          >
            Conceder acesso
          </ActionButton>
        </form>
      </div>
    </div>
  );
}
