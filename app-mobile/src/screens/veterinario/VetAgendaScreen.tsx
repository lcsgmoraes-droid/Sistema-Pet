import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useMemo, useState } from "react";
import { Alert } from "react-native";

import {
  criarAgendamentoVet,
  listarAgendamentosVet,
  listarConsultoriosVet,
  listarPetsVet,
  VetAgendamento,
  VetConsultorio,
  VetPetResumo,
} from "../../services/vet.service";
import { VetAgendaAppointmentModal } from "./vet-agenda/VetAgendaAppointmentModal";
import { VetAgendaContent } from "./vet-agenda/VetAgendaContent";
import {
  addDays,
  addMonths,
  AgendaModo,
  dataDoAgendamento,
  dataReferenciaModal,
  dateFromIso,
  formInicialAgendamento,
  gerarCalendarioDias,
  gerarHorariosBase,
  horaDoAgendamento,
  isoDate,
  mensagemErroApi,
  MIN_CARACTERES_BUSCA_PET,
  periodoAgenda,
  VetAgendaField,
  VetAgendaGroup,
} from "./vet-agenda/VetAgendaUtils";

export default function VetAgendaScreen() {
  const [itens, setItens] = useState<VetAgendamento[]>([]);
  const [pets, setPets] = useState<VetPetResumo[]>([]);
  const [consultorios, setConsultorios] = useState<VetConsultorio[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modo, setModo] = useState<AgendaModo>("dia");
  const [referencia, setReferencia] = useState(() => new Date());
  const [modalAberto, setModalAberto] = useState(false);
  const [buscaPet, setBuscaPet] = useState("");
  const [salvandoNovo, setSalvandoNovo] = useState(false);
  const [carregandoApoios, setCarregandoApoios] = useState(false);
  const [form, setForm] = useState(() => formInicialAgendamento());
  const [calendarioAberto, setCalendarioAberto] = useState(false);
  const [calendarioReferencia, setCalendarioReferencia] = useState(
    () => formInicialAgendamento().data,
  );

  const periodo = useMemo(
    () => periodoAgenda(modo, referencia),
    [modo, referencia],
  );
  const horariosBase = useMemo(() => gerarHorariosBase(), []);
  const calendarioDias = useMemo(
    () => gerarCalendarioDias(calendarioReferencia, form.data),
    [calendarioReferencia, form.data],
  );

  const grupos = useMemo<VetAgendaGroup[]>(() => {
    const mapa = new Map<string, VetAgendamento[]>();
    itens.forEach((item) => {
      const chave = item.data_hora
        ? isoDate(new Date(item.data_hora))
        : "sem-data";
      const atuais = mapa.get(chave) || [];
      atuais.push(item);
      mapa.set(chave, atuais);
    });
    return Array.from(mapa.entries()).map(([data, agenda]) => ({
      data,
      agenda,
    }));
  }, [itens]);

  const horariosOcupados = useMemo(() => {
    const ocupados = new Set<string>();
    itens.forEach((item) => {
      if (dataDoAgendamento(item) === form.data) {
        const hora = horaDoAgendamento(item);
        if (hora) ocupados.add(hora);
      }
    });
    return ocupados;
  }, [form.data, itens]);

  const petsFiltrados = useMemo(() => {
    const termo = buscaPet.trim().toLowerCase();
    if (termo.length < MIN_CARACTERES_BUSCA_PET) return [];
    return pets
      .filter((pet) => {
        const texto = [
          pet.nome,
          pet.codigo,
          pet.raca,
          pet.cliente_nome,
          pet.cliente_telefone,
          pet.cliente_celular,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return texto.includes(termo);
      })
      .slice(0, 30);
  }, [buscaPet, pets]);

  const carregar = useCallback(
    async (mostrarErro = true) => {
      try {
        setItens(await listarAgendamentosVet(periodo.params));
      } catch (error) {
        if (mostrarErro)
          Alert.alert(
            "Erro",
            mensagemErroApi(error, "Nao foi possivel carregar a agenda."),
          );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [periodo.params],
  );

  useFocusEffect(
    useCallback(() => {
      carregar(false);
    }, [carregar]),
  );

  function sugerirHorarioLivre(data: string) {
    const ocupados = new Set(
      itens
        .filter((item) => dataDoAgendamento(item) === data)
        .map(horaDoAgendamento)
        .filter(Boolean),
    );
    return (
      horariosBase.find((horario) => !ocupados.has(horario)) ||
      horariosBase[0] ||
      "08:00"
    );
  }

  async function carregarApoiosAgendamento() {
    setCarregandoApoios(true);
    try {
      const [petsDisponiveis, consultoriosDisponiveis] = await Promise.all([
        listarPetsVet(),
        listarConsultoriosVet(),
      ]);
      setPets(petsDisponiveis);
      setConsultorios(consultoriosDisponiveis);
    } catch (error) {
      Alert.alert(
        "Erro",
        mensagemErroApi(
          error,
          "Nao foi possivel carregar pets e consultorios.",
        ),
      );
    } finally {
      setCarregandoApoios(false);
    }
  }

  function abrirModalAgendamento() {
    const data = dataReferenciaModal(referencia);
    setBuscaPet("");
    setForm(formInicialAgendamento(data, sugerirHorarioLivre(data)));
    setCalendarioAberto(false);
    setCalendarioReferencia(data);
    setModalAberto(true);
    carregarApoiosAgendamento();
  }

  function atualizarCampo(campo: VetAgendaField, valor: string) {
    setForm((atual) => {
      if (campo !== "data") return { ...atual, [campo]: valor };
      return { ...atual, data: valor, hora: sugerirHorarioLivre(valor) };
    });
  }

  function abrirCalendario() {
    setCalendarioReferencia(form.data || isoDate(new Date()));
    setCalendarioAberto((aberto) => !aberto);
  }

  function navegarMesCalendario(delta: number) {
    setCalendarioReferencia((atual) =>
      isoDate(addMonths(dateFromIso(atual), delta)),
    );
  }

  function selecionarDataCalendario(data: string) {
    atualizarCampo("data", data);
    setCalendarioReferencia(data);
    setCalendarioAberto(false);
  }

  async function salvarAgendamento() {
    const petId = Number(form.pet_id);
    const duracao = Number(form.duracao_minutos);

    if (!petId) {
      Alert.alert("Pet", "Selecione o pet para agendar a consulta.");
      return;
    }
    if (!form.data || !form.hora) {
      Alert.alert("Data e horario", "Informe data e horario da consulta.");
      return;
    }
    if (!Number.isFinite(duracao) || duracao < 5) {
      Alert.alert("Duracao", "Informe a duracao em minutos.");
      return;
    }

    setSalvandoNovo(true);
    try {
      await criarAgendamentoVet({
        pet_id: petId,
        data_hora: `${form.data}T${form.hora}`,
        duracao_minutos: duracao,
        tipo: "consulta",
        motivo: form.motivo.trim() || null,
        consultorio_id: form.consultorio_id
          ? Number(form.consultorio_id)
          : null,
      });

      const dataSelecionada = new Date(`${form.data}T12:00:00`);
      setModo("dia");
      setReferencia(dataSelecionada);
      setItens(await listarAgendamentosVet({ data: form.data }));
      setModalAberto(false);
    } catch (error) {
      Alert.alert(
        "Erro",
        mensagemErroApi(error, "Nao foi possivel agendar a consulta."),
      );
    } finally {
      setSalvandoNovo(false);
      setLoading(false);
    }
  }

  function navegar(delta: number) {
    setLoading(true);
    setReferencia((atual) => {
      if (modo === "mes") return addMonths(atual, delta);
      return addDays(atual, modo === "semana" ? delta * 7 : delta);
    });
  }

  function atualizarAgenda() {
    setRefreshing(true);
    carregar();
  }

  function alterarModoAgenda(novoModo: AgendaModo) {
    setLoading(true);
    setModo(novoModo);
  }

  return (
    <>
      <VetAgendaContent
        loading={loading}
        refreshing={refreshing}
        modo={modo}
        periodoTitulo={periodo.titulo}
        grupos={grupos}
        totalItens={itens.length}
        onRefresh={atualizarAgenda}
        onOpenAppointment={abrirModalAgendamento}
        onChangeModo={alterarModoAgenda}
        onNavigate={navegar}
      />

      <VetAgendaAppointmentModal
        visible={modalAberto}
        buscaPet={buscaPet}
        form={form}
        consultorios={consultorios}
        petsFiltrados={petsFiltrados}
        carregandoApoios={carregandoApoios}
        calendarioAberto={calendarioAberto}
        calendarioReferencia={calendarioReferencia}
        calendarioDias={calendarioDias}
        horariosBase={horariosBase}
        horariosOcupados={horariosOcupados}
        salvandoNovo={salvandoNovo}
        onClose={() => setModalAberto(false)}
        onBuscaPetChange={setBuscaPet}
        onAtualizarCampo={atualizarCampo}
        onAbrirCalendario={abrirCalendario}
        onNavegarMesCalendario={navegarMesCalendario}
        onSelecionarDataCalendario={selecionarDataCalendario}
        onSalvar={salvarAgendamento}
      />
    </>
  );
}
