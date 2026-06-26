import ActionButton from "../../components/ui/ActionButton";

export default function ProdutosValidadeHeader({ controller }) {
  return (
    <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 md:text-3xl">
          Produtos com validade proxima
        </h1>
        <p className="mt-2 max-w-4xl text-sm text-gray-600">
          A tela considera o lote mais urgente primeiro, pagina em blocos leves e deixa pronto o
          trabalho comercial: enxergar o risco, priorizar o que vence antes e abrir campanhas sem
          perder tempo.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <ActionButton onClick={controller.irParaCampanhas} intent="create" tone="soft">
          Abrir campanhas
        </ActionButton>
        <ActionButton
          onClick={controller.exportarCsv}
          disabled={controller.exportando}
          intent="edit"
          loading={controller.exportando}
          tone="soft"
        >
          Exportar CSV
        </ActionButton>
        <ActionButton onClick={controller.irParaProdutos} tone="soft">
          Voltar para produtos
        </ActionButton>
      </div>
    </div>
  );
}
