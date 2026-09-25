import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

const OPCOES_TIPO_ENDERECO = [
  { value: "principal", label: "Principal" },
  { value: "entrega", label: "Entrega" },
  { value: "cobranca", label: "Cobrança" },
  { value: "comercial", label: "Comercial" },
  { value: "residencial", label: "Residencial" },
  { value: "trabalho", label: "Trabalho" },
];

const OPCOES_TIPO_ENDERECO_ANTIGO_PRINCIPAL = OPCOES_TIPO_ENDERECO.filter(
  (opcao) => opcao.value !== "principal",
);

function ClientePessoaEnderecoModal({
  enderecoAtual,
  fecharModalEndereco,
  loadingCepEndereco,
  principalTemDados,
  salvarEndereco,
  buscarCepModal,
  setEnderecoAtual,
}) {
  const [mostrandoConfirmacao, setMostrandoConfirmacao] = useState(false);
  const [tipoAntigoPrincipal, setTipoAntigoPrincipal] = useState("residencial");

  if (!enderecoAtual) return null;

  const ehEndrecoPrincipalAtual = enderecoAtual.index === "principal";
  const titulo = enderecoAtual.index !== undefined ? "Editar Endereço" : "Adicionar Endereço";

  const aoClicarSalvar = () => {
    const promovendoAPrincipal = enderecoAtual.tipo === "principal" && !ehEndrecoPrincipalAtual;
    if (promovendoAPrincipal && principalTemDados) {
      setMostrandoConfirmacao(true);
      return;
    }
    salvarEndereco();
  };

  if (mostrandoConfirmacao) {
    return (
      <ModalPadrao
        titulo="Trocar o endereço principal?"
        onFechar={fecharModalEndereco}
        rodape={
          <>
            <BotaoCancelar onClick={() => setMostrandoConfirmacao(false)}>
              Cancelar e mudar o tipo
            </BotaoCancelar>
            <BotaoSalva onClick={() => salvarEndereco(tipoAntigoPrincipal)}>
              Confirmar substituição
            </BotaoSalva>
          </>
        }
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-500/30 dark:bg-amber-500/10">
            <AlertTriangle
              className="mt-0.5 h-4 w-4 flex-none text-amber-600 dark:text-amber-400"
              aria-hidden="true"
            />
            <p className="text-sm text-amber-900 dark:text-amber-200">
              Só pode haver um endereço Principal. Este endereço vai virar o novo principal, e o
              que é principal hoje deixa de ser — escolha abaixo para qual tipo ele passa.
            </p>
          </div>

          <InputCombobox
            id="endereco-tipo-antigo-principal"
            label="Novo tipo do endereço que deixará de ser principal"
            required
            opcoes={OPCOES_TIPO_ENDERECO_ANTIGO_PRINCIPAL}
            permitirLimpar={false}
            value={tipoAntigoPrincipal}
            onChange={setTipoAntigoPrincipal}
          />
        </div>
      </ModalPadrao>
    );
  }

  return (
    <ModalPadrao
      titulo={titulo}
      tamanho="grande"
      onFechar={fecharModalEndereco}
      rodape={
        <>
          <BotaoCancelar onClick={fecharModalEndereco}>Cancelar</BotaoCancelar>
          <BotaoSalva onClick={aoClicarSalvar}>Salvar endereço</BotaoSalva>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <InputCombobox
            id="endereco-tipo"
            label="Tipo de endereço"
            required
            disabled={ehEndrecoPrincipalAtual}
            help={
              ehEndrecoPrincipalAtual
                ? "Para trocar quem é o principal, marque outro endereço como Principal."
                : undefined
            }
            opcoes={OPCOES_TIPO_ENDERECO}
            permitirLimpar={false}
            value={enderecoAtual.tipo}
            onChange={(tipo) => setEnderecoAtual({ ...enderecoAtual, tipo })}
          />

          <InputTexto
            id="endereco-apelido"
            label="Apelido (opcional)"
            value={enderecoAtual.apelido}
            onChange={(apelido) => setEnderecoAtual({ ...enderecoAtual, apelido })}
            placeholder="Ex: Casa da mãe, Escritório, Loja"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <InputTexto
            id="endereco-cep"
            label="CEP"
            required
            value={enderecoAtual.cep}
            onChange={(valorDigitado) => {
              const digitos = valorDigitado.replace(/\D/g, "");
              const formatado =
                digitos.length > 5 ? `${digitos.slice(0, 5)}-${digitos.slice(5, 8)}` : digitos;
              setEnderecoAtual({ ...enderecoAtual, cep: formatado });
            }}
            onBlur={(evento) => buscarCepModal(evento.target.value)}
            maxLength={9}
            placeholder="00000-000"
            help={loadingCepEndereco ? "Buscando endereço..." : undefined}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            <InputTexto
              id="endereco-logradouro"
              label="Endereço"
              required
              value={enderecoAtual.endereco}
              onChange={(endereco) => setEnderecoAtual({ ...enderecoAtual, endereco })}
              placeholder="Rua, Avenida, etc."
            />
          </div>

          <InputTexto
            id="endereco-numero"
            label="Número"
            value={enderecoAtual.numero}
            onChange={(numero) => setEnderecoAtual({ ...enderecoAtual, numero })}
            placeholder="123"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <InputTexto
            id="endereco-complemento"
            label="Complemento"
            value={enderecoAtual.complemento}
            onChange={(complemento) => setEnderecoAtual({ ...enderecoAtual, complemento })}
            placeholder="Apto, Bloco, Sala..."
          />

          <InputTexto
            id="endereco-bairro"
            label="Bairro"
            value={enderecoAtual.bairro}
            onChange={(bairro) => setEnderecoAtual({ ...enderecoAtual, bairro })}
            placeholder="Centro, Jardim..."
          />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            <InputTexto
              id="endereco-cidade"
              label="Cidade"
              required
              value={enderecoAtual.cidade}
              onChange={(cidade) => setEnderecoAtual({ ...enderecoAtual, cidade })}
              placeholder="São Paulo"
            />
          </div>

          <InputTexto
            id="endereco-estado"
            label="Estado"
            value={enderecoAtual.estado}
            onChange={(estado) => setEnderecoAtual({ ...enderecoAtual, estado })}
            maxLength={2}
            placeholder="SP"
          />
        </div>

        <p className="text-xs text-gray-500">* Campos obrigatórios</p>
      </div>
    </ModalPadrao>
  );
}

export default ClientePessoaEnderecoModal;
