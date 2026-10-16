import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { HeartPulse, PawPrint, Ruler } from "lucide-react";
import toast from "react-hot-toast";
import api from "../api";
import PetFormView from "./petForm/PetFormView";
import { buildReturnWithNovoPet } from "../utils/petReturnFlow";

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

const normalizarNomeEspecie = (nome = "") =>
  nome
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLocaleLowerCase("pt-BR");

const grupoNomeEspecie = (nome) => {
  const normalizado = normalizarNomeEspecie(nome);
  if (["cao", "caes", "cachorro", "cachorros", "canino", "canina"].includes(normalizado)) {
    return "canina";
  }
  if (["gato", "gatos", "felino", "felina"].includes(normalizado)) return "felina";
  return normalizado;
};

const encontrarEspecieCadastrada = (lista, nome) =>
  lista.find((especie) => normalizarNomeEspecie(especie.nome) === normalizarNomeEspecie(nome)) ||
  lista.find((especie) => grupoNomeEspecie(especie.nome) === grupoNomeEspecie(nome));

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

  // Comeca true (nao false): evita o formulario renderizar vazio por um instante antes
  // do primeiro carregamento comecar — ver nota sobre o padrao de loading unico no AGENTS.md.
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [clientes, setClientes] = useState([]);
  const [especies, setEspecies] = useState([]);
  const [racas, setRacas] = useState([]);
  const [especieOriginal, setEspecieOriginal] = useState("");
  const [especieAlterada, setEspecieAlterada] = useState(false);

  const [abaAtiva, setAbaAtiva] = useState("dados-gerais");

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

  // Um unico ciclo de loading cobrindo tutores + especies + pet (quando editando), em vez de um
  // por chamada: evita o formulario "piscar" entre vazio/carregando varias vezes seguidas antes
  // dos dados finais aparecerem. A flag `ativo` protege contra o StrictMode do React, que em dev
  // roda este efeito duas vezes de proposito (para flagar efeitos com side effect mal limpos) —
  // sem ela, a segunda rodada reacende o loading por um instante mesmo com os dados ja na tela.
  useEffect(() => {
    let ativo = true;

    const loadData = async () => {
      setLoading(true);
      try {
        const clientesCarregados = await loadClientes(() => ativo);
        if (!ativo) return;
        const especiesCarregadas = await loadEspecies(() => ativo);
        if (ativo && isEditing) {
          await loadPet(especiesCarregadas, clientesCarregados, () => ativo);
        }
      } finally {
        if (ativo) setLoading(false);
      }
    };
    loadData();

    return () => {
      ativo = false;
    };
  }, [petId]);

  // Carregar raças quando espécie mudar
  useEffect(() => {
    if (formData.especie) {
      loadRacasPorEspecie(formData.especie);
    } else {
      setRacas([]);
    }
  }, [formData.especie]);

  const loadClientes = async (deveAplicar = () => true) => {
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
      if (deveAplicar()) setClientes(clientesUnicos);
      return clientesUnicos;
    } catch (err) {
      console.error("Erro ao carregar clientes:", err);
      if (deveAplicar()) setClientes([]);
      return [];
    }
  };

  const loadEspecies = async (deveAplicar = () => true) => {
    try {
      const response = await api.get("/cadastros/especies", { params: { ativo: true } });
      if (deveAplicar()) setEspecies(response.data);
      return response.data;
    } catch (err) {
      console.error("Erro ao carregar espécies:", err);
      return [];
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

  const loadPet = async (especiesCarregadas, clientesCarregados, deveAplicar) => {
    try {
      const response = await api.get(`/pets/${petId}`);
      const pet = response.data;
      if (!deveAplicar()) return;

      if (
        pet.cliente_id &&
        !clientesCarregados.some((cliente) => String(cliente.id) === String(pet.cliente_id))
      ) {
        try {
          const responseTutor = await api.get(`/clientes/${pet.cliente_id}`);
          if (deveAplicar() && responseTutor.data?.id) {
            setClientes((atuais) => [
              responseTutor.data,
              ...atuais.filter((cliente) => String(cliente.id) !== String(pet.cliente_id)),
            ]);
          }
        } catch (erroTutor) {
          console.warn("Não foi possível carregar o tutor do pet:", erroTutor);
        }
      }
      if (!deveAplicar()) return;

      // A lista vem da resposta desta carga, sem depender do estado do render anterior.
      // Cadastros antigos também usam Cão/Cachorro e Gato no lugar de Canina/Felina.
      const especieEncontrada = encontrarEspecieCadastrada(especiesCarregadas, pet.especie);
      setEspecieOriginal(pet.especie || "");
      setEspecieAlterada(false);

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
      if (deveAplicar()) setError("Erro ao carregar informações do pet");
    }
  };

  const setField = (name) => (value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleEspecieChange = (value) => {
    setEspecieAlterada(true);
    setFormData((prev) => ({ ...prev, especie: value, raca: "" }));
  };

  // Desmarcar "castrado" limpa a data de castracao escondida — evita submeter uma
  // data de castracao presa no estado enquanto o pet nao esta mais marcado como castrado.
  const handleCastradoChange = (castrado) => {
    setFormData((prev) => ({
      ...prev,
      castrado,
      castrado_data: castrado ? prev.castrado_data : "",
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
      setEspecieAlterada(true);
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

  const erros = useMemo(() => {
    const proximosErros = {};
    if (!formData.nome.trim()) proximosErros.nome = "Informe o nome do pet.";
    if (!formData.especie) proximosErros.especie = "Selecione a espécie.";
    if (!formData.cliente_id) proximosErros.cliente_id = "Selecione o tutor.";
    return proximosErros;
  }, [formData.nome, formData.especie, formData.cliente_id]);

  const abas = useMemo(
    () => [
      {
        id: "dados-gerais",
        label: "Dados gerais",
        icon: PawPrint,
        descricao: "Tutor, identificação e observações",
        invalida: Boolean(erros.nome || erros.especie || erros.cliente_id),
      },
      {
        id: "caracteristicas",
        label: "Características físicas",
        icon: Ruler,
        descricao: "Idade, peso, porte e demais características",
      },
      {
        id: "saude",
        label: "Saúde",
        icon: HeartPulse,
        descricao: "Alergias, doenças, medicamentos e histórico clínico",
      },
    ],
    [erros],
  );

  const handleSubmit = async () => {
    setError("");
    setSuccess("");

    if (Object.keys(erros).length > 0) {
      setAbaAtiva((atual) => {
        const abaComErro = abas.find((aba) => aba.invalida);
        return abaComErro ? abaComErro.id : atual;
      });
      toast.error("Corrija os campos destacados antes de salvar.");
      return;
    }

    try {
      setSaving(true);

      // Converter ID da espécie para nome (já que o backend espera nome)
      const especieSelecionada = especies.find((e) => e.id === parseInt(formData.especie));

      // Preparar dados para envio
      const dataToSend = {
        ...formData,
        // Resolver um alias ao carregar não é uma alteração solicitada pelo usuário.
        especie:
          isEditing && !especieAlterada && especieOriginal
            ? especieOriginal
            : especieSelecionada?.nome || formData.especie,
        cliente_id: parseInt(formData.cliente_id),
        peso: formData.peso ? parseFloat(String(formData.peso).replace(",", ".")) : null,
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
        setEspecieOriginal(dataToSend.especie);
        setEspecieAlterada(false);
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
      erros={erros}
      setField={setField}
      handleEspecieChange={handleEspecieChange}
      handleCastradoChange={handleCastradoChange}
      clientes={clientes}
      abrirQuickAdd={abrirQuickAdd}
      especies={especies}
      racas={racas}
      especieSelecionadaAtual={especieSelecionadaAtual}
      setFormData={setFormData}
      saving={saving}
      abaAtiva={abaAtiva}
      setAbaAtiva={setAbaAtiva}
      abas={abas}
      showQuickAddModal={showQuickAddModal}
      quickAddTipo={quickAddTipo}
      handleQuickAddSuccess={handleQuickAddSuccess}
      fecharQuickAdd={fecharQuickAdd}
    />
  );
};

export default PetForm;
