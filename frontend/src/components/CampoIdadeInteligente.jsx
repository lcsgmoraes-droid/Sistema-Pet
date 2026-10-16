import { AlertTriangle, Calendar, CheckCircle2, Keyboard } from "lucide-react";
import { useEffect, useState } from "react";
import {
  parseIdadeParaMeses,
  formatarIdadeMeses,
  calcularIdadeMeses,
} from "../helpers/idadeHelper";
import BotaoInteracao from "./v2/BotaoInteracao/BotaoInteracao";
import InputData from "./v2/InputData/InputData";
import InputTexto from "./v2/InputTexto/InputTexto";

/**
 * Campo inteligente para entrada de idade
 * Aceita: anos, meses, anos e meses, data de nascimento
 * Sempre retorna valor em meses via onChange
 */
export default function CampoIdadeInteligente({
  value,
  onChange,
  name = "idade",
  label = "Idade",
  className = "",
  mostrarDataNascimento = true,
  required = false,
}) {
  const [modo, setModo] = useState("texto"); // 'texto' ou 'data'
  const [textoIdade, setTextoIdade] = useState("");
  const [dataNascimento, setDataNascimento] = useState("");
  const [feedback, setFeedback] = useState(null); // { tipo: "sucesso" | "erro", texto }

  // Inicializar com valor recebido
  useEffect(() => {
    if (value && typeof value === "number") {
      setTextoIdade(formatarIdadeMeses(value));
    }
  }, [value]);

  const handleTextoChange = (texto) => {
    setTextoIdade(texto);

    if (!texto) {
      setFeedback(null);
      onChange(null);
    }
  };

  const handleTextoBlur = () => {
    if (!textoIdade) {
      setFeedback(null);
      onChange(null);
      return;
    }

    // Converter ao sair do campo
    const meses = parseIdadeParaMeses(textoIdade);

    if (meses !== null) {
      const formatado = formatarIdadeMeses(meses);
      setTextoIdade(formatado);
      setFeedback({ tipo: "sucesso", texto: formatado });
      onChange(meses);
    } else {
      setFeedback({
        tipo: "erro",
        texto: "Formato inválido. Ex: 12 meses, 2 anos, 1.5 anos",
      });
      onChange(null);
    }
  };

  const handleDataChange = (data) => {
    setDataNascimento(data);

    if (!data) {
      setFeedback(null);
      onChange(null);
      return;
    }

    // Calcular idade em meses
    const meses = calcularIdadeMeses(data);

    if (meses !== null && meses >= 0) {
      setFeedback({ tipo: "sucesso", texto: formatarIdadeMeses(meses) });
      onChange(meses);
    } else {
      setFeedback({ tipo: "erro", texto: "Data inválida — não pode ser no futuro" });
      onChange(null);
    }
  };

  const renderFeedback = () => {
    if (!feedback) return null;
    const sucesso = feedback.tipo === "sucesso";
    const Icone = sucesso ? CheckCircle2 : AlertTriangle;
    return (
      <p
        className={`mt-1 flex items-center gap-1 text-xs ${sucesso ? "text-green-700" : "text-amber-800"}`}
      >
        <Icone size={14} aria-hidden="true" />
        <span>
          <span className="font-medium">{sucesso ? "Idade reconhecida: " : "Atenção: "}</span>
          {feedback.texto}
        </span>
      </p>
    );
  };

  const toggleModo = () => {
    const novoModo = modo === "texto" ? "data" : "texto";
    setModo(novoModo);
    setTextoIdade("");
    setDataNascimento("");
    setFeedback(null);
    onChange(null);
  };

  return (
    <div className={className}>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-600">
          {label}
          {required ? <span className="ml-0.5 text-red-500">*</span> : null}
        </span>

        {mostrarDataNascimento && (
          <BotaoInteracao
            icon={modo === "texto" ? Calendar : Keyboard}
            onClick={toggleModo}
            tamanho="pequeno"
          >
            {modo === "texto" ? "Usar data de nascimento" : "Digitar idade"}
          </BotaoInteracao>
        )}
      </div>

      {modo === "texto" ? (
        <div>
          <InputTexto
            name={name}
            value={textoIdade}
            onChange={handleTextoChange}
            onBlur={handleTextoBlur}
            placeholder="Ex: 12 meses, 2 anos, 1.5 anos, 2anos6meses"
            required={required}
          />
          {renderFeedback()}
          <p className="mt-1 text-xs text-gray-500">
            Digite a idade e pressione Tab ou clique fora do campo
          </p>
        </div>
      ) : (
        <div>
          <InputData
            name={name}
            value={dataNascimento}
            onChange={handleDataChange}
            required={required}
          />
          {renderFeedback()}
          <p className="mt-1 text-xs text-gray-500">Data de nascimento do pet</p>
        </div>
      )}
    </div>
  );
}
