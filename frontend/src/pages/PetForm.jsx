import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import api from '../api';
import { FiArrowLeft, FiSave, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';
import { PawPrint } from 'lucide-react';
import CampoIdadeInteligente from '../components/CampoIdadeInteligente';

const PetForm = () => {
  const { petId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const isEditing = !!petId;

  // Pegar cliente_id do state de navegação (vindo de ClientesNovo.jsx)
  const clienteIdFromState = location.state?.clienteId;

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [clientes, setClientes] = useState([]);
  const [racas, setRacas] = useState([]);

  const [formData, setFormData] = useState({
    cliente_id: clienteIdFromState || '',  // Preenche automaticamente se vier do state
    nome: '',
    especie: '',
    raca: '',
    sexo: '',
    castrado: false,
    data_nascimento: '',
    idade_aproximada: '',
    peso: '',
    cor: '',
    porte: '',
    microchip: '',
    alergias: '',
    doencas_cronicas: '',
    medicamentos_continuos: '',
    historico_clinico: '',
    observacoes: '',
    foto_url: '',
    ativo: true
  });

  useEffect(() => {
    loadClientes();
    loadRacas();
    if (isEditing) {
      loadPet();
    }
  }, [petId]);

  const loadClientes = async () => {
    try {
      const response = await api.get('/clientes');
      setClientes(response.data);
    } catch (err) {
      console.error('Erro ao carregar clientes:', err);
    }
  };

  const loadRacas = async () => {
    try {
      const response = await api.get('/racas');
      setRacas(response.data);
    } catch (err) {
      console.error('Erro ao carregar raças:', err);
    }
  };

  const loadPet = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/pets/${petId}`);
      const pet = response.data;
      
      setFormData({
        cliente_id: pet.cliente_id || '',
        nome: pet.nome || '',
        especie: pet.especie || '',
        raca: pet.raca || '',
        sexo: pet.sexo || '',
        castrado: pet.castrado || false,
        data_nascimento: '',  // Não usamos mais diretamente
        idade_aproximada: pet.idade_meses || pet.idade_aproximada || '',
        peso: pet.peso || '',
        cor: pet.cor || '',
        porte: pet.porte || '',
        microchip: pet.microchip || '',
        alergias: pet.alergias || '',
        doencas_cronicas: pet.doencas_cronicas || '',
        medicamentos_continuos: pet.medicamentos_continuos || '',
        historico_clinico: pet.historico_clinico || '',
        observacoes: pet.observacoes || '',
        foto_url: pet.foto_url || '',
        ativo: pet.ativo !== undefined ? pet.ativo : true
      });
    } catch (err) {
      console.error('Erro ao carregar pet:', err);
      setError('Erro ao carregar informações do pet');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const validateForm = () => {
    if (!formData.nome.trim()) {
      setError('Nome do pet é obrigatório');
      return false;
    }
    if (!formData.especie) {
      setError('Espécie é obrigatória');
      return false;
    }
    if (!formData.cliente_id) {
      setError('Cliente (tutor) é obrigatório');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!validateForm()) {
      return;
    }

    try {
      setSaving(true);
      
      // Preparar dados para envio
      const dataToSend = {
        ...formData,
        cliente_id: parseInt(formData.cliente_id),
        peso: formData.peso ? parseFloat(formData.peso) : null,
        idade_aproximada: formData.idade_aproximada ? parseInt(formData.idade_aproximada) : null,
        data_nascimento: formData.data_nascimento || null
      };

      if (isEditing) {
        await api.put(`/pets/${petId}`, dataToSend);
        setSuccess('Pet atualizado com sucesso!');
        setTimeout(() => navigate(`/pets/${petId}`), 1500);
      } else {
        const response = await api.post('/pets', dataToSend);
        setSuccess('Pet cadastrado com sucesso!');
        setTimeout(() => navigate(`/pets/${response.data.id}`), 1500);
      }
    } catch (err) {
      console.error('Erro ao salvar pet:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar pet');
    } finally {
      setSaving(false);
    }
  };

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
          onClick={() => navigate(isEditing ? `/pets/${petId}` : '/pets')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <FiArrowLeft />
          {isEditing ? 'Voltar para detalhes do pet' : 'Voltar para lista de pets'}
        </button>

        <div className="flex items-center gap-3 mb-2">
          <PawPrint className="text-blue-600" size={36} />
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? 'Editar Pet' : 'Cadastrar Novo Pet'}
          </h1>
        </div>
        <p className="text-gray-600">
          {isEditing 
            ? 'Atualize as informações do pet' 
            : 'Preencha os dados do animal de estimação'}
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
      {clienteIdFromState && (
        <div className="mb-6 bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <FiCheckCircle />
          <span>
            ✅ Tutor pré-selecionado automaticamente! Você pode alterar se necessário.
          </span>
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
                  clienteIdFromState ? 'border-blue-400 bg-blue-50' : 'border-gray-300'
                }`}
              >
                <option value="">Selecione o tutor...</option>
                {clientes.map(cliente => (
                  <option key={cliente.id} value={cliente.id}>
                    {cliente.nome} {cliente.cpf && `- CPF: ${cliente.cpf}`}
                  </option>
                ))}
              </select>
              {clienteIdFromState && (
                <p className="text-xs text-blue-600 mt-1">
                  🎯 Tutor selecionado automaticamente
                </p>
              )}
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome do Pet *
              </label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Espécie *
              </label>
              <select
                name="especie"
                value={formData.especie}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                <option value="">Selecione...</option>
                <option value="Cão">Cão</option>
                <option value="Gato">Gato</option>
                <option value="Ave">Ave</option>
                <option value="Roedor">Roedor</option>
                <option value="Réptil">Réptil</option>
                <option value="Outro">Outro</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Raça
              </label>
              <input
                type="text"
                name="raca"
                value={formData.raca}
                onChange={handleChange}
                list="racas-list"
                placeholder="Ex: SRD, Poodle, Siamês"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              />
              <datalist id="racas-list">
                <option value="SRD (Sem Raça Definida)" />
                {racas.map((raca) => (
                  <option key={raca.id} value={raca.nome} />
                ))}
              </datalist>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Sexo
              </label>
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
              onChange={(meses) => setFormData(prev => ({ ...prev, idade_aproximada: meses, data_nascimento: '' }))}
              name="idade_aproximada"
              label="Idade do Pet"
              mostrarDataNascimento={true}
              className="col-span-2"
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Peso (kg)
              </label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Porte
              </label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cor/Pelagem
              </label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Microchip
              </label>
              <input
                type="text"
                name="microchip"
                value={formData.microchip}
                onChange={handleChange}
                placeholder="Número do microchip"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none font-mono text-sm"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                URL da Foto
              </label>
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
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Alergias
              </label>
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
                {isEditing ? 'Salvar Alterações' : 'Cadastrar Pet'}
              </>
            )}
          </button>

          <button
            type="button"
            onClick={() => navigate(isEditing ? `/pets/${petId}` : '/pets')}
            disabled={saving}
            className="px-6 py-3 border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors font-medium disabled:opacity-50"
          >
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
};

export default PetForm;
