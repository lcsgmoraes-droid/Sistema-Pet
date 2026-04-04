export default function CampanhasConfigSchedulerHeader() {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-6">
      <h2 className="font-semibold text-gray-800 mb-1">
        {"\u2699\uFE0F"} Configuracoes de Envio
      </h2>
      <p className="text-xs text-gray-500">
        Defina os horarios em que o sistema envia as mensagens automaticas de
        cada campanha.
      </p>
    </div>
  );
}
