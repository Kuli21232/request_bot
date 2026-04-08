import type { VolumePoint } from '../api/client'

interface Props {
  data: VolumePoint[]
  height?: number
  color?: string
}

function fmtDay(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }).replace(' ', '/')
}

export function MiniBarChart({ data, height = 64, color = '#2481cc' }: Props) {
  if (!data || data.length === 0) return (
    <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb', fontSize: 12 }}>
      Нет данных
    </div>
  )
  const max = Math.max(...data.map(d => d.count), 1)
  const barW = 28
  const gap = 6
  const padL = 4
  const totalW = data.length * (barW + gap) - gap + padL * 2
  const padB = 20

  return (
    <div style={{ width: '100%', overflowX: 'auto' }} className="scrollbar-hide">
      <svg width={totalW} height={height + padB} style={{ display: 'block', minWidth: '100%' }}>
        {data.map((pt, i) => {
          const barH = Math.max(3, (pt.count / max) * (height - 12))
          const x = padL + i * (barW + gap)
          const y = height - barH
          return (
            <g key={pt.day}>
              <rect x={x} y={y} width={barW} height={barH} rx={5}
                fill={i === data.length - 1 ? color : `${color}99`} />
              {pt.count > 0 && (
                <text x={x + barW / 2} y={y - 3} textAnchor="middle" fontSize={9} fill={color} fontWeight="700">
                  {pt.count}
                </text>
              )}
              <text x={x + barW / 2} y={height + padB - 2} textAnchor="middle" fontSize={9} fill="#aaa">
                {fmtDay(pt.day)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
