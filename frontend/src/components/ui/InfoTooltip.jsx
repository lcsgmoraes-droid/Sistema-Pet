import PropTypes from "prop-types";
import { Info } from "lucide-react";

export default function InfoTooltip({ label = "Ajuda", text }) {
  return (
    <span
      aria-label={label}
      className="inline-flex cursor-help align-middle text-gray-400 transition-colors hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      role="img"
      tabIndex={0}
      title={text}
    >
      <Info aria-hidden="true" className="h-3.5 w-3.5" />
    </span>
  );
}

InfoTooltip.propTypes = {
  label: PropTypes.string,
  text: PropTypes.string.isRequired,
};
