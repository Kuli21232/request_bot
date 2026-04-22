import { Link, useLocation } from 'react-router-dom'

const TABS = [
  { path: '/',        label: 'Обзор',    icon: HomeIcon },
  { path: '/topics',  label: 'Темы',     icon: TopicIcon },
  { path: '/signals', label: 'Поток',    icon: ListIcon },
  { path: '/cases',   label: 'Ситуации', icon: FolderIcon },
  { path: '/team',    label: 'Команда',  icon: UserIcon },
]

function HomeIcon({ active }: { active: boolean }) {
  return (
    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      stroke={active ? 'var(--brand)' : 'var(--text-muted)'}>
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"
        fill={active ? 'rgba(15,118,110,0.12)' : 'none'} />
      <path d="M9 21V12h6v9" />
    </svg>
  )
}

function ListIcon({ active }: { active: boolean }) {
  return (
    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      stroke={active ? 'var(--brand)' : 'var(--text-muted)'}>
      <path d="M4 6h16M4 10h16M4 14h10M4 18h6" />
    </svg>
  )
}

function FolderIcon({ active }: { active: boolean }) {
  return (
    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      stroke={active ? 'var(--brand)' : 'var(--text-muted)'}>
      <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"
        fill={active ? 'rgba(15,118,110,0.12)' : 'none'} />
    </svg>
  )
}

function TopicIcon({ active }: { active: boolean }) {
  return (
    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      stroke={active ? 'var(--brand)' : 'var(--text-muted)'}>
      <rect x="3" y="3" width="18" height="18" rx="3"
        fill={active ? 'rgba(15,118,110,0.12)' : 'none'} />
      <path d="M7 8h10M7 12h7M7 16h5" />
    </svg>
  )
}

function UserIcon({ active }: { active: boolean }) {
  return (
    <svg width="23" height="23" viewBox="0 0 24 24" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      stroke={active ? 'var(--brand)' : 'var(--text-muted)'}>
      <circle cx="12" cy="8" r="4" fill={active ? 'rgba(15,118,110,0.12)' : 'none'} />
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
    </svg>
  )
}

export function BottomNav() {
  const { pathname } = useLocation()

  return (
    <nav style={{
      position: 'fixed',
      bottom: 0, left: 0, right: 0,
      background: 'rgba(255,255,255,0.96)',
      borderTop: '1px solid rgba(15,23,42,0.07)',
      paddingBottom: 'calc(env(safe-area-inset-bottom) + 2px)',
      display: 'flex',
      backdropFilter: 'blur(20px)',
      boxShadow: '0 -4px 20px rgba(15,23,42,0.07)',
      zIndex: 100,
    }}>
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
              justifyContent: 'center',
              padding: '10px 0 8px',
              gap: 3,
              textDecoration: 'none',
              color: active ? 'var(--brand)' : 'var(--text-muted)',
              fontSize: 10,
              fontWeight: active ? 700 : 500,
              position: 'relative',
            }}
          >
            {/* Active indicator bar at top */}
            {active && (
              <span style={{
                position: 'absolute',
                top: 0, left: '20%', right: '20%',
                height: 2,
                borderRadius: '0 0 3px 3px',
                background: 'var(--brand)',
              }} />
            )}
            <Icon active={active} />
            <span style={{ letterSpacing: '0.01em' }}>{tab.label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
