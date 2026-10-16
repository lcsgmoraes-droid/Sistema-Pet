import { Trash2 } from "lucide-react";
import BotaoInteracao from "../v2/BotaoInteracao/BotaoInteracao";
import IconActionButton from "../ui/IconActionButton";
import InputTelefone from "../v2/InputTelefone/InputTelefone";
import InputTexto from "../v2/InputTexto/InputTexto";
import InputTextoLongo from "../v2/InputTextoLongo/InputTextoLongo";

export default function ClientePessoaContatosTab({
  erros = {},
  formData,
  onBlurCampo,
  setFormData,
}) {
  const contatosAdicionais = formData.contatos_adicionais || [];
  const errosContatos = erros.contatos_adicionais || {};

  const atualizarContato = (index, campo, valor) => {
    setFormData((prev) => {
      const contatos = [...(prev.contatos_adicionais || [])];
      contatos[index] = { ...contatos[index], [campo]: valor };
      return { ...prev, contatos_adicionais: contatos };
    });
  };

  const removerContato = (index) => {
    setFormData((prev) => ({
      ...prev,
      contatos_adicionais: (prev.contatos_adicionais || []).filter((_, i) => i !== index),
    }));
  };

  const adicionarContato = () => {
    setFormData((prev) => ({
      ...prev,
      contatos_adicionais: [...(prev.contatos_adicionais || []), { numero: "", vinculo: "" }],
    }));
  };

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-stretch">
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

      <div className="flex w-full flex-1 flex-col gap-6">
        <InputTextoLongo
          id="pessoa-observacoes"
          label="Observações"
          linhas={4}
          preencherAltura
          value={formData.observacoes}
          onChange={(observacoes) => setFormData((prev) => ({ ...prev, observacoes }))}
          placeholder="Informações adicionais sobre a pessoa..."
        />

        <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Contatos adicionais
          </h4>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Cadastre o celular da mãe, irmã ou de outra pessoa. No PDV, esse número encontra o
            cadastro principal e seus benefícios.
          </p>

          <div className="mt-3 flex flex-col gap-3">
            {contatosAdicionais.map((contato, index) => (
              <div key={index} className="flex flex-wrap items-start gap-2">
                <div className="min-w-[180px] flex-1">
                  <InputTelefone
                    id={`pessoa-contato-adicional-numero-${index}`}
                    label="Celular"
                    tipo="celular"
                    value={contato.numero}
                    error={errosContatos[index]?.numero}
                    onChange={(numero) => atualizarContato(index, "numero", numero)}
                  />
                </div>
                <div className="min-w-[160px] flex-1">
                  <InputTexto
                    id={`pessoa-contato-adicional-vinculo-${index}`}
                    label="Vínculo"
                    value={contato.vinculo}
                    error={errosContatos[index]?.vinculo}
                    onChange={(vinculo) => atualizarContato(index, "vinculo", vinculo)}
                    placeholder="Mãe, irmã, pai..."
                    maxLength={60}
                  />
                </div>
                <IconActionButton
                  icon={Trash2}
                  intent="delete"
                  className="mt-6"
                  aria-label={`Remover contato adicional ${index + 1}`}
                  onClick={() => removerContato(index)}
                />
              </div>
            ))}

            <div>
              <BotaoInteracao tamanho="pequeno" onClick={adicionarContato}>
                + Adicionar contato
              </BotaoInteracao>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
