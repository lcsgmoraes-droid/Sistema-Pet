import AssistenteIAMedicamentosContexto from "./AssistenteIAMedicamentosContexto";
import AssistenteIAModoToggle from "./AssistenteIAModoToggle";
import AssistenteIASelecaoContexto from "./AssistenteIASelecaoContexto";
import AssistenteIAVinculosResumo from "./AssistenteIAVinculosResumo";

export default function AssistenteIAContextoPanel({
  consultaId,
  consultaSelecionada,
  consultas,
  exameId,
  exameSelecionado,
  exames,
  med1,
  med2,
  modo,
  onAbrirConsulta,
  onSelecionarPet,
  onSelecionarTutor,
  pesoKg,
  petId,
  petsDoTutor,
  retornoNovoPet,
  setConsultaId,
  setExameId,
  setMed1,
  setMed2,
  setModo,
  setPesoKg,
  tutorSelecionado,
}) {
  return (
    <>
      <AssistenteIAModoToggle modo={modo} setModo={setModo} />

      <AssistenteIASelecaoContexto
        consultaId={consultaId}
        consultas={consultas}
        exameId={exameId}
        exames={exames}
        modo={modo}
        onSelecionarPet={onSelecionarPet}
        onSelecionarTutor={onSelecionarTutor}
        petId={petId}
        petsDoTutor={petsDoTutor}
        retornoNovoPet={retornoNovoPet}
        setConsultaId={setConsultaId}
        setExameId={setExameId}
        tutorSelecionado={tutorSelecionado}
      />

      <AssistenteIAVinculosResumo
        consultaSelecionada={consultaSelecionada}
        exameSelecionado={exameSelecionado}
        onAbrirConsulta={onAbrirConsulta}
      />

      <AssistenteIAMedicamentosContexto
        med1={med1}
        med2={med2}
        pesoKg={pesoKg}
        setMed1={setMed1}
        setMed2={setMed2}
        setPesoKg={setPesoKg}
      />
    </>
  );
}
