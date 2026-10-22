import InputCheckTexto from "../v2/InputCheckTexto/InputCheckTexto";
import InputDataHora from "../v2/InputDataHora/InputDataHora";
import InputMoeda from "../v2/InputMoeda/InputMoeda";
import PromocaoFields from "./PromocaoFields";
import MargemPrecoField from "./MargemPrecoField";
import IfoodProdutoSection from "./IfoodProdutoSection";

export default function ProdutosNovoPrecosSection({
  camposEmEdicao,
  formData,
  handleChange,
  imagens,
  onCorrigirIfood,
  setCamposEmEdicao,
}) {
  if (formData.tipo_produto === "PAI") return null;

  const lojaFisicaAtiva = formData.ativo !== false && formData.situacao !== false;

  return (
    <>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <InputMoeda
          id="produto-preco-custo"
          label="Preço de custo (R$)"
          value={formData.preco_custo}
          onChange={(value) => handleChange("preco_custo", value)}
        />
        <MargemPrecoField
          camposEmEdicao={camposEmEdicao}
          formData={formData}
          handleChange={handleChange}
          setCamposEmEdicao={setCamposEmEdicao}
        />
        <InputMoeda
          id="produto-preco-venda"
          label="Preço de venda (R$)"
          required
          value={formData.preco_venda}
          onChange={(value) => handleChange("preco_venda", value)}
        />
      </div>

      <PromocaoFields
        title="Promoção ERP / Loja física"
        description="Durante o período, este preço entra automaticamente no PDV."
        startLabel="Início da promoção"
        endLabel="Fim da promoção"
        startValue={formData.data_inicio_promocao}
        endValue={formData.data_fim_promocao}
        onStartChange={(value) => handleChange("data_inicio_promocao", value)}
        onEndChange={(value) => handleChange("data_fim_promocao", value)}
        priceControl={
          <InputMoeda
            id="produto-preco-promocional"
            label="Preço promocional (R$)"
            value={formData.preco_promocional}
            onChange={(value) => handleChange("preco_promocional", value > 0 ? value : "")}
          />
        }
      />

      <section className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-950/40">
        <div>
          <h3 className="v2-titulo-secao">Canais de venda</h3>
          <p className="v2-texto-ajuda mt-1">
            Preço e seleção são desta loja. No app e ecommerce, preço vazio usa o preço de venda
            padrão.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {[
            { campo: "ecommerce", nome: "Ecommerce" },
            { campo: "app", nome: "App móvel" },
          ].map(({ campo, nome }) => (
            <div key={campo} className="space-y-3">
              <InputCheckTexto
                id={`produto-anunciar-${campo}`}
                checked={lojaFisicaAtiva && formData[`anunciar_${campo}`] !== false}
                disabled={!lojaFisicaAtiva}
                onChange={(checked) => handleChange(`anunciar_${campo}`, checked)}
              >
                Exibir no {nome}
              </InputCheckTexto>
              <InputMoeda
                id={`produto-preco-${campo}`}
                label={`Preço específico ${nome} (R$)`}
                value={formData[`preco_${campo}`]}
                onChange={(value) => handleChange(`preco_${campo}`, value > 0 ? value : "")}
              />
              <InputMoeda
                id={`produto-preco-${campo}-promo`}
                label={`Preço promocional ${nome} (R$)`}
                value={formData[`preco_${campo}_promo`]}
                onChange={(value) => handleChange(`preco_${campo}_promo`, value > 0 ? value : "")}
              />
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <InputDataHora
                  id={`produto-${campo}-promo-inicio`}
                  label="Início da promoção"
                  value={formData[`preco_${campo}_promo_inicio`] || ""}
                  onChange={(value) => handleChange(`preco_${campo}_promo_inicio`, value)}
                />
                <InputDataHora
                  id={`produto-${campo}-promo-fim`}
                  label="Fim da promoção"
                  value={formData[`preco_${campo}_promo_fim`] || ""}
                  onChange={(value) => handleChange(`preco_${campo}_promo_fim`, value)}
                />
              </div>
            </div>
          ))}
        </div>
        {!lojaFisicaAtiva ? (
          <p className="text-xs text-amber-700 dark:text-amber-300">
            Produto inativo na loja física: ecommerce e app ficam desativados automaticamente.
          </p>
        ) : null}

        <IfoodProdutoSection
          formData={formData}
          handleChange={handleChange}
          imagens={imagens}
          onCorrigir={onCorrigirIfood}
        />
      </section>
    </>
  );
}
