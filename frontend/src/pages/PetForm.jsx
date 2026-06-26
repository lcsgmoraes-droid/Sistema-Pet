import { useState, useEffect } from "react";
import { useParams, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import api from "../api";
import PetFormView from "./petForm/PetFormView";
import { buildReturnWithNovoPet } from "../utils/petReturnFlow";
import "./EspeciesRacas.css"; // Para estilos do botão de adicionar rápido

const listToTextarea = (items = [], fallback = "") => {
  if (Array.isArray(items) && items.length > 0) {
    return items.join("\n");
  }
  return fallback || "";
};

const textareaToList = (value = "") =>
  value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);

const PetForm = () => {
  const { petId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const isEditing = !!petId;

  // Pegar cliente_id do state de navegação (vindo de ClientesNovo.jsx)
  const clienteIdFromState = location.state?.clienteId;
  const clienteIdFromQuery = searchParams.get("cliente_id");
  const tutorNomeFromQuery = searchParams.get("tutor_nome") || "";
  const returnTo = searchParams.get("return_to") || "";
  const clienteIdPreSelecionado = clienteIdFromQuery || clienteIdFromState || "";

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [clientes, setClientes] = useState([]);
  const [especies, setEspecies] = useState([]);
  const [racas, setRacas] = useState([]);

  // Estados para modal rápido
  const [showQuickAddModal, setShowQuickAddModal] = useState(false);
  const [quickAddTipo, setQuickAddTipo] = useState(null); // 'especie' ou 'raca'

  const [formData, setFormData] = useState({
    cliente_id: clienteIdPreSelecionado || "", // Preenche automaticamente se vier do state/query
    nome: "",
    especie: "",
    raca: "",
    sexo: "",
    castrado: false,
    data_nascimento: "",
    idade_aproximada: "",
    peso: "",
    cor: "",
    porte: "",
    microchip: "",
    alergias: "",
    doencas_cronicas: "",
    medicamentos_continuos: "",
    restricoes_alimentares: "",
    historico_clinico: "",
    tipo_sanguineo: "",
    pedigree_registro: "",
    castrado_data: "",
    observacoes: "",
    foto_url: "",
    ativo: true,
  });
  const especieSelecionadaAtual = especies.find(
    (especie) => String(especie.id) === String(formData.especie),
  );

  useEffect(() => {
    const loadData = async () => {
      await loadClientes();
      await loadEspecies();
      if (isEditing) {
        await loadPet();
      }
    };
    loadData();
  }, [petId]);

  // Carregar raças quando espécie mudar
  useEffect(() => {
    if (formData.especie) {
      loadRacasPorEspecie(formData.especie);
    } else {
      setRacas([]);
    }
  }, [formData.especie]);

  const loadClientes = async () => {
    try {
      const response = await api.get("/clientes/");
      const lista = response.data?.items || response.data?.clientes || response.data || [];
      let clientesCarregados = Array.isArray(lista) ? lista : [];

      if (
        clienteIdPreSelecionado &&
        !clientesCarregados.some(
          (cliente) => String(cliente.id) === String(clienteIdPreSelecionado),
        )
      ) {
        try {
          const responseTutor = await api.get(`/clientes/${clienteIdPreSelecionado}`);
          if (responseTutor?.data?.id) {
            clientesCarregados = [responseTutor.data, ...clientesCarregados];
          }
        } catch (erroTutor) {
          console.warn("Não foi possível carregar o tutor pré-selecionado:", erroTutor);
        }
      }

      const clientesUnicos = Array.from(
        new Map(clientesCarregados.map((cliente) => [String(cliente.id), cliente])).values(),
      );
      setClientes(clientesUnicos);
    } catch (err) {
      console.error("Erro ao carregar clientes:", err);
      setClientes([]);
    }
  };

  const loadEspecies = async () => {
    try {
      const response = await api.get("/cadastros/especies", { params: { ativo: true } });
      setEspecies(response.data);
    } catch (err) {
      console.error("Erro ao carregar espécies:", err);
    }
  };

  const loadRacasPorEspecie = async (especieId) => {
    try {
      // Buscar pelo ID da espécie
      const response = await api.get("/cadastros/racas", {
        params: {
          ativo: true,
          especie_id: especieId,
        },
      });
      setRacas(response.data);
    } catch (err) {
      console.error("Erro ao carregar raças:", err);
      setRacas([]);
    }
  };

  const loadPet = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/pets/${petId}`);
      const pet = response.data;

      // Converter nome da espécie para ID
      const especieEncontrada = especies.find((e) => e.nome === pet.especie);

      setFormData({
        cliente_id: pet.cliente_id || "",
        nome: pet.nome || "",
        especie: especieEncontrada ? especieEncontrada.id.toString() : "",
        raca: pet.raca || "",
        sexo: pet.sexo || "",
        castrado: pet.castrado || false,
        data_nascimento: "", // Não usamos mais diretamente
        idade_aproximada: pet.idade_meses || pet.idade_aproximada || "",
        peso: pet.peso || "",
        cor: pet.cor || "",
        porte: pet.porte || "",
        microchip: pet.microchip || "",
        alergias: listToTextarea(pet.alergias_lista, pet.alergias),
        doencas_cronicas: listToTextarea(pet.condicoes_cronicas_lista, pet.doencas_cronicas),
        medicamentos_continuos: listToTextarea(
          pet.medicamentos_continuos_lista,
          pet.medicamentos_continuos,
        ),
        restricoes_alimentares: listToTextarea(pet.restricoes_alimentares_lista),
        historico_clinico: pet.historico_clinico || "",
        tipo_sanguineo: pet.tipo_sanguineo || "",
        pedigree_registro: pet.pedigree_registro || "",
        castrado_data: pet.castrado_data || "",
        observacoes: pet.observacoes || "",
        foto_url: pet.foto_url || "",
        ativo: pet.ativo !== undefined ? pet.ativo : true,
      });
    } catch (err) {
      console.error("Erro ao carregar pet:", err);
      setError("Erro ao carregar informações do pet");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (name === "especie") {
      setFormData((prev) => ({
        ...prev,
        especie: value,
        raca: "",
      }));
      return;
    }
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  // Funções para Quick Add
  const abrirQuickAdd = (tipo) => {
    if (tipo === "raca" && !especieSelecionadaAtual) {
      setError(
        "Escolha uma especie antes de cadastrar uma raca. Depois, clique em Nova novamente.",
      );
      return;
    }
    setError("");
    setQuickAddTipo(tipo);
    setShowQuickAddModal(true);
  };

  const fecharQuickAdd = () => {
    setShowQuickAddModal(false);
    setQuickAddTipo(null);
  };

  const handleQuickAddSuccess = (novoItem) => {
    if (quickAddTipo === "especie") {
      setEspecies((prev) => {
        const semDuplicar = prev.filter((especie) => especie.id !== novoItem.id);
        return [...semDuplicar, novoItem].sort((a, b) => a.nome.localeCompare(b.nome));
      });
      setFormData((prev) => ({ ...prev, especie: novoItem.id.toString(), raca: "" }));
      loadEspecies();
    } else if (quickAddTipo === "raca") {
      const especieId = novoItem.especie_id || formData.especie;
      if (especieId) {
        setRacas((prev) => {
          const semDuplicar = prev.filter((raca) => raca.id !== novoItem.id);
          return [...semDuplicar, novoItem].sort((a, b) => a.nome.localeCompare(b.nome));
        });
        setFormData((prev) => ({ ...prev, raca: novoItem.nome }));
        loadRacasPorEspecie(especieId);
      }
    }
  };

  const validateForm = () => {
    if (!formData.nome.trim()) {
      setError("Nome do pet é obrigatório");
      return false;
    }
    if (!formData.especie) {
      setError("Espécie é obrigatória");
      return false;
    }
    if (!formData.cliente_id) {
      setError("Cliente (tutor) é obrigatório");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!validateForm()) {
      return;
    }

    try {
      setSaving(true);

      // Converter ID da espécie para nome (já que o backend espera nome)
      const especieSelecionada = especies.find((e) => e.id === parseInt(formData.especie));

      // Preparar dados para envio
      const dataToSend = {
        ...formData,
        especie: especieSelecionada?.nome || formData.especie,
        cliente_id: parseInt(formData.cliente_id),
        peso: formData.peso ? parseFloat(formData.peso) : null,
        idade_aproximada: formData.idade_aproximada ? parseInt(formData.idade_aproximada) : null,
        data_nascimento: formData.data_nascimento || null,
        alergias_lista: textareaToList(formData.alergias),
        condicoes_cronicas_lista: textareaToList(formData.doencas_cronicas),
        medicamentos_continuos_lista: textareaToList(formData.medicamentos_continuos),
        restricoes_alimentares_lista: textareaToList(formData.restricoes_alimentares),
        castrado_data: formData.castrado_data || null,
      };

      if (isEditing) {
        await api.put(`/pets/${petId}`, dataToSend);
        setSuccess("Pet atualizado com sucesso!");
        setTimeout(() => navigate(`/pets/${petId}`), 1500);
      } else {
        const response = await api.post("/pets", dataToSend);
        const tutorSelecionado = clientes.find(
          (cliente) => String(cliente.id) === String(dataToSend.cliente_id),
        );
        const petCriado = {
          id: response.data?.id,
          nome: dataToSend.nome,
          cliente_id: dataToSend.cliente_id,
          cliente_nome: tutorSelecionado?.nome || tutorNomeFromQuery || "",
        };

        if (returnTo) {
          setSuccess("Pet cadastrado com sucesso! Voltando ao atendimento...");
          setTimeout(
            () => navigate(buildReturnWithNovoPet(returnTo, petCriado), { replace: true }),
            600,
          );
        } else {
          setSuccess("Pet cadastrado com sucesso!");
          setTimeout(() => navigate(`/pets/${response.data.id}`), 1500);
        }
      }
    } catch (err) {
      console.error("Erro ao salvar pet:", err);
      setError(err.response?.data?.detail || "Erro ao salvar pet");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PetFormView
      loading={loading}
      isEditing={isEditing}
      returnTo={returnTo}
      navigate={navigate}
      petId={petId}
      error={error}
      success={success}
      clienteIdPreSelecionado={clienteIdPreSelecionado}
      handleSubmit={handleSubmit}
      formData={formData}
      handleChange={handleChange}
      clientes={clientes}
      abrirQuickAdd={abrirQuickAdd}
      especies={especies}
      racas={racas}
      especieSelecionadaAtual={especieSelecionadaAtual}
      setFormData={setFormData}
      saving={saving}
      showQuickAddModal={showQuickAddModal}
      quickAddTipo={quickAddTipo}
      handleQuickAddSuccess={handleQuickAddSuccess}
      fecharQuickAdd={fecharQuickAdd}
    />
  );
};

export default PetForm;
