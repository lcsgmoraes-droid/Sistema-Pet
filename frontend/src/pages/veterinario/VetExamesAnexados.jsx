import ExamesAnexadosErro from "./examesAnexados/ExamesAnexadosErro";
import ExamesAnexadosFiltros from "./examesAnexados/ExamesAnexadosFiltros";
import ExamesAnexadosHeader from "./examesAnexados/ExamesAnexadosHeader";
import ExamesAnexadosLista from "./examesAnexados/ExamesAnexadosLista";
import NovoExameAnexadoModal from "./examesAnexados/NovoExameAnexadoModal";
import { useVetExamesAnexados } from "./examesAnexados/useVetExamesAnexados";

export default function VetExamesAnexados() {
  const exames = useVetExamesAnexados();

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-5">
      <ExamesAnexadosHeader
        onNovoExame={exames.abrirNovoExame}
        onVerPets={exames.verPets}
      />

      <ExamesAnexadosFiltros
        periodo={exames.periodo}
        dataInicio={exames.dataInicio}
        dataFim={exames.dataFim}
        tutorBusca={exames.tutorBusca}
        carregando={exames.carregando}
        onChangePeriodo={exames.setPeriodo}
        onChangeDataInicio={exames.setDataInicio}
        onChangeDataFim={exames.setDataFim}
        onChangeTutorBusca={exames.setTutorBusca}
        onAplicar={exames.carregar}
        onLimpar={exames.limparFiltros}
      />

      <ExamesAnexadosErro erro={exames.erro} />

      <ExamesAnexadosLista
        itens={exames.itens}
        total={exames.dados.total}
        exameExpandidoId={exames.exameExpandidoId}
        onToggleExame={exames.toggleExameExpandido}
        onAbrirConsulta={exames.abrirConsultaExame}
        onVerPet={exames.verPet}
        onAtualizarResumo={exames.atualizarResumoExame}
        onNovoExame={exames.abrirNovoExame}
      />

      <NovoExameAnexadoModal
        isOpen={exames.novaAberta}
        consultaId={exames.consultaIdQuery}
        erroNovo={exames.erroNovo}
        tutorFormSelecionado={exames.tutorFormSelecionado}
        setTutorFormSelecionado={exames.setTutorFormSelecionado}
        form={exames.form}
        setForm={exames.setForm}
        petsDoTutor={exames.petsDoTutor}
        retornoNovoPet={exames.retornoNovoPet}
        onClose={exames.fecharNovoExame}
        onSalvar={exames.salvarExame}
        salvandoNovo={exames.salvandoNovo}
        setArquivoNovo={exames.setArquivoNovo}
      />
    </div>
  );
}
