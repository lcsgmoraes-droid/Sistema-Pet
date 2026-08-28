import { useFocusEffect } from "@react-navigation/native";
import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  criarAgendamentoBanhoTosaFuncionario,
  FuncionarioBanhoTosaAgendamento,
  FuncionarioBanhoTosaApoios,
  FuncionarioBanhoTosaAtendimento,
  listarAgendaBanhoTosaFuncionario,
  listarApoiosBanhoTosaFuncionario,
  listarFilaBanhoTosaFuncionario,
  moverEtapaBanhoTosaFuncionario,
  realizarCheckinBanhoTosaFuncionario,
} from "../../services/funcionarioBanhoTosa.service";
import {
  FuncionarioBanhoTosaAgenda,
  FuncionarioBanhoTosaFila,
} from "./banho-tosa/FuncionarioBanhoTosaContent";
import {
  NovoAgendamentoBanhoTosaModal,
  NovoAgendamentoForm,
  TransicaoBanhoTosaForm,
  TransicaoBanhoTosaModal,
} from "./banho-tosa/FuncionarioBanhoTosaModals";
import { styles } from "./banho-tosa/FuncionarioBanhoTosaStyles";
import {
  addDays,
  addMonths,
  agruparAgenda,
  BanhoTosaAgendaModo,
  ETAPAS_COM_TIMER,
  isoDate,
  mensagemErroApi,
  periodoAgenda,
} from "./banho-tosa/FuncionarioBanhoTosaUtils";

const APOIOS_VAZIOS: FuncionarioBanhoTosaApoios = {
  fluxo_etapas: ["chegou", "banho", "secagem", "tosa", "pronto"],
  funcionario_id: 0,
  funcionarios: [],
  recursos: [],
  servicos: [],
  pets: [],
};

function novoForm(data = isoDate(new Date())): NovoAgendamentoForm {
  return {
    pet_id: "",
    data,
    hora: "08:00",
    servico_id: "",
    recurso_id: "",
    valor: "0,00",
    observacoes: "",
  };
}

export default function FuncionarioBanhoTosaScreen() {
  const [aba, setAba] = useState<"agenda" | "fila">("agenda");
  const [modo, setModo] = useState<BanhoTosaAgendaModo>("dia");
  const [referencia, setReferencia] = useState(() => new Date());
  const [agenda, setAgenda] = useState<FuncionarioBanhoTosaAgendamento[]>([]);
  const [fila, setFila] = useState<FuncionarioBanhoTosaAtendimento[]>([]);
  const [apoios, setApoios] = useState(APOIOS_VAZIOS);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [salvandoId, setSalvandoId] = useState<number | null>(null);
  const [modalAgenda, setModalAgenda] = useState(false);
  const [salvandoAgenda, setSalvandoAgenda] = useState(false);
  const [formAgenda, setFormAgenda] = useState(() => novoForm());
  const [transicao, setTransicao] = useState<FuncionarioBanhoTosaAtendimento | null>(null);
  const [formTransicao, setFormTransicao] = useState<TransicaoBanhoTosaForm>({
    responsavel_id: "",
    recurso_id: "",
    observacoes: "",
  });
  const [etapaSelecionada, setEtapaSelecionada] = useState("chegou");
  const periodo = useMemo(() => periodoAgenda(modo, referencia), [modo, referencia]);
  const grupos = useMemo(() => agruparAgenda(agenda), [agenda]);
  const periodoKey = JSON.stringify(periodo.params);

  const carregarOperacao = useCallback(
    async (mostrarErro = true) => {
      try {
        const [agendaAtual, filaAtual] = await Promise.all([
          listarAgendaBanhoTosaFuncionario(periodo.params),
          listarFilaBanhoTosaFuncionario(),
        ]);
        setAgenda(agendaAtual);
        setFila(filaAtual);
      } catch (error) {
        if (mostrarErro) {
          Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel atualizar o banho e tosa."));
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [periodoKey],
  );

  useFocusEffect(
    useCallback(() => {
      void Promise.all([
        carregarOperacao(false),
        listarApoiosBanhoTosaFuncionario()
          .then((data) => {
            setApoios(data);
            setEtapaSelecionada((atual) =>
              data.fluxo_etapas.includes(atual) ? atual : data.fluxo_etapas[0] || "chegou",
            );
          })
          .catch(() => undefined),
      ]);
      const timer = setInterval(() => void carregarOperacao(false), 30000);
      return () => clearInterval(timer);
    }, [carregarOperacao]),
  );

  function navegar(delta: number) {
    setLoading(true);
    setReferencia((atual) =>
      modo === "mes" ? addMonths(atual, delta) : addDays(atual, modo === "semana" ? delta * 7 : delta),
    );
  }

  function atualizar() {
    setRefreshing(true);
    void carregarOperacao();
  }

  function abrirNovoHorario() {
    setFormAgenda(novoForm(isoDate(referencia)));
    setModalAgenda(true);
  }

  function atualizarFormAgenda(campo: keyof NovoAgendamentoForm, valor: string) {
    setFormAgenda((atual) => ({ ...atual, [campo]: valor }));
  }

  async function salvarAgendamento() {
    const pet = apoios.pets.find((item) => String(item.id) === formAgenda.pet_id);
    const servico = apoios.servicos.find((item) => String(item.id) === formAgenda.servico_id);
    if (!pet || !servico) {
      Alert.alert("Dados do agendamento", "Selecione o pet e o servico.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(formAgenda.data) || !/^\d{2}:\d{2}$/.test(formAgenda.hora)) {
      Alert.alert("Data e hora", "Informe no formato AAAA-MM-DD e HH:MM.");
      return;
    }
    const valor = Number(formAgenda.valor.replace(/\./g, "").replace(",", "."));
    if (!Number.isFinite(valor) || valor < 0) {
      Alert.alert("Valor", "Informe um valor previsto valido.");
      return;
    }

    setSalvandoAgenda(true);
    try {
      await criarAgendamentoBanhoTosaFuncionario({
        cliente_id: pet.cliente_id,
        pet_id: pet.id,
        data_hora_inicio: `${formAgenda.data}T${formAgenda.hora}:00`,
        recurso_id: formAgenda.recurso_id ? Number(formAgenda.recurso_id) : null,
        origem: "app_funcionario",
        observacoes: formAgenda.observacoes.trim() || null,
        valor_previsto: valor,
        servicos: [
          {
            servico_id: servico.id,
            nome_servico: servico.nome,
            quantidade: 1,
            valor_unitario: valor,
            tempo_previsto_minutos: servico.duracao_padrao_minutos,
          },
        ],
      });
      setReferencia(new Date(`${formAgenda.data}T12:00:00`));
      setModo("dia");
      setModalAgenda(false);
      await carregarOperacao();
    } catch (error) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel criar o agendamento."));
    } finally {
      setSalvandoAgenda(false);
    }
  }

  async function fazerCheckin(item: FuncionarioBanhoTosaAgendamento) {
    setSalvandoId(item.id);
    try {
      await realizarCheckinBanhoTosaFuncionario(item.id);
      setAba("fila");
      setEtapaSelecionada("chegou");
      await carregarOperacao();
    } catch (error) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel fazer o check-in."));
    } finally {
      setSalvandoId(null);
    }
  }

  function prepararAvanco(item: FuncionarioBanhoTosaAtendimento) {
    const proxima = item.proxima_etapa_codigo;
    if (!proxima) return;
    if (!ETAPAS_COM_TIMER.has(proxima)) {
      void confirmarAvancoDireto(item);
      return;
    }
    const etapaAberta = item.etapas.find((etapa) => etapa.inicio_em && !etapa.fim_em);
    setFormTransicao({
      responsavel_id: String(apoios.funcionario_id || etapaAberta?.responsavel_id || ""),
      recurso_id: String(etapaAberta?.recurso_id || ""),
      observacoes: "",
    });
    setTransicao(item);
  }

  async function confirmarAvancoDireto(item: FuncionarioBanhoTosaAtendimento) {
    if (!item.proxima_etapa_codigo) return;
    setSalvandoId(item.id);
    try {
      await moverEtapaBanhoTosaFuncionario(item.id, {
        tipo: item.proxima_etapa_codigo,
        iniciar_timer: false,
        finalizar_etapa_atual: true,
      });
      await carregarOperacao();
    } catch (error) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel avancar a etapa."));
    } finally {
      setSalvandoId(null);
    }
  }

  async function confirmarTransicao() {
    if (!transicao?.proxima_etapa_codigo) return;
    setSalvandoId(transicao.id);
    try {
      await moverEtapaBanhoTosaFuncionario(transicao.id, {
        tipo: transicao.proxima_etapa_codigo,
        iniciar_timer: true,
        finalizar_etapa_atual: true,
        responsavel_id: formTransicao.responsavel_id ? Number(formTransicao.responsavel_id) : null,
        recurso_id: formTransicao.recurso_id ? Number(formTransicao.recurso_id) : null,
        observacoes: formTransicao.observacoes.trim() || null,
      });
      setEtapaSelecionada(transicao.proxima_etapa_codigo);
      setTransicao(null);
      await carregarOperacao();
    } catch (error) {
      Alert.alert("Erro", mensagemErroApi(error, "Nao foi possivel iniciar a etapa."));
    } finally {
      setSalvandoId(null);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0F766E" />
        <Text style={styles.loadingText}>Carregando operacao...</Text>
      </View>
    );
  }

  return (
    <>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={atualizar} />}
      >
        <View style={styles.hero}>
          <Text style={styles.heroEyebrow}>OPERACAO DO DIA</Text>
          <Text style={styles.heroTitle}>Banho & Tosa</Text>
          <Text style={styles.heroText}>Agenda, check-in e andamento dos pets no mesmo lugar.</Text>
        </View>

        <View style={styles.tabs}>
          {(["agenda", "fila"] as const).map((item) => (
            <TouchableOpacity
              key={item}
              style={[styles.tab, aba === item && styles.tabActive]}
              onPress={() => setAba(item)}
            >
              <Text style={[styles.tabText, aba === item && styles.tabTextActive]}>
                {item === "agenda" ? `Agenda (${agenda.length})` : `Fila (${fila.length})`}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {aba === "agenda" ? (
          <FuncionarioBanhoTosaAgenda
            modo={modo}
            periodoTitulo={periodo.titulo}
            grupos={grupos}
            salvandoId={salvandoId}
            onChangeModo={(value) => {
              setLoading(true);
              setModo(value);
            }}
            onNavigate={navegar}
            onNovo={abrirNovoHorario}
            onCheckin={fazerCheckin}
          />
        ) : (
          <FuncionarioBanhoTosaFila
            itens={fila}
            fluxo={apoios.fluxo_etapas.length ? apoios.fluxo_etapas : APOIOS_VAZIOS.fluxo_etapas}
            etapaSelecionada={etapaSelecionada}
            salvandoId={salvandoId}
            onEtapaSelecionada={setEtapaSelecionada}
            onAvancar={prepararAvanco}
          />
        )}
      </ScrollView>

      <NovoAgendamentoBanhoTosaModal
        visible={modalAgenda}
        form={formAgenda}
        pets={apoios.pets}
        servicos={apoios.servicos}
        recursos={apoios.recursos}
        salvando={salvandoAgenda}
        onClose={() => setModalAgenda(false)}
        onChange={atualizarFormAgenda}
        onSelectServico={(servico) =>
          setFormAgenda((atual) => ({
            ...atual,
            servico_id: String(servico.id),
            valor: Number(servico.preco_base || 0).toLocaleString("pt-BR", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            }),
          }))
        }
        onSalvar={salvarAgendamento}
      />

      <TransicaoBanhoTosaModal
        atendimento={transicao}
        form={formTransicao}
        funcionarios={apoios.funcionarios}
        recursos={apoios.recursos}
        salvando={Boolean(transicao && salvandoId === transicao.id)}
        onClose={() => setTransicao(null)}
        onChange={(campo, valor) => setFormTransicao((atual) => ({ ...atual, [campo]: valor }))}
        onConfirmar={confirmarTransicao}
      />
    </>
  );
}
