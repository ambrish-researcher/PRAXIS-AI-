import { test, expect } from "@playwright/test";

test("landing, data mission, measured experiment, graph selection, evidence and transfer", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Intelligence.*Put to work/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/landing-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Enter the workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Make the next leap." }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/workspace-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Create your first mission" }).click();
  await page.getByRole("button", { name: "Launch mission" }).click();
  await expect(
    page.getByText("COMPLETED", { exact: true }).first(),
  ).toBeVisible({ timeout: 30000 });
  await expect(
    page.locator(".verified-text").filter({
      hasText:
        "SQL aggregates independently checked; held-out detector fixture passed",
    }),
  ).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole("link", { name: /report.md/ })).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: /report.md/ }).click();
  expect((await downloadPromise).suggestedFilename()).toBe("report.md");
  await page
    .getByRole("button", { name: "Experiments", exact: false })
    .first()
    .click();
  await expect(page.getByText("baseline", { exact: true })).toBeVisible();
  await expect(
    page.getByText(
      "Median/MAD resists contamination that masks an extreme value in small samples",
    ),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/experiment.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Intelligence graph", exact: true })
    .click();
  await expect(page.locator(".full-graph canvas")).toBeVisible();
  await page
    .getByRole("button", { name: "Uploaded CSV", exact: false })
    .click();
  await expect(
    page
      .locator(".node-inspector")
      .getByRole("heading", { name: "Uploaded CSV" }),
  ).toBeVisible();
  await page.screenshot({ path: "test-results/graph.png", fullPage: true });
  // Confirm pointer orbit changes rendered pixels, rather than checking only for a canvas.
  const canvas = page.locator(".full-graph canvas");
  const before = await canvas.screenshot();
  const box = await canvas.boundingBox();
  if (!box) throw Error("Missing canvas");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width / 2 + 110,
    box.y + box.height / 2 + 40,
    { steps: 12 },
  );
  await page.mouse.up();
  await page.waitForTimeout(500);
  const after = await canvas.screenshot();
  expect(Buffer.compare(before, after)).not.toBe(0);
  await page.getByRole("button", { name: "Evidence", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Search evidence" })
    .fill("Uploaded CSV");
  await expect(
    page.getByRole("heading", { name: "Uploaded CSV" }).first(),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "New mission", exact: true })
    .last()
    .click();
  await page
    .getByLabel("Dataset (CSV, 5–10,000 rows)")
    .fill("row,value\na,20\nb,21\nc,19\nd,20\ne,22\nf,20\ng,21\nh,19\ni,200");
  await page.getByRole("button", { name: "Launch mission" }).click();
  await expect(
    page.getByText("COMPLETED", { exact: true }).first(),
  ).toBeVisible({ timeout: 30000 });
  await page
    .getByRole("button", { name: "Skill library", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: /Transfer evaluation/ }).first(),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("software gate, execution, failure diagnosis and downloadable source", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Enter the workspace" }).click();
  await page.getByRole("button", { name: "Create your first mission" }).click();
  await page.getByLabel("Capability").selectOption("software");
  await page.getByRole("button", { name: "Launch mission" }).click();
  await expect(
    page.getByRole("heading", { name: "Your approval is required" }),
  ).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Approve sandbox execution" }).click();
  await expect(
    page
      .locator(".verified-text")
      .filter({ hasText: "8/8 contract cases; 2 HTTP checks passed" }),
  ).toBeVisible({ timeout: 45000 });
  await expect(
    page.getByRole("link", { name: /calculator-source.zip/ }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Execution theater", exact: true })
    .click();
  await expect(
    page.getByText(/Summation parser does not implement/),
  ).toBeVisible();
});

test("mobile and reduced motion have no horizontal overflow; research executes", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: "Enter the workspace" }).click();
  await page.screenshot({
    path: "test-results/workspace-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Create your first mission" }).click();
  await page.getByLabel("Capability").selectOption("research");
  await page.getByRole("button", { name: "Launch mission" }).click();
  await expect(
    page
      .locator(".verified-text")
      .filter({ hasText: "Selected quotations match supplied text exactly" }),
  ).toBeVisible({ timeout: 30000 });
  await expect(
    page.getByText(/identified 1 potential numeric contradictions/),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("button", { name: "Integrations", exact: true }).click();
  await page
    .getByRole("button", { name: "Run real health check" })
    .first()
    .click();
  await expect(
    page.getByText("Missing server-side configuration"),
  ).toBeVisible();
});

test("cross-domain demo executes a validated DAG and produces a real dossier", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Enter the workspace" }).click();
  await page.getByRole("button", { name: "Create your first mission" }).click();
  await page.getByRole("button", { name: "Cross-domain dossier" }).click();
  await page.getByLabel("Intelligence provider").selectOption("offline");
  await page.getByRole("button", { name: "Launch mission" }).click();
  await expect(
    page.getByText(
      "All selected tools completed their independent checks; all artifact hashes verified.",
    ),
  ).toBeVisible({ timeout: 30000 });
  await expect(
    page.locator(".intelligence-brief").getByText("3 / 3 tools verified"),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /synthesis--dossier.md/ }),
  ).toBeVisible();
  await expect(
    page.getByText("OFFLINE PLANNER", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/cross-domain-mission.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Intelligence graph", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "synthesis adapter" }),
  ).toBeVisible();
});

test("record app demo requires approval and verifies actual HTTP CRUD and persistence", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Enter the workspace" }).click();
  await page.getByRole("button", { name: "Create your first mission" }).click();
  await page
    .getByRole("button", { name: "Build a task board", exact: true })
    .click();
  await page.getByLabel("Intelligence provider").selectOption("offline");
  await page.getByRole("button", { name: "Launch mission" }).click();
  await expect(
    page.getByRole("heading", { name: "Your approval is required" }),
  ).toBeVisible({ timeout: 30000 });
  await expect(
    page.locator(".tool-chain").getByText("workspace", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Approve sandbox execution" }).click();
  await expect(
    page.locator(".verified-text").filter({
      hasText:
        "7/7 CRUD contract cases; independent restart persistence and HTML checks passed",
    }),
  ).toBeVisible({ timeout: 45000 });
  await expect(
    page.getByRole("link", { name: /workspace-source.zip/ }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Experiments", exact: false })
    .first()
    .click();
  await expect(
    page.getByText(
      "Strict record validation preserves CRUD and rejects invalid or unknown input",
    ),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/record-app-experiment.png",
    fullPage: true,
  });
});
