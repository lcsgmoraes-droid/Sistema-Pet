import { useState } from "react";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import InputRadio from "../../components/v2/InputRadio/InputRadio";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import ModalPadrao from "../../components/v2/ModalPadrao/ModalPadrao";
import { rotuloDaOportunidade } from "./crmUtils";

const OPCOES_DE_RESULTADO = [
  { value: "resolvida", label: "Resolvida" },
  { value: "descartada", label: "Descartada" },
];

// Pergunta o resultado de cada oportunidade aberta ao concluir ou encerrar um card.
export default function CrmConcluirModal({ pendencia, onCancelar, onConfirmar }) {
  const { card, colunaDestino, exigeMotivoDaPerda, oportunidades } = pendencia;
  const [resultados, setResultados] = useState({});
  const [motivoPerda, setMotivoPerda] = useState("");
  const [tentou, setTentou] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const atualizar = (id, campo, valor) =>
    setResultados((atual) => ({ ...atual, [id]: { ...atual[id], [campo]: valor } }));

  const erroDe = (oportunidade) => {
    const resultado = resultados[oportunidade.id];
    if (!resultado?.estado) return "Escolha o resultado.";
    if (resultado.estado === "descartada" && !(resultado.motivo || "").trim()) {
      return "Informe o motivo de descartar.";
    }
    return "";
  };
  const erroDaPerda = exigeMotivoDaPerda && !motivoPerda.trim() ? "Informe o motivo." : "";
  const valido = oportunidades.every((item) => !erroDe(item)) && !erroDaPerda;

  const enviar = async (evento) => {
    evento.preventDefault();
    setTentou(true);
    if (!valido) return;
    setEnviando(true);
    try {
      await onConfirmar({
        motivoPerda,
        resultados: oportunidades.map((item) => ({
          oportunidade_id: item.id,
          estado: resultados[item.id].estado,
          motivo: resultados[item.id].motivo || null,
        })),
      });
    } finally {
      setEnviando(false);
    }
  };

  return (
    <ModalPadrao
      titulo={`Mover para “${colunaDestino.nome}”`}
      tamanho="normal"
      onFechar={onCancelar}
      rodape={
        <>
          <BotaoCancelar onClick={onCancelar} disabled={enviando} />
          <BotaoSalva type="submit" form="crm-concluir" loading={enviando}>
            Mover card
          </BotaoSalva>
        </>
      }
    >
      <form id="crm-concluir" noValidate onSubmit={enviar} className="space-y-5">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          {card.nome}: informe como terminou cada oportunidade antes de fechar o ciclo.
        </p>

        {oportunidades.map((oportunidade) => {
          const resultado = resultados[oportunidade.id] || {};
          const erro = tentou ? erroDe(oportunidade) : "";
          return (
            <fieldset key={oportunidade.id} className="space-y-2">
              <InputRadio
                label={rotuloDaOportunidade(oportunidade)}
                name={`resultado-${oportunidade.id}`}
                opcoes={OPCOES_DE_RESULTADO}
                value={resultado.estado}
                onChange={(valor) => atualizar(oportunidade.id, "estado", valor)}
                error={erro && !resultado.estado ? erro : ""}
              />
              {resultado.estado === "descartada" ? (
                <InputTexto
                  id={`motivo-${oportunidade.id}`}
                  label="Motivo de descartar"
                  value={resultado.motivo || ""}
                  maxLength={200}
                  onChange={(valor) => atualizar(oportunidade.id, "motivo", valor)}
                  error={erro && resultado.estado ? erro : ""}
                  required
                />
              ) : null}
            </fieldset>
          );
        })}

        {exigeMotivoDaPerda ? (
          <InputTexto
            id="crm-motivo-perda"
            label="Por que o card está sendo encerrado sem resultado?"
            value={motivoPerda}
            maxLength={200}
            onChange={setMotivoPerda}
            error={tentou ? erroDaPerda : ""}
            required
          />
        ) : null}
      </form>
    </ModalPadrao>
  );
}
