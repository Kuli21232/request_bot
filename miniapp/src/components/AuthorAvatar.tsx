import { getAuthorColor, getAuthorInitial } from '../utils/flow'

export function AuthorAvatar({
  name,
  userId,
  size = 26,
}: {
  name?: string | null
  userId?: number | string | null
  size?: number
}) {
  const color = getAuthorColor(userId ?? name ?? 0)
  return (
    <div
      title={name || 'Автор не определён'}
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        flexShrink: 0,
        background: color,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: Math.round(size * 0.42),
        fontWeight: 700,
        letterSpacing: '-0.01em',
      }}
    >
      {getAuthorInitial(name)}
    </div>
  )
}
