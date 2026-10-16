# Ape X build runner

Ape X build runner compiles Android APK/AAB files from a website build specification.

## Android build workflow

Workflow: `.github/workflows/android-build.yml`

It is started with GitHub Actions `workflow_dispatch` inputs:

- `spec`: JSON build specification.
- `build_id`: unique build identifier used to name the uploaded artifact.

Minimal specification:

```json
{
  "application": {
    "name": "Example App",
    "applicationId": "mw.example.app",
    "minSdk": 24,
    "targetSdk": 35,
    "versionCode": 1,
    "versionName": "1.0.0"
  },
  "webview": {
    "startUrl": "https://example.com",
    "allowedHosts": ["example.com"],
    "externalLinks": "browser",
    "backButton": "history"
  },
  "appearance": {
    "themeColor": "#0F172A",
    "orientation": "portrait",
    "fullscreen": false
  },
  "artifact": "apk"
}
```

Use `artifact: "apk"` for an installable Android package or `artifact: "aab"` for a Play Store bundle. Unsupported values fail the workflow.

### Android signing secrets

For stable production updates, configure all four repository Actions secrets:

- `APEX_KEYSTORE_B64`: base64-encoded Java keystore.
- `APEX_KEYSTORE_PASSWORD`: keystore password.
- `APEX_KEY_ALIAS`: alias stored in the keystore.
- `APEX_KEY_PASSWORD`: private key password.

Keep the keystore and passwords private; never commit them to the repository. The workflow permits a temporary test key when no production keystore is configured. Such builds are for testing only: future builds will not share the same signing identity and they are not suitable for production updates. If a production keystore is configured but credentials are incomplete, the workflow fails early.

The workflow uploads an artifact named `apex-<build_id>`. The website/backend must retain the workflow run ID, verify its status and artifact association, and authorize downloads only for the user who owns the build. GitHub Actions artifacts expire according to repository retention settings; copy completed artifacts into controlled storage if customers need longer-term access.

## Security and product integration

This repository only generates and builds mobile packages. It does not implement the customer-facing website, payment verification, database authorization, or customer download endpoints. Those must be implemented and tested in the Ape X frontend/backend repository. A workflow run or browser redirect must never be treated as proof of payment.
