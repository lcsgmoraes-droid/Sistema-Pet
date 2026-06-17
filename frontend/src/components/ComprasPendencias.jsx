import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock, Mail, RefreshCw, Send, X } from "lucide-react";
import { toast } from "react-hot-toast";
import api from "../api";
import FornecedorSelector, { getFornecedorNome } from "./fornecedores/FornecedorSelector";
import ActionButton from "./ui/ActionButton";
import ExportActionButton from "./ui/ExportActionButton";
import FornecedorIdentity from "./ui/FornecedorIdentity";

const STATUS_META = {
  aberta: { label: "Aberta", cls: "bg-blue-50 text-blue-700 border-blue-200" },
  aguardando_fornecedor: {
    label: "Aguardando fornecedor",
    cls: "bg-amber-50 text-amber-700 border-amber-200",
  },
  em_tratativa: { label: "Em tratativa", cls: "bg-purple-50 text-purple-700 border-purple-200" },
  resolvida: { label: "Resolvida", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  cancelada: { label: "Cancelada", cls: "bg-slate-100 text-slate-600 border-slate-200" },
};

function formatarData(valor, comHora = false) {
  if (!valor) return "-";
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return "-";
  return data.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    ...(comHora ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

function formatarMoeda(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatarQtd(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  });
}

function baixarBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default function ComprasPendencias() {
  const [pendencias, setPendencias] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [statusFiltro, setStatusFiltro] = useState("ativas");
  const [fornecedorFiltro, setFornecedorFiltro] = useState("");
  const [detalhe, setDetalhe] = useState(null);
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [emailConfigurado, setEmailConfigurado] = useState(false);
  const [emailForm, setEmailForm] = useState({
    email_destinatario: "",
    email_assunto: "",
    email_mensagem: "",
  });
  const [observacao, setObservacao] = useState("");

  const resumo = useMemo(() => {
    return pendencias.reduce(
      (acc, item) => {
        acc.total += 1;
        if (!["resolvida", "cancelada"].includes(item.status)) acc.ativas += 1;
        acc.valor += Number(item.resumo_numerico?.valor_estimado || 0);
        return acc;
      },
      { total: 0, ativas: 0, valor: 0 },
    );
  }, [pendencias]);

  async function carregarPendencias() {
    setCarregando(true);
    try {
      const params = {};
      if (statusFiltro === "ativas") {
        params.incluir_finalizadas = false;
      } else if (statusFiltro !== "todas") {
        params.status = statusFiltro;
      }
      if (fornecedorFiltro.trim()) {
        params.fornecedor = fornecedorFiltro.trim();
      }
      const { data } = await api.get("/compras-pendencias/", { params });
      setPendencias(Array.isArray(data) ? data : []);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao carregar pendencias");
    } finally {
      setCarregando(false);
    }
  }

  async function carregarStatusEnvio() {
    try {
      const { data } = await api.get("/compras-pendencias/envio/status");
      setEmailConfigurado(Boolean(data?.email_configurado));
    } catch {
      setEmailConfigurado(false);
    }
  }

  async function abrirDetalhe(id) {
    setCarregandoDetalhe(true);
    try {
      const { data } = await api.get(`/compras-pendencias/${id}`);
      setDetalhe(data);
      setEmailForm({
        email_destinatario: data.email_destinatario || "",
        email_assunto: data.email_assunto || "",
        email_mensagem: data.email_mensagem || "",
      });
      setObservacao("");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao abrir pendencia");
    } finally {
      setCarregandoDetalhe(false);
    }
  }

  async function recarregarDetalhe() {
    if (!detalhe?.id) return;
    await abrirDetalhe(detalhe.id);
    await carregarPendencias();
  }

  async function baixarPdf(pendencia = detalhe) {
    if (!pendencia?.id) return;
    try {
      const { data } = await api.get(`/compras-pendencias/${pendencia.id}/pdf`, {
        responseType: "blob",
      });
      baixarBlob(data, `pendencia_fornecedor_${pendencia.codigo || pendencia.id}.pdf`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao gerar PDF");
    }
  }

  async function copiarMensagem() {
    if (!emailForm.email_mensagem?.trim()) {
      toast.error("Nao ha mensagem para copiar.");
      return;
    }
    await navigator.clipboard.writeText(emailForm.email_mensagem);
    toast.success("Mensagem copiada");
  }

  async function registrarEmail() {
    if (!detalhe?.id) return;
    setSalvando(true);
    try {
      await api.post(`/compras-pendencias/${detalhe.id}/registrar-email`, {
        ...emailForm,
        observacao: observacao || "Envio ao fornecedor registrado pela tela de pendencias.",
      });
      toast.success("Contato registrado");
      await recarregarDetalhe();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao registrar contato");
    } finally {
      setSalvando(false);
    }
  }

  async function enviarEmail() {
    if (!detalhe?.id) return;
    if (!emailConfigurado) {
      toast.error("Envio automatico ainda nao esta configurado no servidor.");
      return;
    }
    setSalvando(true);
    try {
      await api.post(`/compras-pendencias/${detalhe.id}/enviar-email`, {
        ...emailForm,
        observacao: observacao || "E-mail enviado ao fornecedor pela tela de pendencias.",
      });
      toast.success("E-mail enviado ao fornecedor");
      await recarregarDetalhe();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao enviar e-mail");
    } finally {
      setSalvando(false);
    }
  }

  async function atualizarStatus(status, resolucao = null) {
    if (!detalhe?.id) return;
    setSalvando(true);
    try {
      await api.patch(`/compras-pendencias/${detalhe.id}`, {
        status,
        observacao: observacao || null,
        resolucao_observacao: resolucao || observacao || null,
      });
      toast.success("Pendencia atualizada");
      await recarregarDetalhe();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erro ao atualizar pendencia");
    } finally {
      setSalvando(false);
    }
  }

  useEffect(() => {
    carregarStatusEnvio();
    carregarPendencias();
  }, [statusFiltro]);

  const statusOptions = [
    ["ativas", "Ativas"],
    ["todas", "Todas"],
    ["aberta", "Aberta"],
    ["aguardando_fornecedor", "Aguardando"],
    ["em_tratativa", "Tratativa"],
    ["resolvida", "Resolvida"],
    ["cancelada", "Cancelada"],
  ];

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-7xl space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Compras</p>
            <h1 className="text-2xl font-bold text-slate-900">Pendencias de fornecedor</h1>
            <p className="text-sm text-slate-600">
              Acompanhe divergencias de NF, contato com fornecedor e resolucao.
            </p>
          </div>
          <ActionButton
            icon={RefreshCw}
            intent="edit"
            tone="soft"
            onClick={carregarPendencias}
            loading={carregando}
          >
            Atualizar
          </ActionButton>
        </div>

        <section className="grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Pendencias</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{resumo.total}</p>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-xs font-semibold uppercase text-amber-700">Ativas</p>
            <p className="mt-1 text-2xl font-bold text-amber-800">{resumo.ativas}</p>
          </div>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-xs font-semibold uppercase text-emerald-700">Valor estimado</p>
            <p className="mt-1 text-2xl font-bold text-emerald-800">
              {formatarMoeda(resumo.valor)}
            </p>
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <div className="flex flex-wrap gap-2">
              {statusOptions.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setStatusFiltro(value)}
                  className={`rounded-md px-3 py-2 text-sm font-semibold transition-colors ${
                    statusFiltro === value
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="ml-auto flex min-w-[280px] flex-1 items-center gap-2 lg:max-w-md">
              <FornecedorSelector
                value={fornecedorFiltro}
                showLabel={false}
                placeholder="Buscar fornecedor..."
                className="flex-1"
                inputClassName="rounded-md border-slate-300"
                onInputChange={setFornecedorFiltro}
                onKeyDown={(event) => {
                  if (event.key === "Enter") carregarPendencias();
                }}
                onSelect={(fornecedor) => setFornecedorFiltro(getFornecedorNome(fornecedor))}
                onClear={() => setFornecedorFiltro("")}
                onFornecedorCriado={(fornecedor) =>
                  setFornecedorFiltro(getFornecedorNome(fornecedor))
                }
              />
              <ActionButton intent="edit" tone="soft" onClick={carregarPendencias}>
                Filtrar
              </ActionButton>
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">Pendencia</th>
                  <th className="px-4 py-3 text-left">Fornecedor</th>
                  <th className="px-4 py-3 text-left">NF / Pedido</th>
                  <th className="px-4 py-3 text-right">Divergencia</th>
                  <th className="px-4 py-3 text-center">Status</th>
                  <th className="px-4 py-3 text-right">Acoes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pendencias.map((item) => {
                  const meta = STATUS_META[item.status] || STATUS_META.aberta;
                  return (
                    <tr key={item.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">
                          {item.codigo || `#${item.id}`}
                        </div>
                        <div className="text-xs text-slate-500">{item.titulo}</div>
                        <div className="mt-1 text-xs text-slate-400">
                          Criada em {formatarData(item.created_at, true)}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <FornecedorIdentity
                          document={item.fornecedor_cnpj}
                          nameClassName="font-medium text-slate-900"
                          record={item}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div>NF {item.numero_nota || "-"}</div>
                        <div className="text-xs text-slate-500">
                          Pedido {item.numero_pedido || "-"}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="font-semibold text-slate-900">
                          {formatarMoeda(item.resumo_numerico?.valor_estimado)}
                        </div>
                        <div className="text-xs text-slate-500">
                          {formatarQtd(item.resumo_numerico?.faltante)} falta /{" "}
                          {formatarQtd(item.resumo_numerico?.avariada)} avaria
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${meta.cls}`}
                        >
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <ExportActionButton
                            type="pdf"
                            tone="soft"
                            onClick={() => baixarPdf(item)}
                          >
                            PDF
                          </ExportActionButton>
                          <ActionButton
                            intent="edit"
                            tone="soft"
                            onClick={() => abrirDetalhe(item.id)}
                            loading={carregandoDetalhe}
                          >
                            Abrir
                          </ActionButton>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {!carregando && pendencias.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                      Nenhuma pendencia encontrada.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {detalhe && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="max-h-[92vh] w-full max-w-5xl overflow-hidden rounded-xl bg-white shadow-xl">
            <div className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
                  {detalhe.codigo}
                </p>
                <h2 className="text-xl font-bold text-slate-900">{detalhe.titulo}</h2>
                <p className="text-sm text-slate-600">
                  NF {detalhe.numero_nota || "-"} | Pedido {detalhe.numero_pedido || "-"} |{" "}
                  <FornecedorIdentity
                    document={detalhe.fornecedor_cnpj}
                    layout="inline"
                    nameClassName="font-medium text-slate-700"
                    record={detalhe}
                  />
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDetalhe(null)}
                className="rounded-md p-2 text-slate-500 hover:bg-slate-100"
              >
                <X size={18} />
              </button>
            </div>

            <div className="max-h-[calc(92vh-84px)] overflow-y-auto p-5">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Status</p>
                  <p className="mt-1 font-bold text-slate-900">
                    {STATUS_META[detalhe.status]?.label || detalhe.status}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Prazo</p>
                  <p className="mt-1 font-bold text-slate-900">
                    {formatarData(detalhe.prazo_previsto)}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Email enviado</p>
                  <p className="mt-1 font-bold text-slate-900">
                    {formatarData(detalhe.email_enviado_em, true)}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold uppercase text-slate-500">Valor estimado</p>
                  <p className="mt-1 font-bold text-slate-900">
                    {formatarMoeda(detalhe.resumo_numerico?.valor_estimado)}
                  </p>
                </div>
              </div>

              <div className="mt-5 grid gap-5 lg:grid-cols-[1.3fr_0.9fr]">
                <section className="rounded-lg border border-slate-200">
                  <div className="border-b border-slate-200 px-4 py-3">
                    <h3 className="font-bold text-slate-900">Itens divergentes</h3>
                    <p className="text-sm text-slate-500">{detalhe.resumo}</p>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {(detalhe.itens || []).map((item) => (
                      <div key={item.id} className="p-4">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="font-semibold text-slate-900">{item.descricao}</div>
                            <div className="text-xs text-slate-500">
                              Codigo: {item.codigo_produto || "-"}
                            </div>
                          </div>
                          <span className="rounded-full bg-orange-50 px-2 py-1 text-xs font-semibold text-orange-700">
                            {item.status_conferencia}
                          </span>
                        </div>
                        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-5">
                          <div>
                            NF: <b>{formatarQtd(item.quantidade_nf)}</b>
                          </div>
                          <div>
                            Recebida: <b>{formatarQtd(item.quantidade_recebida)}</b>
                          </div>
                          <div>
                            Falta:{" "}
                            <b className="text-red-600">{formatarQtd(item.quantidade_faltante)}</b>
                          </div>
                          <div>
                            Avaria:{" "}
                            <b className="text-orange-600">
                              {formatarQtd(item.quantidade_avariada)}
                            </b>
                          </div>
                          <div>
                            Valor: <b>{formatarMoeda(item.valor_total_divergente)}</b>
                          </div>
                        </div>
                        {item.observacao && (
                          <p className="mt-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
                            {item.observacao}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>

                <section className="space-y-4">
                  <div className="rounded-lg border border-slate-200 p-4">
                    <h3 className="font-bold text-slate-900">Contato com fornecedor</h3>
                    <label className="mt-3 block text-xs font-semibold uppercase text-slate-500">
                      Destinatario
                    </label>
                    <input
                      value={emailForm.email_destinatario}
                      onChange={(event) =>
                        setEmailForm((prev) => ({
                          ...prev,
                          email_destinatario: event.target.value,
                        }))
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                      placeholder="email@fornecedor.com"
                    />
                    <label className="mt-3 block text-xs font-semibold uppercase text-slate-500">
                      Assunto
                    </label>
                    <input
                      value={emailForm.email_assunto}
                      onChange={(event) =>
                        setEmailForm((prev) => ({ ...prev, email_assunto: event.target.value }))
                      }
                      className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    />
                    <label className="mt-3 block text-xs font-semibold uppercase text-slate-500">
                      Mensagem
                    </label>
                    <textarea
                      value={emailForm.email_mensagem}
                      onChange={(event) =>
                        setEmailForm((prev) => ({ ...prev, email_mensagem: event.target.value }))
                      }
                      className="mt-1 h-48 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    />
                    <label className="mt-3 block text-xs font-semibold uppercase text-slate-500">
                      Observacao / retorno
                    </label>
                    <textarea
                      value={observacao}
                      onChange={(event) => setObservacao(event.target.value)}
                      className="mt-1 h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                      placeholder="Ex.: fornecedor ficou de repor na proxima entrega..."
                    />
                    <div className="mt-4 flex flex-wrap gap-2">
                      <ExportActionButton type="pdf" tone="soft" onClick={() => baixarPdf(detalhe)}>
                        PDF
                      </ExportActionButton>
                      <ActionButton
                        icon={Send}
                        intent="create"
                        tone={emailConfigurado ? "solid" : "soft"}
                        onClick={enviarEmail}
                        loading={salvando}
                        disabled={!emailConfigurado}
                        title={
                          emailConfigurado
                            ? "Enviar e-mail com PDF anexado"
                            : "Configure SMTP para envio automatico"
                        }
                      >
                        Enviar e-mail
                      </ActionButton>
                      <ActionButton icon={Mail} intent="edit" tone="soft" onClick={copiarMensagem}>
                        Copiar texto
                      </ActionButton>
                      <ActionButton
                        icon={Clock}
                        intent="edit"
                        onClick={registrarEmail}
                        loading={salvando}
                      >
                        Registrar manual
                      </ActionButton>
                    </div>
                    {!emailConfigurado && (
                      <p className="mt-2 text-xs text-slate-500">
                        Envio automatico indisponivel. Use Copiar texto e Registrar manual ate
                        configurar SMTP.
                      </p>
                    )}
                  </div>

                  <div className="rounded-lg border border-slate-200 p-4">
                    <h3 className="font-bold text-slate-900">Resolucao</h3>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <ActionButton
                        icon={Clock}
                        intent="edit"
                        tone="soft"
                        onClick={() => atualizarStatus("em_tratativa")}
                      >
                        Em tratativa
                      </ActionButton>
                      <ActionButton
                        icon={CheckCircle2}
                        intent="create"
                        onClick={() => atualizarStatus("resolvida", observacao)}
                        loading={salvando}
                      >
                        Marcar resolvida
                      </ActionButton>
                      <ActionButton
                        intent="delete"
                        tone="soft"
                        onClick={() => atualizarStatus("cancelada")}
                        loading={salvando}
                      >
                        Cancelar
                      </ActionButton>
                    </div>
                  </div>

                  <div className="rounded-lg border border-slate-200 p-4">
                    <h3 className="font-bold text-slate-900">Historico</h3>
                    <div className="mt-3 space-y-3">
                      {(detalhe.historico || []).map((item) => (
                        <div key={item.id} className="rounded-md bg-slate-50 p-3 text-sm">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-slate-900">{item.tipo}</span>
                            <span className="text-xs text-slate-500">
                              {formatarData(item.created_at, true)}
                            </span>
                          </div>
                          {item.observacao && (
                            <p className="mt-1 text-slate-600">{item.observacao}</p>
                          )}
                          {item.status_novo && (
                            <p className="mt-1 text-xs text-slate-500">
                              {item.status_anterior || "-"} {"->"} {item.status_novo}
                            </p>
                          )}
                        </div>
                      ))}
                      {(detalhe.historico || []).length === 0 && (
                        <p className="text-sm text-slate-500">Sem historico registrado.</p>
                      )}
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
