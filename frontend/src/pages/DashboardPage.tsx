import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { useAuth } from "../auth/AuthContext";
import { AttentionCard } from "../components/AttentionCard";
import { IntegrationList } from "../components/IntegrationList";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { OriginBadge } from "../components/OriginBadge";
import type { Digest } from "../types";

export function DashboardPage() {
  const auth = useAuth();
  const [digest, setDigest] = useState<Digest | null>(null);
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
    setLoading(true);
    setError(null);
    try {
      setDigest(await api.dashboard());
    } catch (reason) {
      handleError(reason);
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  useEffect(() => {
    let active = true;
    api.dashboard()
      .then((result) => {
        if (active) setDigest(result);
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
  }, [handleError]);

  return (
    <div className="dashboard-grid">
      <section className="attention-section" aria-labelledby="attention-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Обзор руководителя</p>
            <h1 id="attention-heading">Что требует внимания</h1>
          </div>
          {digest ? <OriginBadge origin={digest.data_origin} /> : null}
        </div>
        {loading ? <LoadingState label="Загружаем приоритеты…" /> : null}
        {!loading && error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
        {!loading && !error && digest?.attention_items.length === 0 ? <EmptyState /> : null}
        {!loading && !error && digest ? (
          <div className="card-grid">
            {digest.attention_items.map((item) => <AttentionCard item={item} key={item.item_id} />)}
          </div>
        ) : null}
      </section>
      {digest && !loading && !error ? <IntegrationList integrations={digest.integrations} /> : null}
    </div>
  );
}
