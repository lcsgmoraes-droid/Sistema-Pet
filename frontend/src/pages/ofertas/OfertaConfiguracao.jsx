import { CalendarRange, LayoutGrid, Palette, Smartphone, Store } from "lucide-react";

import { FORMATOS_OFERTA, PERIODICIDADES, TIPOS_ARTE, itensPorPagina } from "./ofertasEstudioUtils";

export default function OfertaConfiguracao({ config, onChange, onPeriodicidade }) {
  const fieldClass = "mt-1 h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm";
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="flex items-center gap-2 font-black text-slate-950">
        <CalendarRange size={19} className="text-teal-700" /> Edição da promoção
      </h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <label className="text-xs font-bold text-slate-700 sm:col-span-2 xl:col-span-3">
          Título da arte
          <input
            value={config.titulo}
            onChange={(event) => onChange({ titulo: event.target.value.slice(0, 160) })}
            className={fieldClass}
            placeholder="Ofertas da semana"
          />
        </label>
        <label className="text-xs font-bold text-slate-700">
          Frequência
          <select
            value={config.periodicidade}
            onChange={(event) => onPeriodicidade(event.target.value)}
            className={fieldClass}
          >
            {Object.entries(PERIODICIDADES).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-bold text-slate-700">
          Início
          <input
            type="datetime-local"
            value={config.inicio}
            onChange={(event) => onChange({ inicio: event.target.value })}
            className={fieldClass}
          />
        </label>
        <label className="text-xs font-bold text-slate-700">
          Final da promoção
          <input
            type="datetime-local"
            value={config.fim}
            onChange={(event) => onChange({ fim: event.target.value })}
            className={fieldClass}
          />
        </label>
        <label className="text-xs font-bold text-slate-700">
          Link disponível até
          <input
            type="datetime-local"
            value={config.expira}
            onChange={(event) => onChange({ expira: event.target.value })}
            className={fieldClass}
          />
        </label>
        <label className="text-xs font-bold text-slate-700">
          <span className="flex items-center gap-1">
            <LayoutGrid size={14} /> Tipo de arte
          </span>
          <select
            value={config.tipoArte}
            onChange={(event) => onChange({ tipoArte: event.target.value })}
            className={fieldClass}
          >
            {Object.entries(TIPOS_ARTE).map(([key, item]) => (
              <option key={key} value={key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-bold text-slate-700">
          Formato
          <select
            value={config.formato}
            onChange={(event) => onChange({ formato: event.target.value })}
            className={fieldClass}
          >
            {Object.entries(FORMATOS_OFERTA).map(([key, item]) => (
              <option key={key} value={key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-bold text-slate-700">
          <span className="flex items-center gap-1">
            <Palette size={14} /> Visual
          </span>
          <select
            value={config.tema}
            onChange={(event) => onChange({ tema: event.target.value })}
            className={fieldClass}
          >
            <option value="premium">Premium CorePet</option>
            <option value="natural">Natural</option>
            <option value="varejo">Oferta forte</option>
          </select>
        </label>
      </div>
      <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-black text-slate-800">Onde divulgar depois de gerar o link</p>
        <p className="mt-1 text-[11px] text-slate-500">
          A arte aparecerá durante o período da promoção. Isso não altera o preço oficial dos
          produtos nos canais.
        </p>
        <div className="mt-3 flex flex-wrap gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-sm">
            <input
              type="checkbox"
              checked={Boolean(config.exibirEcommerce)}
              onChange={(event) => onChange({ exibirEcommerce: event.target.checked })}
              className="h-4 w-4 accent-teal-700"
            />
            <Store size={15} /> Mostrar no e-commerce
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-sm">
            <input
              type="checkbox"
              checked={Boolean(config.exibirApp)}
              onChange={(event) => onChange({ exibirApp: event.target.checked })}
              className="h-4 w-4 accent-teal-700"
            />
            <Smartphone size={15} /> Mostrar no aplicativo
          </label>
        </div>
      </div>
      {config.tipoArte === "jornal" ? (
        <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-xs font-semibold text-emerald-800">
          Para manter fotos e textos legíveis, este formato usa até{" "}
          {itensPorPagina(config.tipoArte, config.formato)} produtos por página. Os demais vão
          automaticamente para a página seguinte.
        </p>
      ) : null}
      {config.tipoArte === "produto" ? (
        <p className="mt-4 rounded-lg bg-blue-50 p-3 text-xs font-semibold text-blue-800">
          “Só a imagem do produto” gera uma página limpa para cada item. Em cada produto você poderá
          abrir um prompt e pedir uma nova criação a partir da foto escolhida.
        </p>
      ) : null}
    </section>
  );
}
