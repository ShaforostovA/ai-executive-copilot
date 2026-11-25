import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AttentionCard } from "./AttentionCard";
import type { AttentionItem } from "../types";

const item: AttentionItem = {
  item_id: "item-1",
  tenant_id: "tenant-1",
  owner_id: "owner-1",
  source_id: "source-1",
  score: 91,
  summary: "Synthetic priority",
  importance_reason: "Synthetic deadline",
  next_step: "Review the proposal",
  source_timestamp: "2026-11-25T12:00:00Z",
  data_origin: "DEMO",
};

describe("AttentionCard", () => {
  it("shows priority, action item, origin and source link", () => {
    render(<AttentionCard item={item} />, { wrapper: MemoryRouter });
    expect(screen.getByText("Synthetic priority")).toBeInTheDocument();
    expect(screen.getByText("Review the proposal")).toBeInTheDocument();
    expect(screen.getByText("DEMO")).toBeInTheDocument();
    expect(screen.getByLabelText("Оценка важности 91 из 100")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Открыть источник" })).toHaveAttribute("href", "/sources/source-1");
  });
});
