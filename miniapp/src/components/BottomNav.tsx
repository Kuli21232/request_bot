import { Link, useLocation } from 'react-router-dom'

const TABS = [
  { path: '/', label: 'Обзор', icon: HomeIcon },
  { path: '/topics', label: 'Темы', icon: TopicIcon },
  { path: '/signals', label: 'Поток', icon: ListIcon },
  { path: '/cases', label: 'Ситуации', icon: FolderIcon },
  { path: '/team', label: 'Профиль', icon: UserIcon },
]

function HomeIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#0f766e' : 'none'} stroke={active ? '#0f766e' : '#64748b'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z" />
      <path d="M9 21V12h6v9" />
    </svg>
  )
}

function ListIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#0f766e' : '#64748b'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

function FolderIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#0f766e' : '#64748b'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </svg>
  )
}

function TopicIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? '#0f766e' : '#64748b'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6h16" />
      <path d="M7 12h10" />
      <path d="M10 18h4" />
    </svg>
  )
}

function UserIcon({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#0f766e' : 'none'} stroke={active ? '#0f766e' : '#64748b'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

export function BottomNav() {
  const { pathname } = useLocation()

  return (
    <nav
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'rgba(255,255,255,0.92)',
        borderTop: '1px solid rgba(15,23,42,0.08)',
        paddingBottom: 'calc(env(safe-area-inset-bottom) + 2px)',
        display: 'flex',
        backdropFilter: 'blur(16px)',
        boxShadow: '0 -12px 30px rgba(15,23,42,0.08)',
        zIndex: 100,
      }}
    >
      {TABS.map((tab) => {
        const active = tab.path === '/' ? pathname === '/' : pathname.startsWith(tab.path)
        const Icon = tab.icon
        return (
          <Link
            key={tab.path}
            to={tab.path}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '9px 0 8px',
              gap: 3,
              textDecoration: 'none',
              color: active ? '#0f766e' : '#64748b',
              fontSize: 11,
              fontWeight: active ? 700 : 500,
            }}
          >
            <Icon active={active} />
            <span>{tab.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
