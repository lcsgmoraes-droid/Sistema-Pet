import { FiArrowLeft, FiSave, FiAlertCircle, FiCheckCircle, FiPlus } from "react-icons/fi";
import { PawPrint } from "lucide-react";

import CampoIdadeInteligente from "../../components/CampoIdadeInteligente";
import QuickAddModal from "../../components/QuickAddModal";

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
  handleChange,
  clientes,
  abrirQuickAdd,
  especies,
  racas,
  especieSelecionadaAtual,
  setFormData,
  saving,
  showQuickAddModal,
  quickAddTipo,
  handleQuickAddSuccess,
  fecharQuickAdd,
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => {
            if (!isEditing && returnTo) {
              navigate(returnTo);
              return;
            }
            navigate(isEditing ? `/pets/${petId}` : "/pets");
          }}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <FiArrowLeft />
          {isEditing ? "Voltar para detalhes do pet" : "Voltar para lista de pets"}
        </button>

        <div className="flex items-center gap-3 mb-2">
          <PawPrint className="text-blue-600" size={36} />
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? "Editar Pet" : "Cadastrar Novo Pet"}
          </h1>
        </div>
        <p className="text-gray-600">
          {isEditing
            ? "Atualize as informações do pet"
            : "Preencha os dados do animal de estimação"}
        </p>
      </div>

      {/* Mensagens */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <FiAlertCircle />
          {error}
        </div>
      )}

      {success && (
        <div className="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <FiCheckCircle />
          {success}
        </div>
      )}

      {/* Aviso de tutor pré-selecionado */}
      {clienteIdPreSelecionado && (
        <div className="mb-6 bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <FiCheckCircle />
          <span>✅ Tutor pré-selecionado automaticamente! Você pode alterar se necessário.</span>
        </div>
      )}

      {/* Formulário */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Dados Básicos */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Dados Básicos</h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cliente (Tutor) *
              </label>
              <select
                name="cliente_id"
                value={formData.cliente_id}
                onChange={handleChange}
                required
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none ${
                  clienteIdPreSelecionado ? "border-blue-400 bg-blue-50" : "border-gray-300"
                }`}
              >
                <option value="">Selecione o tutor...</option>
                {clientes.map((cliente) => (
                  <option key={cliente.id} value={cliente.id}>
                    {cliente.nome} {cliente.cpf && `- CPF: ${cliente.cpf}`}
                  </option>
                ))}
              </select>
              {clienteIdPreSelecionado && (
                <p className="text-xs text-blue-600 mt-1">🎯 Tutor selecionado automaticamente</p>
              )}
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Pet *</label>
              <input
                type="text"
                name="nome"
                value={formData.nome}
                onChange={handleChange}
                required
                placeholder="Ex: Rex, Miau, Totó"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Espécie *</label>
              <div className="field-with-action">
                <select
                  name="especie"
                  value={formData.especie}
                  onChange={handleChange}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                >
                  <option value="">Selecione...</option>
                  {especies.map((especie) => (
                    <option key={especie.id} value={especie.id}>
                      {especie.nome}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-add-quick"
                  onClick={() => abrirQuickAdd("especie")}
                  title="Adicionar nova espécie"
                >
                  <FiPlus /> Nova
                </button>
              </div>
              {especies.length === 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  Nenhuma espécie cadastrada. Cadastre em Cadastros → Espécies e Raças.
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Raça</label>
              <div className="field-with-action">
                <select
                  name="raca"
                  value={formData.raca}
                  onChange={handleChange}
                  disabled={!formData.especie}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="">
                    {!formData.especie ? "Selecione uma espécie primeiro" : "Selecione uma raça..."}
                  </option>
                  {racas.map((raca) => (
                    <option key={raca.id} value={raca.nome}>
                      {raca.nome}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn-add-quick"
                  onClick={() => abrirQuickAdd("raca")}
                  title="Adicionar nova raça"
                  disabled={!formData.especie}
                >
                  <FiPlus /> Nova
                </button>
              </div>
              {formData.especie && racas.length === 0 && (
                <p className="text-xs text-amber-600 mt-1">
                  Nenhuma raça cadastrada para{" "}
                  {especieSelecionadaAtual?.nome || "a espécie selecionada"}.
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sexo</label>
              <select
                name="sexo"
                value={formData.sexo}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                <option value="">Selecione...</option>
                <option value="Macho">Macho</option>
                <option value="Fêmea">Fêmea</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                name="castrado"
                id="castrado"
                checked={formData.castrado}
                onChange={handleChange}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
              />
              <label htmlFor="castrado" className="text-sm font-medium text-gray-700">
                Pet castrado
              </label>
            </div>
          </div>
        </div>

        {/* Características Físicas */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Características Físicas</h2>

          <div className="grid grid-cols-2 gap-4">
            <CampoIdadeInteligente
              value={formData.idade_aproximada}
              onChange={(meses) =>
                setFormData((prev) => ({ ...prev, idade_aproximada: meses, data_nascimento: "" }))
              }
              name="idade_aproximada"
              label="Idade do Pet"
              mostrarDataNascimento={true}
              className="col-span-2"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Peso (kg)</label>
              <input
                type="number"
                name="peso"
                value={formData.peso}
                onChange={handleChange}
                step="0.1"
                min="0"
                placeholder="Ex: 5.5"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Porte</label>
              <select
                name="porte"
                value={formData.porte}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                <option value="">Selecione...</option>
                <option value="Mini">Mini</option>
                <option value="Pequeno">Pequeno</option>
                <option value="Médio">Médio</option>
                <option value="Grande">Grande</option>
                <option value="Gigante">Gigante</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Cor/Pelagem</label>
              <input
                type="text"
                name="cor"
                value={formData.cor}
                onChange={handleChange}
                placeholder="Ex: Preto, Branco, Caramelo"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Microchip</label>
              <input
                type="text"
                name="microchip"
                value={formData.microchip}
                onChange={handleChange}
                placeholder="Número do microchip"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none font-mono text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo sanguíneo</label>
              <input
                type="text"
                name="tipo_sanguineo"
                value={formData.tipo_sanguineo}
                onChange={handleChange}
                placeholder="Ex: DEA 1.1, A, B"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Registro de pedigree
              </label>
              <input
                type="text"
                name="pedigree_registro"
                value={formData.pedigree_registro}
                onChange={handleChange}
                placeholder="Código do registro, se houver"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data da castração
              </label>
              <input
                type="date"
                name="castrado_data"
                value={formData.castrado_data}
                onChange={handleChange}
                disabled={!formData.castrado}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none disabled:bg-gray-100"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">URL da Foto</label>
              <input
                type="url"
                name="foto_url"
                value={formData.foto_url}
                onChange={handleChange}
                placeholder="https://exemplo.com/foto-do-pet.jpg"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
          </div>
        </div>

        {/* Informações de Saúde */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Informações de Saúde</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Alergias</label>
              <p className="text-xs text-gray-500 mb-2">Uma linha por item.</p>
              <textarea
                name="alergias"
                value={formData.alergias}
                onChange={handleChange}
                rows="3"
                placeholder="Descreva alergias conhecidas (alimentares, medicamentos, etc)"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Doenças Crônicas
              </label>
              <p className="text-xs text-gray-500 mb-2">Uma linha por condição registrada.</p>
              <textarea
                name="doencas_cronicas"
                value={formData.doencas_cronicas}
                onChange={handleChange}
                rows="3"
                placeholder="Descreva doenças crônicas diagnosticadas"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Medicamentos Contínuos
              </label>
              <p className="text-xs text-gray-500 mb-2">
                Uma linha por medicamento, de preferência com dose.
              </p>
              <textarea
                name="medicamentos_continuos"
                value={formData.medicamentos_continuos}
                onChange={handleChange}
                rows="3"
                placeholder="Liste medicamentos de uso contínuo com dosagem"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Restrições alimentares
              </label>
              <p className="text-xs text-gray-500 mb-2">
                Uma linha por restrição, intolerância ou dieta especial.
              </p>
              <textarea
                name="restricoes_alimentares"
                value={formData.restricoes_alimentares}
                onChange={handleChange}
                rows="3"
                placeholder="Ex: sem frango, dieta renal, alimento úmido controlado"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Histórico Clínico
              </label>
              <textarea
                name="historico_clinico"
                value={formData.historico_clinico}
                onChange={handleChange}
                rows="4"
                placeholder="Descreva o histórico clínico do pet (cirurgias, tratamentos anteriores, etc)"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>
          </div>
        </div>

        {/* Observações */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Observações Adicionais</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Observações Gerais
              </label>
              <textarea
                name="observacoes"
                value={formData.observacoes}
                onChange={handleChange}
                rows="4"
                placeholder="Informações adicionais, comportamento, preferências, etc"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
            </div>

            {isEditing && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  name="ativo"
                  id="ativo"
                  checked={formData.ativo}
                  onChange={handleChange}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
                />
                <label htmlFor="ativo" className="text-sm font-medium text-gray-700">
                  Pet ativo no sistema
                </label>
              </div>
            )}
          </div>
        </div>

        {/* Botões */}
        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Salvando...
              </>
            ) : (
              <>
                <FiSave />
                {isEditing ? "Salvar Alterações" : "Cadastrar Pet"}
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => navigate(isEditing ? `/pets/${petId}` : "/pets")}
            disabled={saving}
            className="px-6 py-3 border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors font-medium disabled:opacity-50"
          >
            Cancelar
          </button>
        </div>
      </form>

      {/* Modal de Adicionar Rápido */}
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
