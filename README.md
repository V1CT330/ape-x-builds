# Ape X Build Runner

Ape X converts a website into Android and iOS WebView apps through GitHub Actions. Android builds produce APK/AAB artifacts; iOS builds produce an IPA plus the generated Xcode project.

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
    "iconUrl": "https://example.com/favicon.png",
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

The build attempts to use the site's favicon as the launcher icon. You can optionally set `application.iconUrl` to a public HTTPS image hosted on the start URL's host or another configured allowed host. The icon downloader rejects non-HTTPS, disallowed, private, and internal hosts; if no usable icon is available, the generic fallback icon is retained.


## iOS builds

Open **Actions → Ape X iOS Build → Run workflow** and provide the same JSON `spec` object and a unique `build_id` used by the Android workflow. The iOS generator uses `ios.bundleId` when provided, otherwise `application.applicationId`. The website `webview.startUrl` must use HTTPS.

### Optional App Store Connect signing

To produce a signed IPA, configure all four repository secrets:

- `APPLE_CERT_P12`: base64-encoded Apple Distribution .p12 certificate.
- `APPLE_CERT_PASSWORD`: password for the .p12 file.
- `APPLE_PROVISIONING_PROFILE_B64`: base64-encoded App Store provisioning profile for the exact bundle ID.
- `APPLE_TEAM_ID`: Apple Developer Team ID.

Set all four secrets or leave all four empty. Partial configuration fails intentionally. The workflow checks that the profile's application identifier matches the configured team and bundle ID, imports signing assets into a temporary keychain, exports and validates the IPA, and cleans up temporary signing assets. The signed export is configured for App Store Connect distribution; the certificate and provisioning profile must be valid for that distribution method.

If all signing secrets are absent, the workflow builds an **unsigned development IPA** and includes the Xcode project ZIP. An unsigned IPA is not installable like a signed app and must not be presented as a release-ready customer build. All uploaded build artifacts expire after seven days.

CI runs iOS generator regression tests on every push and pull request. The macOS iOS build itself is triggered manually from GitHub Actions.
