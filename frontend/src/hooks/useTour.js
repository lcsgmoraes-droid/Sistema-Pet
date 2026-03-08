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
 * @param {string} tourKey - Chave única da página (ex: "dashboard", "pdv", "pessoas")
 * @param {Array}  steps   - Array de passos do driver.js
 * @param {Object} [opcoes]
 * @param {number} [opcoes.delay=800] - Delay em ms antes de iniciar (para a DOM renderizar)
 * @returns {{ iniciarTour: Function, resetarTour: Function }}
 */
export function useTour(tourKey, steps, { delay = 800 } = {}) {
  const driverRef = useRef(null);

  const iniciarTour = useCallback(() => {
    if (!steps || steps.length === 0) return;

    // Destrói instância anterior se existir
    if (driverRef.current) {
      driverRef.current.destroy();
    }

    driverRef.current = driver({
      showProgress: true,
      progressText: "{{current}} de {{total}}",
      nextBtnText: "Próximo →",
      prevBtnText: "← Anterior",
      doneBtnText: "Concluir ✓",
      overlayClickBtnText: "Próximo →",
      allowClose: true,
      smoothScroll: true,
      stagePadding: 8,
      stageRadius: 8,
      popoverClass: "tour-petshop",
      onDestroyed: () => {
        localStorage.setItem(`tour_visto_${tourKey}`, "1");
      },
      steps,
    });

    driverRef.current.drive();
  }, [tourKey, steps]);

  // Inicia automaticamente na primeira visita
  useEffect(() => {
    const jaVisto = localStorage.getItem(`tour_visto_${tourKey}`);
    if (jaVisto) return;

    const timer = setTimeout(() => {
      iniciarTour();
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [tourKey, delay, iniciarTour]);

  // Destrói ao desmontar o componente
  useEffect(() => {
    return () => {
      if (driverRef.current) {
        driverRef.current.destroy();
      }
    };
  }, []);

  const resetarTour = useCallback(() => {
    localStorage.removeItem(`tour_visto_${tourKey}`);
  }, [tourKey]);

  return { iniciarTour, resetarTour };
}
