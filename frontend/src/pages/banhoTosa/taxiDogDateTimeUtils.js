const OPERATIONAL_DATE_TIME = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/;

function parseOperationalDateTime(value) {
  const match = String(value || "").match(OPERATIONAL_DATE_TIME);
  if (!match) return null;

  const [, year, month, day, hour, minute, second = "00"] = match;
  return {
    year: Number(year),
    month: Number(month),
    day: Number(day),
    hour: Number(hour),
    minute: Number(minute),
    second: Number(second),
  };
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function formatDateTimeInput(date) {
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
}

export function toOperationalDateTimeInput(value) {
  const parts = parseOperationalDateTime(value);
  if (!parts) return "";

  return `${parts.year}-${pad(parts.month)}-${pad(parts.day)}T${pad(parts.hour)}:${pad(parts.minute)}`;
}

export function addOperationalMinutes(value, minutes) {
  const parts = parseOperationalDateTime(value);
  if (!parts) return "";

  const date = new Date(
    Date.UTC(
      parts.year,
      parts.month - 1,
      parts.day,
      parts.hour,
      parts.minute + Number(minutes || 0),
      parts.second,
    ),
  );
  return formatDateTimeInput(date);
}

export function buildTaxiDogWindow(appointmentStart) {
  return {
    inicio: addOperationalMinutes(appointmentStart, -60),
    fim: toOperationalDateTimeInput(appointmentStart),
  };
}
