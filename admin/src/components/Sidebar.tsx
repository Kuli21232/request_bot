import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Network,
  Radio,
  FolderKanban,
  MessageSquare,
  BarChart2,
  Users,
  Building2,
  ChevronLeft,
  ChevronRight,
  Bot,
} from 'lucide-react'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Панель' },
  { to: '/topics', icon: Network, label: 'Топики' },
  { to: '/signals', icon: Radio, label: 'Сигналы' },
  { to: '/cases', icon: FolderKanban, label: 'Кейсы' },
  { to: '/requests', icon: MessageSquare, label: 'Заявки' },
  { to: '/analytics', icon: BarChart2, label: 'Аналитика' },
  { to: '/departments', icon: Building2, label: 'Отделы' },
  { to: '/users', icon: Users, label: 'Пользователи' },
]

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={`
        flex flex-col bg-slate-800 text-white transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-64'}
        min-h-screen flex-shrink-0 relative
      `}
    >
      <div className="flex items-center h-16 px-4 border-b border-slate-700 flex-shrink-0">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="bg-blue-500 rounded-lg p-1.5 flex-shrink-0">
            <Bot className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="text-white font-semibold text-sm leading-tight truncate">FlowDesk</p>
              <p className="text-slate-400 text-xs truncate">Admin Panel</p>
            </div>
          )}
        </div>
      </div>

      <nav className="flex-1 py-4 overflow-y-auto scrollbar-thin">
        <ul className="space-y-1 px-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-900/30'
                      : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`
                }
                title={collapsed ? label : undefined}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed && <span className="text-sm font-medium truncate">{label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="p-2 border-t border-slate-700 flex-shrink-0">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:bg-slate-700 hover:text-white transition-colors"
          title={collapsed ? 'Развернуть' : 'Свернуть'}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span className="text-xs">Свернуть</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}
