import { STATUS_CONFIG } from './pedidoBlingUtils';

export default function PedidoBlingStatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || {
    label: status,
    cor: 'bg-gray-100 text-gray-700',
    dot: 'bg-gray-400',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.cor}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}
