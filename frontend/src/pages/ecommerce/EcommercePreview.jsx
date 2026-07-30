import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, ExternalLink, Monitor, Smartphone, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../../services/api";

export default function EcommercePreview() {
  const [data, setData] = useState({
    context: null,
    config: null,
    health: null,
    payment: null,
  });
  const [device, setDevice] = useState("desktop");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.get("/ecommerce-aparencia/tenant-context"),
      api.get("/ecommerce-config"),
      api.get("/ecommerce-analytics/catalogo-saude"),
      api.get("/ecommerce-payment-config/mercadopago"),
    ])
      .then(([context, config, health, payment]) => {
        setData({
          context: context.data,
          config: config.data,
          health: health.data,
          payment: payment.data,
        });
      })
      .catch((requestError) => {
        setError(
          requestError?.response?.data?.detail ||
            "Não foi possível montar a prévia da loja.",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const checklist = useMemo(() => {
    const { context, config, health, payment } = data;
    return [
      ["Endereço público definido", Boolean(context?.ecommerce_slug), "/ecommerce/aparencia"],
      ["Loja está online", Boolean(config?.ecommerce_ativo), "/ecommerce/configuracoes"],
      [
        "Entrega ou retirada configurada",
        Boolean(config?.ecommerce_entrega_ativa || config?.ecommerce_retirada_ativa),
        "/ecommerce/configuracoes",
      ],
      [
        "Mercado Pago conectado e ativo",
        Boolean(payment?.enabled && (payment?.oauth_connected || payment?.access_token_configured)),
        "/ecommerce/configuracoes",
      ],
      ["Logo configurado", Boolean(context?.logo_url), "/ecommerce/aparencia"],
      [
        "Há produtos prontos para venda",
        Number(health?.prontos_para_venda || 0) > 0,
        "/ecommerce/analytics",
      ],
    ];
  }, [data]);

  const readyCount = checklist.filter((item) => item[1]).length;
  const storefrontPath = data.context?.ecommerce_slug
    ? `/${data.context.ecommerce_slug}`
    : "";

  if (loading) {
    return <div className="p-10 text-center text-gray-500">Preparando a prévia...</div>;
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Prévia da loja</h1>
          <p className="mt-1 text-sm text-gray-500">
            Confira o que o cliente verá e resolva pendências antes de divulgar.
          </p>
        </div>
        {storefrontPath && (
          <a
            href={storefrontPath}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
          >
            <ExternalLink size={16} />
            Abrir loja pública
          </a>
        )}
      </header>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="font-bold text-gray-900">Prontidão</h2>
              <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700">
                {readyCount}/{checklist.length}
              </span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-indigo-500"
                style={{ width: `${(readyCount / checklist.length) * 100}%` }}
              />
            </div>
            <div className="mt-4 space-y-3">
              {checklist.map(([label, ready, path]) => (
                <Link
                  key={label}
                  to={path}
                  className="flex items-start gap-2 text-sm no-underline"
                >
                  {ready ? (
                    <CheckCircle2 size={17} className="mt-0.5 shrink-0 text-emerald-600" />
                  ) : (
                    <XCircle size={17} className="mt-0.5 shrink-0 text-amber-600" />
                  )}
                  <span className={ready ? "text-gray-600" : "font-medium text-gray-800"}>
                    {label}
                  </span>
                </Link>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-5 text-sm shadow-sm">
            <h2 className="font-bold text-gray-900">Catálogo</h2>
            <dl className="mt-3 space-y-2 text-gray-600">
              <div className="flex justify-between"><dt>Publicados</dt><dd>{data.health?.publicados ?? 0}</dd></div>
              <div className="flex justify-between"><dt>Prontos</dt><dd className="font-bold text-emerald-700">{data.health?.prontos_para_venda ?? 0}</dd></div>
              <div className="flex justify-between"><dt>Sem imagem</dt><dd>{data.health?.sem_imagem ?? 0}</dd></div>
              <div className="flex justify-between"><dt>Sem estoque</dt><dd>{data.health?.sem_estoque ?? 0}</dd></div>
            </dl>
          </div>
        </aside>

        <section className="min-w-0 rounded-xl border border-gray-200 bg-gray-100 p-3 shadow-sm md:p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="font-bold text-gray-900">Visualização ao vivo</h2>
              <p className="text-xs text-gray-500">A prévia usa os dados salvos.</p>
            </div>
            <div className="flex rounded-lg border border-gray-300 bg-white p-1">
              {[
                ["desktop", Monitor],
                ["mobile", Smartphone],
              ].map(([value, Icon]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setDevice(value)}
                  className={`rounded-md p-2 ${
                    device === value ? "bg-indigo-100 text-indigo-700" : "text-gray-500"
                  }`}
                  aria-label={value === "desktop" ? "Prévia desktop" : "Prévia celular"}
                >
                  <Icon size={17} />
                </button>
              ))}
            </div>
          </div>

          {storefrontPath ? (
            <div
              className="mx-auto overflow-hidden rounded-xl border border-gray-300 bg-white shadow-lg transition-all"
              style={{ width: device === "mobile" ? 390 : "100%", maxWidth: "100%", height: 760 }}
            >
              <iframe
                src={storefrontPath}
                title="Prévia da loja pública"
                className="h-full w-full border-0"
              />
            </div>
          ) : (
            <div className="flex h-96 flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center">
              <XCircle size={34} className="text-amber-500" />
              <h3 className="mt-3 font-bold text-gray-900">Defina o endereço da loja</h3>
              <p className="mt-1 max-w-sm text-sm text-gray-500">
                Salve um endereço público em Aparência para liberar a prévia.
              </p>
              <Link to="/ecommerce/aparencia" className="mt-4 text-sm font-semibold text-indigo-700">
                Configurar endereço
              </Link>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
