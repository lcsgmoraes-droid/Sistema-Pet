import { useState } from "react";
import api from "../api";
import BotaoCancelar from "./v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "./v2/BotaoSalva/BotaoSalva";
import InputTexto from "./v2/InputTexto/InputTexto";
import ModalPadrao from "./v2/ModalPadrao/ModalPadrao";

/**
 * Modal rapido para adicionar especie ou raca sem sair do formulario de Pet.
 */
const QuickAddModal = ({ tipo, especieId, especieNome, onSuccess, onClose }) => {
  const [nome, setNome] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const isRaca = tipo === "raca";
  const especieIdNormalizado = Number.parseInt(especieId, 10);
  const especieValida = Number.isInteger(especieIdNormalizado) && especieIdNormalizado > 0;
  const fieldId = `quick-add-${tipo || "item"}-nome`;

  const getApiErrorMessage = (err) => {
    const detail = err.response?.data?.detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => item?.msg || item?.message)
        .filter(Boolean)
        .join(" ");
      if (messages) return messages;
    }
    if (typeof detail === "string") return detail;
    return "Nao foi possivel salvar agora. Revise os dados e tente novamente.";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!nome || nome.trim() === "") {
      setError(`O nome ${tipo === "especie" ? "da especie" : "da raca"} e obrigatorio.`);
      return;
    }

    if (isRaca && !especieValida) {
      setError(
        "Selecione uma especie antes de cadastrar a raca. Escolha uma especie no campo anterior e tente novamente.",
      );
      return;
    }

    try {
      setSaving(true);
      let response;

      if (tipo === "especie") {
        response = await api.post("/cadastros/especies", {
          nome: nome.trim(),
          ativo: true,
        });
      } else {
        response = await api.post("/cadastros/racas", {
          nome: nome.trim(),
          especie_id: especieIdNormalizado,
          ativo: true,
        });
      }

      if (onSuccess) {
        onSuccess(response.data);
      }

      onClose();
    } catch (err) {
      console.error("Erro ao salvar:", err);
      setError(getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalPadrao
      titulo={`${tipo === "especie" ? "Nova espécie" : "Nova raça"}${
        isRaca && especieNome ? ` — ${especieNome}` : ""
      }`}
      onFechar={onClose}
      tamanho="pequena"
      rodape={
        <>
          <BotaoCancelar disabled={saving} onClick={onClose} />
          <BotaoSalva disabled={isRaca && !especieValida} loading={saving} onClick={handleSubmit}>
            Salvar
          </BotaoSalva>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        {error && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <InputTexto
          id={fieldId}
          label={`Nome ${tipo === "especie" ? "da espécie" : "da raça"}`}
          value={nome}
          onChange={setNome}
          placeholder={
            tipo === "especie" ? "Ex: Cão, Gato, Ave..." : "Ex: Labrador, SRD, Siamês..."
          }
          required
          autoFocus
          disabled={saving}
        />

        <p className="mt-3 text-xs text-slate-500">
          {tipo === "especie"
            ? "Esta espécie ficará disponível para todos os pets."
            : `Esta raça será adicionada à espécie "${especieNome || "selecionada"}".`}
        </p>
        {isRaca && !especieValida && (
          <p className="mt-2 text-xs font-medium text-amber-800">
            Selecione uma espécie no formulário antes de salvar a raça.
          </p>
        )}
      </form>
    </ModalPadrao>
  );
};

export default QuickAddModal;
