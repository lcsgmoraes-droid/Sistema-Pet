import { useCallback, useEffect, useRef, useState } from "react";

export function useConfiguracoesFeedback() {
  const sucessoTimerRef = useRef(null);
  const [sucesso, setSucesso] = useState(null);

  const mostrarSucesso = useCallback((mensagem) => {
    window.clearTimeout(sucessoTimerRef.current);
    setSucesso(mensagem);
    sucessoTimerRef.current = window.setTimeout(() => setSucesso(null), 3000);
  }, []);

  useEffect(() => (
    () => {
      window.clearTimeout(sucessoTimerRef.current);
    }
  ), []);

  return { mostrarSucesso, sucesso };
}
