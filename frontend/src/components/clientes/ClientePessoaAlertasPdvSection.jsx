import { useState } from "react";
import { AlertTriangle, Edit2, Plus } from "lucide-react";
import toast from "react-hot-toast";
import { buildEmptyClienteAlertaPdv } from "../../utils/clienteAlertasPdv";
import BotaoExcluir from "../v2/BotaoExcluir/BotaoExcluir";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import ClientePessoaAlertaPdvModal from "./ClientePessoaAlertaPdvModal";

const ROTULO_PRIORIDADE = {
  aviso: "Aviso",
  importante: "Importante",
  info: "Info",
};

// Uma cor por prioridade, mesma lógica das badges de tipo de endereço — evidencia a severidade
// do alerta sem depender só do texto.
const COR_PRIORIDADE = {
  aviso: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200",
  importante: "bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200",
  info: "bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-200",
};

function CardAlerta({ alerta, onEditar, onExcluir }) {
  const inativo = alerta.ativo === false;

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={[
                "rounded px-2 py-0.5 text-xs font-medium",
                COR_PRIORIDADE[alerta.prioridade] || COR_PRIORIDADE.aviso,
              ].join(" ")}
            >
              {ROTULO_PRIORIDADE[alerta.prioridade] || "Aviso"}
            </span>
            {inativo ? (
              <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                Inativo
              </span>
            ) : null}
          </div>

          <p className="mb-1 text-sm font-semibold text-slate-900 dark:text-slate-100">
            {alerta.titulo || "Sem título"}
          </p>
          <p className="line-clamp-2 text-sm text-slate-700 dark:text-slate-300">
            {alerta.mensagem || "Sem mensagem"}
          </p>
        </div>
        <div className="flex flex-none gap-1">
          <BotaoInteracao icon={Edit2} tamanho="pequeno" onClick={onEditar}>
            Editar
          </BotaoInteracao>
          <BotaoExcluir
            tamanho="pequeno"
            mensagemConfirmacao="Deseja realmente remover este alerta?"
            onClick={onExcluir}
          >
            Excluir
          </BotaoExcluir>
        </div>
      </div>
    </div>
  );
}

export default function ClientePessoaAlertasPdvSection({ formData, setFormData }) {
  const alertasPdv = Array.isArray(formData.alertas_pdv) ? formData.alertas_pdv : [];
  const [alertaAtual, setAlertaAtual] = useState(null);

  const setAlertasPdv = (alertas) => setFormData((prev) => ({ ...prev, alertas_pdv: alertas }));

  const abrirModalAlerta = (index) => {
    if (index === undefined) {
      setAlertaAtual(buildEmptyClienteAlertaPdv());
    } else {
      setAlertaAtual({ ...alertasPdv[index], index });
    }
  };

  const fecharModalAlerta = () => setAlertaAtual(null);

  const salvarAlerta = () => {
    if (!alertaAtual.titulo || !alertaAtual.titulo.trim()) {
      toast.error("Informe a tag do alerta.");
      return;
    }

    const novosAlertas = [...alertasPdv];
    if (alertaAtual.index !== undefined) {
      const { index, ...alerta } = alertaAtual;
      novosAlertas[index] = alerta;
    } else {
      novosAlertas.push(alertaAtual);
    }
    setAlertasPdv(novosAlertas);
    fecharModalAlerta();
  };

  const excluirAlerta = (index) => {
    setAlertasPdv(alertasPdv.filter((_, alertaIndex) => alertaIndex !== index));
  };

  return (
    <section>
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-2">
          <AlertTriangle
            className="mt-0.5 h-4 w-4 flex-none text-amber-600 dark:text-amber-400"
            aria-hidden="true"
          />
          <div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Alertas do PDV
            </h4>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Mensagens que aparecem automaticamente no PDV ao atender esta pessoa.
            </p>
          </div>
        </div>
        <BotaoInteracao
          icon={Plus}
          className="self-start sm:self-auto"
          onClick={() => abrirModalAlerta()}
        >
          Adicionar alerta
        </BotaoInteracao>
      </div>

      {alertasPdv.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {alertasPdv.map((alerta, index) => (
            <CardAlerta
              key={index}
              alerta={alerta}
              onEditar={() => abrirModalAlerta(index)}
              onExcluir={() => excluirAlerta(index)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-amber-200 bg-amber-50 px-4 py-5 text-center text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
          Nenhum alerta cadastrado
        </div>
      )}

      <ClientePessoaAlertaPdvModal
        alertaAtual={alertaAtual}
        fecharModal={fecharModalAlerta}
        salvarAlerta={salvarAlerta}
        setAlertaAtual={setAlertaAtual}
      />
    </section>
  );
}
