import { useEffect, useState } from "react";
import { banhoTosaApi } from "../banhoTosaApi";
import { formatarCreditos, resumirCreditosAgendamento } from "../banhoTosaPacotesUtils";

export default function BanhoTosaAgendaPacoteAviso({ clienteId, petId, servicoId, data }) {
  const chave = [clienteId, petId, servicoId, data].join(":");
  const [consulta, setConsulta] = useState({ chave, loading: true, creditos: [], error: false });
  useEffect(() => {
    if (!clienteId || !petId || !servicoId || !data) return;
    let ativo = true;
    setConsulta({ chave, loading: true, creditos: [], error: false });
    banhoTosaApi
      .listarCreditosPacote({
        cliente_id: clienteId,
        pet_id: petId,
        disponiveis_only: true,
        data_referencia: data,
        limit: 500,
      })
      .then(
        (response) =>
          ativo &&
          setConsulta({
            chave,
            loading: false,
            creditos: Array.isArray(response.data) ? response.data : [],
            error: false,
          }),
      )
      .catch(() => ativo && setConsulta({ chave, loading: false, creditos: [], error: true }));
    return () => {
      ativo = false;
    };
  }, [chave, clienteId, petId, servicoId, data]);
  if (!clienteId || !petId || !servicoId || !data)
    return (
      <p className="text-xs text-slate-500 dark:text-slate-400">
        Selecione pet, serviço e data para consultar o pacote. Havendo saldo válido, o agendamento
        reserva automaticamente.
      </p>
    );
  const resumo = resumirCreditosAgendamento(consulta.creditos, { petId, servicoId, data });
  return (
    <output className="block rounded-lg border border-cyan-200 bg-cyan-50 p-3 text-sm text-cyan-900 dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-200">
      <ConteudoAvisoPacote consulta={consulta} chave={chave} resumo={resumo} />
      <span className="mt-1 block text-xs">
        Saldo sujeito às reservas feitas até a confirmação do agendamento. Pacotes expirados podem
        ser prorrogados na tela de pacotes.
      </span>
    </output>
  );
}

function ConteudoAvisoPacote({ consulta, chave, resumo }) {
  if (consulta.loading || consulta.chave !== chave) return "Consultando pacotes do pet...";
  if (consulta.error)
    return "Não foi possível consultar a prévia do saldo. Ao salvar, o sistema verificará os pacotes automaticamente.";
  if (resumo.saldo <= 0)
    return "Sem saldo válido para este serviço na data escolhida. O agendamento seguirá como avulso.";
  return (
    <>
      <span className="block font-semibold">
        {formatarCreditos(resumo.saldo)} crédito(s) para este serviço na data escolhida.
      </span>
      <span className="block">
        Ao salvar, até 1 crédito será reservado automaticamente. O check-in confirma o uso; cancelar
        devolve a reserva. Valores não cobertos e táxi dog continuam à parte.
      </span>
      {resumo.pagamentoPendente && (
        <span className="mt-1 block text-amber-800 dark:text-amber-300">
          Há pacote com pagamento a conferir. O saldo pode ser usado e a cobrança continua em
          aberto.
        </span>
      )}
    </>
  );
}
