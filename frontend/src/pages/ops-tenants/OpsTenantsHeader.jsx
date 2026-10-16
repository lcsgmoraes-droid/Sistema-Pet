import { useState } from "react";
import { FiMove, FiPlusCircle, FiRefreshCw, FiUsers } from "react-icons/fi";

import BotaoInteracao from "../../components/v2/BotaoInteracao/BotaoInteracao";
import OpsGrupoComercialOnboardingModal from "./OpsGrupoComercialOnboardingModal";
import OpsMoverLojaModal from "./OpsMoverLojaModal";

export default function OpsTenantsHeader({
  items,
  loading,
  onRefresh,
  onGrupoCriado,
  onDefinirProposta,
}) {
  const [modalAberto, setModalAberto] = useState(false);
  const [moverLojaAberto, setMoverLojaAberto] = useState(false);

  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold text-blue-600">
          <FiUsers className="h-5 w-5" />
          Gestao de tenants
        </div>
        <h1 className="mt-1 text-2xl font-bold text-slate-950">Clientes e catalogo base</h1>
        <p className="mt-1 text-sm text-slate-500">
          Visao operacional dos tenants e comando controlado para copiar o cadastro base da loja
          Lucas.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <BotaoInteracao icon={FiPlusCircle} onClick={() => setModalAberto(true)}>
          Novo grupo comercial (onboarding assistido)
        </BotaoInteracao>
        <BotaoInteracao icon={FiMove} onClick={() => setMoverLojaAberto(true)}>
          Mover loja entre grupos
        </BotaoInteracao>
        <BotaoInteracao icon={FiRefreshCw} loading={loading} onClick={onRefresh}>
          Atualizar
        </BotaoInteracao>
      </div>

      {modalAberto ? (
        <OpsGrupoComercialOnboardingModal
          onClose={() => setModalAberto(false)}
          onCreated={onGrupoCriado}
          onDefinirProposta={onDefinirProposta}
        />
      ) : null}

      {moverLojaAberto ? (
        <OpsMoverLojaModal
          items={items}
          onClose={() => setMoverLojaAberto(false)}
          onMoved={onGrupoCriado}
        />
      ) : null}
    </div>
  );
}
