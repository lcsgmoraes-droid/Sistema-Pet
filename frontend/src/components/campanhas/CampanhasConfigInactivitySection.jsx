export default function CampanhasConfigInactivitySection({
  schedulerConfig,
  setSchedulerConfig,
}) {
  return (
    <div className="bg-white rounded-xl border shadow-sm p-6">
      <div className="flex items-center gap-3 mb-5">
        <span className="text-2xl">{"\u{1F634}"}</span>
        <div>
          <h3 className="font-medium text-gray-800">
            Mensagens de Reativacao (Clientes Inativos)
          </h3>
          <p className="text-xs text-gray-500">
            Enviadas uma vez por semana para clientes sem compras ha muito tempo
          </p>
        </div>
      </div>
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600 w-44">Dia da semana:</label>
          <select
            value={schedulerConfig.inactivity_day_of_week}
            onChange={(e) =>
              setSchedulerConfig({
                ...schedulerConfig,
                inactivity_day_of_week: e.target.value,
              })
            }
            className="border rounded-lg px-3 py-2 text-sm"
          >
            <option value="mon">Segunda-feira</option>
            <option value="tue">Terca-feira</option>
            <option value="wed">Quarta-feira</option>
            <option value="thu">Quinta-feira</option>
            <option value="fri">Sexta-feira</option>
            <option value="sat">Sabado</option>
            <option value="sun">Domingo</option>
          </select>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600 w-44">Hora de envio:</label>
          <select
            value={schedulerConfig.inactivity_send_hour}
            onChange={(e) =>
              setSchedulerConfig({
                ...schedulerConfig,
                inactivity_send_hour: Number(e.target.value),
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
    </div>
  );
}
