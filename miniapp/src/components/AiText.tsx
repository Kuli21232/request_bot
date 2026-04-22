/**
 * Formats plain AI-generated summary text into a readable block.
 * Splits into bullets on ';' or '. ', bolds text inside **…**, highlights numbers,
 * and emphasizes lines starting with capital-case "Label:" patterns.
 */
export function AiText({ text, compact = false }: { text?: string | null; compact?: boolean }) {
  if (!text) return null
  const paragraphs = text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: compact ? 6 : 10 }}>
      {paragraphs.map((para, idx) => {
        const bullets = splitBullets(para)
        if (bullets.length > 1) {
          return (
            <ul key={idx} style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 5 }}>
              {bullets.map((b, i) => (
                <li key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 14, lineHeight: 1.5, color: 'var(--text-main)' }}>
                  <span style={{ color: 'var(--brand)', marginTop: 2, fontWeight: 800 }}>•</span>
                  <span style={{ flex: 1 }}>{renderInline(b)}</span>
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={idx} style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: 'var(--text-main)' }}>
            {renderInline(para)}
          </p>
        )
      })}
    </div>
  )
}

function splitBullets(text: string): string[] {
  const semi = text.split(/\s*;\s+/).map((s) => s.trim()).filter(Boolean)
  if (semi.length > 1) return semi
  const sentences = text.split(/(?<=[.!?])\s+(?=[A-ZА-ЯЁ])/u).map((s) => s.trim()).filter(Boolean)
  if (sentences.length > 2) return sentences
  return [text]
}

function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = []
  const labelMatch = /^([A-ZА-ЯЁ][А-Яа-яA-Za-zЁё0-9 \-]{2,40}):\s+/u.exec(text)
  let rest = text
  if (labelMatch) {
    nodes.push(
      <strong key="label" style={{ color: 'var(--text-main)', fontWeight: 800 }}>
        {labelMatch[1]}:
      </strong>,
      ' ',
    )
    rest = text.slice(labelMatch[0].length)
  }

  const parts = rest.split(/(\*\*[^*]+\*\*|\b\d+[\d.,]*\s?(?:кг|шт|л|руб|₽|%)?)/gi)
  parts.forEach((part, i) => {
    if (!part) return
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      nodes.push(
        <strong key={`b-${i}`} style={{ color: 'var(--text-main)', fontWeight: 700 }}>
          {part.slice(2, -2)}
        </strong>,
      )
    } else if (/^\d+[\d.,]*\s?(?:кг|шт|л|руб|₽|%)?$/i.test(part)) {
      nodes.push(
        <span key={`n-${i}`} style={{ fontWeight: 700, color: '#1d4ed8' }}>
          {part}
        </span>,
      )
    } else {
      nodes.push(part)
    }
  })
  return nodes
}
