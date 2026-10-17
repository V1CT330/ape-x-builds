const OWNER = "V1CT330";
const REPO = "ape-x-builds";
const WORKFLOW = "android-build.yml";
const BRANCH = "Filorux-Blockchain";

function send(res, status, body) {
  res.status(status).setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  return res.end(JSON.stringify(body));
}
function validPackage(value) {
  return typeof value === "string" &&
    /^(?![0-9])[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$/.test(value);
}
module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return send(res, 405, { error: "Use POST to start a build." });
  }
  const token = process.env.APEX_GITHUB_TOKEN;
  if (!token) {
    return send(res, 503, {
      error: "Build service is not connected yet. Configure APEX_GITHUB_TOKEN on the Ape X Vercel project to enable real Android builds."
    });
  }
  const body = req.body || {};
  const website = String(body.website || "");
  const appName = String(body.appName || "My Android app").trim().slice(0, 50);
  const packageId = String(body.packageId || "");
  const artifact = String(body.outputFormat || "apk").toLowerCase();
  let parsed;
  try { parsed = new URL(website); } catch { return send(res, 400, { error: "Enter a valid website URL." }); }
  if (parsed.protocol !== "https:" || !parsed.hostname || ["localhost", "127.0.0.1", "::1"].includes(parsed.hostname)) {
    return send(res, 400, { error: "The app website must be a public HTTPS URL." });
  }
  if (!validPackage(packageId)) return send(res, 400, { error: "Package ID is invalid. Use a value like com.example.myapp." });
  if (!["apk", "aab"].includes(artifact)) return send(res, 400, { error: "The connected build runner supports APK or AAB output. IPA requires the iOS workflow." });
  const color = /^#[0-9a-f]{6}$/i.test(body.themeColor || "") ? body.themeColor : "#285788";
  const orientationMap = { Portrait: "portrait", Landscape: "landscape", Unspecified: "unspecified" };
  const backMap = { web: "history", exit: "exit", browser: "history" };
  const buildId = "apex-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8);
  const spec = {
    application: { name: appName || "My Android app", applicationId: packageId, versionName: "1.0.0", versionCode: 1, minSdk: 24, targetSdk: 35 },
    webview: { startUrl: parsed.href, allowedHosts: [parsed.hostname], externalLinks: body.externalLinks === "webview" ? "internal" : "browser", backButton: backMap[body.backButton] || "history", userAgentSuffix: "ApeX/1.0" },
    appearance: { themeColor: color, orientation: orientationMap[body.orientation] || "portrait", fullscreen: Boolean(body.fullscreen) },
    artifact
  };
  try {
    const response = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ ref: BRANCH, inputs: { spec: JSON.stringify(spec), build_id: buildId } })
    });
    if (response.status !== 204) {
      const details = await response.text();
      console.error("GitHub workflow dispatch failed", response.status, details.slice(0, 500));
      return send(res, response.status === 401 || response.status === 403 ? 502 : 502, {
        error: "GitHub rejected the build request. Check that APEX_GITHUB_TOKEN has Actions write access to the Ape X build repository."
      });
    }
    return send(res, 202, { accepted: true, buildId, artifact, message: "Build queued in GitHub Actions. View progress in the Ape X Android Build workflow." });
  } catch (error) {
    console.error("Ape X build dispatch error", error);
    return send(res, 502, { error: "Could not reach the build service. Try again shortly." });
  }
};