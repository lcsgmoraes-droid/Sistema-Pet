import { forwardRef } from "react";
import MesGrade from "../CalendarioPainel/MesGrade";
import { adicionarMeses } from "../utils/calendario";

const CalendarioIntervaloPainel = forwardRef(function CalendarioIntervaloPainel(
  { fim, inicio, mesEsquerdo, onMudarMesEsquerdo, onSelecionarDia },
  ref,
) {
  const mesDireito = adicionarMeses(mesEsquerdo, 1);
  const selecionados = [inicio, fim].filter(Boolean);
  const intervalo = inicio && fim ? { inicio, fim } : null;

  return (
    <div
      ref={ref}
      className="absolute z-20 mt-1 flex max-w-[calc(100vw-5rem)] flex-col gap-4 rounded-lg border border-slate-200 bg-white p-3 shadow-lg sm:max-w-none sm:flex-row dark:border-slate-700 dark:bg-slate-900"
    >
      <MesGrade
        mesVisivel={mesEsquerdo}
        mostrarSetaProxima={false}
        onMudarMes={onMudarMesEsquerdo}
        onSelecionarDia={onSelecionarDia}
        selecionados={selecionados}
        intervalo={intervalo}
      />
      <div className="h-px shrink-0 bg-slate-100 sm:h-auto sm:w-px dark:bg-slate-800" />
      <MesGrade
        mesVisivel={mesDireito}
        mostrarSetaAnterior={false}
        onMudarMes={(novoMesDireito) => onMudarMesEsquerdo(adicionarMeses(novoMesDireito, -1))}
        onSelecionarDia={onSelecionarDia}
        selecionados={selecionados}
        intervalo={intervalo}
      />
    </div>
  );
});

export default CalendarioIntervaloPainel;
