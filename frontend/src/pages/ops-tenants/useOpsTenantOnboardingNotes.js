import { useCallback, useEffect, useRef, useState } from "react";

import api from "../../platformApi";

import { extractError } from "./opsTenantsFormatters";

export default function useOpsTenantOnboardingNotes(selectedTenantId) {
  const [notes, setNotes] = useState([]);
  const [notesLoading, setNotesLoading] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [noteError, setNoteError] = useState("");
  const [noteSuccess, setNoteSuccess] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const requestSequence = useRef(0);
  const activeTenantId = useRef(selectedTenantId);
  activeTenantId.current = selectedTenantId;

  const loadNotes = useCallback(async (tenantId) => {
    const requestId = ++requestSequence.current;
    if (!tenantId) {
      setNotes([]);
      setNotesLoading(false);
      return;
    }
    setNotesLoading(true);
    setNoteError("");
    try {
      const response = await api.get(`/admin/tenants/${tenantId}/onboarding-follow-up/notes`, {
        params: { limit: 20 },
      });
      if (requestId === requestSequence.current) {
        setNotes(response.data?.items || []);
      }
    } catch (err) {
      if (requestId === requestSequence.current) {
        setNoteError(extractError(err, "Nao foi possivel carregar o historico."));
      }
    } finally {
      if (requestId === requestSequence.current) {
        setNotesLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    setNoteText("");
    setNoteError("");
    setNoteSuccess("");
    loadNotes(selectedTenantId);
    return () => {
      requestSequence.current += 1;
    };
  }, [loadNotes, selectedTenantId]);

  function handleNoteChange(value) {
    setNoteText(value);
    setNoteError("");
    setNoteSuccess("");
  }

  async function handleNoteSubmit(event) {
    event.preventDefault();
    const tenantId = selectedTenantId;
    if (!tenantId) {
      setNoteError("Selecione uma empresa antes de registrar a nota.");
      return;
    }
    const note = noteText.trim();
    if (note.length < 3) {
      setNoteError("Escreva uma nota com pelo menos 3 caracteres.");
      return;
    }

    setNoteSaving(true);
    setNoteError("");
    setNoteSuccess("");
    try {
      const response = await api.post(
        `/admin/tenants/${tenantId}/onboarding-follow-up/notes`,
        { note },
      );
      if (activeTenantId.current === tenantId) {
        setNotes((current) => [response.data, ...current]);
        setNoteText("");
        setNoteSuccess("Nota registrada no historico.");
      }
    } catch (err) {
      if (activeTenantId.current === tenantId) {
        setNoteError(extractError(err, "Nao foi possivel registrar a nota."));
      }
    } finally {
      setNoteSaving(false);
    }
  }

  return {
    handleNoteChange,
    handleNoteSubmit,
    noteError,
    noteSaving,
    noteSuccess,
    noteText,
    notes,
    notesLoading,
  };
}
