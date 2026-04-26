import CalendarioPreventivoTab from "./vacinas/CalendarioPreventivoTab";
import CarteiraVacinasTab from "./vacinas/CarteiraVacinasTab";
import RegistrarVacinaModal from "./vacinas/RegistrarVacinaModal";
import VacinasErro from "./vacinas/VacinasErro";
import VacinasHeader from "./vacinas/VacinasHeader";
import VacinasTabs from "./vacinas/VacinasTabs";
import VacinasVencendoTab from "./vacinas/VacinasVencendoTab";
import { useVetVacinas } from "./vacinas/useVetVacinas";

export default function VetVacinas() {
  const vacinas = useVetVacinas();

  return (
    <div className="p-6 space-y-5">
      <VacinasHeader onRegistrarVacina={() => vacinas.setNovaAberta(true)} />

      <VacinasTabs
        aba={vacinas.aba}
        vacinasVencendoTotal={vacinas.vacinasVencendo.length}
        onChangeAba={vacinas.setAba}
      />

      <VacinasErro erro={vacinas.erro} />

      {vacinas.aba === "registros" && (
        <CarteiraVacinasTab
          tutorFiltroSelecionado={vacinas.tutorFiltroSelecionado}
          pessoaFiltro={vacinas.pessoaFiltro}
          petSelecionado={vacinas.petSelecionado}
          petsFiltradosCarteira={vacinas.petsFiltradosCarteira}
          vacinas={vacinas.vacinas}
          carregando={vacinas.carregando}
          onSelecionarTutor={vacinas.selecionarTutorFiltro}
          onSelecionarPet={vacinas.setPetSelecionado}
          onRegistrarPrimeiraVacina={vacinas.abrirRegistroPrimeiraVacina}
        />
      )}

      {vacinas.aba === "vencendo" && (
        <VacinasVencendoTab vacinasVencendo={vacinas.vacinasVencendo} />
      )}

      {vacinas.aba === "calendario" && (
        <CalendarioPreventivoTab
          calendario={vacinas.calendario}
          especieCalendario={vacinas.especieCalendario}
          carregandoCalendario={vacinas.carregandoCalendario}
          onChangeEspecie={vacinas.setEspecieCalendario}
          onCarregarCalendario={vacinas.carregarCalendarioPreventivo}
        />
      )}

      <RegistrarVacinaModal
        isOpen={vacinas.novaAberta}
        consultaId={vacinas.consultaIdQuery}
        tutorFormSelecionado={vacinas.tutorFormSelecionado}
        form={vacinas.form}
        petsDaPessoa={vacinas.petsDaPessoa}
        sugestaoDose={vacinas.sugestaoDose}
        veterinarios={vacinas.veterinarios}
        erro={vacinas.erro}
        salvando={vacinas.salvando}
        retornoNovoPet={vacinas.retornoNovoPet}
        onSelecionarTutor={vacinas.selecionarTutorForm}
        onSetCampo={vacinas.setCampo}
        onFechar={vacinas.fecharModalVacina}
        onSalvar={vacinas.salvarVacina}
        onBeforeNovoPet={() => vacinas.setNovaAberta(false)}
      />
    </div>
  );
}
