import { useState, useEffect } from 'react'
import { departmentsApi, type Department } from '../api/client'
import { Loader } from '../components/Loader'
import { Building2 } from 'lucide-react'

export function Departments() {
  const [departments, setDepartments] = useState<Department[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    departmentsApi.list()
      .then((r) => setDepartments(r.data))
      .catch(() => setError('Не удалось загрузить отделы'))
      .finally(() => setIsLoading(false))
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-600 rounded-xl p-6 text-sm text-center">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-800">Отделы</h2>
        <span className="text-sm text-slate-500">{departments.length} отделов</span>
      </div>

      {departments.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 flex flex-col items-center justify-center h-64 text-slate-400">
          <Building2 className="w-10 h-10 mb-3 opacity-40" />
          <p className="text-base font-medium">Отделы не найдены</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {departments.map((dept) => (
            <div
              key={dept.id}
              className="bg-white rounded-xl shadow-sm border border-slate-100 p-5 hover:shadow-md transition-shadow flex items-center gap-4"
            >
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0 text-2xl">
                {dept.emoji || <Building2 className="w-5 h-5 text-blue-400" />}
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-slate-800 truncate">{dept.name}</p>
                <p className="text-xs text-slate-400 mt-0.5">ID: {dept.id}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
