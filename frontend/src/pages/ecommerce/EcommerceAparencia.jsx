import { useEffect, useRef, useState } from 'react'
import { api } from '../../services/api'

const TIPOS = [
  { key: 'logo',     label: 'Logo da Loja',   desc: 'Aparece no cabeçalho da loja virtual (recomendado: 200×80 px)' },
  { key: 'banner_1', label: 'Banner 1',        desc: 'Primeiro slide do banner rotativo (recomendado: 1200×400 px)' },
  { key: 'banner_2', label: 'Banner 2',        desc: 'Segundo slide (opcional)' },
  { key: 'banner_3', label: 'Banner 3',        desc: 'Terceiro slide (opcional)' },
]

function PreviewImage({ url, label, cacheBuster }) {
  if (!url) return (
    <div style={{
      width: '100%', minHeight: 120, background: '#f3f4f6', border: '2px dashed #d1d5db',
      borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#9ca3af', fontSize: 14,
    }}>
      Sem imagem
    </div>
  )
  // Adiciona ?t= para evitar que o navegador use a imagem antiga do cache
  const src = url.startsWith('/uploads/') ? `${url}?t=${cacheBuster}` : url
  return (
    <img
      src={src}
      alt={label}
      style={{ width: '100%', maxHeight: 200, objectFit: 'contain', borderRadius: 8, border: '1px solid #e5e7eb' }}
    />
  )
}

export default function EcommerceAparencia() {
  const [aparencia, setAparencia] = useState({
    logo_url: null, banner_1_url: null, banner_2_url: null, banner_3_url: null,
  })
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState({})
  const [msg, setMsg] = useState(null)
  const [cacheBuster, setCacheBuster] = useState(Date.now())
  const inputRefs = useRef({})

  useEffect(() => {
    api.get('/ecommerce-aparencia')
      .then(r => setAparencia(r.data))
      .catch(() => setMsg({ tipo: 'erro', texto: 'Não foi possível carregar as configurações.' }))
      .finally(() => setCarregando(false))
  }, [])

  function mostrarMsg(tipo, texto) {
    setMsg({ tipo, texto })
    setTimeout(() => setMsg(null), 4000)
  }

  async function uploadArquivo(tipo, arquivo) {
    setSalvando(s => ({ ...s, [tipo]: true }))
    const form = new FormData()
    form.append('file', arquivo)
    try {
      const r = await api.post(`/ecommerce-aparencia/upload/${tipo}`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setAparencia(r.data)
      setCacheBuster(Date.now())
      mostrarMsg('ok', 'Imagem salva com sucesso!')
    } catch {
      mostrarMsg('erro', 'Erro ao enviar a imagem. Verifique o formato e o tamanho (máx. 5 MB).')
    } finally {
      setSalvando(s => ({ ...s, [tipo]: false }))
    }
  }

  async function remover(tipo) {
    setSalvando(s => ({ ...s, [tipo]: true }))
    try {
      const r = await api.delete(`/ecommerce-aparencia/${tipo}`)
      setAparencia(r.data)
      setCacheBuster(Date.now())
      mostrarMsg('ok', 'Imagem removida.')
    } catch {
      mostrarMsg('erro', 'Erro ao remover a imagem.')
    } finally {
      setSalvando(s => ({ ...s, [tipo]: false }))
    }
  }

  if (carregando) return (
    <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>Carregando...</div>
  )

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#111827', marginBottom: 4 }}>
        🖼️ Aparência da Loja
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 32 }}>
        Configure o logo e os banners que aparecem na sua loja virtual.
      </p>

      {msg && (
        <div style={{
          padding: '12px 16px',
          borderRadius: 8,
          marginBottom: 24,
          background: msg.tipo === 'ok' ? '#f0fdf4' : '#fef2f2',
          color: msg.tipo === 'ok' ? '#166534' : '#991b1b',
          border: `1px solid ${msg.tipo === 'ok' ? '#bbf7d0' : '#fecaca'}`,
          fontWeight: 500,
        }}>
          {msg.tipo === 'ok' ? '✅ ' : '❌ '}{msg.texto}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {TIPOS.map(({ key, label, desc }) => {
          const urlAtual = aparencia[`${key}_url`]
          const ocupado = salvando[key]

          return (
            <div key={key} style={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: 12,
              padding: 24,
              boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
            }}>
              <div style={{ marginBottom: 12 }}>
                <span style={{ fontWeight: 600, fontSize: 16, color: '#111827' }}>{label}</span>
                <span style={{ marginLeft: 10, fontSize: 13, color: '#9ca3af' }}>{desc}</span>
              </div>

              <PreviewImage url={urlAtual} label={label} cacheBuster={cacheBuster} />

              <div style={{ marginTop: 14, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  style={{ display: 'none' }}
                  ref={el => (inputRefs.current[key] = el)}
                  onChange={e => e.target.files[0] && uploadArquivo(key, e.target.files[0])}
                />
                <button
                  onClick={() => inputRefs.current[key]?.click()}
                  disabled={ocupado}
                  style={{
                    padding: '8px 18px',
                    background: ocupado ? '#d1d5db' : '#2e7d32',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 7,
                    fontWeight: 600,
                    cursor: ocupado ? 'not-allowed' : 'pointer',
                    fontSize: 14,
                  }}
                >
                  {ocupado ? 'Enviando...' : urlAtual ? '🔄 Trocar imagem' : '📤 Fazer upload'}
                </button>

                {urlAtual && (
                  <button
                    onClick={() => remover(key)}
                    disabled={ocupado}
                    style={{
                      padding: '8px 14px',
                      background: '#fff',
                      color: '#dc2626',
                      border: '1px solid #fca5a5',
                      borderRadius: 7,
                      fontWeight: 500,
                      cursor: ocupado ? 'not-allowed' : 'pointer',
                      fontSize: 14,
                    }}
                  >
                    🗑 Remover
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div style={{ marginTop: 32, padding: 16, background: '#fffbeb', borderRadius: 10, border: '1px solid #fde68a', fontSize: 13, color: '#92400e' }}>
        <strong>💡 Dica:</strong> As imagens são atualizadas imediatamente na loja após o upload. Para ver o resultado, acesse a <a href="/ecommerce" style={{ color: '#c41c1c' }}>prévia da loja</a>.
      </div>
    </div>
  )
}
