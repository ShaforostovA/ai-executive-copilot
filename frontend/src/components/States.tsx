export function LoadingState({ label = "Загрузка данных…" }: { label?: string }) {
  return (
    <div className="state-panel" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-panel state-error" role="alert">
      <strong>Не удалось загрузить данные</strong>
      <p>{message}</p>
      {onRetry ? (
        <button className="button button-secondary" onClick={onRetry} type="button">
          Повторить
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState() {
  return (
    <div className="state-panel" role="status">
      <strong>Срочных событий нет</strong>
      <p>Новые приоритетные события появятся здесь после анализа источников.</p>
    </div>
  );
}
