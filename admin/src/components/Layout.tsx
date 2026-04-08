import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

const pageTitles: Record<string, string> = {
  '/': 'Панель управления',
  '/requests': 'Заявки',
  '/analytics': 'Аналитика',
  '/departments': 'Отделы',
  '/users': 'Пользователи',
}

export function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  const title =
    pageTitles[location.pathname] ||
    (location.pathname.startsWith('/requests/') ? 'Детали заявки' : 'Admin Panel')

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
