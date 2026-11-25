import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthContext } from "../auth/AuthContext";
import { ApiError, api } from "../lib/api";
import type { Digest } from "../types";
import { DashboardPage } from "./DashboardPage";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, api: { ...actual.api, dashboard: vi.fn() } };
});

const dashboardMock = vi.mocked(api.dashboard);
const authValue = {
  user: { user_id: "owner-1", organization_id: "tenant-1", organization_slug: "demo", email: "demo@example.test" },
  loading: false,
  error: null,
  login: vi.fn(),
  logout: vi.fn(),
  expireSession: vi.fn(),
};
const digest: Digest = {
  digest_id: "digest-1",
  generated_at: "2026-11-25T12:05:00Z",
  attention_items: [{
    item_id: "item-1",
    tenant_id: "tenant-1",
    owner_id: "owner-1",
    source_id: "source-1",
    score: 82,
    summary: "Synthetic dashboard item",
    importance_reason: "Synthetic reason",
    next_step: "Synthetic action",
    source_timestamp: "2026-11-25T12:00:00Z",
    data_origin: "DEMO",
  }],
  integrations: [],
  data_origin: "DEMO",
};

function renderDashboard() {
  return render(
    <AuthContext.Provider value={authValue}>
      <DashboardPage />
    </AuthContext.Provider>,
    { wrapper: MemoryRouter },
  );
}

afterEach(() => vi.clearAllMocks());

describe("DashboardPage", () => {
  it("renders attention items and DEMO origin", async () => {
    dashboardMock.mockResolvedValue(digest);
    renderDashboard();
    expect(await screen.findByText("Synthetic dashboard item")).toBeInTheDocument();
    expect(screen.getAllByText("DEMO").length).toBeGreaterThan(0);
  });

  it("renders empty state", async () => {
    dashboardMock.mockResolvedValue({ ...digest, attention_items: [] });
    renderDashboard();
    expect(await screen.findByText("Срочных событий нет")).toBeInTheDocument();
  });

  it("renders error state and retries", async () => {
    dashboardMock
      .mockRejectedValueOnce(new ApiError("Temporary failure", 500, "internal_error"))
      .mockResolvedValueOnce(digest);
    renderDashboard();
    expect(await screen.findByText("Temporary failure")).toBeInTheDocument();
    screen.getByRole("button", { name: "Повторить" }).click();
    expect(await screen.findByText("Synthetic dashboard item")).toBeInTheDocument();
    expect(dashboardMock).toHaveBeenCalledTimes(2);
  });
});
