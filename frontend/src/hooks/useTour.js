import { driver } from "driver.js";
import "driver.js/dist/driver.css";
import { useCallback, useEffect, useRef } from "react";

/**
 * Hook para criar tours guiados.
 *
 * - Na primeira visita à página, o tour inicia automaticamente.
 * - O usuário pode reiniciar o tour chamando `iniciarTour()`.
 * - O status "já visto" é salvo no localStorage.
 *
 * Usa refs para acessar valores atuais sem colocá-los nas deps do useEffect,
 * evitando problemas com o React.StrictMode (que roda efeitos duas vezes em dev).
 */
export function useTour(tourKey, steps, { delay = 600 } = {}) {
  const driverRef = useRef(null);
  // Refs para acessar valores atuais sem trigger de re-render
  const stepsRef = useRef(steps);
  const tourKeyRef = useRef(tourKey);
  stepsRef.current = steps;
  tourKeyRef.current = tourKey;

  const iniciarTour = useCallback(() => {
    const currentSteps = stepsRef.current;
    const currentKey = tourKeyRef.current;

    if (!currentSteps || currentSteps.length === 0) return;

    if (driverRef.current) {
      try {
        driverRef.current.destroy();
      } catch (_) {}
    }

    // Filtra passos cujo elemento não existe no DOM (evita travar o tour)
    const stepsValidos = currentSteps.filter((step) => {
      if (!step.element) return true; // passos de intro (sem elemento) sempre ok
      const found = !!document.querySelector(step.element);
      if (!found)
        console.warn(
          `[Tour:${currentKey}] elemento não encontrado: ${step.element}`,
        );
      return found;
    });

    if (stepsValidos.length === 0) return;

    driverRef.current = driver({
      showProgress: true,
      progressText: "{{current}} de {{total}}",
      nextBtnText: "Próximo →",
      prevBtnText: "← Anterior",
      doneBtnText: "Concluir ✓",
      allowClose: true,
      smoothScroll: true,
      stagePadding: 8,
      stageRadius: 8,
      popoverClass: "tour-petshop",
      onDestroyed: () => {
        localStorage.setItem(`tour_visto_${currentKey}`, "1");
      },
      steps: stepsValidos,
    });

    driverRef.current.drive();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // deps vazio: usa refs para acessar valores atuais

  // Auto-start: roda UMA vez após montagem real.
  useEffect(() => {
    const key = tourKeyRef.current;
    const jaVisto = localStorage.getItem(`tour_visto_${key}`);
    if (jaVisto) return;

    const timer = setTimeout(() => {
      try {
        iniciarTour();
      } catch (err) {
        console.error(`[Tour:${key}] ERRO em iniciarTour:`, err);
      }
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, []); // deps vazio intencional

  // Destrói ao desmontar
  useEffect(() => {
    return () => {
      if (driverRef.current) {
        try {
          driverRef.current.destroy();
        } catch (_) {}
        driverRef.current = null;
      }
    };
  }, []);

  const resetarTour = useCallback(() => {
    localStorage.removeItem(`tour_visto_${tourKey}`);
  }, [tourKey]);

  return { iniciarTour, resetarTour };
}
