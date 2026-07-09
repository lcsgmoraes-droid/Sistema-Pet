import api from './api';

export type AppNotification = {
  id: number;
  title: string;
  body: string;
  source: string;
  kind: string;
  data: Record<string, unknown>;
  read_at?: string | null;
  created_at?: string | null;
  delivered_at?: string | null;
  is_read?: boolean;
};

export type AppNotificationsResponse = {
  items: AppNotification[];
  unread_count: number;
};

export async function listarNotificacoesApp(): Promise<AppNotificationsResponse> {
  const { data } = await api.get('/app/notificacoes');
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    unread_count: Number(data?.unread_count ?? 0),
  };
}

export async function markNotificationAsRead(id: number): Promise<AppNotification> {
  const { data } = await api.post(`/app/notificacoes/${id}/lida`);
  return data;
}

export async function limparNotificacoesApp(): Promise<{ cleared: number }> {
  const { data } = await api.delete('/app/notificacoes');
  return { cleared: Number(data?.cleared ?? 0) };
}
