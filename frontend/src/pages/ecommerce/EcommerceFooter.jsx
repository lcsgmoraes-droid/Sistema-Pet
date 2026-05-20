const FOOTER_LINKS = [
  { label: '🛍️ Loja', view: 'loja' },
  { label: '🛒 Carrinho', view: 'carrinho' },
  { label: '📦 Pedidos', view: 'pedidos' },
  { label: '👤 Conta', view: 'conta' },
];

function getTenantName(tenantContext) {
  return tenantContext?.nome_fantasia || tenantContext?.nome || 'Pet Store';
}

export default function EcommerceFooter({ tenantContext, styles: S, onNavigate }) {
  const tenantName = getTenantName(tenantContext);

  return (
    <footer style={S.footer}>
      <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 28 }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 20, color: '#fff', marginBottom: 8 }}>
            🐾 {tenantName}
          </div>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
            Produtos de qualidade para o seu pet com carinho e dedicação. Compre online com facilidade!
          </div>
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.85)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Navegação</div>
          {FOOTER_LINKS.map(({ label, view }) => (
            <button key={view} onClick={() => onNavigate(view)} style={{ display: 'block', background: 'none', border: 'none', color: 'rgba(255,255,255,0.65)', fontSize: 13, cursor: 'pointer', padding: '3px 0', textAlign: 'left' }}>{label}</button>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.85)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>Contato</div>
          {tenantContext?.whatsapp && (
            <a href={`https://wa.me/55${tenantContext.whatsapp.replace(/\D/g, '')}`} target="_blank" rel="noreferrer" style={{ display: 'block', color: 'rgba(255,255,255,0.65)', fontSize: 13, textDecoration: 'none', marginBottom: 4 }}>📱 WhatsApp</a>
          )}
          {tenantContext?.email && (
            <a href={`mailto:${tenantContext.email}`} style={{ display: 'block', color: 'rgba(255,255,255,0.65)', fontSize: 13, textDecoration: 'none' }}>✉️ {tenantContext.email}</a>
          )}
          {tenantContext?.cidade && (
            <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12, marginTop: 8 }}>📍 {tenantContext.cidade}{tenantContext.uf ? `, ${tenantContext.uf}` : ''}</div>
          )}
        </div>
      </div>
      <div style={{ maxWidth: 1100, margin: '20px auto 0', paddingTop: 16, borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: 12, color: 'rgba(255,255,255,0.4)', textAlign: 'center' }}>
        © {new Date().getFullYear()} {tenantName}. Todos os direitos reservados.
      </div>
    </footer>
  );
}
