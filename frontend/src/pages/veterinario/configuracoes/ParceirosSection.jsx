import ParceiroFormPanel from "./ParceiroFormPanel";
import ParceirosHeader from "./ParceirosHeader";
import ParceirosLista from "./ParceirosLista";

export default function ParceirosSection({
  form,
  mostrarForm,
  onCancel,
  onChangeForm,
  onRemover,
  onSave,
  onToggleAtivo,
  onToggleForm,
  parceiros,
  salvando,
  tenantsVet,
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <ParceirosHeader
        mostrarForm={mostrarForm}
        onToggleForm={onToggleForm}
        totalParceiros={parceiros.length}
      />

      {mostrarForm && (
        <ParceiroFormPanel
          form={form}
          onCancel={onCancel}
          onChangeForm={onChangeForm}
          onSave={onSave}
          salvando={salvando}
          tenantsVet={tenantsVet}
        />
      )}

      <ParceirosLista
        onRemover={onRemover}
        onToggleAtivo={onToggleAtivo}
        parceiros={parceiros}
      />
    </div>
  );
}
