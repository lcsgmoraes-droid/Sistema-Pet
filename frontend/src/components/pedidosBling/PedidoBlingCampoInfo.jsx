export default function PedidoBlingCampoInfo({ label, valor }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] uppercase tracking-wide text-gray-400">{label}</p>
      <p className="text-sm text-gray-700 break-words">{valor || '-'}</p>
    </div>
  );
}
