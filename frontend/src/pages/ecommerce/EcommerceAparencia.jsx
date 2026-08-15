import { useEffect, useRef, useState } from "react";
import { api } from "../../services/api";

const TIPOS = [
  {
    key: "logo",
    label: "Logo da Loja",
    desc: "Aparece na loja virtual e como imagem da loja no app (use uma imagem nítida e com pouco espaço vazio)",
    targetW: 400,
    targetH: 160,
  },
  {
    key: "banner_1",
    label: "Banner 1",
    desc: "Primeiro slide do banner rotativo — será redimensionado para até 1200 px de largura",
    targetW: 1200,
    targetH: null,
  },
  {
    key: "banner_2",
    label: "Banner 2",
    desc: "Segundo slide (opcional)",
    targetW: 1200,
    targetH: null,
  },
  {
    key: "banner_3",
    label: "Banner 3",
    desc: "Terceiro slide (opcional)",
    targetW: 1200,
    targetH: null,
  },
];

/**
 * Redimensiona a imagem no navegador usando Canvas.
 * Banners: escala para até 1200px de largura mantendo proporção original (sem corte).
 * Logo: limita a 400×160 preservando a proporção, sem adicionar espaço vazio.
 */
function resizeImage(file, targetW, targetH, outputType = "image/webp", quality = 0.9) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");

      if (targetH === null) {
        // Modo banner: apenas limita a largura, mantém proporção
        const scale = img.naturalWidth > targetW ? targetW / img.naturalWidth : 1;
        canvas.width = Math.round(img.naturalWidth * scale);
        canvas.height = Math.round(img.naturalHeight * scale);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      } else {
        // Modo logo: preserva o formato original para funcionar no site e no cartão quadrado do app.
        const scale = Math.min(targetW / img.naturalWidth, targetH / img.naturalHeight, 1);
        const drawW = Math.max(1, Math.round(img.naturalWidth * scale));
        const drawH = Math.max(1, Math.round(img.naturalHeight * scale));
        canvas.width = drawW;
        canvas.height = drawH;
        ctx.drawImage(img, 0, 0, drawW, drawH);
      }

      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error("canvas toBlob falhou"))),
        outputType,
        quality,
      );
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Falha ao carregar imagem"));
    };
    img.src = url;
  });
}

function PreviewImage({ url, label, cacheBuster, isBanner }) {
  if (!url)
    return (
      <div
        style={{
          width: "100%",
          minHeight: 120,
          background: "#f3f4f6",
          border: "2px dashed #d1d5db",
          borderRadius: 8,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#9ca3af",
          fontSize: 14,
        }}
      >
        Sem imagem
      </div>
    );
  const src = url.startsWith("/uploads/") ? `${url}?t=${cacheBuster}` : url;
  return (
    <img
      src={src}
      alt={label}
      style={{
        width: "100%",
        height: isBanner ? 140 : 100,
        objectFit: "contain",
        background: "#111",
        borderRadius: 8,
        border: "1px solid #e5e7eb",
        display: "block",
      }}
    />
  );
}

function imageUrlWithCache(url, cacheBuster) {
  if (!url) return null;
  return url.startsWith("/uploads/") ? `${url}?t=${cacheBuster}` : url;
}

function AppStoreLogoPreview({ logoUrl, cacheBuster, storeName, cidade, uf }) {
  const src = imageUrlWithCache(logoUrl, cacheBuster);
  const local = [cidade, uf].filter(Boolean).join("/") || "Localização da loja";

  return (
    <div
      style={{
        marginTop: 16,
        padding: 16,
        background: "#f0fdfa",
        border: "1px solid #99f6e4",
        borderRadius: 10,
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 700, color: "#115e59", marginBottom: 4 }}>
        Prévia no aplicativo
      </div>
      <p style={{ fontSize: 12, color: "#475569", margin: "0 0 12px" }}>
        Esta logo aparece nas buscas e em “Lojas mais próximas”. Se não houver uma logo cadastrada,
        o app poderá usar o primeiro banner.
      </p>

      <div
        style={{
          maxWidth: 430,
          padding: "10px 12px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          background: "#fff",
          border: "1px solid #d1d5db",
          borderRadius: 12,
          boxShadow: "0 1px 2px rgba(15, 23, 42, 0.06)",
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            background: "#fff",
            border: "1px solid #e2e8f0",
            borderRadius: 10,
          }}
        >
          {src ? (
            <img
              src={src}
              alt={`Logo de ${storeName || "sua loja"} no aplicativo`}
              style={{ width: 42, height: 42, objectFit: "contain", display: "block" }}
            />
          ) : (
            <span style={{ fontSize: 10, color: "#94a3b8", textAlign: "center", lineHeight: 1.1 }}>
              Sem
              <br />
              logo
            </span>
          )}
        </div>

        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              color: "#111827",
              fontSize: 14,
              fontWeight: 700,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {storeName || "Nome da sua loja"}
          </div>
          <div style={{ color: "#64748b", fontSize: 12, marginTop: 3 }}>{local}</div>
        </div>
        <span aria-hidden="true" style={{ color: "#94a3b8", fontSize: 24, lineHeight: 1 }}>
          ›
        </span>
      </div>
    </div>
  );
}

export default function EcommerceAparencia() {
  const [aparencia, setAparencia] = useState({
    logo_url: null,
    banner_1_url: null,
    banner_2_url: null,
    banner_3_url: null,
  });
  const [slug, setSlug] = useState("");
  const [slugOriginal, setSlugOriginal] = useState("");
  const [tenantContext, setTenantContext] = useState({
    name: "",
    cidade: "",
    uf: "",
  });
  const [salvandoSlug, setSalvandoSlug] = useState(false);
  const [localizacao, setLocalizacao] = useState({
    latitude: null,
    longitude: null,
  });
  const [salvandoLocalizacao, setSalvandoLocalizacao] = useState(false);
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState({});
  const [msg, setMsg] = useState(null);
  const [cacheBuster, setCacheBuster] = useState(Date.now());
  const inputRefs = useRef({});

  useEffect(() => {
    const fetchAparencia = api
      .get("/ecommerce-aparencia")
      .then((r) => setAparencia(r.data))
      .catch(() => setMsg({ tipo: "erro", texto: "Não foi possível carregar as configurações." }));
    const fetchSlug = api
      .get("/ecommerce-aparencia/tenant-context")
      .then((r) => {
        setSlug(r.data.ecommerce_slug || "");
        setSlugOriginal(r.data.ecommerce_slug || "");
        setTenantContext({
          name: r.data.name || "",
          cidade: r.data.cidade || "",
          uf: r.data.uf || "",
        });
        setLocalizacao({
          latitude: r.data.latitude ?? null,
          longitude: r.data.longitude ?? null,
        });
      })
      .catch(() => {});
    Promise.all([fetchAparencia, fetchSlug]).finally(() => setCarregando(false));
  }, []);

  function mostrarMsg(tipo, texto) {
    setMsg({ tipo, texto });
    setTimeout(() => setMsg(null), 4000);
  }

  async function salvarSlug() {
    setSalvandoSlug(true);
    try {
      await api.put("/ecommerce-aparencia/slug", { slug: slug.trim() });
      setSlugOriginal(slug.trim());
      mostrarMsg("ok", "Endereço da loja salvo com sucesso!");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      mostrarMsg("erro", detail || "Erro ao salvar o endereço.");
    } finally {
      setSalvandoSlug(false);
    }
  }

  function salvarLocalizacaoAtual() {
    if (!navigator.geolocation) {
      mostrarMsg("erro", "Este navegador nao oferece acesso a localizacao.");
      return;
    }

    setSalvandoLocalizacao(true);
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const payload = {
            latitude: coords.latitude,
            longitude: coords.longitude,
          };
          const response = await api.put("/ecommerce-aparencia/localizacao", payload);
          setLocalizacao(response.data);
          mostrarMsg("ok", "Localizacao da loja salva com sucesso!");
        } catch {
          mostrarMsg("erro", "Nao foi possivel salvar a localizacao da loja.");
        } finally {
          setSalvandoLocalizacao(false);
        }
      },
      () => {
        mostrarMsg(
          "erro",
          "Nao foi possivel obter a localizacao. Confira a permissao do navegador.",
        );
        setSalvandoLocalizacao(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 60000,
      },
    );
  }

  async function uploadArquivo(tipo, arquivo) {
    setSalvando((s) => ({ ...s, [tipo]: true }));
    try {
      // Redimensiona antes de enviar
      const tipoConfig = TIPOS.find((t) => t.key === tipo);
      let fileToUpload = arquivo;
      if (tipoConfig && arquivo.type.startsWith("image/")) {
        const isLogo = tipo === "logo";
        const outputType = isLogo ? "image/png" : "image/webp";
        const extension = isLogo ? ".png" : ".webp";
        const blob = await resizeImage(arquivo, tipoConfig.targetW, tipoConfig.targetH, outputType);
        fileToUpload = new File([blob], arquivo.name.replace(/\.[^.]+$/, extension), {
          type: outputType,
        });
      }
      const form = new FormData();
      form.append("file", fileToUpload);
      const r = await api.post(`/ecommerce-aparencia/upload/${tipo}`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setAparencia(r.data);
      setCacheBuster(Date.now());
      mostrarMsg("ok", "Imagem salva com sucesso!");
    } catch {
      mostrarMsg("erro", "Erro ao enviar a imagem. Verifique o formato e o tamanho (máx. 5 MB).");
    } finally {
      setSalvando((s) => ({ ...s, [tipo]: false }));
    }
  }

  async function remover(tipo) {
    setSalvando((s) => ({ ...s, [tipo]: true }));
    try {
      const r = await api.delete(`/ecommerce-aparencia/${tipo}`);
      setAparencia(r.data);
      setCacheBuster(Date.now());
      mostrarMsg("ok", "Imagem removida.");
    } catch {
      mostrarMsg("erro", "Erro ao remover a imagem.");
    } finally {
      setSalvando((s) => ({ ...s, [tipo]: false }));
    }
  }

  if (carregando)
    return <div style={{ padding: 40, textAlign: "center", color: "#6b7280" }}>Carregando...</div>;

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 4 }}>
        🖼️ Aparência da Loja
      </h1>
      <p style={{ color: "#6b7280", marginBottom: 32 }}>
        Configure o logo e os banners que aparecem na sua loja virtual.
      </p>

      {msg && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: 8,
            marginBottom: 24,
            background: msg.tipo === "ok" ? "#f0fdf4" : "#fef2f2",
            color: msg.tipo === "ok" ? "#166534" : "#991b1b",
            border: `1px solid ${msg.tipo === "ok" ? "#bbf7d0" : "#fecaca"}`,
            fontWeight: 500,
          }}
        >
          {msg.tipo === "ok" ? "✅ " : "❌ "}
          {msg.texto}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* Slug da loja */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 12,
            padding: 24,
            boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
          }}
        >
          <div style={{ marginBottom: 4 }}>
            <span style={{ fontWeight: 600, fontSize: 16, color: "#111827" }}>
              🔗 Endereço da loja
            </span>
          </div>
          <p style={{ fontSize: 13, color: "#9ca3af", margin: "0 0 12px" }}>
            Define a URL pública da sua loja. Use apenas letras minúsculas, números e hífens.
          </p>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ fontSize: 13, color: "#6b7280", whiteSpace: "nowrap", flexShrink: 0 }}>
              corepet.com.br/
            </span>
            <input
              id="ecommerce-store-slug"
              name="store_slug"
              aria-label="Endereço público da loja"
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
              placeholder="nome-da-loja"
              style={{
                flex: 1,
                minWidth: 160,
                padding: "8px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 7,
                fontSize: 14,
              }}
            />
            <button
              onClick={salvarSlug}
              disabled={salvandoSlug || slug === slugOriginal}
              style={{
                padding: "8px 18px",
                background: salvandoSlug || slug === slugOriginal ? "#d1d5db" : "#6366f1",
                color: "#fff",
                border: "none",
                borderRadius: 7,
                fontWeight: 600,
                cursor: salvandoSlug || slug === slugOriginal ? "not-allowed" : "pointer",
                fontSize: 14,
                flexShrink: 0,
              }}
            >
              {salvandoSlug ? "Salvando..." : "Salvar"}
            </button>
          </div>
          {slugOriginal && (
            <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
              🌐 Loja pública:{" "}
              <a
                href={`/${slugOriginal}`}
                target="_blank"
                rel="noreferrer"
                style={{ color: "#6366f1" }}
              >
                corepet.com.br/{slugOriginal}
              </a>
            </div>
          )}
        </div>
        {/* Coordenadas usadas para ordenar lojas proximas no app */}
        <div
          style={{
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: 12,
            padding: 24,
            boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
          }}
        >
          <div style={{ marginBottom: 4 }}>
            <span style={{ fontWeight: 600, fontSize: 16, color: "#111827" }}>
              Localizacao da loja
            </span>
          </div>
          <p style={{ fontSize: 13, color: "#6b7280", margin: "0 0 12px" }}>
            Use este computador na loja e salve a posicao atual. Ela permite que clientes encontrem
            primeiro as lojas mais proximas no app.
          </p>
          <button
            onClick={salvarLocalizacaoAtual}
            disabled={salvandoLocalizacao}
            style={{
              padding: "9px 18px",
              background: salvandoLocalizacao ? "#d1d5db" : "#0f766e",
              color: "#fff",
              border: "none",
              borderRadius: 7,
              fontWeight: 600,
              cursor: salvandoLocalizacao ? "not-allowed" : "pointer",
              fontSize: 14,
            }}
          >
            {salvandoLocalizacao
              ? "Obtendo localizacao..."
              : localizacao.latitude !== null
                ? "Atualizar localizacao atual"
                : "Usar localizacao atual"}
          </button>
          {localizacao.latitude !== null && localizacao.longitude !== null && (
            <div style={{ marginTop: 10, fontSize: 12, color: "#15803d" }}>
              Localizacao configurada para esta loja.
            </div>
          )}
        </div>
        {TIPOS.map(({ key, label, desc }) => {
          const urlAtual = aparencia[`${key}_url`];
          const ocupado = salvando[key];

          return (
            <div
              key={key}
              style={{
                background: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: 12,
                padding: 24,
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
              }}
            >
              <div style={{ marginBottom: 12 }}>
                <span style={{ fontWeight: 600, fontSize: 16, color: "#111827" }}>{label}</span>
                <span style={{ marginLeft: 10, fontSize: 13, color: "#9ca3af" }}>{desc}</span>
              </div>

              <PreviewImage
                url={urlAtual}
                label={label}
                cacheBuster={cacheBuster}
                isBanner={key !== "logo"}
              />

              {key === "logo" && (
                <AppStoreLogoPreview
                  logoUrl={aparencia.logo_url}
                  cacheBuster={cacheBuster}
                  storeName={tenantContext.name}
                  cidade={tenantContext.cidade}
                  uf={tenantContext.uf}
                />
              )}

              <div
                style={{
                  marginTop: 14,
                  display: "flex",
                  gap: 10,
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                <input
                  id={`ecommerce-${key}-upload`}
                  name={`${key}_upload`}
                  aria-label={`Selecionar imagem para ${label}`}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  style={{ display: "none" }}
                  ref={(el) => (inputRefs.current[key] = el)}
                  onChange={(e) => e.target.files[0] && uploadArquivo(key, e.target.files[0])}
                />
                <button
                  onClick={() => inputRefs.current[key]?.click()}
                  disabled={ocupado}
                  style={{
                    padding: "8px 18px",
                    background: ocupado ? "#d1d5db" : "#6366f1",
                    color: "#fff",
                    border: "none",
                    borderRadius: 7,
                    fontWeight: 600,
                    cursor: ocupado ? "not-allowed" : "pointer",
                    fontSize: 14,
                  }}
                >
                  {ocupado ? "Enviando..." : urlAtual ? "🔄 Trocar imagem" : "📤 Fazer upload"}
                </button>

                {urlAtual && (
                  <button
                    onClick={() => remover(key)}
                    disabled={ocupado}
                    style={{
                      padding: "8px 14px",
                      background: "#fff",
                      color: "#dc2626",
                      border: "1px solid #fca5a5",
                      borderRadius: 7,
                      fontWeight: 500,
                      cursor: ocupado ? "not-allowed" : "pointer",
                      fontSize: 14,
                    }}
                  >
                    🗑 Remover
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          marginTop: 32,
          padding: 16,
          background: "#fffbeb",
          borderRadius: 10,
          border: "1px solid #fde68a",
          fontSize: 13,
          color: "#92400e",
        }}
      >
        <strong>💡 Dica:</strong> As imagens são redimensionadas automaticamente ao fazer upload.
        Para ver o resultado, acesse a{" "}
        <a href="/ecommerce/preview" style={{ color: "#6366f1" }}>
          prévia da loja
        </a>
        .
      </div>
    </div>
  );
}
