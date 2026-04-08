import WebApp from '../telegram'

export function useTelegram() {
  const tg = WebApp

  const onClose = () => tg.close()
  const onToggleButton = () => {
    if (tg.MainButton.isVisible) {
      tg.MainButton.hide()
    } else {
      tg.MainButton.show()
    }
  }

  return {
    tg,
    user: tg.initDataUnsafe?.user,
    initData: tg.initData,
    colorScheme: tg.colorScheme,
    onClose,
    onToggleButton,
  }
}
