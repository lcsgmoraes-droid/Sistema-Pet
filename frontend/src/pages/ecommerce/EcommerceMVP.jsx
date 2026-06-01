import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import ecommerceApi from '../../services/ecommerceApi';
import { api } from '../../services/api';
import EcommerceAccountPage from './EcommerceAccountPage';
import { EcommerceCartPage } from './EcommerceCartPanels';
import EcommerceCheckoutPage from './EcommerceCheckoutPage';
import EcommerceFooter from './EcommerceFooter';
import EcommerceNotifyMeModal from './EcommerceNotifyMeModal';
import EcommerceOrdersPage from './EcommerceOrdersPage';
import EcommerceProductDetailModal from './EcommerceProductDetailModal';
import EcommerceStorePage from './EcommerceStorePage';
import EcommerceStorefrontChrome from './EcommerceStorefrontChrome';
import ecommerceMvpStyles from './ecommerceMvpStyles';
import useEcommerceCart from './useEcommerceCart';
import useEcommerceCatalog from './useEcommerceCatalog';
import useEcommerceCheckout from './useEcommerceCheckout';
import useEcommerceCustomer from './useEcommerceCustomer';
import useEcommerceEngagement from './useEcommerceEngagement';
import useEcommerceOrders from './useEcommerceOrders';
import useEcommerceProductModal from './useEcommerceProductModal';
import {
  readMercadoPagoPaymentReturn,
  stripMercadoPagoPaymentReturnParams,
} from '../../utils/mercadoPagoPaymentReturn';
import {
  trackPageView,
  trackViewCart,
} from '../../services/analytics';
import {
  STORAGE_TOKEN_KEY,
  buildActiveBanners,
  extractApiErrorMessage,
  isProductOutOfStock,
  normalizeProductPayload,
  resolveStoreDisplayName,
} from './ecommerceMvpUtils';

export default function EcommerceMVP() {
  // Inject Plus Jakarta Sans font (matches design system)
  useEffect(() => {
    const id = 'plus-jakarta-sans-font';
    if (!document.getElementById(id)) {
      const link = document.createElement('link');
      link.id = id;
      link.rel = 'stylesheet';
      link.href = 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap';
      document.head.appendChild(link);
    }
  }, []);

  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  const [view, setView] = useState('loja');

  // Detecta mobile (< 768px)
  const [isMobile, setIsMobile] = useState(typeof window !== 'undefined' ? window.innerWidth < 768 : false);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  // Rastreia no Google Analytics sempre que o cliente muda de tela
  useEffect(() => {
    trackPageView(view);
    if (view === 'carrinho') trackViewCart(cart);
  }, [view]);
  const [bannerSlide, setBannerSlide] = useState(0);
  const [hoveredCard, setHoveredCard] = useState(null);
  const [loading, setLoading] = useState(false);
  const {
    products,
    setProducts,
    search,
    setSearch,
    categoria,
    setCategoria,
    somenteComEstoque,
    setSomenteComEstoque,
    somenteComImagem,
    setSomenteComImagem,
    ordenacaoCatalogo,
    setOrdenacaoCatalogo,
    categorias,
    catalogMetrics,
    filteredProducts,
    productMap,
    clearCatalogFilters,
  } = useEcommerceCatalog();
  const {
    selectedProduct,
    activeProductImage,
    setActiveProductImage,
    openProductDetails,
    closeProductModal,
  } = useEcommerceProductModal({ products, location, navigate });
  const [customerToken, setCustomerToken] = useState(localStorage.getItem(STORAGE_TOKEN_KEY) || '');

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [tenantContext, setTenantContext] = useState(null);

  // Banners: usa URLs do tenant se configuradas, senão exibe os padrões
  const activeBanners = useMemo(() => {
    return buildActiveBanners(tenantContext);
  }, [tenantContext]);

  const tenantRef = useMemo(() => {
    const query = new URLSearchParams(location.search);
    const tenantFromQuery = query.get('tenant');
    return tenantFromQuery || params.tenantId || '';
  }, [location.search, params.tenantId]);

  const tenantHeaders = useMemo(() => {
    if (!tenantContext?.id) return {};
    return { 'X-Tenant-ID': tenantContext.id };
  }, [tenantContext?.id]);

  const authHeaders = useMemo(() => {
    if (!customerToken) return {};
    return { Authorization: `Bearer ${customerToken}` };
  }, [customerToken]);

  const storefrontRef = tenantContext?.ecommerce_slug || tenantRef || '';

  const storeDisplayName = useMemo(() => {
    return resolveStoreDisplayName({ tenantContext, storefrontRef });
  }, [tenantContext, storefrontRef]);

  const {
    cart,
    cartLoading,
    cartTotal,
    addToCart,
    clearCart,
    loadCart,
    restoreGuestCart,
    syncGuestCartToServer,
    updateCartItem,
  } = useEcommerceCart({
    authHeaders,
    customerToken,
    productMap,
    onError: setError,
    onSuccess: setSuccess,
  });

  const {
    authLoading,
    clearCustomerSession,
    closePasswordRecovery,
    customer,
    customerDisplayName,
    handleDeliveryCepBlur,
    handleLogin,
    handlePasswordRecoveryRequest,
    handlePasswordRecoveryReset,
    handleProfileCepBlur,
    handleRegister,
    isProfileComplete,
    loginForm,
    openPasswordRecovery,
    passwordRecoveryMode,
    profileForm,
    profileSaving,
    recoveryForm,
    recoveryLoading,
    recoveryStep,
    recoveryTokenFromLink,
    registerForm,
    saveProfile,
    setLoginForm,
    setProfileForm,
    setRecoveryForm,
    setRecoveryStep,
    setRecoveryTokenFromLink,
    setRegisterForm,
    setShowLoginPassword,
    setShowRecoveryConfirmPassword,
    setShowRecoveryPassword,
    setShowRegisterPassword,
    showLoginPassword,
    showRecoveryConfirmPassword,
    showRecoveryPassword,
    showRegisterPassword,
  } = useEcommerceCustomer({
    authHeaders,
    customerToken,
    loadCart,
    location,
    navigate,
    restoreGuestCart,
    setCustomerToken,
    setView,
    syncGuestCartToServer,
    tenantContext,
    tenantHeaders,
    onError: setError,
    onSuccess: setSuccess,
  });

  const {
    wishlist,
    notifyRequests,
    notifyMeModal,
    setNotifyMeModal,
    toggleWishlist,
    registerNotifyMe,
    submitNotifyMe,
  } = useEcommerceEngagement({
    customer,
    loginEmail: loginForm.email,
    registerEmail: registerForm.email,
    storefrontRef,
    tenantContext,
    tenantRef,
    onError: setError,
    onSuccess: setSuccess,
  });

  const {
    ordersDetailed,
    ordersLoading,
    loadOrdersDetailed,
    avisarCheguei,
    recordOrderId,
  } = useEcommerceOrders({
    authHeaders,
    customerToken,
    view,
    onError: setError,
  });

  useEffect(() => {
    const viewParam = new URLSearchParams(location.search).get('view');
    if (['loja', 'carrinho', 'checkout', 'pedidos', 'conta'].includes(viewParam)) {
      setView(viewParam);
    }
  }, [location.search]);

  useEffect(() => {
    const paymentReturn = readMercadoPagoPaymentReturn(location.search);
    if (!paymentReturn) return;

    setView('pedidos');
    if (paymentReturn.level === 'error') {
      setError(paymentReturn.message);
      setSuccess('');
    } else {
      setError('');
      setSuccess(paymentReturn.message);
    }
    if (paymentReturn.pedidoId) {
      void recordOrderId(paymentReturn.pedidoId);
    }

    const cleanedSearch = stripMercadoPagoPaymentReturnParams(location.search);
    navigate(`${location.pathname}${cleanedSearch ? `?${cleanedSearch}` : ''}`, { replace: true });
  }, [location.pathname, location.search, navigate, recordOrderId]);

  const {
    addressFields,
    checkoutLoading,
    checkoutResumo,
    checkoutResult,
    cidadeDestino,
    cupom,
    cupomResult,
    deliveryMode,
    isDrive,
    pagamentoBandeira,
    pagamentoParcelas,
    pagamentoTipo,
    tipoRetirada,
    applyCupom,
    calcularResumoCheckout,
    finalizarCheckout,
    handleCheckoutCepBlur,
    handleCheckoutFromLoja,
    resetCheckoutStatus,
    setAddressFields,
    setCidadeDestino,
    setCupom,
    setDeliveryMode,
    setIsDrive,
    setPagamentoBandeira,
    setPagamentoParcelas,
    setPagamentoTipo,
    setTipoRetirada,
  } = useEcommerceCheckout({
    authHeaders,
    cart,
    clearCart,
    customer,
    customerToken,
    isProfileComplete,
    recordOrderId,
    setView,
    tenantContext,
    onError: setError,
    onSuccess: setSuccess,
  });

  // Ler ?busca= da URL (ex: link do email de avise-me) e pré-filtrar
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const buscaParam = params.get('busca');
    if (buscaParam) {
      setSearch(buscaParam);
    }
  }, [location.search]);

  useEffect(() => {
    // Sem slug = acesso pelo painel (usuario logado) → carrega via API autenticada
    loadTenantContext();
    if (tenantRef) {
      loadProducts();
    }
  }, [tenantRef]);

  // Apos carregar o contexto via painel (sem slug), usar o tenant.id para buscar produtos
  // e redirecionar para a URL real da loja (/{slug})
  useEffect(() => {
    if (!tenantRef && tenantContext?.id) {
      if (tenantContext.ecommerce_slug) {
        navigate(`/${tenantContext.ecommerce_slug}`, { replace: true });
      } else {
        loadProductsById(tenantContext.id);
      }
    }
  }, [tenantContext?.id]);

  useEffect(() => {
    const total = activeBanners.length;
    const timer = setInterval(() => setBannerSlide((prev) => (prev + 1) % total), 4000);
    return () => clearInterval(timer);
  }, [activeBanners.length]);

  async function loadTenantContext() {
    try {
      // Sem slug na URL = acesso pelo painel (usuario logado) → usa API autenticada
      if (!tenantRef) {
        const response = await api.get('/ecommerce-aparencia/tenant-context');
        setTenantContext(response?.data || null);
        return;
      }
      const response = await ecommerceApi.get('/api/ecommerce/tenant-context', {
        params: { tenant: tenantRef },
      });
      setTenantContext(response?.data || null);
    } catch (err) {
      setTenantContext(null);
      setError(extractApiErrorMessage(err, 'Loja inválida para e-commerce'));
    }
  }

  async function loadProducts() {
    if (!tenantRef) return;
    setLoading(true);
    setError('');
    try {
      const response = await ecommerceApi.get('/api/ecommerce/produtos', {
        params: { tenant: tenantRef, limit: 500, ordenacao: 'prontos' },
      });
      setProducts(normalizeProductPayload(response?.data));
    } catch (err) {
      setProducts([]);
      setError(extractApiErrorMessage(err, 'Erro ao carregar produtos vendáveis'));
    } finally {
      setLoading(false);
    }
  }

  async function loadProductsById(tenantId) {
    setLoading(true);
    setError('');
    try {
      const response = await ecommerceApi.get('/api/ecommerce/produtos', {
        params: { tenant: tenantId, limit: 500, ordenacao: 'prontos' },
      });
      setProducts(normalizeProductPayload(response?.data));
    } catch (err) {
      setProducts([]);
      setError(extractApiErrorMessage(err, 'Erro ao carregar produtos vendáveis'));
    } finally {
      setLoading(false);
    }
  }

  function logoutCustomer() {
    clearCustomerSession();
    clearCart();
    resetCheckoutStatus();
    setSuccess('Sess\u00e3o encerrada.');
  }

  const S = ecommerceMvpStyles;

  return (
    <div style={S.page}>
      <EcommerceStorefrontChrome
        activeBanners={activeBanners}
        bannerSlide={bannerSlide}
        cart={cart}
        cartTotal={cartTotal}
        customerDisplayName={customerDisplayName}
        isMobile={isMobile}
        search={search}
        storeDisplayName={storeDisplayName}
        styles={S}
        tenantContext={tenantContext}
        view={view}
        wishlist={wishlist}
        onBannerSlideChange={setBannerSlide}
        onNavigate={setView}
        onSearchChange={setSearch}
      />

      {!tenantRef && (
        <div style={{ background: '#fef2f2', color: '#991b1b', padding: '10px 20px', fontSize: 13, borderBottom: '1px solid #fecaca' }}>
          ⚠️ Use a URL no formato: /slug-da-loja
        </div>
      )}

      {/* ALERTAS */}
      {(error || success) && (
        <div style={{ padding: '0 20px' }}>
          <div style={{ maxWidth: 1280, margin: '0 auto' }}>
            {error && <div style={S.alertError}>⚠️ {error}</div>}
            {success && <div style={S.alertSuccess}>✓ {success}</div>}
          </div>
        </div>
      )}

      {view === 'loja' && (
        <EcommerceStorePage
          cart={cart}
          cartTotal={cartTotal}
          catalogMetrics={catalogMetrics}
          categories={categorias}
          category={categoria}
          customerToken={customerToken}
          filteredProducts={filteredProducts}
          hoveredCard={hoveredCard}
          isMobile={isMobile}
          loading={loading}
          order={ordenacaoCatalogo}
          productMap={productMap}
          search={search}
          showOnlyInStock={somenteComEstoque}
          showOnlyWithImage={somenteComImagem}
          styles={S}
          wishlist={wishlist}
          onAddToCart={addToCart}
          onCategoryChange={setCategoria}
          onCheckout={handleCheckoutFromLoja}
          onClearFilters={clearCatalogFilters}
          onHoverProduct={setHoveredCard}
          onImageFilterChange={() => setSomenteComImagem((value) => !value)}
          onNotifyMe={registerNotifyMe}
          onOpenProduct={openProductDetails}
          onOrderChange={setOrdenacaoCatalogo}
          onRefresh={loadProducts}
          onSearchChange={setSearch}
          onStockFilterChange={() => setSomenteComEstoque((value) => !value)}
          onToggleWishlist={toggleWishlist}
          onViewCart={() => setView('carrinho')}
        />
      )}

      {selectedProduct && (
        <EcommerceProductDetailModal
          activeImage={activeProductImage}
          isMobile={isMobile}
          product={selectedProduct}
          styles={S}
          wishlist={wishlist}
          onAddToCart={addToCart}
          onClose={closeProductModal}
          onCopyLink={(product) => {
            const url = `${window.location.origin}${location.pathname}?produto=${product.id}`;
            navigator.clipboard?.writeText(url).then(() => setSuccess('Link copiado!')).catch(() => setSuccess(`Link: ${url}`));
          }}
          onImageChange={setActiveProductImage}
          onNotifyMe={registerNotifyMe}
          onToggleWishlist={toggleWishlist}
          onViewCart={() => {
            closeProductModal();
            setView('carrinho');
          }}
        />
      )}

      {view === 'carrinho' && (
        <EcommerceCartPage
          cart={cart}
          cartLoading={cartLoading}
          cartTotal={cartTotal}
          cupom={cupom}
          cupomResult={cupomResult}
          isMobile={isMobile}
          productMap={productMap}
          styles={S}
          onApplyCoupon={applyCupom}
          onCheckout={handleCheckoutFromLoja}
          onContinueShopping={() => setView('loja')}
          onCouponChange={setCupom}
          onUpdateItem={updateCartItem}
        />
      )}

      {view === 'checkout' && (
        <EcommerceCheckoutPage
          addressFields={addressFields}
          cart={cart}
          cartTotal={cartTotal}
          checkoutLoading={checkoutLoading}
          checkoutResumo={checkoutResumo}
          checkoutResult={checkoutResult}
          cidadeDestino={cidadeDestino}
          deliveryMode={deliveryMode}
          isDrive={isDrive}
          isProfileComplete={isProfileComplete}
          pagamentoBandeira={pagamentoBandeira}
          pagamentoParcelas={pagamentoParcelas}
          pagamentoTipo={pagamentoTipo}
          setAddressFields={setAddressFields}
          styles={S}
          tenantContext={tenantContext}
          tipoRetirada={tipoRetirada}
          onCalculateSummary={calcularResumoCheckout}
          onCheckoutCepBlur={handleCheckoutCepBlur}
          onCidadeDestinoChange={setCidadeDestino}
          onDeliveryModeChange={setDeliveryMode}
          onFinalizeCheckout={finalizarCheckout}
          onIsDriveChange={setIsDrive}
          onPagamentoBandeiraChange={setPagamentoBandeira}
          onPagamentoParcelasChange={setPagamentoParcelas}
          onPagamentoTipoChange={setPagamentoTipo}
          onTipoRetiradaChange={setTipoRetirada}
        />
      )}

      {view === 'pedidos' && (
        <EcommerceOrdersPage
          orders={ordersDetailed}
          ordersLoading={ordersLoading}
          styles={S}
          onContinueShopping={() => setView('loja')}
          onDriveArrived={avisarCheguei}
          onReload={loadOrdersDetailed}
        />
      )}
      {view === 'conta' && (
        <EcommerceAccountPage
          authLoading={authLoading}
          customer={customer}
          customerToken={customerToken}
          isMobile={isMobile}
          loginForm={loginForm}
          notifyRequestsCount={notifyRequests.length}
          passwordRecoveryMode={passwordRecoveryMode}
          profileForm={profileForm}
          profileSaving={profileSaving}
          recoveryForm={recoveryForm}
          recoveryLoading={recoveryLoading}
          recoveryStep={recoveryStep}
          recoveryTokenFromLink={recoveryTokenFromLink}
          registerForm={registerForm}
          setLoginForm={setLoginForm}
          setProfileForm={setProfileForm}
          setRecoveryForm={setRecoveryForm}
          setRegisterForm={setRegisterForm}
          showLoginPassword={showLoginPassword}
          showRecoveryConfirmPassword={showRecoveryConfirmPassword}
          showRecoveryPassword={showRecoveryPassword}
          showRegisterPassword={showRegisterPassword}
          styles={S}
          wishlistCount={wishlist.length}
          onClosePasswordRecovery={closePasswordRecovery}
          onDeliveryCepBlur={handleDeliveryCepBlur}
          onLogin={handleLogin}
          onLogout={logoutCustomer}
          onOpenPasswordRecovery={openPasswordRecovery}
          onPasswordRecoveryRequest={handlePasswordRecoveryRequest}
          onPasswordRecoveryReset={handlePasswordRecoveryReset}
          onProfileCepBlur={handleProfileCepBlur}
          onRegister={handleRegister}
          onSaveProfile={saveProfile}
          onSwitchRecoveryToRequest={() => {
            setRecoveryStep('request');
            setRecoveryTokenFromLink(false);
            setError('');
            setSuccess('');
          }}
          onSwitchRecoveryToReset={() => {
            setRecoveryStep('reset');
            setRecoveryTokenFromLink(false);
          }}
          onToggleLoginPassword={() => setShowLoginPassword((prev) => !prev)}
          onToggleRecoveryConfirmPassword={() => setShowRecoveryConfirmPassword((prev) => !prev)}
          onToggleRecoveryPassword={() => setShowRecoveryPassword((prev) => !prev)}
          onToggleRegisterPassword={() => setShowRegisterPassword((prev) => !prev)}
        />
      )}

      <EcommerceNotifyMeModal
        modal={notifyMeModal}
        styles={S}
        onClose={() => setNotifyMeModal({ open: false, product: null, email: '', loading: false })}
        onEmailChange={(email) => setNotifyMeModal((prev) => ({ ...prev, email }))}
        onSubmit={submitNotifyMe}
      />

      <EcommerceFooter tenantContext={tenantContext} styles={S} onNavigate={setView} />
    </div>
  );
}
