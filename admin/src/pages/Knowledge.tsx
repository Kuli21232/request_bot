import { useEffect, useState } from 'react'
import { BookOpen, Plus, Save, Search } from 'lucide-react'
import { knowledgeApi, type KnowledgeArticle } from '../api/client'

const EMPTY_FORM = {
  title: '',
  slug: '',
  summary: '',
  body: '',
  tags: '',
  audience: 'all',
  is_published: true,
}

export function Knowledge() {
  const [items, setItems] = useState<KnowledgeArticle[]>([])
  const [selected, setSelected] = useState<KnowledgeArticle | null>(null)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState(EMPTY_FORM)

  const load = async (query = '') => {
    const { data } = await knowledgeApi.list({ search: query, include_drafts: true })
    setItems(data)
    if (!selected && data.length > 0) {
      setSelected(data[0])
    }
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    if (!selected) {
      setForm(EMPTY_FORM)
      return
    }
    setForm({
      title: selected.title,
      slug: selected.slug,
      summary: selected.summary || '',
      body: selected.body,
      tags: (selected.tags || []).join(', '),
      audience: selected.audience,
      is_published: selected.is_published,
    })
  }, [selected])

  const save = async () => {
    const payload = {
      title: form.title,
      slug: form.slug,
      summary: form.summary || undefined,
      body: form.body,
      tags: form.tags.split(',').map((item) => item.trim()).filter(Boolean),
      audience: form.audience,
      is_published: form.is_published,
    }
    if (selected) {
      const { data } = await knowledgeApi.update(selected.id, payload)
      setSelected(data)
    } else {
      const { data } = await knowledgeApi.create(payload)
      setSelected(data)
    }
    await load(search)
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-slate-800">База знаний</h2>
        <p className="text-sm text-slate-500 mt-1">Статьи, по которым бот отвечает на вопросы и проводит инструктаж.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-4">
        <section className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex gap-2">
            <label className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 flex-1">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && load(search)}
                className="w-full bg-transparent outline-none text-sm"
                placeholder="Поиск по знаниям"
              />
            </label>
            <button
              onClick={() => setSelected(null)}
              className="inline-flex items-center justify-center w-10 rounded-xl bg-slate-900 text-white"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="max-h-[70vh] overflow-y-auto">
            {items.map((article) => (
              <button
                key={article.id}
                onClick={() => setSelected(article)}
                className={`w-full text-left px-4 py-3 border-b border-slate-100 transition ${
                  selected?.id === article.id ? 'bg-blue-50' : 'hover:bg-slate-50'
                }`}
              >
                <div className="font-semibold text-slate-800">{article.title}</div>
                <div className="text-xs text-slate-500 mt-1">{article.slug} · {article.audience}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5 space-y-4">
          <div className="flex items-center gap-2 text-slate-800 font-semibold">
            <BookOpen className="w-5 h-5" />
            {selected ? 'Редактирование статьи' : 'Новая статья'}
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <input
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              placeholder="Название"
              className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none"
            />
            <input
              value={form.slug}
              onChange={(e) => setForm((prev) => ({ ...prev, slug: e.target.value }))}
              placeholder="slug"
              className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none"
            />
          </div>

          <input
            value={form.summary}
            onChange={(e) => setForm((prev) => ({ ...prev, summary: e.target.value }))}
            placeholder="Короткое описание"
            className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none"
          />

          <div className="grid md:grid-cols-2 gap-3">
            <input
              value={form.tags}
              onChange={(e) => setForm((prev) => ({ ...prev, tags: e.target.value }))}
              placeholder="Теги через запятую"
              className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none"
            />
            <select
              value={form.audience}
              onChange={(e) => setForm((prev) => ({ ...prev, audience: e.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none"
            >
              <option value="all">Все</option>
              <option value="agent">Исполнители</option>
              <option value="admin">Руководители</option>
            </select>
          </div>

          <textarea
            value={form.body}
            onChange={(e) => setForm((prev) => ({ ...prev, body: e.target.value }))}
            placeholder="Полный текст инструкции"
            className="w-full min-h-[320px] rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none"
          />

          <label className="inline-flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={form.is_published}
              onChange={(e) => setForm((prev) => ({ ...prev, is_published: e.target.checked }))}
            />
            Статья опубликована
          </label>

          <div className="flex justify-end">
            <button
              onClick={save}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-medium"
            >
              <Save className="w-4 h-4" />
              Сохранить
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
