import ModalAdicionarCredito from "../ModalAdicionarCredito";
import ModalImportacaoPessoas from "../ModalImportacaoPessoas";
import ModalRemoverCredito from "../ModalRemoverCredito";
import ClientesNovoEnderecoModal from "./ClientesNovoEnderecoModal";
import ClientesNovoWizardModal from "./ClientesNovoWizardModal";

const ClientesNovoModalsLayer = ({
  showModal,
  editingCliente,
  formData,
  closeModal,
  steps,
  currentStep,
  setCurrentStep,
  error,
  showDuplicadoWarning,
  clienteDuplicado,
  clientes,
  isDocumentoUnico,
  loading,
  cancelarRemocao,
  confirmarRemocaoEContinuar,
  continuarMesmoDuplicado,
  editarClienteExistente,
  irParaClienteExistente,
  showConfirmacaoRemocao,
  setShowDuplicadoWarning,
  setClienteDuplicado,
  setFormData,
  buscarCep,
  loadingCep,
  cepError,
  enderecosAdicionais,
  abrirModalEndereco,
  removerEndereco,
  pets,
  navigate,
  refreshKeyCredito,
  resumoFinanceiro,
  loadingResumo,
  saldoCampanhas,
  setMostrarModalAdicionarCredito,
  setMostrarModalRemoverCredito,
  prevStep,
  nextStep,
  handleSubmitFinal,
  mostrarFormEndereco,
  enderecoAtual,
  fecharModalEndereco,
  loadingCepEndereco,
  salvarEndereco,
  buscarCepModal,
  setEnderecoAtual,
  showModalImportacao,
  setShowModalImportacao,
  fetchClientes,
  mostrarModalAdicionarCredito,
  mostrarModalRemoverCredito,
  setEditingCliente,
  setRefreshKeyCredito,
  loadClientes,
}) => {
  return (
    <>
      <ClientesNovoWizardModal
        showModal={showModal}
        editingCliente={editingCliente}
        formData={formData}
        closeModal={closeModal}
        steps={steps}
        currentStep={currentStep}
        setCurrentStep={setCurrentStep}
        error={error}
        showDuplicadoWarning={showDuplicadoWarning}
        clienteDuplicado={clienteDuplicado}
        clientes={clientes}
        isDocumentoUnico={isDocumentoUnico}
        loading={loading}
        cancelarRemocao={cancelarRemocao}
        confirmarRemocaoEContinuar={confirmarRemocaoEContinuar}
        continuarMesmoDuplicado={continuarMesmoDuplicado}
        editarClienteExistente={editarClienteExistente}
        irParaClienteExistente={irParaClienteExistente}
        showConfirmacaoRemocao={showConfirmacaoRemocao}
        setShowDuplicadoWarning={setShowDuplicadoWarning}
        setClienteDuplicado={setClienteDuplicado}
        setFormData={setFormData}
        buscarCep={buscarCep}
        loadingCep={loadingCep}
        cepError={cepError}
        enderecosAdicionais={enderecosAdicionais}
        abrirModalEndereco={abrirModalEndereco}
        removerEndereco={removerEndereco}
        pets={pets}
        navigate={navigate}
        refreshKeyCredito={refreshKeyCredito}
        resumoFinanceiro={resumoFinanceiro}
        loadingResumo={loadingResumo}
        saldoCampanhas={saldoCampanhas}
        setMostrarModalAdicionarCredito={setMostrarModalAdicionarCredito}
        setMostrarModalRemoverCredito={setMostrarModalRemoverCredito}
        prevStep={prevStep}
        nextStep={nextStep}
        handleSubmitFinal={handleSubmitFinal}
      />

      {mostrarFormEndereco && enderecoAtual && (
        <ClientesNovoEnderecoModal
          enderecoAtual={enderecoAtual}
          fecharModalEndereco={fecharModalEndereco}
          loadingCepEndereco={loadingCepEndereco}
          salvarEndereco={salvarEndereco}
          buscarCepModal={buscarCepModal}
          setEnderecoAtual={setEnderecoAtual}
        />
      )}

      <ModalImportacaoPessoas
        isOpen={showModalImportacao}
        onClose={() => {
          setShowModalImportacao(false);
          fetchClientes();
        }}
      />

      {mostrarModalAdicionarCredito && editingCliente && (
        <ModalAdicionarCredito
          cliente={editingCliente}
          onConfirmar={(novoSaldo) => {
            setEditingCliente({ ...editingCliente, credito: novoSaldo });
            setRefreshKeyCredito((k) => k + 1);
            loadClientes();
          }}
          onClose={() => setMostrarModalAdicionarCredito(false)}
        />
      )}

      {mostrarModalRemoverCredito && editingCliente && (
        <ModalRemoverCredito
          cliente={editingCliente}
          onConfirmar={(novoSaldo) => {
            setEditingCliente({ ...editingCliente, credito: novoSaldo });
            setRefreshKeyCredito((k) => k + 1);
            loadClientes();
          }}
          onClose={() => setMostrarModalRemoverCredito(false)}
        />
      )}
    </>
  );
};

export default ClientesNovoModalsLayer;
