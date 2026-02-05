import { useState, useEffect } from 'react';
import { Calculator, Minimize2, Maximize2 } from 'lucide-react';

/**
 * Botão Flutuante da Calculadora de Ração
 * =======================================
 * 
 * - Aparece em TODAS as telas do sistema
 * - Minimizável (fica só o ícone pequeno)
 * - Arrastável para reposicionar
 */
export default function FloatingCalculatorButton({ onClick }) {
  const [isDragging, setIsDragging] = useState(false);
  const [hasDragged, setHasDragged] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [dragStartPos, setDragStartPos] = useState({ x: 0, y: 0 });
  
  // Função para garantir posição segura
  const getSafePosition = (pos, isMinimized) => {
    const maxX = window.innerWidth - (isMinimized ? 60 : 200);
    const maxY = window.innerHeight - (isMinimized ? 60 : 300);
    
    return {
      x: Math.max(20, Math.min(pos.x, maxX)),
      y: Math.max(20, Math.min(pos.y, maxY))
    };
  };
  
  const [position, setPosition] = useState(() => {
    const saved = localStorage.getItem('calc_button_pos');
    const defaultPos = { 
      x: window.innerWidth - 150, 
      y: window.innerHeight - 150 
    };
    
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // Verificar se a posição salva está dentro da tela
        return getSafePosition(parsed, true);
      } catch {
        return defaultPos;
      }
    }
    return defaultPos;
  });

  // Estado de minimizado
  const [minimizado, setMinimizado] = useState(() => {
    return localStorage.getItem('calc_button_minimizado') === 'true';
  });

  const handleMouseDown = (e) => {
    // Permitir arrastar de qualquer lugar EXCETO o botão de expandir/minimizar
    const isToggleButton = e.target.closest('button[title="Expandir"], button[title="Minimizar"]');
    
    // Se clicou no botão de toggle, não arrastar
    if (isToggleButton) {
      e.stopPropagation();
      return;
    }
    
    setIsDragging(true);
    setHasDragged(false);
    setDragStartPos({ x: e.clientX, y: e.clientY });
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      // Calcular distância do ponto inicial
      const distance = Math.sqrt(
        Math.pow(e.clientX - dragStartPos.x, 2) + 
        Math.pow(e.clientY - dragStartPos.y, 2)
      );
      
      // Só considerar como arraste se mover mais de 5 pixels
      if (distance > 5) {
        setHasDragged(true);
      }
      
      const newX = e.clientX - dragOffset.x;
      const newY = e.clientY - dragOffset.y;
      
      const maxX = window.innerWidth - (minimizado ? 60 : 200);
      const maxY = window.innerHeight - (minimizado ? 60 : 300);
      
      const finalPos = {
        x: Math.max(20, Math.min(newX, maxX)),
        y: Math.max(20, Math.min(newY, maxY))
      };
      
      setPosition(finalPos);
    }
  };

  const handleMouseUp = () => {
    if (isDragging) {
      setIsDragging(false);
      localStorage.setItem('calc_button_pos', JSON.stringify(position));
    }
  };

  // Event listeners globais
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset, position]);

  const handleClick = (e) => {
    console.log('🖱️ Clique detectado, hasDragged:', hasDragged);
    // Só abre se não houve arraste
    if (!hasDragged) {
      console.log('✅ Abrindo calculadora...');
      onClick();
    } else {
      console.log('❌ Ignorando clique (foi arraste)');
    }
  };

  const handleToggleMinimize = (e) => {
    e.stopPropagation();
    const newVal = !minimizado;
    
    // Ao expandir, reposicionar se estiver muito perto das bordas
    if (!newVal) { // se vai expandir (newVal = false = expandido)
      const safePos = getSafePosition(position, false);
      if (safePos.x !== position.x || safePos.y !== position.y) {
        setPosition(safePos);
        localStorage.setItem('calc_button_pos', JSON.stringify(safePos));
      }
    }
    
    setMinimizado(newVal);
    localStorage.setItem('calc_button_minimizado', newVal.toString());
  };

  // Ajustar posição ao redimensionar janela
  useEffect(() => {
    const handleResize = () => {
      const safePos = getSafePosition(position, minimizado);
      if (safePos.x !== position.x || safePos.y !== position.y) {
        setPosition(safePos);
        localStorage.setItem('calc_button_pos', JSON.stringify(safePos));
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [position, minimizado]);

  return (
    <div 
      className="fixed z-50"
      style={{ 
        left: `${position.x}px`, 
        top: `${position.y}px`
      }}
    >
      {/* Versão Minimizada */}
      {minimizado ? (
        <div 
          className="relative group cursor-move"
          onMouseDown={handleMouseDown}
        >
          <button
            onClick={handleClick}
            onMouseDown={(e) => e.stopPropagation()} 
            className="calc-button-main
              flex items-center justify-center
              w-12 h-12
              bg-gradient-to-br from-orange-500 to-orange-600
              hover:from-orange-600 hover:to-orange-700
              text-white
              rounded-full
              shadow-lg hover:shadow-xl
              transition-all duration-200
              hover:scale-110
              active:scale-95
              pointer-events-auto
            "
            title="Calculadora de Ração"
          >
            <Calculator size={20} />
          </button>

          {/* Botão expandir (aparece ao hover) */}
          <button
            onClick={handleToggleMinimize}
            onMouseDown={(e) => e.stopPropagation()}
            className="
              absolute -bottom-1 -right-1
              bg-blue-600 hover:bg-blue-700
              text-white
              w-6 h-6
              rounded-full
              flex items-center justify-center
              opacity-0 group-hover:opacity-100
              transition-opacity
              shadow-md
            "
            title="Expandir"
          >
            <Maximize2 size={12} />
          </button>
        </div>
      ) : (
        /* Versão Expandida */
        <div 
          className="
            flex flex-col gap-2
            bg-white
            rounded-2xl
            shadow-2xl
            p-3
            border-2 border-orange-500
            min-w-[140px]
          "
          style={{ cursor: isDragging ? 'grabbing' : 'default' }}
        >
          {/* Header - Área de arraste */}
          <div 
            className="flex items-center justify-between gap-2 drag-handle cursor-move"
            onMouseDown={handleMouseDown}
          >
            <div className="flex items-center gap-2 pointer-events-none">
              <div className="
                w-10 h-10
                bg-gradient-to-br from-orange-500 to-orange-600
                rounded-full
                flex items-center justify-center
                text-white
              ">
                <Calculator size={20} />
              </div>
              <span className="text-xs font-semibold text-gray-700">
                Calculadora
              </span>
            </div>
            
            {/* Botão minimizar */}
            <button
              onClick={handleToggleMinimize}
              className="
                p-1 hover:bg-gray-100 
                rounded-lg transition-colors
                pointer-events-auto
              "
              title="Minimizar"
            >
              <Minimize2 size={16} className="text-gray-500" />
            </button>
          </div>

          {/* Botão Calcular */}
          <button
            onClick={handleClick}
            className="calc-button-main
              w-full
              px-4 py-2
              bg-gradient-to-r from-orange-500 to-orange-600
              hover:from-orange-600 hover:to-orange-700
              text-white
              rounded-lg
              font-medium text-sm
              transition-all
              hover:shadow-lg
            "
          >
            🥫 Calcular Ração
          </button>

          {/* Info adicional */}
          <div className="text-[10px] text-gray-500 text-center">
            Arraste para mover
          </div>
        </div>
      )}
    </div>
  );
}
