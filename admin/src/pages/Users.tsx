import { Users as UsersIcon, Construction } from 'lucide-react'

export function Users() {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold text-slate-800">Пользователи</h2>
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 flex flex-col items-center justify-center h-80 text-slate-400 gap-4">
        <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center">
          <UsersIcon className="w-8 h-8 text-slate-400" />
        </div>
        <div className="text-center">
          <p className="text-base font-semibold text-slate-600">Управление пользователями</p>
          <p className="text-sm mt-1 flex items-center gap-1.5 justify-center text-slate-400">
            <Construction className="w-4 h-4" />
            Раздел в разработке
          </p>
        </div>
        <p className="text-xs text-slate-300 max-w-xs text-center">
          Здесь будет управление агентами, ролями и правами доступа.
        </p>
      </div>
    </div>
  )
}
