import { describe, expect, it } from "vitest";
import { posthogOptions } from "./posthog";

// Briefings shown after Unlock hold customer messages and draft replies.
// Analytics may count clicks, but must never carry that text to PostHog.
describe("posthog options", () => {
  it("keeps element text and attributes out of autocapture", () => {
    expect(posthogOptions.mask_all_text).toBe(true);
    expect(posthogOptions.mask_all_element_attributes).toBe(true);
  });

  it("masks every input and every text node in session recordings", () => {
    expect(posthogOptions.session_recording?.maskAllInputs).toBe(true);
    expect(posthogOptions.session_recording?.maskTextSelector).toBe("*");
  });

  it("still reports unhandled errors", () => {
    expect(posthogOptions.capture_exceptions).toMatchObject({
      capture_unhandled_errors: true,
      capture_unhandled_rejections: true,
    });
  });
});
