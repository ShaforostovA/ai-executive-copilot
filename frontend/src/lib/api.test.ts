import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import type { Digest } from "../types";

const digest: Digest = {
  digest_id: "digest-1",
  generated_at: "2026-11-25T12:05:00Z",
  attention_items: [],
  integrations: [],
  data_origin: "DEMO",
};

afterEach(() => vi.unstubAllGlobals());

describe("API client", () => {
  it("uses server cookies and typed dashboard response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(digest), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.dashboard()).resolves.toEqual(digest);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/dashboard",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("preserves structured backend errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: "unauthorized", message: "Authentication required.", request_id: "request-1" },
    }), { status: 401, headers: { "Content-Type": "application/json" } })));
    const promise = api.me();
    await expect(promise).rejects.toMatchObject({
      status: 401,
      code: "unauthorized",
      requestId: "request-1",
    });
  });
});
