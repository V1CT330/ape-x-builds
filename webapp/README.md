# Ape X App Maker frontend

This standalone frontend lives in `webapp/` so it does not replace or interfere with the repository's Android/iOS generators or existing deployment.

## Deploy as a separate Vercel project

Create a new Vercel project connected to `V1CT330/ape-x-builds` and set **Root Directory** to `webapp`. Use the framework preset **Other** (static HTML plus a Vercel serverless function). Do not point this frontend at the existing `ape-x-builds` production domain/project.

## Enable real Android build requests

The frontend calls `POST /api/build`. Configure a Vercel environment variable named `APEX_GITHUB_TOKEN` on the new frontend project (Preview and Production). Use a fine-grained GitHub token scoped only to `V1CT330/ape-x-builds` with **Actions: read and write** and **Contents: read** permissions. Never place this token in browser code or commit it to GitHub. Redeploy after setting the variable.

The API validates the HTTPS start URL, package ID, and artifact choice, then dispatches `.github/workflows/android-build.yml` on `Filorux-Blockchain`. Builds run on GitHub Actions. This first integration confirms that a build was queued; it does not yet provide in-app artifact polling or authenticated artifact downloads. The workflow's uploaded artifacts expire after seven days. APK/AAB signing follows the repository workflow's configured signing secrets.

## Current functionality

- Website URL validation and iframe preview attempt (some sites block iframe embedding).
- App name and Android package ID validation.
- Theme color, orientation, app icon and splash image uploads (5 MB limit each).
- Back button, external link and full-screen settings.
- Local save/load and build history in the current browser.
- APK/AAB build dispatch via a server-side API endpoint when the GitHub token is configured.
- Clear status when the build service is not connected.

Sign-in is a placeholder, not an authentication system. Configuration history is local to the browser, not synced across devices. Full website security/mobile analysis, build status polling, artifact download UI, and iOS build dispatch still need dedicated backend routes before they can be represented as complete features.
