interface LoaderProps {
  size?: 'sm' | 'md' | 'lg'
  fullPage?: boolean
}

export function Loader({ size = 'md', fullPage = false }: LoaderProps) {
  const sizes = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-2',
    lg: 'h-12 w-12 border-4',
  }

  const spinner = (
    <div
      className={`${sizes[size]} animate-spin rounded-full border-slate-300 border-t-blue-500`}
    />
  )

  if (fullPage) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-slate-50/80 z-50">
        <div className="flex flex-col items-center gap-3">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-300 border-t-blue-500" />
          <p className="text-slate-500 text-sm">Загрузка...</p>
        </div>
      </div>
    )
  }

  return spinner
}
