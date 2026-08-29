import { Ionicons } from "@expo/vector-icons";
import React from "react";
import { Image, ScrollView, Text, TouchableOpacity, View } from "react-native";
import {
  FuncionarioBanhoTosaAgendamento,
  FuncionarioBanhoTosaAtendimento,
} from "../../../services/funcionarioBanhoTosa.service";
import { resolveTenantAssetUrl } from "../../../store/tenant.store";
import { formatarMoeda } from "../../../utils/format";
import { styles } from "./FuncionarioBanhoTosaStyles";
import {
  AgendaGrupo,
  BanhoTosaAgendaModo,
  formatarData,
  formatarHora,
  formatarTempo,
  itensDaEtapa,
  labelEtapa,
  statusAgendamentoLabel,
} from "./FuncionarioBanhoTosaUtils";

type AgendaProps = {
  modo: BanhoTosaAgendaModo;
  periodoTitulo: string;
  grupos: AgendaGrupo[];
  salvandoId?: number | null;
  onChangeModo: (modo: BanhoTosaAgendaModo) => void;
  onNavigate: (delta: number) => void;
  onNovo: () => void;
  onCheckin: (item: FuncionarioBanhoTosaAgendamento) => void;
};

export function FuncionarioBanhoTosaAgenda({
  modo,
  periodoTitulo,
  grupos,
  salvandoId,
  onChangeModo,
  onNavigate,
  onNovo,
  onCheckin,
}: AgendaProps) {
  const total = grupos.reduce((soma, grupo) => soma + grupo.itens.length, 0);
  return (
    <>
      <View style={styles.toolbar}>
        <View style={styles.headerRow}>
          <Text style={styles.title}>Agenda da equipe</Text>
          <TouchableOpacity style={styles.primaryButton} onPress={onNovo}>
            <Text style={styles.primaryButtonText}>Novo horario</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.segment}>
          {(["dia", "semana", "mes"] as BanhoTosaAgendaModo[]).map((item) => (
            <TouchableOpacity
              key={item}
              style={[styles.segmentButton, modo === item && styles.segmentButtonActive]}
              onPress={() => onChangeModo(item)}
            >
              <Text style={[styles.segmentText, modo === item && styles.segmentTextActive]}>
                {item === "dia" ? "Dia" : item === "semana" ? "Semana" : "Mes"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.navRow}>
          <TouchableOpacity style={styles.navButton} onPress={() => onNavigate(-1)}>
            <Text style={styles.navText}>Anterior</Text>
          </TouchableOpacity>
          <Text style={styles.periodTitle}>{periodoTitulo}</Text>
          <TouchableOpacity style={styles.navButton} onPress={() => onNavigate(1)}>
            <Text style={styles.navText}>Proximo</Text>
          </TouchableOpacity>
        </View>
      </View>

      {grupos.map((grupo) => (
        <View key={grupo.data}>
          <Text style={styles.dayTitle}>{formatarData(grupo.itens[0]?.data_hora_inicio)}</Text>
          {grupo.itens.map((item) => (
            <AgendaCard
              key={item.id}
              item={item}
              salvando={salvandoId === item.id}
              onCheckin={onCheckin}
            />
          ))}
        </View>
      ))}

      {!total && (
        <View style={styles.empty}>
          <Ionicons name="calendar-outline" size={34} color="#94A3B8" />
          <Text style={styles.emptyTitle}>Nenhum pet neste periodo</Text>
          <Text style={styles.emptyText}>Use “Novo horario” para incluir o primeiro agendamento.</Text>
        </View>
      )}
    </>
  );
}

function AgendaCard({
  item,
  salvando,
  onCheckin,
}: {
  item: FuncionarioBanhoTosaAgendamento;
  salvando: boolean;
  onCheckin: (item: FuncionarioBanhoTosaAgendamento) => void;
}) {
  const permiteCheckin = ["agendado", "confirmado"].includes(item.status);
  const servicos = item.servicos?.map((servico) => servico.nome_servico_snapshot).join(" • ");
  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={styles.petIdentity}>
          <PetPhoto name={item.pet_nome} url={item.pet_foto_url} />
          <View style={styles.petIdentityText}>
            <Text style={styles.cardPet}>
              {formatarHora(item.data_hora_inicio)} · {item.pet_nome || `Pet #${item.pet_id}`}
            </Text>
            <Text style={styles.cardTutor}>{item.cliente_nome || "Tutor nao informado"}</Text>
          </View>
        </View>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{statusAgendamentoLabel(item.status)}</Text>
        </View>
      </View>
      <Text style={styles.services}>{servicos || "Servico avulso"}</Text>
      <Text style={styles.meta}>
        {item.recurso_nome || "Sem box definido"}
        {item.taxi_dog_id ? " · Taxi Dog" : ""}
      </Text>
      {item.observacoes ? <Text style={styles.meta}>Obs.: {item.observacoes}</Text> : null}
      <View style={styles.cardActions}>
        <Text style={styles.amount}>{formatarMoeda(Number(item.valor_previsto || 0))}</Text>
        {permiteCheckin ? (
          <TouchableOpacity
            disabled={salvando}
            style={[styles.secondaryButton, salvando && styles.primaryButtonDisabled]}
            onPress={() => onCheckin(item)}
          >
            <Text style={styles.secondaryButtonText}>{salvando ? "Entrando..." : "Fazer check-in"}</Text>
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

type FilaProps = {
  itens: FuncionarioBanhoTosaAtendimento[];
  fluxo: string[];
  etapaSelecionada: string;
  salvandoId?: number | null;
  onEtapaSelecionada: (etapa: string) => void;
  onAvancar: (item: FuncionarioBanhoTosaAtendimento) => void;
};

export function FuncionarioBanhoTosaFila({
  itens,
  fluxo,
  etapaSelecionada,
  salvandoId,
  onEtapaSelecionada,
  onAvancar,
}: FilaProps) {
  const visiveis = itensDaEtapa(itens, etapaSelecionada);
  const atrasados = itens.filter((item) => item.atrasado).length;
  return (
    <>
      <View style={styles.toolbar}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>Fila em tempo real</Text>
            <Text style={styles.meta}>
              {itens.length} pet(s) em andamento · {atrasados} atrasado(s)
            </Text>
          </View>
          <View style={[styles.badge, atrasados > 0 && styles.badgeAlert]}>
            <Text style={[styles.badgeText, atrasados > 0 && styles.badgeAlertText]}>
              {atrasados > 0 ? `${atrasados} alerta(s)` : "No ritmo"}
            </Text>
          </View>
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.stageScroll}>
          {fluxo.map((etapa) => {
            const ativa = etapa === etapaSelecionada;
            const total = itensDaEtapa(itens, etapa).length;
            return (
              <TouchableOpacity
                key={etapa}
                style={[styles.stageChip, ativa && styles.stageChipActive]}
                onPress={() => onEtapaSelecionada(etapa)}
              >
                <Text style={[styles.stageChipText, ativa && styles.stageChipTextActive]}>
                  {labelEtapa(etapa)} {total}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {visiveis.map((item) => (
        <FilaCard
          key={item.id}
          item={item}
          salvando={salvandoId === item.id}
          onAvancar={onAvancar}
        />
      ))}

      {!visiveis.length && (
        <View style={styles.empty}>
          <Ionicons name="paw-outline" size={34} color="#94A3B8" />
          <Text style={styles.emptyTitle}>Nenhum pet em {labelEtapa(etapaSelecionada)}</Text>
          <Text style={styles.emptyText}>As mudancas feitas no ERP aparecem aqui ao atualizar.</Text>
        </View>
      )}
    </>
  );
}

function FilaCard({
  item,
  salvando,
  onAvancar,
}: {
  item: FuncionarioBanhoTosaAtendimento;
  salvando: boolean;
  onAvancar: (item: FuncionarioBanhoTosaAtendimento) => void;
}) {
  const etapaAberta = item.etapas?.find((etapa) => etapa.inicio_em && !etapa.fim_em);
  const alertas = Object.values(item.restricoes_veterinarias_snapshot || {})
    .flatMap((value) => (Array.isArray(value) ? value : value ? [value] : []))
    .filter(Boolean);
  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={styles.petIdentity}>
          <PetPhoto name={item.pet_nome} url={item.pet_foto_url} />
          <View style={styles.petIdentityText}>
            <Text style={styles.cardPet}>{item.pet_nome || `Pet #${item.pet_id}`}</Text>
            <Text style={styles.cardTutor}>{item.cliente_nome || "Tutor nao informado"}</Text>
          </View>
        </View>
        <View style={[styles.badge, item.atrasado && styles.badgeAlert]}>
          <Text style={[styles.badgeText, item.atrasado && styles.badgeAlertText]}>
            {item.etapa_atual_label || labelEtapa(item.etapa_atual_codigo)}
          </Text>
        </View>
      </View>
      <Text style={styles.meta}>
        Chegou {formatarHora(item.checkin_em)} · {item.pet_porte || "porte nao informado"}
      </Text>
      {etapaAberta ? (
        <View style={styles.timerRow}>
          <Ionicons name="time-outline" size={17} color={item.atrasado ? "#B91C1C" : "#64748B"} />
          <Text style={[styles.timerText, item.atrasado && styles.timerAlert]}>
            {etapaAberta.responsavel_nome || "Sem responsavel"} · {formatarTempo(item.tempo_decorrido_segundos)}
            {item.atrasado ? ` · atraso ${formatarTempo(item.atraso_segundos)}` : ""}
          </Text>
        </View>
      ) : null}
      {alertas.length ? (
        <View style={styles.warningBox}>
          <Text style={styles.warningText}>Atencao veterinaria: {alertas.join(" · ")}</Text>
        </View>
      ) : null}
      {item.observacoes_entrada ? <Text style={styles.meta}>Obs.: {item.observacoes_entrada}</Text> : null}
      {item.proxima_etapa_codigo ? (
        <View style={styles.cardActions}>
          <Text style={styles.meta}>Proximo passo</Text>
          <TouchableOpacity
            disabled={salvando}
            style={[styles.primaryButton, salvando && styles.primaryButtonDisabled]}
            onPress={() => onAvancar(item)}
          >
            <Text style={styles.primaryButtonText}>
              {salvando
                ? "Atualizando..."
                : `${item.pet_nome || "Pet"} → ${item.proxima_etapa_label || labelEtapa(item.proxima_etapa_codigo)}`}
            </Text>
          </TouchableOpacity>
        </View>
      ) : (
        <Text style={styles.meta}>Pronto para fechamento e entrega no ERP.</Text>
      )}
    </View>
  );
}

function PetPhoto({ name, url }: { name?: string | null; url?: string | null }) {
  const imageUrl = resolveTenantAssetUrl(url);
  return (
    <View style={styles.petPhotoFrame} accessibilityLabel={`Foto de ${name || "pet"}`}>
      {imageUrl ? (
        <Image source={{ uri: imageUrl }} style={styles.petPhoto} resizeMode="cover" />
      ) : (
        <Ionicons name="paw" size={24} color="#64748B" />
      )}
    </View>
  );
}
