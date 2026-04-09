import { useEffect, useMemo, useState } from 'react'
import { Bell, BellOff, MessageSquarePlus, Search, Shield, UserRound } from 'lucide-react'
import { type AdminUser, type ProfileNote, usersApi } from '../api/client'

function formatDate(value?: string) {
  if (!value) return 'нет данных'
  return new Date(value).toLocaleString('ru-RU')
}

export function Users() {
  const [items, setItems] = useState<AdminUser[]>([])
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selected, setSelected] = useState<AdminUser | null>(null)
  const [noteText, setNoteText] = useState('')
  const [loading, setLoading] = useState(true)

  const loadUsers = async (query = '') => {
    setLoading(true)
    try {
      const { data } = await usersApi.list({ search: query || undefined })
      setItems(data)
      if (!selectedId && data.length > 0) {
        setSelectedId(data[0].id)
      }
    } finally {
      setLoading(false)
    }
  }

  const loadProfile = async (userId: number) => {
    const { data } = await usersApi.get(userId)
    setSelected(data)
  }

  useEffect(() => {
    loadUsers()
  }, [])

  useEffect(() => {
    if (selectedId) loadProfile(selectedId)
  }, [selectedId])

  const filteredPlaceholder = useMemo(() => (loading ? 'Загрузка...' : 'Поиск по имени, username или email'), [loading])

  const submitNote = async () => {
    if (!selected || !noteText.trim()) return
    await usersApi.addNote(selected.id, noteText.trim())
    setNoteText('')
    await loadProfile(selected.id)
    await loadUsers(search)
  }

  const toggleWatch = async () => {
    if (!selected) return
    if (selected.is_watching) await usersApi.unwatch(selected.id)
    else await usersApi.watch(selected.id)
    await loadProfile(selected.id)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Пользователи</h2>
          <p className="text-sm text-slate-500 mt-1">Профили сотрудников, заметки и подписки на уведомления.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-4">
        <section className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-4 border-b border-slate-100">
            <label className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50 border border-slate-200">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadUsers(search)}
                className="w-full bg-transparent outline-none text-sm"
                placeholder={filteredPlaceholder}
              />
            </label>
          </div>
          <div className="max-h-[70vh] overflow-y-auto">
            {items.map((user) => (
              <button
                key={user.id}
                onClick={() => setSelectedId(user.id)}
                className={`w-full text-left px-4 py-3 border-b border-slate-100 transition ${
                  selectedId === user.id ? 'bg-blue-50' : 'hover:bg-slate-50'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-800">{user.first_name} {user.last_name || ''}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {user.username ? `@${user.username}` : 'без username'} · {user.role}
                    </div>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600">
                    {user.notes_count || 0}
                  </span>
                </div>
              </button>
            ))}
            {!loading && items.length === 0 && (
              <div className="p-6 text-sm text-slate-400 text-center">Пользователей не найдено</div>
            )}
          </div>
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-slate-100 min-h-[420px]">
          {!selected ? (
            <div className="h-full flex items-center justify-center text-slate-400">
              Выберите пользователя слева
            </div>
          ) : (
            <div className="p-5 space-y-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center">
                    <UserRound className="w-7 h-7 text-slate-500" />
                  </div>
                  <div>
                    <div className="text-xl font-bold text-slate-800">{selected.first_name} {selected.last_name || ''}</div>
                    <div className="text-sm text-slate-500 mt-1">
                      {selected.username ? `@${selected.username}` : 'без username'} · {selected.role}
                    </div>
                  </div>
                </div>
                <button
                  onClick={toggleWatch}
                  className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium ${
                    selected.is_watching ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'
                  }`}
                >
                  {selected.is_watching ? <BellOff className="w-4 h-4" /> : <Bell className="w-4 h-4" />}
                  {selected.is_watching ? 'Не следить' : 'Следить'}
                </button>
              </div>

              <div className="grid md:grid-cols-3 gap-3">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Telegram</div>
                  <div className="mt-2 text-sm font-medium text-slate-700">{selected.telegram_user_id || 'нет'}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Активность</div>
                  <div className="mt-2 text-sm font-medium text-slate-700">{formatDate(selected.last_active_at)}</div>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <div className="text-xs uppercase tracking-wide text-slate-400">Подписчики</div>
                  <div className="mt-2 text-sm font-medium text-slate-700">{selected.watchers_count || 0}</div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 p-4">
                <div className="flex items-center gap-2 text-slate-800 font-semibold mb-3">
                  <MessageSquarePlus className="w-4 h-4" />
                  Новая заметка
                </div>
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Например: отвечает быстро по поставкам, лучше писать утром."
                  className="w-full min-h-28 rounded-xl border border-slate-200 px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-200"
                />
                <div className="flex justify-end mt-3">
                  <button
                    onClick={submitNote}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-medium"
                  >
                    <Shield className="w-4 h-4" />
                    Сохранить заметку
                  </button>
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold text-slate-800 mb-3">История заметок</div>
                <div className="space-y-3">
                  {(selected.notes || []).map((note: ProfileNote) => (
                    <div key={note.id} className="rounded-2xl border border-slate-200 p-4">
                      <div className="text-sm text-slate-700 whitespace-pre-wrap">{note.body}</div>
                      <div className="mt-2 text-xs text-slate-400">
                        {note.author_name || 'Система'} · {formatDate(note.created_at)}
                      </div>
                    </div>
                  ))}
                  {(!selected.notes || selected.notes.length === 0) && (
                    <div className="text-sm text-slate-400">Пока нет заметок по этому сотруднику.</div>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
