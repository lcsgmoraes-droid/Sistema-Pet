import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";

import { coordenadasDaRota, obterEstadoSinal } from "./rastreamentoAoVivoUtils";

function criarIconeMoto(rota, selecionada) {
  const estado = obterEstadoSinal(rota);
  const pulso = estado.key === "ao_vivo" ? "tracker-live-pulse" : "";
  return L.divIcon({
    html: `<div style="position:relative;width:46px;height:46px;display:grid;place-items:center;">
      <div class="${pulso}" style="position:absolute;inset:2px;border-radius:999px;background:${estado.cor};opacity:.22"></div>
      <div style="position:relative;width:38px;height:38px;border-radius:999px;display:grid;place-items:center;background:${estado.cor};border:${selecionada ? "4px solid #0f172a" : "3px solid white"};box-shadow:0 4px 14px rgba(15,23,42,.35);font-size:20px;">🛵</div>
    </div>`,
    className: "",
    iconSize: [46, 46],
    iconAnchor: [23, 23],
  });
}

export default function RastreamentoMapa({ rotas, trilhas, rotaSelecionadaId, onSelecionar }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef(new Map());
  const polylinesRef = useRef(new Map());
  const assinaturaAjusteRef = useRef("");
  const rotaSelecionada = rotas.find((item) => String(item.id) === String(rotaSelecionadaId));
  const coordenadasSelecionadas = coordenadasDaRota(rotaSelecionada);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, { zoomControl: true, scrollWheelZoom: true }).setView(
      [-14.235, -51.9253],
      4,
    );
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
    }).addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current.clear();
      polylinesRef.current.clear();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const rotasComPosicao = rotas
      .map((rota) => ({ rota, coordenadas: coordenadasDaRota(rota) }))
      .filter((item) => item.coordenadas);
    const idsAtivos = new Set(rotasComPosicao.map(({ rota }) => String(rota.id)));

    for (const [id, marker] of markersRef.current.entries()) {
      if (!idsAtivos.has(id)) {
        marker.removeFrom(map);
        markersRef.current.delete(id);
      }
    }
    for (const [id, polyline] of polylinesRef.current.entries()) {
      if (!idsAtivos.has(id)) {
        polyline.removeFrom(map);
        polylinesRef.current.delete(id);
      }
    }

    rotasComPosicao.forEach(({ rota, coordenadas }) => {
      const id = String(rota.id);
      const latLng = [coordenadas.latitude, coordenadas.longitude];
      let marker = markersRef.current.get(id);
      if (!marker) {
        marker = L.marker(latLng).addTo(map);
        markersRef.current.set(id, marker);
      }
      marker.setLatLng(latLng);
      marker.setIcon(criarIconeMoto(rota, String(rotaSelecionadaId) === id));
      marker.unbindTooltip();
      const tooltip = document.createElement("span");
      tooltip.textContent = `${rota.entregador?.nome || "Entregador"} · ${
        rota.numero || `Rota #${rota.id}`
      }`;
      marker.bindTooltip(tooltip, { direction: "top", offset: [0, -18] });
      marker.off("click");
      marker.on("click", () => onSelecionar(rota.id));

      const pontos = trilhas[id] || [];
      if (pontos.length > 1) {
        const latLngs = pontos.map((ponto) => [ponto.latitude, ponto.longitude]);
        let polyline = polylinesRef.current.get(id);
        if (!polyline) {
          polyline = L.polyline(latLngs, { color: "#0f766e", weight: 4, opacity: 0.72 }).addTo(map);
          polylinesRef.current.set(id, polyline);
        } else {
          polyline.setLatLngs(latLngs);
        }
      }
    });

    const assinatura = rotasComPosicao
      .map(({ rota }) => rota.id)
      .sort()
      .join("|");
    if (assinatura && assinatura !== assinaturaAjusteRef.current) {
      const bounds = L.latLngBounds(
        rotasComPosicao.map(({ coordenadas }) => [coordenadas.latitude, coordenadas.longitude]),
      );
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
      assinaturaAjusteRef.current = assinatura;
    }
  }, [onSelecionar, rotaSelecionadaId, rotas, trilhas]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && coordenadasSelecionadas) {
      map.flyTo(
        [coordenadasSelecionadas.latitude, coordenadasSelecionadas.longitude],
        Math.max(map.getZoom(), 16),
        { duration: 0.8 },
      );
    }
  }, [coordenadasSelecionadas?.latitude, coordenadasSelecionadas?.longitude, rotaSelecionadaId]);

  const temPosicao = rotas.some((rota) => coordenadasDaRota(rota));

  return (
    <div className="relative h-[620px] overflow-hidden rounded-xl border border-slate-200 bg-slate-100">
      <div ref={containerRef} className="h-full w-full" />
      {!temPosicao ? (
        <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center bg-white/80 p-6 text-center">
          <div>
            <div className="text-4xl">📍</div>
            <p className="mt-3 font-bold text-slate-800">Aguardando o primeiro sinal</p>
            <p className="mt-1 max-w-sm text-sm text-slate-500">
              Assim que o app do entregador enviar a localização, a moto aparecerá aqui.
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
