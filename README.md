# Ape X Android Build Runner

Ape X converts a website into an Android application and builds an APK or Android App Bundle (AAB) through GitHub Actions.

## Current scope

- Android only.
- WebView-based app with no artificial browser title bar.
- HTTPS website entry URL.
- Website host allowlist; the start URL host is used when no allowlist is supplied.
- Configurable application ID, app name, version, theme color, orientation, fullscreen mode, external-link handling, and back-button behavior.
- APK or AAB output.
- Production signing via GitHub Actions repository secrets.
- Generator smoke tests and a generated-app compile check run on pushes and pull requests.

## Trigger a build

Open **Actions → Ape X Android Build → Run workflow** and provide:

1. `spec`: a JSON object matching the structure below.
2. `build_id`: a unique identifier containing only letters, digits, `.`, `_`, or `-` (maximum 80 characters).

Example build spec:

```json
{
  "application": {
    "name": "My Website",
    "applicationId": "mw.example.mywebsite",
    "versionName": "1.0.0",
    "versionCode": 1,
    "minSdk": 24,
    "targetSdk": 35
  },
  "webview": {
    "startUrl": "https://example.com",
    "allowedHosts": ["example.com"],
    "externalLinks": "browser",
    "backButton": "history",
    "userAgentSuffix": "ApeX/1.0"
  },
  "appearance": {
    "themeColor": "#0F172A",
    "orientation": "portrait",
    "fullscreen": false
  },
  "artifact": "apk"
}
```

Use `"artifact": "aab"` when an Android App Bundle is required. The start URL must use HTTPS. Set `allowedHosts` to the site and any trusted subdomains needed for login or navigation. Avoid allowing unrelated hosts.

## Production signing

Configure these GitHub Actions repository secrets:

- `APEX_KEYSTORE_B64`: base64-encoded production keystore.
- `APEX_KEYSTORE_PASSWORD`: keystore password.
- `APEX_KEY_ALIAS`: signing key alias.
- `APEX_KEY_PASSWORD`: signing key password.

The workflow validates the configured keystore and verifies the signature on the output artifact. If production secrets are absent, it creates a temporary development key and clearly marks the artifact as development-only. **A temporary-key build cannot update an existing production app and must not be released as a customer build.**

## Output and limitations

Successful runs upload the APK or AAB as a GitHub Actions artifact for seven days. This runner alone does not implement customer accounts, payment collection/verification, per-customer build ownership, website-side status polling, or authenticated customer download links. Those features must be implemented in the Ape X web application/backend, with payment verified server-side before a customer's build becomes downloadable.

The website's logo/icon still needs a dedicated asset-input or favicon-fetching feature; the current generator creates a generic fallback icon.
