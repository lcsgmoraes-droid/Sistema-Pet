export default function ExamesAnexadosErro({ erro }) {
  if (!erro) return null;

  return (
    <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
      {erro}
    </div>
  );
}
