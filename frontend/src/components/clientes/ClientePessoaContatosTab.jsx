import InputTelefone from "../v2/InputTelefone/InputTelefone";
import InputTexto from "../v2/InputTexto/InputTexto";

export default function ClientePessoaContatosTab({ erros = {}, formData, onBlurCampo, setFormData }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4">
        <div className="w-full max-w-[230px]">
          <InputTelefone
            id="pessoa-celular"
            label="Celular"
            tipo="celular"
            required={formData.tipo_cadastro === "cliente"}
            value={formData.celular}
            error={erros.celular}
            onChange={(celular) => setFormData((prev) => ({ ...prev, celular }))}
            onBlur={() => onBlurCampo?.("celular")}
            whatsapp={formData.celular_whatsapp}
            onChangeWhatsapp={(celular_whatsapp) =>
              setFormData((prev) => ({ ...prev, celular_whatsapp }))
            }
            help={
              formData.tipo_cadastro === "cliente"
                ? "Obrigatório para clientes do app, e-commerce e loja física."
                : undefined
            }
          />
        </div>

        <div className="w-full max-w-[230px]">
          <InputTelefone
            id="pessoa-telefone"
            label="Telefone fixo"
            tipo="fixo"
            value={formData.telefone}
            onChange={(telefone) => setFormData((prev) => ({ ...prev, telefone }))}
          />
        </div>

        <div className="w-full max-w-sm">
          <InputTexto
            id="pessoa-email"
            label="E-mail"
            type="email"
            value={formData.email}
            onChange={(email) => setFormData((prev) => ({ ...prev, email }))}
            placeholder="email@exemplo.com"
          />
        </div>
      </div>
    </div>
  );
}
