# ADR-006: Tailwind CSS from CDN, homepage at `/`, app at `/app`

Date: 2026-10-24
Status: Accepted. Amends ADR-001 Decision 2 and Decision 7.

## Context

ADR-001 Decision 2 chose plain HTML, CSS and JavaScript with no framework. The user asked for a better-looking UI and a homepage. The product is named Dhwani.

## Decision

- Style pages with Tailwind CSS, loaded from `cdn.jsdelivr.net` at version `@tailwindcss/browser@4.1.11`. The version is at least two weeks old. The build compiles classes in the browser, so no build step is needed.
- Use Tailwind component classes defined in a `<style type="text/tailwindcss">` block on each page. The app keeps no separate stylesheet.
- Serve the homepage at `/` (`home.html`). Serve the notes app at `/app` (`app.html`).
- Keep vanilla JavaScript modules for behavior (`app.js`, `recorder.js`). No framework.
- Add a ripple animation to the homepage. It stops under `prefers-reduced-motion: reduce`.
- Use the product name Dhwani on the homepage and app. The Python package stays `voicenotes`.

## Consequences

- Good: Modern look with little code. Dark mode follows the system setting. Homepage and app are separate pages.
- Bad: The pages need internet access for the CDN. Without it, the pages load unstyled. Notes and audio are not sent to the CDN.
- Bad: The CDN request exposes the browser's IP address and page URL to jsDelivr. See ADR-001 Decision 7 for the exception.
- Revisit trigger: The app needs to work offline. Then copy the Tailwind browser build into `voicenotes/static/`.
