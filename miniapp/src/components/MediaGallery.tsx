import { useMemo, useState } from 'react'
import { type FlowMediaItem, resolveApiUrl } from '../api/client'

function isImage(item: FlowMediaItem) {
  return (item.mime_type || '').startsWith('image/')
}

function mediaLabel(item: FlowMediaItem) {
  if (item.kind === 'photo') return 'Фото'
  if (item.kind === 'video') return 'Видео'
  if (item.kind === 'voice') return 'Голос'
  if (item.kind === 'audio') return 'Аудио'
  if (item.kind === 'document') return 'Документ'
  return item.kind
}

export function MediaGallery({
  items,
  title = 'Медиа',
  compact = false,
}: {
  items: FlowMediaItem[]
  title?: string
  compact?: boolean
}) {
  const [selected, setSelected] = useState<FlowMediaItem | null>(null)
  const visibleItems = useMemo(() => items.filter(Boolean), [items])

  if (!visibleItems.length) return null

  return (
    <>
      <section className="glass-card" style={{ padding: 16 }}>
        <div className="section-title" style={{ marginBottom: 10 }}>
          {title}
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: compact ? 'repeat(2, minmax(0, 1fr))' : 'repeat(3, minmax(0, 1fr))',
            gap: 10,
          }}
        >
          {visibleItems.map((item) => {
            const previewUrl = resolveApiUrl(item.preview_url || item.content_url)
            const contentUrl = resolveApiUrl(item.content_url || item.preview_url)
            const image = isImage(item)
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setSelected(item)}
                style={{
                  border: '1px solid rgba(148,163,184,0.16)',
                  background: 'rgba(248,250,252,0.9)',
                  borderRadius: 18,
                  padding: 0,
                  overflow: 'hidden',
                  textAlign: 'left',
                  cursor: 'pointer',
                }}
              >
                <div
                  style={{
                    minHeight: compact ? 120 : 132,
                    background: image && previewUrl
                      ? 'transparent'
                      : 'linear-gradient(135deg, rgba(219,234,254,0.9), rgba(220,252,231,0.9))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {image && previewUrl ? (
                    <img
                      src={previewUrl}
                      alt={item.file_name || mediaLabel(item)}
                      style={{ width: '100%', height: compact ? 120 : 132, objectFit: 'cover', display: 'block' }}
                    />
                  ) : (
                    <div style={{ padding: 14, textAlign: 'center', color: 'var(--text-main)' }}>
                      <div style={{ fontSize: 26, marginBottom: 6 }}>
                        {item.kind === 'video' ? '🎬' : item.kind === 'voice' ? '🎙️' : item.kind === 'audio' ? '🎧' : '📄'}
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 700 }}>{mediaLabel(item)}</div>
                    </div>
                  )}
                </div>
                <div style={{ padding: '10px 12px 12px' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-main)' }}>{mediaLabel(item)}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-soft)', lineHeight: 1.4, marginTop: 4 }}>
                    {item.file_name || item.topic_title || 'Открыть вложение'}
                  </div>
                  {item.signal_summary && (
                    <div style={{ fontSize: 11, color: 'var(--text-soft)', lineHeight: 1.4, marginTop: 6 }}>
                      {item.signal_summary}
                    </div>
                  )}
                  {contentUrl && (
                    <div style={{ fontSize: 11, color: '#0f766e', marginTop: 8, fontWeight: 700 }}>
                      Открыть
                    </div>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </section>

      {selected && (
        <div
          onClick={() => setSelected(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15,23,42,0.82)',
            zIndex: 140,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 18,
          }}
        >
          <div
            onClick={(event) => event.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: 420,
              background: '#fff',
              borderRadius: 24,
              overflow: 'hidden',
              boxShadow: '0 20px 50px rgba(15,23,42,0.35)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px 0' }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)' }}>{mediaLabel(selected)}</div>
              <button
                type="button"
                onClick={() => setSelected(null)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  color: '#64748b',
                  fontSize: 20,
                }}
              >
                ×
              </button>
            </div>
            <div style={{ padding: 16 }}>
              {isImage(selected) ? (
                <img
                  src={resolveApiUrl(selected.content_url || selected.preview_url)}
                  alt={selected.file_name || mediaLabel(selected)}
                  style={{ width: '100%', maxHeight: '60vh', objectFit: 'contain', borderRadius: 18, background: '#f8fafc' }}
                />
              ) : (
                <div
                  style={{
                    minHeight: 180,
                    borderRadius: 18,
                    background: 'linear-gradient(135deg, rgba(219,234,254,0.9), rgba(220,252,231,0.9))',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  <div style={{ fontSize: 40 }}>
                    {selected.kind === 'video' ? '🎬' : selected.kind === 'voice' ? '🎙️' : selected.kind === 'audio' ? '🎧' : '📄'}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>{selected.file_name || mediaLabel(selected)}</div>
                </div>
              )}
              <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
                {selected.topic_title && (
                  <div style={{ fontSize: 13, color: 'var(--text-soft)' }}>
                    Топик: {selected.topic_title}
                  </div>
                )}
                {selected.signal_summary && (
                  <div style={{ fontSize: 13, color: 'var(--text-main)', lineHeight: 1.45 }}>
                    {selected.signal_summary}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {selected.width && selected.height && (
                    <span className="pill" style={{ background: '#eff6ff', color: '#1d4ed8' }}>
                      {selected.width}×{selected.height}
                    </span>
                  )}
                  {selected.duration_seconds && (
                    <span className="pill" style={{ background: '#f1f5f9', color: '#334155' }}>
                      {selected.duration_seconds} сек
                    </span>
                  )}
                </div>
                {selected.can_open_content && (
                  <a
                    href={resolveApiUrl(selected.content_url || selected.preview_url)}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: 16,
                      background: 'linear-gradient(135deg, #0f766e, #0ea5a4)',
                      color: '#fff',
                      textDecoration: 'none',
                      padding: '12px 16px',
                      fontSize: 14,
                      fontWeight: 700,
                      marginTop: 4,
                    }}
                  >
                    Открыть файл
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
