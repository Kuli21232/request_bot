import type { FlowCase, FlowSignal, Topic, TopicSection } from '../api/client'

const SIGNAL_KIND_LABELS: Record<string, string> = {
  problem: 'Проблема',
  request: 'Запрос',
  status_update: 'Обновление',
  photo_report: 'Фотоотчет',
  delivery: 'Доставка',
  finance: 'Финансы',
  compliance: 'Контроль',
  inventory: 'Товар',
  'chat/noise': 'Шум',
  escalation: 'Срочно',
  news: 'Новости',
}

const IMPORTANCE_LABELS: Record<string, string> = {
  low: 'Низкий приоритет',
  normal: 'Обычный приоритет',
  medium: 'Обычный приоритет',
  high: 'Важно',
  critical: 'Критично',
}

const ACTION_LABELS: Record<string, string> = {
  ignore: 'Можно пропустить',
  digest_only: 'В сводку',
  attach_to_case: 'Добавить в ситуацию',
  create_case: 'Открыть ситуацию',
  suggest_escalation: 'Эскалировать',
  suggest_reply: 'Нужен ответ',
  route_to_topic: 'Перенаправить',
  shadow_request: 'Отдать в работу',
  review_topic_queue: 'Разобрать топик',
  watch_topic: 'Наблюдать',
  collect_context: 'Собрать контекст',
  follow_up: 'Нужен follow-up',
}

const CASE_STATUS_LABELS: Record<string, string> = {
  open: 'Активна',
  watching: 'Под наблюдением',
  resolved: 'Решена',
  closed: 'Закрыта',
}

const CASE_PRIORITY_LABELS: Record<string, string> = {
  low: 'Спокойно',
  normal: 'Обычно',
  medium: 'Обычно',
  high: 'Важно',
  critical: 'Критично',
}

const TOPIC_KIND_LABELS: Record<string, string> = {
  operational: 'Рабочий топик',
  operations: 'Операционный поток',
  finance: 'Финансовый топик',
  reporting: 'Отчетность',
  support: 'Поддержка',
  compliance: 'Контроль',
  logistics: 'Логистика',
  incident: 'Инциденты',
  mixed: 'Смешанный поток',
}

export function getSignalKindLabel(kind?: string) {
  if (!kind) return 'Сообщение'
  return SIGNAL_KIND_LABELS[kind] ?? kind
}

export function getImportanceLabel(value?: string) {
  if (!value) return 'Без оценки'
  return IMPORTANCE_LABELS[value] ?? value
}

export function getRecommendedActionLabel(value?: string) {
  if (!value) return ''
  return ACTION_LABELS[value] ?? value
}

export function getCaseStatusLabel(value?: string) {
  if (!value) return 'Активна'
  return CASE_STATUS_LABELS[value] ?? value
}

export function getCasePriorityLabel(value?: string) {
  if (!value) return 'Обычно'
  return CASE_PRIORITY_LABELS[value] ?? value
}

export function getTopicKindLabel(value?: string) {
  if (!value) return 'Топик'
  return TOPIC_KIND_LABELS[value] ?? value
}

export function getSignalAccent(signal: Pick<FlowSignal, 'importance' | 'has_media' | 'is_noise'>) {
  if (signal.is_noise) return '#64748b'
  if (signal.importance === 'critical') return '#dc2626'
  if (signal.importance === 'high') return '#ea580c'
  if (signal.has_media) return '#0f766e'
  return '#2563eb'
}

export function getCaseAccent(flowCase: Pick<FlowCase, 'is_critical' | 'priority'>) {
  if (flowCase.is_critical || flowCase.priority === 'critical') return '#dc2626'
  if (flowCase.priority === 'high') return '#ea580c'
  return '#0f766e'
}

export function getTopicSummary(topic: Topic) {
  if (topic.profile?.automation?.summary) return topic.profile.automation.summary
  if (topic.profile?.profile_summary) return topic.profile.profile_summary
  if (topic.signal_count > 0) return `В потоке уже разобрано ${topic.signal_count} сообщений.`
  return 'Новый топик, система пока собирает контекст.'
}

export function getReadableSignalTitle(signal: Pick<FlowSignal, 'summary' | 'body' | 'kind'>) {
  return signal.summary || signal.body || getSignalKindLabel(signal.kind)
}

export function getReadableCaseHint(flowCase: Pick<FlowCase, 'summary' | 'signal_count' | 'stores_affected'>) {
  if (flowCase.summary) return flowCase.summary
  if (flowCase.stores_affected?.length) {
    return `Затронуто точек: ${flowCase.stores_affected.length}`
  }
  return `Сообщений в ситуации: ${flowCase.signal_count}`
}

export function getSectionAccent(section: Pick<TopicSection, 'priority'>) {
  if (section.priority === 'critical') return '#dc2626'
  if (section.priority === 'high') return '#ea580c'
  if (section.priority === 'normal') return '#0f766e'
  return '#64748b'
}

export function getTopicSectionSummary(section: TopicSection) {
  if (section.automation?.summary) return section.automation.summary
  if (section.profile_summary) return section.profile_summary
  return `В разделе ${section.stats.signal_count} сигналов и ${section.stats.open_case_count} активных ситуаций.`
}
