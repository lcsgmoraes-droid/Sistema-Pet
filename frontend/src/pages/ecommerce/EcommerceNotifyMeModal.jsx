export default function EcommerceNotifyMeModal({
  modal,
  styles: S,
  onClose,
  onEmailChange,
  onSubmit,
}) {
  if (!modal.open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.6)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
      onClick={onClose}
    >
      <div
        style={{ background: '#fff', borderRadius: 18, padding: 28, maxWidth: 380, width: '100%', boxShadow: '0 24px 80px rgba(0,0,0,0.25)', border: '1px solid #e5e7eb' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontSize: 32, marginBottom: 8 }}>🔔</div>
        <h3 style={{ margin: '0 0 8px', fontSize: 18, fontWeight: 800, color: '#1c1917' }}>Avise-me quando chegar</h3>
        <p style={{ margin: '0 0 18px', fontSize: 14, color: '#6b7280' }}>
          <strong>{modal.product?.nome}</strong> está sem estoque agora. Informe seu email e te avisamos quando voltar!
        </p>
        <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input type="email" required placeholder="seu@email.com" value={modal.email} autoFocus onChange={(e) => onEmailChange(e.target.value)} style={S.formInput} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={onClose} style={{ flex: 1, padding: '10px 0', borderRadius: 10, border: '1.5px solid #e5e7eb', background: '#fff', color: '#374151', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>Cancelar</button>
            <button type="submit" disabled={modal.loading} style={{ flex: 2, padding: '10px 0', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #f97316 0%, #fb923c 100%)', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer', opacity: modal.loading ? 0.7 : 1 }}>
              {modal.loading ? 'Registrando…' : '🔔 Me avise!'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
