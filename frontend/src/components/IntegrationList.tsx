import type { IntegrationStatus } from "../types";
import { OriginBadge } from "./OriginBadge";

const statusLabels = {
  NOT_CONFIGURED: "Не подключено",
  CONNECTED: "Подключено",
  DEGRADED: "Есть задержки",
  ERROR: "Ошибка",
};

export function IntegrationList({ integrations }: { integrations: IntegrationStatus[] }) {
  return (
    <section className="integrations-panel" aria-labelledby="integrations-heading">
      <h2 id="integrations-heading">Интеграции</h2>
      {integrations.length === 0 ? (
        <p className="muted">Источники еще не подключены.</p>
      ) : (
        <ul className="integration-list">
          {integrations.map((integration) => (
            <li key={integration.integration_id}>
              <div>
                <strong>{integration.provider}</strong>
                <p>{integration.detail}</p>
              </div>
              <div className="integration-status">
                <OriginBadge origin={integration.data_origin} />
                <span>{statusLabels[integration.status]}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
