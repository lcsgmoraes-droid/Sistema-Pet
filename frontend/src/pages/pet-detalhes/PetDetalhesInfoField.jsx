export default function PetDetalhesInfoField({ children, mono = false, label }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <p className={`text-gray-900 ${mono ? "font-mono text-sm" : ""}`}>{children || "-"}</p>
    </div>
  );
}
