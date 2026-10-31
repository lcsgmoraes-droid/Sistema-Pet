import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  FiCheckCircle,
  FiChevronDown,
  FiChevronUp,
  FiFileText,
  FiRefreshCw,
  FiXCircle,
} from "react-icons/fi";
import { api } from "../../services/api";

function StatusChip({ conectado }) {
  if (conectado) {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2.5 py-1 rounded-full">
        <FiCheckCircle size={12} /> Conectado
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-xs font-medium text-gray-600 bg-gray-100 px-2.5 py-1 rounded-full">
      <FiXCircle size={12} /> Nao conectado
    </span>
  );
}

StatusChip.propTypes = {
  conectado: PropTypes.bool.isRequired,
};

async function getConfigComFallback() {
  try {
    const { data } = await api.get("/sefaz/config");
    return data;
  } catch (error_) {
    console.warn("Falha em /sefaz/config, tentando endpoint legado /sefaz/status-config", error_);
    const { data } = await api.get("/sefaz/status-config");
    return data;
  }
}

function emailDestinoValido(valor) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(valor || "").trim());
}

function dataEmSaoPaulo(valor) {
  if (typeof valor === "string" && /^\d{4}-\d{2}-\d{2}$/.test(valor)) return valor;
  const data = valor ? new Date(valor) : new Date();
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(Number.isNaN(data.getTime()) ? new Date() : data);
  const parte = (tipo) => partes.find((item) => item.type === tipo)?.value;
  return `${parte("year")}-${parte("month")}-${parte("day")}`;
}

export default function SefazIntegracaoCard({ modoModal = false, onStatusChange }) {
  const [expandido, setExpandido] = useState(false);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState("");
  const [arquivoCertificado, setArquivoCertificado] = useState(null);
  const [statusEntrega, setStatusEntrega] = useState(null);

  const [status, setStatus] = useState({
    enabled: false,
    cert_ok: false,
    cert_existe: false,
    cert_senha_configurada: false,
    encaminhamento_email_ativo: false,
    encaminhamento_email_destino: "",
    encaminhamento_inicio_em: dataEmSaoPaulo(),
    mensagem: "",
  });

  const [form, setForm] = useState({
    enabled: false,
    modo: "mock",
    ambiente: "homologacao",
    uf: "SP",
    cnpj: "",
    cert_password: "",
    importacao_automatica: false,
    importacao_intervalo_min: 15,
    encaminhamento_email_ativo: false,
    encaminhamento_email_destino: "",
    encaminhamento_inicio_em: dataEmSaoPaulo(),
  });

  useEffect(() => {
    carregar();
  }, []);

  function atualizarCampo(campo, valor) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  async function carregar() {
    try {
      setLoading(true);
      const data = await getConfigComFallback();

      setForm((prev) => ({
        ...prev,
        enabled: Boolean(data.enabled),
        modo: data.modo || "mock",
        ambiente: data.ambiente || "homologacao",
        uf: data.uf || data.empresa?.uf || "SP",
        cnpj: data.cnpj || data.empresa?.cnpj || "",
        importacao_automatica: Boolean(data.importacao_automatica),
        importacao_intervalo_min: data.importacao_intervalo_min || 15,
        encaminhamento_email_ativo: Boolean(data.encaminhamento_email_ativo),
        encaminhamento_email_destino: data.encaminhamento_email_destino || "",
        encaminhamento_inicio_em: dataEmSaoPaulo(data.encaminhamento_inicio_em),
      }));

      setStatus({
        enabled: Boolean(data.enabled),
        cert_ok: Boolean(data.cert_ok),
        cert_existe: Boolean(data.cert_existe),
        cert_senha_configurada: Boolean(data.cert_senha_configurada),
        encaminhamento_email_ativo: Boolean(data.encaminhamento_email_ativo),
        encaminhamento_email_destino: data.encaminhamento_email_destino || "",
        encaminhamento_inicio_em: dataEmSaoPaulo(data.encaminhamento_inicio_em),
        mensagem: data.mensagem || "",
      });

      if (onStatusChange) {
        onStatusChange({
          enabled: Boolean(data.enabled),
          cert_ok: Boolean(data.cert_ok),
          mensagem: data.mensagem || "",
        });
      }

      try {
        const { data: entrega } = await api.get("/sefaz/encaminhamento-status");
        setStatusEntrega(entrega);
      } catch {
        setStatusEntrega(null);
      }
    } catch (err) {
      setStatusEntrega(null);
      setMensagem(
        err?.response?.data?.detail || "Nao foi possivel carregar configuracao da SEFAZ.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function salvar(e) {
    e.preventDefault();
    setMensagem("");

    const destinoEmail = form.encaminhamento_email_destino.trim();
    if (destinoEmail && !emailDestinoValido(destinoEmail)) {
      setMensagem("Informe um e-mail válido para o encaminhamento dos XMLs.");
      return;
    }
    if (form.encaminhamento_email_ativo && !destinoEmail) {
      setMensagem("Informe o e-mail do escritório antes de ativar o encaminhamento.");
      return;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(form.encaminhamento_inicio_em)) {
      setMensagem("Informe a data inicial dos XMLs que serão encaminhados.");
      return;
    }

    try {
      setSalvando(true);

      // Primeiro salva configuracao base. Assim o backend ja recebe enabled/modo/ambiente corretos.
      await api.post("/sefaz/config", {
        enabled: form.enabled,
        modo: form.modo,
        ambiente: form.ambiente,
        uf: form.uf,
        cnpj: form.cnpj,
        cert_password: form.cert_password || undefined,
        importacao_automatica: form.importacao_automatica,
        importacao_intervalo_min: Number(form.importacao_intervalo_min || 15),
        encaminhamento_email_ativo: form.encaminhamento_email_ativo,
        encaminhamento_email_destino: destinoEmail,
        encaminhamento_inicio_em: form.encaminhamento_inicio_em,
      });

      if (arquivoCertificado) {
        if (!form.cert_password) {
          setMensagem("Informe a senha do certificado para fazer upload.");
          return;
        }

        const fd = new FormData();
        fd.append("file", arquivoCertificado);
        fd.append("cert_password", form.cert_password);
        await api.post("/sefaz/upload-certificado", fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      setMensagem("Configuracao SEFAZ salva com sucesso.");
      setArquivoCertificado(null);
      await carregar();
    } catch (err) {
      const detalhe = err?.response?.data?.detail;
      setMensagem(
        detalhe
          ? `Não foi possível salvar a configuração SEFAZ: ${detalhe}`
          : "Erro ao salvar configuracao da SEFAZ.",
      );
    } finally {
      setSalvando(false);
    }
  }

  function aplicarPresetSefazSP() {
    setForm((prev) => ({
      ...prev,
      uf: "SP",
      modo: "real",
      ambiente: "producao",
      enabled: true,
    }));
    setMensagem("Preset SEFAZ SP aplicado. Agora confira CNPJ, senha e certificado A1 (.pfx).");
  }

  const integradoPronto = status.cert_ok && form.enabled;
  const alteracaoEncaminhamentoPendente =
    status.encaminhamento_email_ativo &&
    (form.encaminhamento_email_destino.trim() !== status.encaminhamento_email_destino ||
      form.encaminhamento_inicio_em !== status.encaminhamento_inicio_em);

  const header = (
    <div className="bg-gray-50 border-b px-5 py-4 flex items-center justify-between">
      <div>
        <h2 className="font-semibold text-gray-800 flex items-center gap-2">
          <FiFileText className="text-indigo-600" />
          SEFAZ - NF-e
        </h2>
        <p className="text-sm text-gray-500">
          Certificado digital A1 e parametros da consulta fiscal.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <StatusChip conectado={status.cert_ok && status.enabled} />
        {!modoModal && (
          <button
            type="button"
            className="text-gray-500 hover:text-gray-700"
            onClick={() => setExpandido((v) => !v)}
            aria-label="Expandir configuracao SEFAZ"
          >
            {expandido ? <FiChevronUp size={18} /> : <FiChevronDown size={18} />}
          </button>
        )}
      </div>
    </div>
  );

  const body = (
    <form onSubmit={salvar} className="p-5 space-y-4">
      <input
        type="text"
        name="username"
        autoComplete="username"
        value="sefaz"
        readOnly
        className="hidden"
        tabIndex={-1}
        aria-hidden="true"
      />

      {integradoPronto ? (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          Integração ativa e validada. Para rotina de importação diária, use as telas NF Entrada
          (SEFAZ) e NF Saída (SEFAZ).
        </div>
      ) : (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <strong>Configuração rápida para SEFAZ SP</strong>
            <button
              type="button"
              onClick={aplicarPresetSefazSP}
              className="text-xs font-medium px-2.5 py-1 rounded bg-sky-100 hover:bg-sky-200 text-sky-800"
            >
              Aplicar padrão SP
            </button>
          </div>
          <p className="text-xs text-sky-800">
            Passos: 1) UF=SP, Modo=Real, Ambiente=Produção. 2) Informar CNPJ. 3) Informar senha e
            anexar certificado .pfx. 4) Salvar configuração.
          </p>
        </div>
      )}

      {loading ? (
        <div className="text-sm text-gray-500 flex items-center gap-2">
          <FiRefreshCw className="animate-spin" /> Carregando configuracao...
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="sefaz-cnpj" className="block text-sm font-medium text-gray-700 mb-1">
                CNPJ
              </label>
              <input
                id="sefaz-cnpj"
                type="text"
                autoComplete="off"
                value={form.cnpj}
                onChange={(e) =>
                  atualizarCampo("cnpj", e.target.value.replaceAll(/\D/g, "").slice(0, 14))
                }
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Somente numeros"
              />
            </div>

            <div>
              <label htmlFor="sefaz-uf" className="block text-sm font-medium text-gray-700 mb-1">
                UF
              </label>
              <input
                id="sefaz-uf"
                type="text"
                autoComplete="address-level1"
                value={form.uf}
                onChange={(e) => atualizarCampo("uf", e.target.value.toUpperCase().slice(0, 2))}
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="SP"
              />
            </div>

            <div>
              <label htmlFor="sefaz-modo" className="block text-sm font-medium text-gray-700 mb-1">
                Modo
              </label>
              <select
                id="sefaz-modo"
                value={form.modo}
                onChange={(e) => atualizarCampo("modo", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                <option value="mock">Mock (simulado)</option>
                <option value="real">Real (SEFAZ)</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="sefaz-ambiente"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Ambiente
              </label>
              <select
                id="sefaz-ambiente"
                value={form.ambiente}
                onChange={(e) => atualizarCampo("ambiente", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              >
                <option value="homologacao">Homologacao</option>
                <option value="producao">Producao</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="sefaz-password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Senha do certificado
              </label>
              <input
                id="sefaz-password"
                type="password"
                autoComplete="current-password"
                value={form.cert_password}
                onChange={(e) => atualizarCampo("cert_password", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Senha do .pfx"
              />
            </div>

            <div>
              <label htmlFor="sefaz-cert" className="block text-sm font-medium text-gray-700 mb-1">
                Certificado A1 (.pfx)
              </label>
              <input
                id="sefaz-cert"
                type="file"
                accept=".pfx"
                onChange={(e) => setArquivoCertificado(e.target.files?.[0] || null)}
                className="w-full border rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => atualizarCampo("enabled", e.target.checked)}
            />
            <span>Habilitar SEFAZ para esta empresa</span>
          </label>

          <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div>
              <h3 className="text-sm font-semibold text-gray-800">
                Encaminhar XMLs ao escritório de contabilidade
              </h3>
              <p className="mt-1 text-xs text-gray-600">
                Informe o endereço confirmado pelo escritório. O CorePet encaminha apenas o XML
                completo das NF-e de entrada destinadas a este CNPJ, após a captura e validação do
                XML. Mesmo se a importação da compra falhar, o XML válido pode ser enviado. Resumos
                de notas ainda sem XML completo não são enviados.
              </p>
            </div>

            <div>
              <label
                htmlFor="sefaz-email-contabilidade"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                E-mail para receber os XMLs
              </label>
              <input
                id="sefaz-email-contabilidade"
                type="email"
                autoComplete="email"
                inputMode="email"
                maxLength={254}
                value={form.encaminhamento_email_destino}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    encaminhamento_email_destino: e.target.value,
                    // Trocar o destinatário exige desativar o envio antes de salvar.
                    encaminhamento_email_ativo: false,
                  }))
                }
                className="w-full border rounded-lg px-3 py-2 text-sm"
                placeholder="Confirme o endereço com o escritório"
                aria-describedby="sefaz-email-contabilidade-ajuda"
              />
            </div>

            <div>
              <label
                htmlFor="sefaz-encaminhamento-inicio"
                className="mb-1 block text-sm font-medium text-gray-700"
              >
                Encaminhar XMLs capturados desde
              </label>
              <input
                id="sefaz-encaminhamento-inicio"
                type="date"
                max={dataEmSaoPaulo()}
                value={form.encaminhamento_inicio_em}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    encaminhamento_inicio_em: e.target.value,
                    encaminhamento_email_ativo: false,
                  }))
                }
                className="w-full border rounded-lg px-3 py-2 text-sm sm:w-auto"
                aria-describedby="sefaz-encaminhamento-inicio-ajuda"
              />
              <p id="sefaz-encaminhamento-inicio-ajuda" className="mt-1 text-xs text-gray-600">
                São encaminhados os XMLs completos capturados pelo CorePet a partir dessa data. A
                data não recupera XMLs de notas que ainda não estejam no CorePet.
              </p>
            </div>

            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.encaminhamento_email_ativo}
                disabled={
                  !emailDestinoValido(form.encaminhamento_email_destino) ||
                  alteracaoEncaminhamentoPendente
                }
                onChange={(e) => atualizarCampo("encaminhamento_email_ativo", e.target.checked)}
              />
              <span>Ativar envio automático para este e-mail</span>
            </label>
            <p id="sefaz-email-contabilidade-ajuda" className="text-xs text-amber-800">
              Combine primeiro com o escritório a troca do coletor de notas e o endereço de entrega.
              Ao trocar o e-mail ou a data, salve com o envio desligado e depois reative. A
              importação automática das notas é configurada separadamente na Central NF-e Entradas.
            </p>

            <div className="grid grid-cols-2 gap-2 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700 sm:grid-cols-4">
              <div>
                Enviados: <strong>{statusEntrega?.enviados ?? "-"}</strong>
              </div>
              <div>
                Pendentes: <strong>{statusEntrega?.pendentes ?? "-"}</strong>
              </div>
              <div>
                Falhas: <strong>{statusEntrega?.falhas ?? "-"}</strong>
              </div>
              <div>
                Servidor de e-mail:{" "}
                <strong>
                  {statusEntrega ? (statusEntrega.smtp_configurado ? "pronto" : "pendente") : "-"}
                </strong>
              </div>
            </div>
            {!statusEntrega && (
              <p className="text-xs text-gray-600">
                Ainda não foi possível consultar o estado dos envios.
              </p>
            )}
          </div>

          <div className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-1">
            <div>Certificado encontrado: {status.cert_existe ? "Sim" : "Nao"}</div>
            <div>Senha configurada: {status.cert_senha_configurada ? "Sim" : "Nao"}</div>
            <div>Validacao do certificado: {status.cert_ok ? "OK" : "Pendente/Erro"}</div>
            <div>Mensagem: {status.mensagem || "-"}</div>
          </div>

          {mensagem && (
            <div className="text-sm bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-700">
              {mensagem}
            </div>
          )}

          <button
            type="submit"
            disabled={salvando}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white px-4 py-2 rounded-lg text-sm font-medium"
          >
            {salvando ? "Salvando..." : "Salvar configuracao"}
          </button>
        </>
      )}
    </form>
  );

  if (modoModal) {
    return (
      <section className="border rounded-xl overflow-hidden">
        {header}
        {body}
      </section>
    );
  }

  return (
    <section className="border rounded-xl overflow-hidden">
      {header}

      {expandido && body}
    </section>
  );
}

SefazIntegracaoCard.propTypes = {
  modoModal: PropTypes.bool,
  onStatusChange: PropTypes.func,
};
