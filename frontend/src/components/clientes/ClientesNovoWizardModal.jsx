import { FiAlertCircle, FiArrowLeft, FiArrowRight, FiCheck, FiSave, FiX } from "react-icons/fi";
import ClientesNovoCadastroStep from "./ClientesNovoCadastroStep";
import ClientesNovoAcessoAppCard from "./ClientesNovoAcessoAppCard";
import ClientesNovoComplementaresStep from "./ClientesNovoComplementaresStep";
import ClientesNovoContatosStep from "./ClientesNovoContatosStep";
import ClientesNovoDuplicadoWarning from "./ClientesNovoDuplicadoWarning";
import ClientesNovoEnderecoStep from "./ClientesNovoEnderecoStep";
import ClientesNovoFinanceiroStep from "./ClientesNovoFinanceiroStep";
import ClientesNovoPetsStep from "./ClientesNovoPetsStep";

const ClientesNovoWizardModal = ({
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
}) => {
  if (!showModal) return null;

  const titulosTipo = {
    cliente: "Cliente",
    fornecedor: "Fornecedor",
    veterinario: "Veterinário",
    funcionario: "Funcionário",
  };
  const tipoTituloEdicao = titulosTipo[editingCliente?.tipo_cadastro] || "Pessoa";
  const tipoTituloNovo = titulosTipo[formData?.tipo_cadastro] || "Pessoa";
  const ultimoStep = steps.at(-1)?.number || 1;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              {editingCliente ? `Editar ${tipoTituloEdicao}` : `Adicionar ${tipoTituloNovo}`}
            </h2>
            <button onClick={closeModal} className="text-gray-400 hover:text-gray-600">
              <FiX size={24} />
            </button>
          </div>

          <div className="flex items-center justify-between mb-2">
            {steps.map((step, index) => (
              <div key={step.number} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <button
                    onClick={() => setCurrentStep(step.number)}
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-semibold text-sm transition-all hover:scale-110 cursor-pointer ${
                      currentStep > step.number
                        ? "bg-green-500 text-white hover:bg-green-600"
                        : currentStep === step.number
                          ? "bg-blue-500 text-white hover:bg-blue-600"
                          : "bg-gray-300 text-gray-600 hover:bg-gray-400"
                    }`}
                    type="button"
                    title={`Ir para: ${step.title}`}
                  >
                    {currentStep > step.number ? <FiCheck /> : step.number}
                  </button>
                  <span className="text-xs mt-1 text-center hidden md:block">{step.title}</span>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`h-0.5 flex-1 ${
                      currentStep > step.number ? "bg-green-500" : "bg-gray-300"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="text-center text-sm text-gray-600">
            {currentStep}/{ultimoStep}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
              <FiAlertCircle />
              <span>{error}</span>
            </div>
          )}

          {showDuplicadoWarning && clienteDuplicado && (
            <ClientesNovoDuplicadoWarning
              clienteDuplicado={clienteDuplicado}
              isDocumentoUnico={isDocumentoUnico}
              loading={loading}
              onContinuarMesmoDuplicado={continuarMesmoDuplicado}
              onEditarClienteExistente={editarClienteExistente}
              onIrParaClienteExistente={irParaClienteExistente}
            />
          )}

          {currentStep === 1 && (
            <ClientesNovoCadastroStep
              formData={formData}
              setFormData={setFormData}
              setShowDuplicadoWarning={setShowDuplicadoWarning}
              setClienteDuplicado={setClienteDuplicado}
              editingCliente={editingCliente}
            />
          )}

          {currentStep === 2 && (
            <ClientesNovoContatosStep
              formData={formData}
              setFormData={setFormData}
              setShowDuplicadoWarning={setShowDuplicadoWarning}
              setClienteDuplicado={setClienteDuplicado}
            />
          )}

          {currentStep === 3 && (
            <ClientesNovoEnderecoStep
              formData={formData}
              setFormData={setFormData}
              buscarCep={buscarCep}
              loadingCep={loadingCep}
              cepError={cepError}
            />
          )}

          {currentStep === 4 && (
            <>
              <ClientesNovoComplementaresStep
                formData={formData}
                setFormData={setFormData}
                enderecosAdicionais={enderecosAdicionais}
                abrirModalEndereco={abrirModalEndereco}
                removerEndereco={removerEndereco}
              />
              <ClientesNovoAcessoAppCard
                formData={formData}
                setFormData={setFormData}
                usuarios={usuariosAcessoApp}
                loadingUsuarios={loadingUsuariosAcessoApp}
              />
            </>
          )}

          {currentStep === 5 && (
            <ClientesNovoPetsStep pets={pets} editingCliente={editingCliente} navigate={navigate} />
          )}

          {currentStep === 6 && (
            <ClientesNovoFinanceiroStep
              editingCliente={editingCliente}
              refreshKeyCredito={refreshKeyCredito}
              resumoFinanceiro={resumoFinanceiro}
              loadingResumo={loadingResumo}
              saldoCampanhas={saldoCampanhas}
              setMostrarModalAdicionarCredito={setMostrarModalAdicionarCredito}
              setMostrarModalRemoverCredito={setMostrarModalRemoverCredito}
              navigate={navigate}
            />
          )}
        </div>

        <div className="border-t border-gray-200 p-4 bg-gray-50 flex justify-between gap-3">
          <button
            onClick={prevStep}
            disabled={currentStep === 1}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiArrowLeft /> Voltar
          </button>

          <div className="flex flex-wrap justify-end gap-2">
            <button
              onClick={handleSubmitFinal}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors disabled:cursor-wait disabled:opacity-60"
            >
              <FiSave /> {loading ? "Salvando..." : `Salvar ${tipoTituloNovo}`}
            </button>
            {currentStep < ultimoStep && (
              <button
                onClick={nextStep}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Avancar <FiArrowRight />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClientesNovoWizardModal;
