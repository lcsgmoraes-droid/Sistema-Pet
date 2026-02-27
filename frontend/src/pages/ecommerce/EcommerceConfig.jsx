import { useEffect, useState } from 'react'
import { api } from '../../services/api'

const DIAS_SEMANA = [
  { key: 'seg', label: 'Segunda' },
  { key: 'ter', label: 'Terça' },
  { key: 'qua', label: 'Quarta' },
  { key: 'qui', label: 'Quinta' },
  { key: 'sex', label: 'Sexta' },
  { key: 'sab', label: 'Sábado' },
  { key: 'dom', label: 'Domingo' },
]

function parseDias(diasStr) {
  if (!diasStr) return []
  return diasStr.split(',').map((d) => d.trim()).filter(Boolean)
}

function formatDias(diasArr) {
  return diasArr.join(',')
}

export default function EcommerceConfig() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const [ativo, setAtivo] = useState(true)
  const [descricao, setDescricao] = useState('')
  const [horarioAbertura, setHorarioAbertura] = useState('')
  const [horarioFechamento, setHorarioFechamento] = useState('')
  const [diasSelecionados, setDiasSelecionados] = useState([])

  // Avise-me pendentes
  const [avisos, setAvisos] = useState([])
  const [loadingAvisos, setLoadingAvisos] = useState(true)

  useEffect(() => {
    fetchConfig()
    fetchAvisos()
  }, [])

  async function fetchConfig() {
    try {
      const res = await api.get('/ecommerce-config')
      const d = res.data
      setAtivo(d.ecommerce_ativo ?? true)
      setDescricao(d.ecommerce_descricao || '')
      setHorarioAbertura(d.ecommerce_horario_abertura || '')
      setHorarioFechamento(d.ecommerce_horario_fechamento || '')
      setDiasSelecionados(parseDias(d.ecommerce_dias_funcionamento))
    } catch (err) {
      setError('Não foi possível carregar as configurações.')
    } finally {
      setLoading(false)
    }
  }

  async function fetchAvisos() {
    try {
      const res = await api.get('/ecommerce-notify/pendentes')
      setAvisos(res.data || [])
    } catch {
      // silencioso
    } finally {
      setLoadingAvisos(false)
    }
  }

  async function salvar(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      await api.put('/ecommerce-config', {
        ecommerce_ativo: ativo,
        ecommerce_descricao: descricao || null,
        ecommerce_horario_abertura: horarioAbertura || null,
        ecommerce_horario_fechamento: horarioFechamento || null,
        ecommerce_dias_funcionamento: diasSelecionados.length > 0 ? formatDias(diasSelecionados) : null,
      })
      setSuccess('Configurações salvas com sucesso!')
      setTimeout(() => setSuccess(''), 4000)
    } catch {
      setError('Erro ao salvar. Tente novamente.')
    } finally {
      setSaving(false)
    }
  }

  function toggleDia(key) {
    setDiasSelecionados((prev) =>
      prev.includes(key) ? prev.filter((d) => d !== key) : [...prev, key]
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    )
  }

  // Agrupar avisos por produto
  const avisosPorProduto = avisos.reduce((acc, aviso) => {
    const key = `${aviso.product_id}__${aviso.product_name || 'Produto'}`
    if (!acc[key]) acc[key] = { product_id: aviso.product_id, product_name: aviso.product_name || 'Produto', emails: [] }
    acc[key].emails.push(aviso.email)
    return acc
  }, {})

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">⚙️ Configurações da Loja Virtual</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm">
          {success}
        </div>
      )}

      <form onSubmit={salvar} className="space-y-6">
        {/* Status da loja */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Status da Loja</h2>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-700">Loja online</p>
              <p className="text-sm text-gray-500">
                {ativo
                  ? 'Sua loja está visível e aceitando pedidos.'
                  : 'Sua loja está offline. Clientes não conseguem fazer pedidos.'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAtivo((v) => !v)}
              className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none ${
                ativo ? 'bg-indigo-500' : 'bg-gray-300'
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                  ativo ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Descrição */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-3">
          <h2 className="text-base font-semibold text-gray-800">Descrição da Loja</h2>
          <textarea
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            rows={3}
            maxLength={500}
            placeholder="Ex.: Petshop especializado em cães e gatos. Atendemos com carinho! 🐾"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
          />
          <p className="text-xs text-gray-400 text-right">{descricao.length}/500</p>
        </div>

        {/* Horário */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Horário de Funcionamento</h2>
          <p className="text-sm text-gray-500">
            Exibido como informação na loja. Não bloqueia pedidos fora do horário.
          </p>
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Abertura</label>
              <input
                type="time"
                value={horarioAbertura}
                onChange={(e) => setHorarioAbertura(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <span className="text-gray-400 mt-5">até</span>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Fechamento</label>
              <input
                type="time"
                value={horarioFechamento}
                onChange={(e) => setHorarioFechamento(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
          </div>

          {/* Dias da semana */}
          <div>
            <p className="text-xs font-medium text-gray-600 mb-2">Dias de funcionamento</p>
            <div className="flex flex-wrap gap-2">
              {DIAS_SEMANA.map((dia) => (
                <button
                  key={dia.key}
                  type="button"
                  onClick={() => toggleDia(dia.key)}
                  className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
                    diasSelecionados.includes(dia.key)
                      ? 'bg-indigo-500 text-white border-indigo-500'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-indigo-400'
                  }`}
                >
                  {dia.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-colors"
        >
          {saving ? 'Salvando…' : 'Salvar Configurações'}
        </button>
      </form>

      {/* Avisos de Estoque Pendentes */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-800">
            🔔 Avisos de Estoque Pendentes
          </h2>
          {avisos.length > 0 && (
            <span className="bg-red-100 text-red-600 text-xs font-bold px-2 py-0.5 rounded-full">
              {avisos.length}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500">
          Clientes que pediram para ser avisados quando um produto voltar ao estoque. Os emails
          são enviados automaticamente quando você aumenta o estoque do produto.
        </p>

        {loadingAvisos ? (
          <div className="animate-pulse h-10 bg-gray-100 rounded" />
        ) : Object.keys(avisosPorProduto).length === 0 ? (
          <p className="text-sm text-gray-400 italic">Nenhum aviso pendente no momento.</p>
        ) : (
          <div className="space-y-3">
            {Object.values(avisosPorProduto).map((grupo) => (
              <div
                key={grupo.product_id}
                className="border border-gray-100 rounded-lg p-3 space-y-1"
              >
                <p className="font-medium text-sm text-gray-800">{grupo.product_name}</p>
                <p className="text-xs text-gray-500">
                  {grupo.emails.length} cliente{grupo.emails.length !== 1 ? 's' : ''} aguardando:{' '}
                  <span className="text-gray-400">{grupo.emails.join(', ')}</span>
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
