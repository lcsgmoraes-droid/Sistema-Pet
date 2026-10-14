import CampoIdadeInteligente from "../../components/CampoIdadeInteligente";
import InputCombobox from "../../components/v2/InputCombobox/InputCombobox";
import InputTexto from "../../components/v2/InputTexto/InputTexto";
import PetAvatar from "../../components/ui/PetAvatar";

const OPCOES_PORTE = [
  { value: "Mini", label: "Mini" },
  { value: "Pequeno", label: "Pequeno" },
  { value: "Médio", label: "Médio" },
  { value: "Grande", label: "Grande" },
  { value: "Gigante", label: "Gigante" },
];

// Aceita digitos com virgula ou ponto, igual ao InputQuantidade — mas sem forcar um minimo:
// peso do pet e uma caracteristica opcional, pode ficar em branco indefinidamente.
function aoDigitarPeso(bruto, setFormData) {
  if (bruto === "" || /^[0-9]*[.,]?[0-9]*$/.test(bruto)) {
    setFormData((prev) => ({ ...prev, peso: bruto }));
  }
}

export default function PetFormCaracteristicasTab({ formData, setField, setFormData }) {
  return (
    <div className="space-y-5">
      <div className="w-full sm:max-w-sm">
        <CampoIdadeInteligente
          value={formData.idade_aproximada}
          onChange={(meses) =>
            setFormData((prev) => ({ ...prev, idade_aproximada: meses, data_nascimento: "" }))
          }
          name="idade_aproximada"
          label="Idade do Pet"
          mostrarDataNascimento={true}
        />
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
        <div className="w-full sm:max-w-[120px]">
          <InputTexto
            id="pet-peso"
            label="Peso (kg)"
            value={formData.peso}
            onChange={(bruto) => aoDigitarPeso(bruto, setFormData)}
            inputMode="decimal"
            placeholder="Ex: 5.5"
          />
        </div>

        <div className="w-full sm:max-w-[180px]">
          <InputCombobox
            id="pet-porte"
            label="Porte"
            opcoes={OPCOES_PORTE}
            value={formData.porte}
            onChange={setField("porte")}
            placeholder="Selecione..."
          />
        </div>

        <div className="w-full sm:max-w-[200px]">
          <InputTexto
            id="pet-cor"
            label="Cor/Pelagem"
            value={formData.cor}
            onChange={setField("cor")}
            placeholder="Ex: Preto, Branco, Caramelo"
          />
        </div>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
        <div className="w-full sm:max-w-[220px]">
          <InputTexto
            id="pet-microchip"
            label="Microchip"
            value={formData.microchip}
            onChange={setField("microchip")}
            inputMode="numeric"
            placeholder="Número do microchip"
          />
        </div>

        <div className="w-full sm:max-w-[160px]">
          <InputTexto
            id="pet-tipo-sanguineo"
            label="Tipo sanguíneo"
            value={formData.tipo_sanguineo}
            onChange={setField("tipo_sanguineo")}
            placeholder="Ex: DEA 1.1, A, B"
          />
        </div>

        <div className="w-full sm:max-w-[220px]">
          <InputTexto
            id="pet-pedigree"
            label="Registro de pedigree"
            value={formData.pedigree_registro}
            onChange={setField("pedigree_registro")}
            placeholder="Código do registro, se houver"
          />
        </div>
      </div>

      <div className="flex items-end gap-3">
        <div className="w-full sm:max-w-sm">
          <InputTexto
            id="pet-foto-url"
            label="URL da Foto"
            type="url"
            value={formData.foto_url}
            onChange={setField("foto_url")}
            placeholder="https://exemplo.com/foto-do-pet.jpg"
          />
        </div>
        <PetAvatar name={formData.nome} url={formData.foto_url} size="lg" />
      </div>
    </div>
  );
}
