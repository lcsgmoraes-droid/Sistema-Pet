import BotaoCancelar from "../v2/BotaoCancelar/BotaoCancelar";
import BotaoSalva from "../v2/BotaoSalva/BotaoSalva";
import InputCombobox from "../v2/InputCombobox/InputCombobox";
import InputTexto from "../v2/InputTexto/InputTexto";
import ModalPadrao from "../v2/ModalPadrao/ModalPadrao";

const OPCOES_TIPO_ENDERECO = [
  { value: "entrega", label: "Entrega" },
  { value: "cobranca", label: "Cobrança" },
  { value: "comercial", label: "Comercial" },
  { value: "residencial", label: "Residencial" },
  { value: "trabalho", label: "Trabalho" },
];

function ClientePessoaEnderecoModal({
  enderecoAtual,
  fecharModalEndereco,
  loadingCepEndereco,
  salvarEndereco,
  buscarCepModal,
  setEnderecoAtual,
}) {
  if (!enderecoAtual) return null;

  const ehPrincipal = enderecoAtual.index === "principal";
  const titulo = ehPrincipal
    ? "Editar Endereço Principal"
    : enderecoAtual.index !== undefined
      ? "Editar Endereço"
      : "Adicionar Novo Endereço";

  return (
    <ModalPadrao
      titulo={titulo}
      tamanho="grande"
      onFechar={fecharModalEndereco}
      rodape={
        <>
          <BotaoCancelar onClick={fecharModalEndereco}>Cancelar</BotaoCancelar>
          <BotaoSalva onClick={salvarEndereco}>Salvar endereço</BotaoSalva>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {ehPrincipal ? (
            <div>
              <span className="text-xs font-medium text-slate-600">Tipo de endereço</span>
              <p className="mt-1 flex h-9 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm text-slate-500">
                Principal — endereço padrão do cadastro
              </p>
            </div>
          ) : (
            <InputCombobox
              id="endereco-tipo"
              label="Tipo de endereço"
              required
              opcoes={OPCOES_TIPO_ENDERECO}
              permitirLimpar={false}
              value={enderecoAtual.tipo}
              onChange={(tipo) => setEnderecoAtual({ ...enderecoAtual, tipo })}
            />
          )}

          {ehPrincipal ? null : (
            <InputTexto
              id="endereco-apelido"
              label="Apelido (opcional)"
              value={enderecoAtual.apelido}
              onChange={(apelido) => setEnderecoAtual({ ...enderecoAtual, apelido })}
              placeholder="Ex: Casa da mãe, Escritório, Loja"
            />
          )}
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
