import ProdutosNovoCaracteristicasTab from './ProdutosNovoCaracteristicasTab';
import ProdutosNovoComposicaoTab from './ProdutosNovoComposicaoTab';
import ProdutosNovoEstoqueTab from './ProdutosNovoEstoqueTab';
import ProdutosNovoFooterActions from './ProdutosNovoFooterActions';
import ProdutosNovoFornecedoresTab from './ProdutosNovoFornecedoresTab';
import ProdutosNovoHeader from './ProdutosNovoHeader';
import ProdutosNovoImagensTab from './ProdutosNovoImagensTab';
import ProdutosNovoRacaoTab from './ProdutosNovoRacaoTab';
import ProdutosNovoRecorrenciaTab from './ProdutosNovoRecorrenciaTab';
import ProdutosNovoStatusBanners from './ProdutosNovoStatusBanners';
import ProdutosNovoTabs from './ProdutosNovoTabs';
import ProdutosNovoTributacaoTab from './ProdutosNovoTributacaoTab';
import ProdutosNovoVariacoesTab from './ProdutosNovoVariacoesTab';

export default function ProdutosNovoMainContent({
  canShowComposicaoTab,
  canShowVariacoesTab,
  caracteristicasTabProps,
  composicaoTabProps,
  estoqueTabProps,
  footerProps,
  fornecedoresTabProps,
  handleSubmit,
  headerProps,
  imagensTabProps,
  racaoTabProps,
  recorrenciaTabProps,
  statusBannersProps,
  tabsProps,
  tributacaoTabProps,
  variacoesTabProps,
}) {
  return (
    <div className="p-6">
      <ProdutosNovoHeader {...headerProps} />

      <ProdutosNovoTabs {...tabsProps} />

      <ProdutosNovoStatusBanners {...statusBannersProps} />

      <form onSubmit={handleSubmit}>
        <div className="bg-white rounded-lg shadow-sm p-6">
          {tabsProps.abaAtiva === 1 && <ProdutosNovoCaracteristicasTab {...caracteristicasTabProps} />}
          {tabsProps.abaAtiva === 2 && <ProdutosNovoImagensTab {...imagensTabProps} />}
          {tabsProps.abaAtiva === 3 && <ProdutosNovoEstoqueTab {...estoqueTabProps} />}
          {tabsProps.abaAtiva === 4 && <ProdutosNovoFornecedoresTab {...fornecedoresTabProps} />}
          {tabsProps.abaAtiva === 5 && <ProdutosNovoTributacaoTab {...tributacaoTabProps} />}
          {tabsProps.abaAtiva === 6 && <ProdutosNovoRecorrenciaTab {...recorrenciaTabProps} />}
          {tabsProps.abaAtiva === 7 && <ProdutosNovoRacaoTab {...racaoTabProps} />}
          {canShowVariacoesTab && <ProdutosNovoVariacoesTab {...variacoesTabProps} />}
          {canShowComposicaoTab && <ProdutosNovoComposicaoTab {...composicaoTabProps} />}
        </div>
        <ProdutosNovoFooterActions {...footerProps} />
      </form>
    </div>
  );
}
