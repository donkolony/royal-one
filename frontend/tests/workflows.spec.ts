import { test, expect } from "@playwright/test";

test("claim registration, adviser updates and persisted client tracking", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Register a claim", exact: true })
    .click();
  await page.getByLabel("Vehicle", { exact: true }).fill("2024 Test vehicle");
  await page.getByLabel("Incident date").fill("2026-09-18");
  await page.getByLabel("Incident time").fill("10:30");
  await page.getByLabel("Location / cross streets").fill("Rosebank");
  await page
    .getByLabel("What happened?")
    .fill("A test incident for workflow verification.");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Driver's full name").fill("Thando Mokoena");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByRole("button", { name: "Submit claim", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("2024 Test vehicle");
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByLabel("View as").selectOption("adviser");
  await page.getByRole("link", { name: /^Claims/ }).click();
  await page
    .getByRole("button", { name: "2024 Test vehicle", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Status", exact: true })
    .selectOption("1");
  await page.getByLabel("Client update").fill("Assessment booked for Monday.");
  await page.getByRole("button", { name: "Save update", exact: true }).click();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByLabel("View as").selectOption("client");
  await page.reload();
  await page.getByRole("link", { name: /^Claims/ }).click();
  await page
    .getByRole("button", { name: "2024 Test vehicle", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Assessment booked for Monday.",
  );
  await expect(
    page.getByRole("button", { name: "Save update", exact: true }),
  ).toHaveCount(0);
});

test("requests, reminders, goals and assistant references", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New request", exact: true }).click();
  await page.getByLabel("Request type").selectOption("Change of address");
  await page.getByLabel("New address").fill("12 Test Street, Johannesburg");
  await page
    .getByRole("button", { name: "Submit request", exact: true })
    .click();
  await expect(
    page.getByText("Address: 12 Test Street, Johannesburg"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByLabel("View as").selectOption("adviser");
  await page.getByRole("link", { name: "Goals", exact: true }).click();
  await page.getByRole("button", { name: "Add goal", exact: true }).click();
  await page.getByLabel("Goal name").fill("Education fund");
  await page.getByLabel("Target amount (R)").fill("100000");
  await page.getByLabel("Target date").fill("2028-01-01");
  await page.getByRole("button", { name: "Save goal", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Education fund" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Reminders", exact: true }).click();
  await page
    .getByRole("button", {
      name: "Complete Annual financial review",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("button", { name: "Restore", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Document assistant", exact: true })
    .click();
  await page
    .getByRole("button", { name: "How is a hire car arranged?", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Motor claims demo guide · p. 2",
      exact: true,
    })
    .click();
  await expect(page.locator(".source-excerpt")).toContainText(
    "weekly repair updates",
  );
  await page.getByRole("link", { name: /^Inbox/ }).click();
  await page
    .getByRole("button", { name: "Prepare demo draft", exact: true })
    .click();
  await page.getByRole("button", { name: "Save draft", exact: true }).click();
  await page.reload();
  await expect(page.getByLabel("Reply draft")).toHaveValue(/Hi Sarah/);
});

test("desktop and mobile layouts render without overflow", async ({ page }) => {
  for (const viewport of [
    { width: 1440, height: 1100 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Good morning, Thando." }),
    ).toBeVisible();
    await expect(page.locator(".review-banner img")).toBeVisible();
    await page.screenshot({
      path: `test-results/overview-${viewport.width}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    if (viewport.width < 760) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await page.getByRole("link", { name: /^Claims/ }).click();
      await expect(
        page.getByRole("heading", { name: "Your claims" }),
      ).toBeVisible();
    }
  }
});
