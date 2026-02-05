/**
 * Performance Optimization Hook
 * Monitora performance e detecta problemas
 */

import { useEffect, useRef } from 'react';

interface PerformanceMetrics {
  renderTime: number;
  memoryUsage?: number;
  fps: number;
}

export const usePerformanceMonitor = (componentName: string) => {
  const renderCount = useRef(0);
  const renderStart = useRef(performance.now());
  const fpsRef = useRef<number[]>([]);
  
  useEffect(() => {
    renderCount.current++;
    const renderTime = performance.now() - renderStart.current;
    
    // Log slow renders (>16ms = below 60fps)
    if (renderTime > 16 && process.env.NODE_ENV === 'development') {
      console.warn(`[Performance] ${componentName} render took ${renderTime.toFixed(2)}ms`);
    }
    
    // Track FPS
    const now = performance.now();
    fpsRef.current.push(now);
    fpsRef.current = fpsRef.current.filter(time => now - time < 1000);
    
    renderStart.current = performance.now();
  });
  
  useEffect(() => {
    // Memory monitoring (if available)
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      const usedMemoryMB = memory.usedJSHeapSize / 1048576;
      
      if (usedMemoryMB > 100) {
        console.warn(`[Performance] ${componentName} using ${usedMemoryMB.toFixed(2)}MB memory`);
      }
    }
  }, [componentName]);
  
  return {
    renderCount: renderCount.current,
    fps: fpsRef.current.length
  };
};

/**
 * Debounce Hook
 */
export const useDebounce = <T,>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = React.useState<T>(value);
  
  React.useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  
  return debouncedValue;
};

/**
 * Throttle Hook
 */
export const useThrottle = <T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T => {
  const lastRan = useRef(Date.now());
  
  return React.useCallback(
    ((...args) => {
      if (Date.now() - lastRan.current >= delay) {
        callback(...args);
        lastRan.current = Date.now();
      }
    }) as T,
    [callback, delay]
  );
};

import React from 'react';
