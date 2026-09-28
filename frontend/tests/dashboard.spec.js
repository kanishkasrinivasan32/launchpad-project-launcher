import { test, expect } from "@playwright/test";
import path from "node:path";
import net from "node:net";

const root = path.resolve("..");
async function freePort() {
  const server = net.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

test("create, launch, inspect logs, restart, stop, edit, persist and delete", async ({
  page,
  request,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const port = await freePort();
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Workspace overview." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add project", exact: true }).click();
  await page
    .getByLabel("Project name", { exact: true })
    .fill("Browser test project");
  await page
    .getByLabel("Description")
    .fill("An actual local HTTP server used for integration testing.");
  await page.getByLabel("Project folder").fill(root);
  await page
    .getByLabel("Startup command")
    .fill(
      `"${root}/.venv/Scripts/python.exe" -u -m http.server ${port} --bind 127.0.0.1`,
    );
  await page.getByLabel("Localhost URL").fill(`http://127.0.0.1:${port}`);
  await page.getByLabel("Project type").selectOption("Python");
  await page.getByLabel("Technologies").fill("Python, HTTP");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add project", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const card = page
    .locator(".project-card")
    .filter({ hasText: "Browser test project" });
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Launch project" }).click();
  await expect(
    page
      .locator(".running-row")
      .filter({ hasText: "Browser test project" })
      .locator(".status"),
  ).toHaveText("Running", { timeout: 15000 });
  await expect(page.locator(".running-row .metric").last()).not.toHaveText(
    "0 MB",
  );
  await card.getByRole("button", { name: "Details", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Browser test project" }),
  ).toBeVisible();
  await expect(page.getByLabel("Process logs")).toContainText("Serving HTTP", {
    timeout: 10000,
  });
  await page.screenshot({
    path: "../test-results/project-details.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Restart", exact: true }).click();
  await expect(page.locator(".detail-heading .status")).toHaveText("Running", {
    timeout: 15000,
  });
  await expect(
    page.getByRole("button", { name: "Stop project", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Stop project", exact: true }).click();
  await expect(page.locator(".detail-heading .status")).toHaveText("Stopped", {
    timeout: 15000,
  });
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page
    .getByLabel("Project name", { exact: true })
    .fill("Renamed browser project");
  await page.getByRole("button", { name: "Save changes", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Renamed browser project" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page
      .locator(".project-card")
      .filter({ hasText: "Renamed browser project" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Session history", exact: true })
    .click();
  await expect(
    page.locator("tbody tr").filter({ hasText: "Renamed browser project" }),
  ).toHaveCount(2);
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page.screenshot({
    path: "../test-results/dashboard-populated.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("heading", { name: "Workspace overview." }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    )
    .toBe(true);
  await page.screenshot({
    path: "../test-results/dashboard-mobile.png",
    fullPage: true,
  });
  await page
    .locator(".project-card")
    .filter({ hasText: "Renamed browser project" })
    .getByRole("button", { name: "Details", exact: true })
    .click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Give your projects a home." }),
  ).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "../test-results/dashboard-empty.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("invalid folder is readable and the modal remains usable", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Add project", exact: true }).click();
  await page.getByLabel("Project name", { exact: true }).fill("Invalid path");
  await page
    .getByLabel("Project folder")
    .fill("D:\\folder-that-does-not-exist-launchpad-test");
  await page.getByLabel("Startup command").fill("npm run dev");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Add project", exact: true })
    .click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "Project folder does not exist",
  );
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("occupied port automatically changes the running URL and Open links", async ({
  page,
  request,
}) => {
  const blocker = net.createServer((socket) =>
    socket.end("HTTP/1.1 200 OK\r\nContent-Length: 8\r\n\r\nunrelated"),
  );
  await new Promise((resolve) => blocker.listen(0, "127.0.0.1", resolve));
  const port = blocker.address().port;
  const preferred = `http://127.0.0.1:${port}`;
  const created = await request.post("/api/projects", {
    data: {
      name: "Automatic port test",
      folder: root,
      type: "Python",
      url: preferred,
      startup_command: `"${root}/.venv/Scripts/python.exe" -u -m http.server ${port} --bind 127.0.0.1`,
    },
  });
  expect(created.status()).toBe(201);
  const project = await created.json();
  let session;
  try {
    await page.goto("/");
    const card = page
      .locator(".project-card")
      .filter({ hasText: "Automatic port test" });
    const launchResponse = page.waitForResponse(
      (r) =>
        r.url().endsWith(`/launcher/launch/${project.id}`) &&
        r.request().method() === "POST",
    );
    await card.getByRole("button", { name: "Launch project" }).click();
    session = await (await launchResponse).json();
    expect(session.actual_url).not.toBe(preferred);
    await expect(
      page
        .locator(".running-row")
        .filter({ hasText: project.name })
        .locator(".status"),
    ).toHaveText("Running", { timeout: 15000 });
    await expect(
      page.getByRole("link", { name: `Open ${project.name}`, exact: true }),
    ).toHaveAttribute("href", session.actual_url);
    await expect(card.locator(".project-endpoint")).toHaveText(
      session.actual_url,
    );
    await card.getByRole("button", { name: "Details", exact: true }).click();
    await expect(page.getByRole("link", { name: "Open app" })).toHaveAttribute(
      "href",
      session.actual_url,
    );
    await expect(page.locator(".config-list")).toContainText(
      session.actual_url,
    );
    await page.screenshot({
      path: "../test-results/automatic-port.png",
      fullPage: true,
    });
  } finally {
    if (session?.id) await request.post(`/api/launcher/stop/${session.id}`);
    await request.delete(`/api/projects/${project.id}`);
    await new Promise((resolve) => blocker.close(resolve));
  }
});
