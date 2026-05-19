import { Calendar } from "lucide-react";
import { useId } from "react";

import { formatarDataIsoParaBr } from "./agendaDateInputUtils";

export default function AgendaDateInputField({ label, onChange, value }) {
  const id = useId();
  const dataFormatada = formatarDataIsoParaBr(value);

  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-gray-600">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type="date"
          value={value || ""}
          onChange={(event) => onChange(event.target.value)}
          className="peer absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
        />
        <div
          aria-hidden="true"
          className={`w-full rounded-lg border border-gray-200 bg-white px-3 py-2 pr-10 text-sm transition peer-focus:border-blue-500 peer-focus:ring-2 peer-focus:ring-blue-100 ${
            dataFormatada ? "text-gray-900" : "text-gray-400"
          }`}
        >
          {dataFormatada || "dd/mm/aaaa"}
        </div>
        <Calendar
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 z-0 h-4 w-4 -translate-y-1/2 text-gray-700"
        />
      </div>
    </div>
  );
}
