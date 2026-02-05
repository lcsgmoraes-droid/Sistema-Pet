import React, { memo } from 'react';

interface ConnectionStatusProps {
  isConnected: boolean;
  socketId?: string;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = memo(({ 
  isConnected, 
  socketId 
}) => {
  return (
    <div className={`
      flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
      ${isConnected 
        ? 'bg-green-50 text-green-700 border border-green-200' 
        : 'bg-red-50 text-red-700 border border-red-200'
      }
    `}>
      {/* Status Indicator */}
      <div className="relative">
        <div className={`
          w-2 h-2 rounded-full
          ${isConnected ? 'bg-green-500' : 'bg-red-500'}
        `}></div>
        {isConnected && (
          <div className="absolute inset-0 w-2 h-2 bg-green-500 rounded-full animate-ping opacity-75"></div>
        )}
      </div>
      
      {/* Status Text */}
      <span>
        {isConnected ? 'Online' : 'Desconectado'}
      </span>
      
      {/* Socket ID (on hover) */}
      {isConnected && socketId && (
        <span 
          className="text-[10px] opacity-50 font-mono"
          title={`Socket ID: ${socketId}`}
        >
          • {socketId.substring(0, 6)}
        </span>
      )}
    </div>
  );
});
