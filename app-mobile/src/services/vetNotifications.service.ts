import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { VetAgendamento, VetProcedimentoAgenda, VetResumo } from "./vet.service";

const SOURCE = "app-vet";
const CHANNEL_ID = "vet-reminders";

async function ensurePermission(): Promise<boolean> {
  const current = await Notifications.getPermissionsAsync();
  if (current.status === "granted") return true;
  const requested = await Notifications.requestPermissionsAsync();
  return requested.status === "granted";
}

async function ensureChannel() {
  if (Platform.OS !== "android") return;
  await Notifications.setNotificationChannelAsync(CHANNEL_ID, {
    name: "Lembretes veterinarios",
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 350, 250, 350],
    lightColor: "#0F5F66",
  });
}

async function cancelPreviousVetNotifications() {
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  await Promise.all(
    scheduled
      .filter((item) => item.content.data?.source === SOURCE)
      .map((item) => Notifications.cancelScheduledNotificationAsync(item.identifier)),
  );
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function scheduleAt(
  date: Date,
  title: string,
  body: string,
  data: Record<string, string | number | null | undefined>,
) {
  if (date.getTime() <= Date.now() + 30_000) return Promise.resolve();
  return Notifications.scheduleNotificationAsync({
    content: {
      title,
      body,
      sound: true,
      data: { ...data, source: SOURCE },
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DATE,
      date,
      channelId: CHANNEL_ID,
    },
  });
}

function agendaReminderDate(agendamento: VetAgendamento): Date | null {
  const date = parseDate(agendamento.data_hora);
  if (!date) return null;
  return new Date(date.getTime() - 10 * 60 * 1000);
}

function procedimentoReminderDate(item: VetProcedimentoAgenda): Date | null {
  return parseDate(item.horario_agendado || item.horario);
}

export async function sincronizarLembretesVet(resumo: VetResumo): Promise<number> {
  const allowed = await ensurePermission();
  if (!allowed) return 0;

  await ensureChannel();
  await cancelPreviousVetNotifications();

  const jobs: Promise<string | void>[] = [];

  resumo.agendamentos_hoje.forEach((item) => {
    const reminderDate = agendaReminderDate(item);
    if (!reminderDate) return;
    jobs.push(
      scheduleAt(
        reminderDate,
        "Consulta em 10 minutos",
        `${item.pet_nome || `Pet #${item.pet_id}`} - ${item.tipo || "consulta"}`,
        { kind: "agendamento", id: item.id, pet_id: item.pet_id },
      ),
    );
  });

  resumo.procedimentos_pendentes.forEach((item) => {
    const reminderDate = procedimentoReminderDate(item);
    if (!reminderDate) return;
    jobs.push(
      scheduleAt(
        reminderDate,
        "Cuidado veterinario agora",
        `${item.medicamento} - ${item.pet_nome}`,
        { kind: "procedimento", id: item.id, pet_id: item.pet_id, internacao_id: item.internacao_id },
      ),
    );
  });

  await Promise.all(jobs);
  return jobs.length;
}

