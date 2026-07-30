import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import ecommerceApi from "../../services/ecommerceApi";
import { api } from "../../services/api";
import EcommerceAccountPage from "./EcommerceAccountPage";
import { EcommerceCartPage } from "./EcommerceCartPanels";
import EcommerceCheckoutPage from "./EcommerceCheckoutPage";
import EcommerceFooter from "./EcommerceFooter";
import EcommerceNotifyMeModal from "./EcommerceNotifyMeModal";
import EcommerceOrdersPage from "./EcommerceOrdersPage";
import EcommerceProductDetailModal from "./EcommerceProductDetailModal";
import EcommerceStorePage from "./EcommerceStorePage";
import EcommerceStorefrontChrome from "./EcommerceStorefrontChrome";
import ecommerceMvpStyles from "./ecommerceMvpStyles";
import useEcommerceCart from "./useEcommerceCart";
import useEcommerceCatalog from "./useEcommerceCatalog";
import useEcommerceCheckout from "./useEcommerceCheckout";
import useEcommerceCustomer from "./useEcommerceCustomer";
import useEcommerceEngagement from "./useEcommerceEngagement";
import useEcommerceOrders from "./useEcommerceOrders";
import useEcommercePaymentReturn from "./useEcommercePaymentReturn";
import useEcommerceProductModal from "./useEcommerceProductModal";
import useEcommerceStorefrontRuntime from "./useEcommerceStorefrontRuntime";
import useEcommerceSeo from "./useEcommerceSeo";
import {
  setEcommerceAnalyticsContext,
  trackPageView,
  trackSearch,
  trackViewCart,
} from "../../services/analytics";
import {
  DEFAULT_CATALOG_LIMIT,
  STORAGE_TOKEN_KEY,
  buildActiveBanners,
  buildCatalogQueryParams,
  buildPaginationWindow,
  extractApiErrorMessage,
  normalizeCatalogPayload,
  resolveStoreDisplayName,
} from "./ecommerceMvpUtils";

export default function EcommerceMVP() {
  const { isMobile } = useEcommerceStorefrontRuntime();
  const location = useLocation();
  const navigate = useNavigate();
  const params = useParams();

  const [view, setView] = useState("loja");
  const [authReturnView, setAuthReturnView] = useState("");

  function requireAuthForCheckout() {
    setAuthReturnView("checkout");
    setView("conta");
  }

  function clearAuthReturnView() {
    setAuthReturnView("");
  }

  const [bannerSlide, setBannerSlide] = useState(0);
  const [hoveredCard, setHoveredCard] = useState(null);
  const [loading, setLoading] = useState(false);
  const {
    products,
    setProducts,
    catalogMeta,
    setCatalogMeta,
    page: catalogPage,
    setPage: setCatalogPage,
    search,
    setSearch,
    categoria,
    setCategoria,
    ordenacaoCatalogo,
    setOrdenacaoCatalogo,
    marca,
    setMarca,
    apenasComEstoque,
    setApenasComEstoque,
    apenasComImagem,
    setApenasComImagem,
    precoMinimo,
    setPrecoMinimo,
    precoMaximo,
    setPrecoMaximo,
    categorias,
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
  const [customerToken, setCustomerToken] = useState(localStorage.getItem(STORAGE_TOKEN_KEY) || "");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [tenantContext, setTenantContext] = useState(null);

  // Banners: usa URLs do tenant se configuradas, senão exibe os padrões
  const activeBanners = useMemo(() => {
    return buildActiveBanners(tenantContext);
  }, [tenantContext]);

  const tenantRef = useMemo(() => {
    const query = new URLSearchParams(location.search);
    const tenantFromQuery = query.get("tenant");
    return tenantFromQuery || params.tenantId || "";
  }, [location.search, params.tenantId]);

  const tenantHeaders = useMemo(() => {
    if (!tenantContext?.id) return {};
    return { "X-Tenant-ID": tenantContext.id };
  }, [tenantContext?.id]);

  const authHeaders = useMemo(() => {
    if (!customerToken) return {};
    return { Authorization: `Bearer ${customerToken}` };
  }, [customerToken]);

  const storefrontRef = tenantContext?.ecommerce_slug || tenantRef || "";

  useEffect(() => {
    setEcommerceAnalyticsContext({
      tenant: storefrontRef,
      channel: "ecommerce",
    });
    if (storefrontRef) trackPageView(view);
  }, [storefrontRef, view]);

  useEffect(() => {
    if (!search.trim()) return undefined;
    const timer = window.setTimeout(() => trackSearch(search), 700);
    return () => window.clearTimeout(timer);
  }, [search]);

  const storeDisplayName = useMemo(() => {
    return resolveStoreDisplayName({ tenantContext, storefrontRef });
  }, [tenantContext, storefrontRef]);

  useEcommerceSeo({
    tenantContext,
    storeDisplayName,
    selectedProduct,
  });

  const catalogPagination = useMemo(() => {
    return buildPaginationWindow({
      total: catalogMeta.total,
      limit: catalogMeta.limit || DEFAULT_CATALOG_LIMIT,
      page: catalogPage,
    });
  }, [catalogMeta.limit, catalogMeta.total, catalogPage]);

  const selectedProductVariations = useMemo(() => {
    if (!selectedProduct?.produto_pai_id) return [];
    return Object.values(productMap).filter(
      (product) => product.produto_pai_id === selectedProduct.produto_pai_id,
    );
  }, [productMap, selectedProduct]);

  const handleCatalogSearchChange = (value) => {
    setSearch(value);
    setCatalogPage(1);
  };

  const handleCatalogCategoryChange = (value) => {
    setCategoria(value);
    setCatalogPage(1);
  };

  const handleCatalogOrderChange = (value) => {
    setOrdenacaoCatalogo(value);
    setCatalogPage(1);
  };

  const handleCatalogFilterChange = (setter) => (value) => {
    setter(value);
    setCatalogPage(1);
  };

  const handleCatalogPageChange = (nextPage) => {
    setCatalogPage(nextPage);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

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

  useEffect(() => {
    if (view === "carrinho") trackViewCart(cart);
  }, [view]);

  const {
    authLoading,
    clearCustomerSession,
    clearProfileFieldError,
    clearRegisterFieldError,
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
    profileFieldError,
    profileForm,
    profileSaving,
    recoveryForm,
    recoveryLoading,
    recoveryStep,
    recoveryTokenFromLink,
    registerFieldError,
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
    authReturnView,
    authHeaders,
    customerToken,
    loadCart,
    location,
    navigate,
    onAuthReturnHandled: clearAuthReturnView,
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
    ordersError,
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

  useEcommercePaymentReturn({
    location,
    navigate,
    recordOrderId,
    setError,
    setSuccess,
    setView,
  });

  useEffect(() => {
    const viewParam = new URLSearchParams(location.search).get("view");
    if (["loja", "carrinho", "checkout", "pedidos", "conta"].includes(viewParam)) {
      setView(viewParam);
    }
  }, [location.search]);

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
    onRequireAuthForCheckout: requireAuthForCheckout,
    onSuccess: setSuccess,
  });

  const abrirPagamentoPedido = (paymentUrl) => {
    if (!paymentUrl) return;
    window.location.assign(paymentUrl);
  };

  // Ler ?busca= da URL (ex: link do email de avise-me) e pré-filtrar
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const buscaParam = params.get("busca");
    if (buscaParam) {
      handleCatalogSearchChange(buscaParam);
    }
  }, [location.search]);

  useEffect(() => {
    // Sem slug = acesso pelo painel (usuario logado) → carrega via API autenticada
    loadTenantContext();
  }, [tenantRef]);

  useEffect(() => {
    if (!tenantRef) return undefined;
    const timer = setTimeout(() => {
      loadProducts();
    }, 220);
    return () => clearTimeout(timer);
  }, [
    tenantRef,
    search,
    categoria,
    ordenacaoCatalogo,
    catalogPage,
    marca,
    apenasComEstoque,
    apenasComImagem,
    precoMinimo,
    precoMaximo,
  ]);

  // Apos carregar o contexto via painel (sem slug), usar o tenant.id para buscar produtos
  // e redirecionar para a URL real da loja (/{slug})
  useEffect(() => {
    if (!tenantRef && tenantContext?.id) {
      if (tenantContext.ecommerce_slug) {
        navigate(`/${tenantContext.ecommerce_slug}`, { replace: true });
      }
    }
  }, [tenantContext?.ecommerce_slug, tenantContext?.id, tenantRef]);

  useEffect(() => {
    if (tenantRef || !tenantContext?.id || tenantContext.ecommerce_slug) return undefined;
    const timer = setTimeout(() => {
      loadProductsById(tenantContext.id);
    }, 220);
    return () => clearTimeout(timer);
  }, [
    tenantContext?.ecommerce_slug,
    tenantContext?.id,
    tenantRef,
    search,
    categoria,
    ordenacaoCatalogo,
    catalogPage,
    marca,
    apenasComEstoque,
    apenasComImagem,
    precoMinimo,
    precoMaximo,
  ]);

  useEffect(() => {
    const total = activeBanners.length;
    const timer = setInterval(() => setBannerSlide((prev) => (prev + 1) % total), 4000);
    return () => clearInterval(timer);
  }, [activeBanners.length]);

  async function loadTenantContext() {
    try {
      // Sem slug na URL = acesso pelo painel (usuario logado) → usa API autenticada
      if (!tenantRef) {
        const response = await api.get("/ecommerce-aparencia/tenant-context");
        setTenantContext(response?.data || null);
        return;
      }
      const response = await ecommerceApi.get("/api/ecommerce/tenant-context", {
        params: { tenant: tenantRef },
      });
      setTenantContext(response?.data || null);
    } catch (err) {
      setTenantContext(null);
      if (!tenantRef) {
        setError("");
      } else {
        setError(extractApiErrorMessage(err, "Loja inválida para e-commerce"));
      }
    }
  }

  async function loadCatalogProducts(tenantValue) {
    if (!tenantValue) return;
    setLoading(true);
    setError("");
    try {
      let selectedCategory = categoria;
      if (String(categoria).startsWith("grupo:")) {
        const selectedGroup = decodeURIComponent(String(categoria).slice("grupo:".length));
        selectedCategory = categorias
          .filter((item) => item.group === selectedGroup && item.value !== "todas")
          .map((item) => item.value);
      }
      const queryParams = buildCatalogQueryParams({
        tenant: tenantValue,
        search,
        category: selectedCategory,
        order: ordenacaoCatalogo,
        page: catalogPage,
        limit: DEFAULT_CATALOG_LIMIT,
        channel: "ecommerce",
        brand: marca,
        onlyInStock: apenasComEstoque,
        onlyWithImage: apenasComImagem,
        minPrice: precoMinimo,
        maxPrice: precoMaximo,
      });
      const [response, filtersResponse] = await Promise.all([
        ecommerceApi.get("/api/ecommerce/produtos", {
          params: queryParams,
          paramsSerializer: { indexes: null },
        }),
        ecommerceApi.get("/api/ecommerce/produtos/filtros", {
          params: {
            tenant: tenantValue,
            busca: search.trim() || undefined,
            canal: "ecommerce",
          },
        }),
      ]);
      const payload = normalizeCatalogPayload(response?.data);
      setProducts(payload.items);
      setCatalogMeta({
        total: payload.total,
        offset: payload.offset,
        limit: payload.limit,
        categories: payload.categories,
        brands: filtersResponse?.data?.marcas || [],
      });
    } catch (err) {
      setProducts([]);
      setCatalogMeta({
        total: 0,
        offset: 0,
        limit: DEFAULT_CATALOG_LIMIT,
        categories: [],
        brands: [],
      });
      setError(extractApiErrorMessage(err, "Erro ao carregar produtos vendaveis"));
    } finally {
      setLoading(false);
    }
  }

  async function loadProducts() {
    return loadCatalogProducts(tenantRef);
  }

  async function loadProductsById(tenantId) {
    return loadCatalogProducts(tenantId);
  }

  function logoutCustomer() {
    clearCustomerSession();
    clearCart();
    resetCheckoutStatus();
    clearAuthReturnView();
    setSuccess("Sess\u00e3o encerrada.");
  }

  const S = useMemo(() => {
    const primary = tenantContext?.ecommerce_cor_primaria || "#f97316";
    const secondary = tenantContext?.ecommerce_cor_secundaria || "#1c1917";
    const softPrimary = `${primary}18`;
    const primaryShadow = `${primary}55`;
    return {
      ...ecommerceMvpStyles,
      topbar: { ...ecommerceMvpStyles.topbar, background: primary },
      cartBtn: { ...ecommerceMvpStyles.cartBtn, background: primary },
      navTab: (active) => ({
        ...ecommerceMvpStyles.navTab(active),
        borderBottom: active ? `2px solid ${primary}` : "2px solid transparent",
        color: active ? primary : "#78716c",
      }),
      addBtn: (out) => ({
        ...ecommerceMvpStyles.addBtn(out),
        background: out ? "#f5f5f4" : primary,
        boxShadow: out ? "none" : `0 2px 8px ${primaryShadow}`,
      }),
      sidebarBadge: { ...ecommerceMvpStyles.sidebarBadge, background: primary },
      checkoutBig: {
        ...ecommerceMvpStyles.checkoutBig,
        background: primary,
        boxShadow: `0 4px 14px ${primaryShadow}`,
      },
      viewCartBtn: {
        ...ecommerceMvpStyles.viewCartBtn,
        borderColor: primary,
        color: primary,
      },
      radioLabelActive: {
        ...ecommerceMvpStyles.radioLabelActive,
        borderColor: primary,
        background: softPrimary,
        color: primary,
      },
      payBtn: (active) => ({
        ...ecommerceMvpStyles.payBtn(active),
        borderColor: active ? primary : "#e7e5e4",
        background: active ? softPrimary : "#fff",
        color: active ? primary : "#374151",
      }),
      finalizarBtn: (disabled) => ({
        ...ecommerceMvpStyles.finalizarBtn(disabled),
        background: disabled ? "#e5e7eb" : primary,
        boxShadow: disabled ? "none" : `0 4px 14px ${primaryShadow}`,
      }),
      rewardBox: {
        ...ecommerceMvpStyles.rewardBox,
        background: softPrimary,
        borderColor: primary,
      },
      saveBtn: { ...ecommerceMvpStyles.saveBtn, background: primary },
      footer: { ...ecommerceMvpStyles.footer, background: secondary },
    };
  }, [tenantContext?.ecommerce_cor_primaria, tenantContext?.ecommerce_cor_secundaria]);

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
        onSearchChange={handleCatalogSearchChange}
      />

      {!tenantRef && (
        <div
          style={{
            maxWidth: 760,
            margin: "24px auto",
            background: "#fff7ed",
            color: "#9a3412",
            padding: "18px 20px",
            fontSize: 14,
            border: "1px solid #fed7aa",
            borderRadius: 12,
          }}
        >
          <strong>Loja não identificada.</strong> Abra o link público fornecido pela loja. Se você
          administra esta loja, use a opção <strong>Prévia da loja</strong> no painel.
        </div>
      )}

      {/* ALERTAS */}
      {(error || success) && (
        <div style={{ padding: "0 20px" }}>
          <div style={{ maxWidth: 1280, margin: "0 auto" }}>
            {error && <div style={S.alertError}>⚠️ {error}</div>}
            {success && <div style={S.alertSuccess}>✓ {success}</div>}
          </div>
        </div>
      )}

      {view === "loja" && (
        <EcommerceStorePage
          cart={cart}
          cartTotal={cartTotal}
          categories={categorias}
          category={categoria}
          brands={catalogMeta.brands}
          brand={marca}
          onlyInStock={apenasComEstoque}
          onlyWithImage={apenasComImagem}
          minPrice={precoMinimo}
          maxPrice={precoMaximo}
          minOrder={tenantContext?.ecommerce_pedido_minimo}
          customerToken={customerToken}
          filteredProducts={filteredProducts}
          hoveredCard={hoveredCard}
          isMobile={isMobile}
          loading={loading}
          order={ordenacaoCatalogo}
          pagination={catalogPagination}
          productMap={productMap}
          productCount={catalogMeta.total}
          search={search}
          styles={S}
          wishlist={wishlist}
          onAddToCart={addToCart}
          onCategoryChange={handleCatalogCategoryChange}
          onBrandChange={handleCatalogFilterChange(setMarca)}
          onOnlyInStockChange={handleCatalogFilterChange(setApenasComEstoque)}
          onOnlyWithImageChange={handleCatalogFilterChange(setApenasComImagem)}
          onMinPriceChange={handleCatalogFilterChange(setPrecoMinimo)}
          onMaxPriceChange={handleCatalogFilterChange(setPrecoMaximo)}
          onCheckout={handleCheckoutFromLoja}
          onClearFilters={clearCatalogFilters}
          onHoverProduct={setHoveredCard}
          onNotifyMe={registerNotifyMe}
          onOpenProduct={openProductDetails}
          onOrderChange={handleCatalogOrderChange}
          onPageChange={handleCatalogPageChange}
          onRefresh={loadProducts}
          onSearchChange={handleCatalogSearchChange}
          onToggleWishlist={toggleWishlist}
          onViewCart={() => setView("carrinho")}
        />
      )}

      {selectedProduct && (
        <EcommerceProductDetailModal
          activeImage={activeProductImage}
          isMobile={isMobile}
          product={selectedProduct}
          variations={selectedProductVariations}
          styles={S}
          wishlist={wishlist}
          onAddToCart={addToCart}
          onClose={closeProductModal}
          onCopyLink={(product) => {
            const url = `${window.location.origin}${location.pathname}?produto=${product.id}`;
            navigator.clipboard
              ?.writeText(url)
              .then(() => setSuccess("Link copiado!"))
              .catch(() => setSuccess(`Link: ${url}`));
          }}
          onImageChange={setActiveProductImage}
          onNotifyMe={registerNotifyMe}
          onSelectVariation={openProductDetails}
          onToggleWishlist={toggleWishlist}
          onViewCart={() => {
            closeProductModal();
            setView("carrinho");
          }}
        />
      )}

      {view === "carrinho" && (
        <EcommerceCartPage
          cart={cart}
          cartLoading={cartLoading}
          cartTotal={cartTotal}
          cupom={cupom}
          cupomResult={cupomResult}
          isMobile={isMobile}
          minOrder={tenantContext?.ecommerce_pedido_minimo}
          productMap={productMap}
          styles={S}
          onApplyCoupon={applyCupom}
          onCheckout={handleCheckoutFromLoja}
          onContinueShopping={() => setView("loja")}
          onCouponChange={setCupom}
          onUpdateItem={updateCartItem}
        />
      )}

      {view === "checkout" && (
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
          isMobile={isMobile}
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

      {view === "pedidos" && (
        <EcommerceOrdersPage
          orders={ordersDetailed}
          ordersError={ordersError}
          ordersLoading={ordersLoading}
          styles={S}
          onContinueShopping={() => setView("loja")}
          onDriveArrived={avisarCheguei}
          onOpenPayment={abrirPagamentoPedido}
          onReload={loadOrdersDetailed}
        />
      )}
      {view === "conta" && (
        <EcommerceAccountPage
          authLoading={authLoading}
          customer={customer}
          customerToken={customerToken}
          isMobile={isMobile}
          loginForm={loginForm}
          notifyRequestsCount={notifyRequests.length}
          passwordRecoveryMode={passwordRecoveryMode}
          profileFieldError={profileFieldError}
          profileForm={profileForm}
          profileSaving={profileSaving}
          recoveryForm={recoveryForm}
          recoveryLoading={recoveryLoading}
          recoveryStep={recoveryStep}
          recoveryTokenFromLink={recoveryTokenFromLink}
          registerFieldError={registerFieldError}
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
          onClearProfileFieldError={clearProfileFieldError}
          onClearRegisterFieldError={clearRegisterFieldError}
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
            setRecoveryStep("request");
            setRecoveryTokenFromLink(false);
            setError("");
            setSuccess("");
          }}
          onSwitchRecoveryToReset={() => {
            setRecoveryStep("reset");
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
        onClose={() => setNotifyMeModal({ open: false, product: null, email: "", loading: false })}
        onEmailChange={(email) => setNotifyMeModal((prev) => ({ ...prev, email }))}
        onSubmit={submitNotifyMe}
      />

      <EcommerceFooter tenantContext={tenantContext} styles={S} onNavigate={setView} />
    </div>
  );
}
