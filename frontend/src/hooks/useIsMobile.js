import { useState, useEffect } from 'react';

/**
 * Hook customizado para detectar se está em dispositivo móvel
 * 
 * Uso:
 * const isMobile = useIsMobile();
 * const isMobile = useIsMobile(1024); // breakpoint customizado
 */
export const useIsMobile = (breakpoint = 768) => {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth < breakpoint : false
  );

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < breakpoint);
    };

    window.addEventListener('resize', handleResize);
    
    // Chamar imediatamente para garantir valor correto
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, [breakpoint]);

  return isMobile;
};

/**
 * Hook para detectar orientação do dispositivo
 */
export const useOrientation = () => {
  const [orientation, setOrientation] = useState(
    typeof window !== 'undefined'
      ? window.innerWidth > window.innerHeight
        ? 'landscape'
        : 'portrait'
      : 'portrait'
  );

  useEffect(() => {
    const handleResize = () => {
      setOrientation(
        window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'
      );
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return orientation;
};

/**
 * Hook para detectar tipo de dispositivo (mobile, tablet, desktop)
 */
export const useDeviceType = () => {
  const [deviceType, setDeviceType] = useState('desktop');

  useEffect(() => {
    const getDeviceType = () => {
      const width = window.innerWidth;
      if (width < 768) return 'mobile';
      if (width < 1024) return 'tablet';
      return 'desktop';
    };

    const handleResize = () => {
      setDeviceType(getDeviceType());
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return deviceType;
};

export default useIsMobile;
