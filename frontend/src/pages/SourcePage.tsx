import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError, api } from "../lib/api";
import { ErrorState, LoadingState } from "../components/States";
import { OriginBadge } from "../components/OriginBadge";
import type { SourceDetail } from "../types";

export function SourcePage() {
  const { sourceId } = useParams<{ sourceId: string }>();
  const auth = useAuth();
  const [source, setSource] = useState<SourceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((reason: unknown) => {
    if (reason instanceof ApiError && reason.status === 401) {
      auth.expireSession();
      return;
    }
    setError(reason instanceof Error ? reason.message : "Неизвестная ошибка.");
  }, [auth]);

  const load = useCallback(async () => {
    if (!sourceId) return;
    setLoading(true);
    setError(null);
    try {
      setSource(await api.source(sourceId));
    } catch (reason) {
      handleError(reason);
    } finally {
      setLoading(false);
    }
  }, [handleError, sourceId]);

  useEffect(() => {
    if (!sourceId) return;
    let active = true;
    api.source(sourceId)
      .then((result) => {
        if (active) setSource(result);
      })
      .catch((reason: unknown) => {
        if (active) handleError(reason);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [handleError, sourceId]);

  return (
    <section className="source-panel" aria-labelledby="source-heading">
      <Link className="back-link" to="/">← Назад к приоритетам</Link>
      {loading ? <LoadingState label="Загружаем исходное сообщение…" /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!loading && !error && source ? (
        <article>
          <div className="section-heading">
            <div>
              <p className="eyebrow">{source.source_type} · {source.external_id}</p>
              <h1 id="source-heading">{source.title}</h1>
            </div>
            <OriginBadge origin={source.data_origin} />
          </div>
          <time dateTime={source.source_timestamp}>
            {new Intl.DateTimeFormat("ru-RU", { dateStyle: "full", timeStyle: "short" }).format(new Date(source.source_timestamp))}
          </time>
          <p className="source-content">{source.content}</p>
          {source.source_url ? (
            <a href={source.source_url} target="_blank" rel="noreferrer">Открыть внешний источник</a>
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
