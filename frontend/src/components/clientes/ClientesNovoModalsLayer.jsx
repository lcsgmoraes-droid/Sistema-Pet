import ModalAdicionarCredito from "../ModalAdicionarCredito";
import ModalImportacaoPessoas from "../ModalImportacaoPessoas";
import ModalRemoverCredito from "../ModalRemoverCredito";
import ClientesNovoEnderecoModal from "./ClientesNovoEnderecoModal";
import ClientesNovoWizardModal from "./ClientesNovoWizardModal";
import UsuarioAcessoInicialModal from "../usuarios/UsuarioAcessoInicialModal";

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
  isDocumentoUnico,
  loading,
  continuarMesmoDuplicado,
  editarClienteExistente,
  irParaClienteExistente,
  setShowDuplicadoWarning,
  setClienteDuplicado,
  setFormData,
  usuariosAcessoApp,
  rolesAcessoApp,
  initialAccessCredentials,
  setInitialAccessCredentials,
  loadingUsuariosAcessoApp,
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
        isDocumentoUnico={isDocumentoUnico}
        loading={loading}
        continuarMesmoDuplicado={continuarMesmoDuplicado}
        editarClienteExistente={editarClienteExistente}
        irParaClienteExistente={irParaClienteExistente}
        setShowDuplicadoWarning={setShowDuplicadoWarning}
        setClienteDuplicado={setClienteDuplicado}
        setFormData={setFormData}
        usuariosAcessoApp={usuariosAcessoApp}
        rolesAcessoApp={rolesAcessoApp}
        loadingUsuariosAcessoApp={loadingUsuariosAcessoApp}
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

      <UsuarioAcessoInicialModal
        credentials={initialAccessCredentials}
        onClose={() => setInitialAccessCredentials(null)}
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
