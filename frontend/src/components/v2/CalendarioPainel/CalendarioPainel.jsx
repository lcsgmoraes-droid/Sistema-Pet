import { forwardRef } from "react";
import MesGrade from "./MesGrade";

const CalendarioPainel = forwardRef(function CalendarioPainel(
  { intervalo, mesVisivel, onMudarMes, onSelecionarDia, rodape, selecionados = [] },
  ref,
) {
  return (
    <div
      ref={ref}
      className="absolute z-20 mt-1 rounded-lg border border-slate-200 bg-white p-3 shadow-lg dark:border-slate-700 dark:bg-slate-900"
    >
      <MesGrade
        mesVisivel={mesVisivel}
        onMudarMes={onMudarMes}
        onSelecionarDia={onSelecionarDia}
        selecionados={selecionados}
        intervalo={intervalo}
      />
      {rodape ? (
        <div className="mt-3 border-t border-slate-100 pt-3 dark:border-slate-800">{rodape}</div>
      ) : null}
    </div>
  );
});

export default CalendarioPainel;
