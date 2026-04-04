export default function CampanhasConfigBirthdaySection({
  schedulerConfig,
  setSchedulerConfig,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-6">
      <div className="flex items-center gap-3 mb-5">
        <span className="text-2xl">{"\u{1F382}"}</span>
        <div>
          <h3 className="font-medium text-gray-800">Mensagens de Aniversario</h3>
          <p className="text-xs text-gray-500">
            Enviadas todos os dias para aniversariantes do dia
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <label className="text-sm text-gray-600 w-44">Hora de envio:</label>
        <select
          value={schedulerConfig.birthday_send_hour}
          onChange={(e) =>
            setSchedulerConfig({
              ...schedulerConfig,
              birthday_send_hour: Number(e.target.value),
            })
          }
          className="border rounded-lg px-3 py-2 text-sm"
        >
          {Array.from({ length: 24 }, (_, i) => (
            <option key={i} value={i}>
              {String(i).padStart(2, "0")}:00
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
