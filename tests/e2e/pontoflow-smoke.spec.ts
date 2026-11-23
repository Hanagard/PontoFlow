import { test, expect } from "@playwright/test";
test("login page does not ship hardcoded demo credentials", async ({ page }) => {
 await page.goto("/");
 await expect(page.getByRole("heading",{name:"Acessar o sistema"})).toBeVisible();
 await expect(page.getByTestId("login-email-input")).toBeVisible();
 await expect(page.getByTestId("login-password-input")).toBeVisible();
 await expect(page.getByTestId("quick-login-admin-btn")).toHaveCount(0);
 expect(await page.locator("body").innerText()).not.toContain("Ponto@2026");
});
