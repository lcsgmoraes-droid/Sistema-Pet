import { useEffect, useState } from 'react'
import { api } from '../../services/api'

function formatCurrency(v) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(v || 0))
}

function formatDate(iso) {
  if (!iso) return '-'
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(iso))
}

const STATUS_LABEL = {
  criado: { label: 'Aguardando', color: '#f59e0b', bg: '#fef3c7' },
  aprovado: { label: 'Aprovado', color: '#10b981', bg: '#d1fae5' },
  entregue: { label: 'Entregue', color: '#6366f1', bg: '#e0e7ff' },
  cancelado: { label: 'Cancelado', color: '#ef4444', bg: '#fee2e2' },
  carrinho: { label: 'Carrinho', color: '#9ca3af', bg: '#f3f4f6' },
}

function StatusBadge({ status }) {
  const s = STATUS_LABEL[status] || { label: status, color: '#6b7280', bg: '#f3f4f6' }
  return (
    <span style={{
      background: s.bg, color: s.color, padding: '2px 10px',
      borderRadius: 99, fontSize: 12, fontWeight: 600,
    }}>{s.label}</span>
  )
}

function StatCard({ icon, label, value, sub, color }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 12, padding: '20px 24px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.08)', flex: 1, minWidth: 160,
    }}>
      <div style={{ fontSize: 28, marginBottom: 6 }}>{icon}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: color || '#1f2937' }}>{value}</div>
      <div style={{ fontSize: 14, color: '#6b7280', marginTop: 2 }}>{label}</div>
      {sub && <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

export default function EcommerceAnalytics() {
  const [resumo, setResumo] = useState(null)
  const [demanda, setDemanda] = useState([])
  const [maisVendidos, setMaisVendidos] = useState([])
  const [pedidosRecentes, setPedidosRecentes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const [r1, r2, r3, r4] = await Promise.all([
          api.get('/ecommerce-analytics/resumo'),
          api.get('/ecommerce-analytics/demanda'),
          api.get('/ecommerce-analytics/mais-vendidos'),
          api.get('/ecommerce-analytics/pedidos-recentes'),
        ])
        setResumo(r1.data)
        setDemanda(r2.data)
        setMaisVendidos(r3.data)
        setPedidosRecentes(r4.data)
      } catch (e) {
        setError('Erro ao carregar dados de analytics.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>Carregando analytics...</div>
  if (error) return <div style={{ padding: 40, color: '#ef4444' }}>{error}</div>

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <span style={{ fontSize: 28 }}>📊</span>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: '#1f2937' }}>Analytics do E-commerce</h1>
          <p style={{ margin: 0, fontSize: 14, color: '#6b7280' }}>Visão geral de pedidos, demanda e produtos</p>
        </div>
      </div>

      {/* Cards de resumo */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 32 }}>
        <StatCard icon="🛍️" label="Total de pedidos" value={resumo?.total_pedidos ?? 0} sub={`${resumo?.pedidos_hoje ?? 0} hoje`} color="#6366f1" />
        <StatCard icon="💰" label="Receita total" value={formatCurrency(resumo?.receita_total)} sub={`Ticket médio: ${formatCurrency(resumo?.ticket_medio)}`} color="#10b981" />
        <StatCard icon="🛒" label="Carrinhos abandonados" value={resumo?.carrinhos_abandonados ?? 0} sub="Há mais de 1h sem finalizar" color="#f59e0b" />
        <StatCard icon="🔔" label="Avise-me pendentes" value={resumo?.avise_me_pendentes ?? 0} sub="Clientes aguardando reposição" color="#ef4444" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        {/* Demanda reprimida */}
        <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 18 }}>🔔</span>
            <div>
              <div style={{ fontWeight: 700, color: '#1f2937' }}>Demanda reprimida</div>
              <div style={{ fontSize: 12, color: '#9ca3af' }}>Produtos com "Avise-me" pendentes — precisa repor</div>
            </div>
          </div>
          {demanda.length === 0 ? (
            <div style={{ padding: 24, color: '#9ca3af', textAlign: 'center' }}>Nenhum pedido de aviso pendente 🎉</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={th}>SKU</th>
                  <th style={th}>Produto</th>
                  <th style={{ ...th, textAlign: 'center' }}>Pedidos</th>
                  <th style={{ ...th, textAlign: 'center' }}>Estoque atual</th>
                </tr>
              </thead>
              <tbody>
                {demanda.map((d, i) => (
                  <tr key={`dem-${d.product_id ?? 'null'}-${i}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ ...td, color: '#6b7280', fontFamily: 'monospace' }}>{d.codigo || '-'}</td>
                    <td style={{ ...td, fontWeight: 500 }}>{d.product_name || `Produto #${d.product_id}`}</td>
                    <td style={{ ...td, textAlign: 'center' }}>
                      <span style={{ background: '#fee2e2', color: '#ef4444', borderRadius: 99, padding: '2px 10px', fontWeight: 700, fontSize: 13 }}>
                        {d.pendentes}
                      </span>
                    </td>
                    <td style={{ ...td, textAlign: 'center', color: d.estoque_atual <= 0 ? '#ef4444' : '#10b981', fontWeight: 600 }}>
                      {d.estoque_atual}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Mais vendidos */}
        <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 18 }}>🏆</span>
            <div>
              <div style={{ fontWeight: 700, color: '#1f2937' }}>Mais vendidos</div>
              <div style={{ fontSize: 12, color: '#9ca3af' }}>Produtos com maior volume de vendas no e-commerce</div>
            </div>
          </div>
          {maisVendidos.length === 0 ? (
            <div style={{ padding: 24, color: '#9ca3af', textAlign: 'center' }}>Nenhuma venda registrada ainda</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={th}>#</th>
                  <th style={th}>Produto</th>
                  <th style={{ ...th, textAlign: 'center' }}>Qtd vendida</th>
                  <th style={{ ...th, textAlign: 'right' }}>Receita</th>
                </tr>
              </thead>
              <tbody>
                {maisVendidos.map((p, i) => (
                  <tr key={`mv-${p.produto_id ?? 'null'}-${i}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ ...td, color: '#9ca3af', width: 32 }}>
                      {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                    </td>
                    <td style={{ ...td, fontWeight: 500 }}>{p.nome}</td>
                    <td style={{ ...td, textAlign: 'center', fontWeight: 700, color: '#6366f1' }}>{p.total_vendido}</td>
                    <td style={{ ...td, textAlign: 'right', color: '#10b981', fontWeight: 600 }}>{formatCurrency(p.receita)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Pedidos recentes */}
      <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #f3f4f6', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 18 }}>🧾</span>
          <div>
            <div style={{ fontWeight: 700, color: '#1f2937' }}>Pedidos recentes</div>
            <div style={{ fontSize: 12, color: '#9ca3af' }}>Últimos 30 pedidos do e-commerce</div>
          </div>
        </div>
        {pedidosRecentes.length === 0 ? (
          <div style={{ padding: 24, color: '#9ca3af', textAlign: 'center' }}>Nenhum pedido ainda</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9fafb' }}>
                <th style={th}>Pedido</th>
                <th style={{ ...th, textAlign: 'center' }}>Status</th>
                <th style={{ ...th, textAlign: 'center' }}>Itens</th>
                <th style={{ ...th, textAlign: 'right' }}>Total</th>
                <th style={{ ...th, textAlign: 'right' }}>Data</th>
              </tr>
            </thead>
            <tbody>
              {pedidosRecentes.map((p, i) => (
                <tr key={`pr-${p.pedido_id ?? i}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ ...td, fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>{p.pedido_id?.slice(0, 8)}…</td>
                  <td style={{ ...td, textAlign: 'center' }}><StatusBadge status={p.status} /></td>
                  <td style={{ ...td, textAlign: 'center', color: '#6b7280' }}>{p.qtd_itens} item(ns)</td>
                  <td style={{ ...td, textAlign: 'right', fontWeight: 600, color: '#1f2937' }}>{formatCurrency(p.total)}</td>
                  <td style={{ ...td, textAlign: 'right', color: '#9ca3af', fontSize: 12 }}>{formatDate(p.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

const th = {
  padding: '10px 16px', textAlign: 'left', fontSize: 12,
  fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em',
}
const td = { padding: '12px 16px', fontSize: 14, color: '#1f2937' }
