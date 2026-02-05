/**
 * Página: IA - Fluxo de Caixa Preditivo
 * ABA 5: Dashboard principal da IA
 */

import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import DashboardFluxoCaixa from '../components/IA/DashboardFluxoCaixa';

export default function IAFluxoCaixa() {
  const { user } = useAuth();

  return (
    <div className="max-w-7xl mx-auto">
      <DashboardFluxoCaixa userId={user?.id || 1} />
    </div>
  );
}
