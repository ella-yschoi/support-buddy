import posthog, { type PostHogConfig } from "posthog-js";

const posthogKey = import.meta.env.VITE_POSTHOG_KEY;
const posthogHost = import.meta.env.VITE_POSTHOG_HOST;
export const isPostHogConfigured = Boolean(posthogKey && posthogHost);

// Briefings shown after Unlock hold customer messages and draft replies, so
// analytics may count clicks but must never carry page text or input values.
export const posthogOptions: Partial<PostHogConfig> = {
  defaults: "2026-08-30",
  mask_all_text: true,
  mask_all_element_attributes: true,
  session_recording: {
    maskAllInputs: true,
    maskTextSelector: "*",
  },
  capture_exceptions: {
    capture_unhandled_errors: true,
    capture_unhandled_rejections: true,
    capture_console_errors: false,
  },
  logs: {
    serviceName: "support-buddy-web",
    environment: import.meta.env.MODE,
  },
};

type PostHogLogAttributes = Record<string, string | number | boolean>;

export const posthogLogger = {
  info(message: string, attributes: PostHogLogAttributes) {
    if (isPostHogConfigured) posthog.logger.info(message, attributes);
  },
};

if (!posthogKey || !posthogHost) {
  if (import.meta.env.DEV) {
    const missingVariable = !posthogKey ? "VITE_POSTHOG_KEY" : "VITE_POSTHOG_HOST";

    console.error(
      new Error(
        `${missingVariable} variable required by PostHog is missing or un-configured, this causes events to be silently missed. This error stops appearing once ${missingVariable} is configured`,
      ),
    );
  }
} else {
  posthog.init(posthogKey, { api_host: posthogHost, ...posthogOptions });
}

export default posthog;
