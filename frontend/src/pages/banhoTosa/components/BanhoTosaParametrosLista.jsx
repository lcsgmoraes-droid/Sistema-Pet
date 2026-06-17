import ActionButton from "../../../components/ui/ActionButton";
import EmptyState from "../../../components/ui/EmptyState";
import Panel from "../../../components/ui/Panel";
import StatusBadge from "../../../components/ui/StatusBadge";

export default function BanhoTosaParametrosLista({ parametros, onEdit, onDelete, onToggleAtivo }) {
  const parametrosOrdenados = [...parametros].sort((a, b) => {
    const pesoA = Number(a.peso_min_kg ?? 999999);
    const pesoB = Number(b.peso_min_kg ?? 999999);
    if (pesoA !== pesoB) return pesoA - pesoB;
    return String(a.porte || "").localeCompare(String(b.porte || ""));
  });

  return (
    <Panel
      subtitle="Visualizacao compacta dos tamanhos usados para agenda, precificacao e custos."
      title="Portes cadastrados"
    >
      {parametrosOrdenados.length === 0 ? (
        <EmptyState
          description='Clique em "Novo porte" para cadastrar o primeiro tamanho.'
          title="Nenhum porte parametrizado ainda"
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200">
          <div className="hidden grid-cols-[1.2fr_1fr_1fr_1fr_auto] gap-3 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500 lg:grid">
            <span>Porte</span>
            <span>Tempo</span>
            <span>Consumo base</span>
            <span>Pelagem</span>
            <span className="text-right">Acoes</span>
          </div>

          <div className="divide-y divide-slate-200">
            {parametrosOrdenados.map((item) => (
              <ParametroPorteRow
                key={item.id}
                item={item}
                onDelete={onDelete}
                onEdit={onEdit}
                onToggleAtivo={onToggleAtivo}
              />
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}

function ParametroPorteRow({ item, onEdit, onDelete, onToggleAtivo }) {
  const tempoTotal =
    Number(item.tempo_banho_min || 0) +
    Number(item.tempo_secagem_min || 0) +
    Number(item.tempo_tosa_min || 0);

  return (
    <article className="grid gap-3 bg-white px-4 py-3 text-sm transition hover:bg-slate-50 lg:grid-cols-[1.2fr_1fr_1fr_1fr_auto] lg:items-center">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold capitalize text-slate-900">{item.porte}</h3>
          <button type="button" onClick={() => onToggleAtivo?.(item)}>
            <StatusBadge status={item.ativo ? "ativo" : "inativo"} />
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {formatKg(item.peso_min_kg)} ate {formatKg(item.peso_max_kg)}
        </p>
      </div>

      <CompactInfo
        primary={`${tempoTotal} min total`}
        secondary={`Banho ${item.tempo_banho_min || 0} / Secagem ${item.tempo_secagem_min || 0} / Tosa ${item.tempo_tosa_min || 0}`}
      />

      <CompactInfo
        primary={`${formatNumber(item.agua_padrao_litros)} L de agua`}
        secondary={`${formatNumber(item.energia_padrao_kwh)} kWh`}
      />

      <CompactInfo
        primary={`Curto ${formatNumber(item.multiplicador_pelo_curto ?? 1)}x / Longo ${formatNumber(item.multiplicador_pelo_longo ?? 1.2)}x`}
        secondary={`Extra longo ${item.tempo_extra_pelo_longo_min || 0} min`}
      />

      <div className="flex flex-wrap justify-end gap-2">
        <ActionButton intent="edit" onClick={() => onEdit?.(item)} size="xs" tone="soft">
          Editar
        </ActionButton>
        <ActionButton intent="delete" onClick={() => onDelete?.(item)} size="xs" tone="soft">
          Excluir
        </ActionButton>
      </div>
    </article>
  );
}

function CompactInfo({ primary, secondary }) {
  return (
    <div>
      <div className="text-sm font-medium text-slate-900">{primary}</div>
      <div className="mt-0.5 text-xs text-slate-500">{secondary}</div>
    </div>
  );
}

function formatKg(value) {
  if (value === null || value === undefined || value === "") return "-";
  return `${formatNumber(value)}kg`;
}

function formatNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 3,
    minimumFractionDigits: 0,
  }).format(number);
}
