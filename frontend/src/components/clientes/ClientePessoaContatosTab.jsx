import InputTelefone from "../v2/InputTelefone/InputTelefone";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";

export default function ClientePessoaContatosTab({ erros = {}, formData, onBlurCampo, setFormData }) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
      <div className="flex w-full flex-col gap-4 lg:max-w-xs">
        <InputTelefone
          id="pessoa-celular"
          label="Celular"
          tipo="celular"
          required={formData.is_cliente}
          value={formData.celular}
          error={erros.celular}
          onChange={(celular) => setFormData((prev) => ({ ...prev, celular }))}
          onBlur={() => onBlurCampo?.("celular")}
          whatsapp={formData.celular_whatsapp}
          onChangeWhatsapp={(celular_whatsapp) =>
            setFormData((prev) => ({ ...prev, celular_whatsapp }))
          }
          help={
            formData.is_cliente
              ? "Obrigatório para clientes do app, e-commerce e loja física."
              : undefined
          }
        />

        <InputTelefone
          id="pessoa-telefone"
          label="Telefone fixo"
          tipo="fixo"
          value={formData.telefone}
          onChange={(telefone) => setFormData((prev) => ({ ...prev, telefone }))}
        />

        <InputTexto
          id="pessoa-email"
          label="E-mail"
          type="email"
          value={formData.email}
          onChange={(email) => setFormData((prev) => ({ ...prev, email }))}
          placeholder="email@exemplo.com"
        />
      </div>

      <div className="flex w-full flex-1 flex-col">
        <InputTextoLongo
          id="pessoa-observacoes"
          label="Observações"
          linhas={4}
          preencherAltura
          value={formData.observacoes}
          onChange={(observacoes) => setFormData((prev) => ({ ...prev, observacoes }))}
          placeholder="Informações adicionais sobre a pessoa..."
        />
      </div>
    </div>
  );
}
