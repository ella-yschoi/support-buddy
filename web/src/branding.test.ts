import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(__dirname, "..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("favicon and boot screen", () => {
  it("links an SVG favicon from index.html", () => {
    expect(read("index.html")).toMatch(/<link[^>]+rel="icon"[^>]+href="\/favicon\.svg"/);
  });

  it("ships the favicon as a self-contained SVG with the two-ring mark", () => {
    const svg = read("public/favicon.svg");
    expect(svg).toContain("<svg");
    expect(svg.match(/<circle/g)).toHaveLength(4);
    expect(svg).not.toMatch(/href=|<image|<script/i);
  });

  it("adapts the favicon to light and dark browser tabs", () => {
    expect(read("public/favicon.svg")).toContain("prefers-color-scheme");
  });

  it("shows the logo in the page before the app has loaded", () => {
    const html = read("index.html");
    const rootDiv = html.slice(html.indexOf('<div id="root">'), html.indexOf("</div>", html.indexOf('<div id="root">')));
    expect(rootDiv).toContain("<svg");
  });

  it("no longer draws the placeholder triangle", () => {
    expect(read("src/styles.css")).not.toContain("border-bottom: 12px solid");
  });
});
