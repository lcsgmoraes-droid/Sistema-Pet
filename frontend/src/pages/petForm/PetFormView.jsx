import { AlertCircle, ArrowLeft, CheckCircle2, PawPrint } from "lucide-react";

import QuickAddModal from "../../components/QuickAddModal";
import BotaoCancelar from "../../components/v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../../components/v2/BotaoSalva/BotaoSalva";
import LinkPadrao from "../../components/v2/LinkPadrao/LinkPadrao";
import AbasNavegacao from "../../components/v2/AbasNavegacao/AbasNavegacao";
import PageHeader from "../../components/ui/PageHeader";
import Panel from "../../components/ui/Panel";
import PetFormCaracteristicasTab from "./PetFormCaracteristicasTab";
import PetFormDadosGeraisTab from "./PetFormDadosGeraisTab";
import PetFormSaudeTab from "./PetFormSaudeTab";

export default function PetFormView({
  loading,
  isEditing,
  returnTo,
  navigate,
  petId,
  error,
  success,
  clienteIdPreSelecionado,
  handleSubmit,
  formData,
  erros,
  setField,
  handleEspecieChange,
  handleCastradoChange,
  clientes,
  abrirQuickAdd,
  especies,
  racas,
  especieSelecionadaAtual,
  setFormData,
  saving,
  abaAtiva,
  setAbaAtiva,
  abas,
  showQuickAddModal,
  quickAddTipo,
  handleQuickAddSuccess,
  fecharQuickAdd,
}) {
  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <div
            className="mx-auto h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600 motion-reduce:animate-none"
            aria-hidden="true"
          />
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  const destinoVoltar = !isEditing && returnTo ? returnTo : isEditing ? `/pets/${petId}` : "/pets";
  const voltar = () => navigate(destinoVoltar);

  return (
    <div className="space-y-6 p-6">
      <LinkPadrao to={destinoVoltar}>
        <span className="inline-flex items-center gap-1">
          <ArrowLeft size={14} aria-hidden="true" />
          {isEditing ? "Voltar para detalhes do pet" : "Voltar para lista de pets"}
        </span>
      </LinkPadrao>

      <PageHeader
        icon={PawPrint}
        title={isEditing ? "Editar Pet" : "Cadastrar Novo Pet"}
        subtitle={
          isEditing ? "Atualize as informações do pet" : "Preencha os dados do animal de estimação"
        }
        actions={
          <>
            <BotaoSalva onClick={handleSubmit} loading={saving} tamanho="grande">
              {isEditing ? "Salvar Alterações" : "Cadastrar Pet"}
            </BotaoSalva>
            <BotaoCancelar disabled={saving} onClick={voltar} tamanho="grande" />
          </>
        }
      />

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
          <AlertCircle size={18} aria-hidden="true" />
          {error}
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-green-700">
          <CheckCircle2 size={18} aria-hidden="true" />
          {success}
        </div>
      )}

      {clienteIdPreSelecionado && (
        <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-blue-700">
          <CheckCircle2 size={18} aria-hidden="true" />
          <span>Tutor pré-selecionado automaticamente! Você pode alterar se necessário.</span>
        </div>
      )}

      <Panel padding="none">
        <AbasNavegacao abas={abas} ativa={abaAtiva} onChange={setAbaAtiva} className="px-4" />
        <div className="p-4">
          {abaAtiva === "dados-gerais" ? (
            <PetFormDadosGeraisTab
              abrirQuickAdd={abrirQuickAdd}
              clientes={clientes}
              clienteIdPreSelecionado={clienteIdPreSelecionado}
              erros={erros}
              especies={especies}
              especieSelecionadaAtual={especieSelecionadaAtual}
              formData={formData}
              handleEspecieChange={handleEspecieChange}
              isEditing={isEditing}
              onChangeCastrado={handleCastradoChange}
              racas={racas}
              setField={setField}
            />
          ) : null}

          {abaAtiva === "caracteristicas" ? (
            <PetFormCaracteristicasTab
              formData={formData}
              setField={setField}
              setFormData={setFormData}
            />
          ) : null}

          {abaAtiva === "saude" ? (
            <PetFormSaudeTab formData={formData} setField={setField} />
          ) : null}
        </div>
      </Panel>

      {showQuickAddModal && (
        <QuickAddModal
          tipo={quickAddTipo}
          especieId={quickAddTipo === "raca" ? Number.parseInt(formData.especie, 10) : null}
          especieNome={quickAddTipo === "raca" ? especieSelecionadaAtual?.nome : null}
          onSuccess={handleQuickAddSuccess}
          onClose={fecharQuickAdd}
        />
      )}
    </div>
  );
}
