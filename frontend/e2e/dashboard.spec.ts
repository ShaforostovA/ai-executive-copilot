import { expect, test } from "@playwright/test";

const email = process.env.E2E_DEMO_EMAIL ?? "demo@example.test";
const password = process.env.E2E_DEMO_PASSWORD ?? "local_demo_password_only";

test("cookie login, dashboard, source and logout", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("heading", { name: "Что требует внимания" })).toBeVisible();
  await expect(page.getByText("DEMO", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Предложенное действие").first()).toBeVisible();
  await page.getByRole("link", { name: "Открыть источник" }).click();
  await expect(page.getByRole("heading", { name: "DEMO: Budget approval required" })).toBeVisible();
  await expect(page.getByText(/Synthetic message for local development/)).toBeVisible();
  await page.getByRole("button", { name: "Выйти" }).click();
  await expect(page.getByRole("heading", { name: "Вход в рабочее пространство" })).toBeVisible();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Вход в рабочее пространство" })).toBeVisible();
});

test("invalid credentials show accessible error", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill("incorrect-synthetic-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByRole("alert")).toContainText("Invalid credentials.");
});
