import { Link } from "react-router-dom";
import type { AttentionItem } from "../types";
import { OriginBadge } from "./OriginBadge";

const timestamp = new Intl.DateTimeFormat("ru-RU", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function AttentionCard({ item }: { item: AttentionItem }) {
  return (
    <article className="attention-card">
      <div className="card-meta">
        <span className="score" aria-label={`Оценка важности ${item.score} из 100`}>
          {item.score}
          <small>/100</small>
        </span>
        <OriginBadge origin={item.data_origin} />
      </div>
      <h3>{item.summary}</h3>
      <p>{item.importance_reason}</p>
      <div className="action-item">
        <span>Предложенное действие</span>
        <strong>{item.next_step}</strong>
      </div>
      <div className="card-footer">
        <time dateTime={item.source_timestamp}>
          {timestamp.format(new Date(item.source_timestamp))}
        </time>
        <Link to={`/sources/${item.source_id}`}>Открыть источник</Link>
      </div>
    </article>
  );
}
