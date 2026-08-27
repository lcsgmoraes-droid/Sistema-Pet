import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import {
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  FileDown,
  ImageDown,
  MessageCircle,
  QrCode,
  Smartphone,
  Store,
} from "lucide-react";
import QRCode from "qrcode";
import { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

import { api } from "../../services/api";
import { resolveMediaUrl } from "../../utils/mediaUrl";
import {
  DIVULGACAO_DESTINOS,
  montarLinksDivulgacao,
  nomeArquivoDivulgacao,
} from "./divulgacaoLojaUtils";

const FORMATOS = {
  a4: { label: "Cartaz A4", aspectRatio: "210 / 297" },
  quadrado: { label: "Post quadrado", aspectRatio: "1 / 1" },
  story: { label: "Story", aspectRatio: "9 / 16" },
};

const DESTINO_ICONES = {
  smart: QrCode,
  ecommerce: Store,
  app: Smartphone,
  whatsapp: MessageCircle,
};

function origemPublicaAtual() {
  if (typeof window === "undefined") return "https://corepet.com.br";
  return ["localhost", "127.0.0.1"].includes(window.location.hostname)
    ? "https://corepet.com.br"
    : window.location.origin;
}

function dispararDownload(href, filename) {
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export default function EcommerceDivulgacao() {
  const arteRef = useRef(null);
  const [contexto, setContexto] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [destino, setDestino] = useState("smart");
  const [formato, setFormato] = useState("a4");
  const [telefone, setTelefone] = useState("");
  const [chamada, setChamada] = useState("Tudo para o seu pet, a poucos toques de distância.");
  const [mensagemWhatsApp, setMensagemWhatsApp] = useState(
    "Olá! Encontrei a loja pelo QR Code e gostaria de fazer um pedido.",
  );
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [exportando, setExportando] = useState(false);

  useEffect(() => {
    api
      .get("/ecommerce-aparencia/tenant-context")
      .then(({ data }) => {
        setContexto(data);
        setTelefone(data?.telefone || "");
      })
      .catch((requestError) => {
        setErro(
          requestError?.response?.data?.detail ||
            "Não foi possível carregar as informações públicas da loja.",
        );
      })
      .finally(() => setCarregando(false));
  }, []);

  const links = useMemo(
    () =>
      montarLinksDivulgacao({
        origin: origemPublicaAtual(),
        slug: contexto?.ecommerce_slug,
        telefone,
        mensagem: mensagemWhatsApp,
      }),
    [contexto?.ecommerce_slug, mensagemWhatsApp, telefone],
  );
  const linkAtual = links[destino] || "";

  useEffect(() => {
    let ativo = true;
    setQrDataUrl("");
    if (!linkAtual) return () => {};

    QRCode.toDataURL(linkAtual, {
      width: 640,
      margin: 2,
      errorCorrectionLevel: "H",
      color: { dark: "#0f172a", light: "#ffffff" },
    })
      .then((dataUrl) => {
        if (ativo) setQrDataUrl(dataUrl);
      })
      .catch(() => {
        if (ativo) setErro("Não foi possível gerar este QR Code.");
      });

    return () => {
      ativo = false;
    };
  }, [linkAtual]);

  async function copiarLink() {
    if (!linkAtual) return;
    try {
      await navigator.clipboard.writeText(linkAtual);
      toast.success("Link copiado.");
    } catch {
      toast.error("Não foi possível copiar automaticamente.");
    }
  }

  async function capturarArte() {
    if (!arteRef.current) throw new Error("Arte indisponível");
    return html2canvas(arteRef.current, {
      scale: 3,
      useCORS: true,
      backgroundColor: "#ffffff",
      logging: false,
    });
  }

  async function baixarArtePng() {
    setExportando(true);
    try {
      const canvas = await capturarArte();
      dispararDownload(
        canvas.toDataURL("image/png", 1),
        nomeArquivoDivulgacao(contexto?.name, formato, "png"),
      );
      toast.success("Arte PNG gerada.");
    } catch {
      toast.error("Não foi possível gerar a arte. Confira se o logo está acessível.");
    } finally {
      setExportando(false);
    }
  }

  async function baixarArtePdf() {
    setExportando(true);
    try {
      const canvas = await capturarArte();
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const image = canvas.toDataURL("image/png", 1);
      const margem = 8;
      const larguraDisponivel = 210 - margem * 2;
      const alturaDisponivel = 297 - margem * 2;
      const proporcao = Math.min(
        larguraDisponivel / canvas.width,
        alturaDisponivel / canvas.height,
      );
      const largura = canvas.width * proporcao;
      const altura = canvas.height * proporcao;
      pdf.addImage(image, "PNG", (210 - largura) / 2, (297 - altura) / 2, largura, altura);
      pdf.save(nomeArquivoDivulgacao(contexto?.name, formato, "pdf"));
      toast.success("PDF pronto para impressão gerado.");
    } catch {
      toast.error("Não foi possível gerar o PDF.");
    } finally {
      setExportando(false);
    }
  }

  function baixarQrCode() {
    if (!qrDataUrl) return;
    dispararDownload(qrDataUrl, nomeArquivoDivulgacao(contexto?.name, `qr-${destino}`, "png"));
  }

  if (carregando) {
    return <div className="p-10 text-center text-slate-500">Preparando materiais da loja...</div>;
  }

  if (erro && !contexto) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">{erro}</div>
      </div>
    );
  }

  if (!contexto?.ecommerce_slug) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <h1 className="text-2xl font-bold text-slate-950">Divulgue sua loja</h1>
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
          Defina primeiro o endereço público da loja. Ele será usado para criar QR Codes únicos e
          seguros.
          <div className="mt-4">
            <Link to="/ecommerce/aparencia" className="font-semibold text-indigo-700 underline">
              Configurar endereço da loja
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const corPrimaria = contexto.ecommerce_cor_primaria || "#0f766e";
  const corSecundaria = contexto.ecommerce_cor_secundaria || "#0f172a";
  const logoUrl = resolveMediaUrl(contexto.logo_url);
  const DestinoIcone = DESTINO_ICONES[destino];
  const formatoAtual = FORMATOS[formato];
  const destinoAtual = DIVULGACAO_DESTINOS[destino];
  const qrIndisponivel = !linkAtual;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">
            E-commerce · Marketing local
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950">Divulgue sua loja</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Gere QR Codes e artes prontas para balcão, impressão e redes sociais.
          </p>
        </div>
        <a
          href={links.ecommerce}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 no-underline"
        >
          <ExternalLink size={16} /> Abrir loja pública
        </a>
      </header>

      <div className="grid gap-6 xl:grid-cols-[390px_minmax(0,1fr)]">
        <aside className="space-y-5">
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-bold text-slate-900">1. Escolha o destino</h2>
            <div className="mt-4 grid gap-2">
              {Object.entries(DIVULGACAO_DESTINOS).map(([key, item]) => {
                const Icone = DESTINO_ICONES[key];
                const indisponivel = key === "whatsapp" && !links.whatsapp;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setDestino(key)}
                    disabled={indisponivel}
                    className={`flex items-start gap-3 rounded-lg border p-3 text-left transition ${
                      destino === key
                        ? "border-teal-500 bg-teal-50 ring-2 ring-teal-100"
                        : "border-slate-200 bg-white hover:border-slate-300"
                    } disabled:cursor-not-allowed disabled:opacity-45`}
                  >
                    <Icone size={19} className="mt-0.5 shrink-0 text-teal-700" />
                    <span>
                      <span className="block text-sm font-bold text-slate-900">{item.label}</span>
                      <span className="mt-0.5 block text-xs text-slate-500">{item.descricao}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-bold text-slate-900">2. Personalize a arte</h2>
            <label className="mt-4 block text-sm font-semibold text-slate-700">Formato</label>
            <select
              value={formato}
              onChange={(event) => setFormato(event.target.value)}
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            >
              {Object.entries(FORMATOS).map(([key, item]) => (
                <option key={key} value={key}>
                  {item.label}
                </option>
              ))}
            </select>

            <label className="mt-4 block text-sm font-semibold text-slate-700">Chamada</label>
            <textarea
              value={chamada}
              onChange={(event) => setChamada(event.target.value.slice(0, 110))}
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 p-3 text-sm"
            />

            <label className="mt-4 block text-sm font-semibold text-slate-700">
              Telefone/WhatsApp
            </label>
            <input
              value={telefone}
              onChange={(event) => setTelefone(event.target.value)}
              placeholder="(18) 99999-0000"
              className="mt-1 h-10 w-full rounded-lg border border-slate-300 px-3 text-sm"
            />
            <label className="mt-4 block text-sm font-semibold text-slate-700">
              Mensagem do WhatsApp
            </label>
            <textarea
              value={mensagemWhatsApp}
              onChange={(event) => setMensagemWhatsApp(event.target.value.slice(0, 240))}
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 p-3 text-sm"
            />
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="font-bold text-slate-900">3. Baixe ou compartilhe</h2>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={baixarArtePng}
                disabled={exportando || qrIndisponivel}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-teal-700 px-3 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
              >
                <ImageDown size={17} /> PNG
              </button>
              <button
                type="button"
                onClick={baixarArtePdf}
                disabled={exportando || qrIndisponivel}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-900 px-3 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
              >
                <FileDown size={17} /> PDF
              </button>
              <button
                type="button"
                onClick={baixarQrCode}
                disabled={!qrDataUrl}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50"
              >
                <Download size={17} /> Só o QR
              </button>
              <button
                type="button"
                onClick={copiarLink}
                disabled={qrIndisponivel}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-50"
              >
                <Copy size={17} /> Copiar link
              </button>
            </div>
            <p className="mt-3 break-all rounded-lg bg-slate-50 p-2 text-xs text-slate-500">
              {linkAtual || "Informe um WhatsApp válido para liberar este destino."}
            </p>
          </section>
        </aside>

        <section className="min-w-0 rounded-xl border border-slate-200 bg-slate-100 p-3 shadow-sm md:p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="font-bold text-slate-900">Prévia da arte</h2>
              <p className="text-xs text-slate-500">
                {formatoAtual.label} · {destinoAtual.label}
              </p>
            </div>
            {exportando ? (
              <span className="text-sm font-semibold text-teal-700">Gerando...</span>
            ) : null}
          </div>

          <div className="mx-auto w-full max-w-[720px] overflow-auto rounded-xl">
            <div
              ref={arteRef}
              style={{
                aspectRatio: formatoAtual.aspectRatio,
                background: `linear-gradient(150deg, ${corSecundaria} 0%, ${corPrimaria} 62%, #ffffff 160%)`,
                color: "#ffffff",
              }}
              className="relative flex w-full flex-col items-center justify-between overflow-hidden rounded-xl p-[7%] text-center shadow-xl"
            >
              <div
                className="absolute -right-[15%] -top-[10%] h-[45%] w-[55%] rounded-full"
                style={{ backgroundColor: "rgba(255,255,255,0.10)" }}
              />
              <div className="relative z-10 flex w-full flex-col items-center">
                <div className="flex max-w-[88%] items-center justify-center gap-3 rounded-2xl bg-white/95 px-5 py-3 text-slate-900 shadow-lg">
                  {logoUrl ? (
                    <img
                      src={logoUrl}
                      alt=""
                      crossOrigin="anonymous"
                      className="max-h-16 max-w-40 object-contain"
                    />
                  ) : (
                    <Store size={34} style={{ color: corPrimaria }} />
                  )}
                  <span
                    className="text-left text-xl font-black leading-tight"
                    style={{ color: "#0f172a" }}
                  >
                    {contexto.name}
                  </span>
                </div>
                <p className="mt-[8%] max-w-[92%] text-[clamp(1.45rem,4vw,3rem)] font-black leading-[1.05] tracking-tight">
                  {chamada || "Conheça nossa loja"}
                </p>
              </div>

              <div className="relative z-10 my-[4%] flex w-[62%] max-w-[390px] flex-col items-center rounded-[8%] bg-white p-[5%] text-slate-900 shadow-2xl">
                {qrDataUrl ? (
                  <img src={qrDataUrl} alt="QR Code da loja" className="h-auto w-full" />
                ) : (
                  <div className="flex aspect-square w-full items-center justify-center bg-slate-100 text-sm text-slate-500">
                    QR indisponível
                  </div>
                )}
                <div className="mt-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-600">
                  <DestinoIcone size={15} /> {destinoAtual.label}
                </div>
              </div>

              <div className="relative z-10 w-full">
                <p className="text-[clamp(1rem,2.2vw,1.55rem)] font-bold">
                  Aponte a câmera do celular para o QR Code
                </p>
                <p className="mt-2 text-sm text-white/85">
                  corepet.com.br/{contexto.ecommerce_slug}
                </p>
                <div className="mx-auto mt-4 inline-flex items-center gap-2 rounded-full bg-white/15 px-4 py-2 text-xs font-semibold">
                  <CheckCircle2 size={15} /> Loja oficial no CorePet
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
