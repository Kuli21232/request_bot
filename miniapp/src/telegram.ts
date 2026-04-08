/**
 * Обёртка над Telegram WebApp SDK.
 * Использует глобальный window.Telegram.WebApp (загружается через telegram-web-app.js).
 */

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp }
  }
}

interface HapticFeedback {
  impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
  notificationOccurred(type: 'error' | 'success' | 'warning'): void
  selectionChanged(): void
}

interface TelegramWebApp {
  ready(): void
  expand(): void
  close(): void
  showAlert(message: string, callback?: () => void): void
  showConfirm(message: string, callback: (confirmed: boolean) => void): void
  initData: string
  initDataUnsafe: {
    user?: {
      id: number
      first_name: string
      last_name?: string
      username?: string
      language_code?: string
      photo_url?: string
    }
    query_id?: string
    auth_date?: number
    hash?: string
  }
  colorScheme: 'light' | 'dark'
  themeParams: Record<string, string>
  version: string
  platform: string
  HapticFeedback: HapticFeedback
  MainButton: {
    isVisible: boolean
    show(): void
    hide(): void
    setText(text: string): void
    onClick(cb: () => void): void
    offClick(cb: () => void): void
    enable(): void
    disable(): void
    showProgress(leaveActive?: boolean): void
    hideProgress(): void
  }
  BackButton: {
    isVisible: boolean
    show(): void
    hide(): void
    onClick(cb: () => void): void
    offClick(cb: () => void): void
  }
}

const fallbackHaptic: HapticFeedback = {
  impactOccurred: () => {},
  notificationOccurred: () => {},
  selectionChanged: () => {},
}

const fallbackWebApp: TelegramWebApp = {
  ready: () => {},
  expand: () => {},
  close: () => {},
  showAlert: (msg, cb) => { alert(msg); cb?.() },
  showConfirm: (msg, cb) => cb(window.confirm(msg)),
  initData: '',
  initDataUnsafe: {},
  colorScheme: 'light',
  themeParams: {},
  version: '6.0',
  platform: 'unknown',
  HapticFeedback: fallbackHaptic,
  MainButton: {
    isVisible: false, show: () => {}, hide: () => {}, setText: () => {},
    onClick: () => {}, offClick: () => {}, enable: () => {}, disable: () => {},
    showProgress: () => {}, hideProgress: () => {},
  },
  BackButton: {
    isVisible: false, show: () => {}, hide: () => {},
    onClick: () => {}, offClick: () => {},
  },
}

export const WebApp: TelegramWebApp = window.Telegram?.WebApp ?? fallbackWebApp

export const haptic = {
  light: () => WebApp.HapticFeedback.impactOccurred('light'),
  medium: () => WebApp.HapticFeedback.impactOccurred('medium'),
  success: () => WebApp.HapticFeedback.notificationOccurred('success'),
  error: () => WebApp.HapticFeedback.notificationOccurred('error'),
  warning: () => WebApp.HapticFeedback.notificationOccurred('warning'),
  select: () => WebApp.HapticFeedback.selectionChanged(),
}

export default WebApp
