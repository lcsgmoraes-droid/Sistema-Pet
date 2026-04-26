import { useEffect } from "react";

export function useInternacoesQueryEffects({
  abrirNovaQuery,
  novoPetIdQuery,
  setFormNova,
  setModalNova,
  setTutorNovaSelecionado,
  tutorIdQuery,
  tutorNomeQuery,
}) {
  useEffect(() => {
    if (abrirNovaQuery) setModalNova(true);
  }, [abrirNovaQuery, setModalNova]);

  useEffect(() => {
    if (!tutorIdQuery) return;

    setFormNova((prev) => ({
      ...prev,
      pessoa_id: prev.pessoa_id || String(tutorIdQuery),
    }));
    setTutorNovaSelecionado(
      (prev) =>
        prev || {
          id: String(tutorIdQuery),
          nome: tutorNomeQuery || `Pessoa #${tutorIdQuery}`,
        }
    );
  }, [setFormNova, setTutorNovaSelecionado, tutorIdQuery, tutorNomeQuery]);

  useEffect(() => {
    if (!novoPetIdQuery) return;

    setModalNova(true);
    setFormNova((prev) => ({
      ...prev,
      pet_id: String(novoPetIdQuery),
    }));
  }, [novoPetIdQuery, setFormNova, setModalNova]);
}
