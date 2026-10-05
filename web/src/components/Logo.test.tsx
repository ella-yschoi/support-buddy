import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../App";
import { Logo } from "./Logo";

describe("Logo", () => {
  it("is decorative: hidden from assistive tech, since the wordmark names the product", () => {
    const { container } = render(<Logo />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
    expect(svg).toHaveAttribute("focusable", "false");
  });

  it("draws two rings and a filled overlap (plus the circle that clips the overlap)", () => {
    const { container } = render(<Logo />);
    expect(container.querySelectorAll("circle")).toHaveLength(4);
    expect(container.querySelectorAll("clipPath")).toHaveLength(1);
  });

  it("gives every instance its own clip-path id so two logos never collide", () => {
    const { container } = render(
      <>
        <Logo />
        <Logo />
      </>,
    );
    const ids = Array.from(container.querySelectorAll("clipPath")).map((c) => c.id);
    expect(new Set(ids).size).toBe(2);
    ids.forEach((id) => expect(id).toMatch(/^[A-Za-z0-9_-]+$/));
  });
});

describe("branding in the app", () => {
  it("shows the logo next to the wordmark in the top bar", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    const { container } = render(<App />);
    expect(container.querySelector(".wordmark svg")).not.toBeNull();
    vi.unstubAllGlobals();
  });
});
