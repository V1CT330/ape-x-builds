#!/usr/bin/env python3
"""Ape X iOS project generator.

Usage: generate_ios_project.py spec.json OUT_DIR

Writes a complete WKWebView iOS app (Swift sources, Info.plist, asset
catalog) plus an XcodeGen project.yml. Signing is NOT configured here —
it is a separate layer applied later by the workflow when credentials exist.
"""
import json
import re
import sys
from pathlib import Path


def hex_rgb(value: str):
    v = (value or "#0F172A").lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", v):
        v = "0F172A"
    return tuple(int(v[i:i + 2], 16) / 255 for i in (0, 2, 4))


def swift_str(s: str) -> str:
    return json.dumps(s or "")


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2])
    ios = spec.get("ios") or {}
    app = spec.get("application") or {}
    web = spec.get("webview") or {}
    look = spec.get("appearance") or {}

    name = ios.get("displayName") or app.get("name") or "Ape X App"
    bundle = ios.get("bundleId") or app.get("applicationId")
    if not bundle or not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*(\.[A-Za-z0-9-]+)+", bundle.replace("_", "-")):
        sys.exit(f"invalid bundle id: {bundle!r}")
    bundle = bundle.replace("_", "-")
    start_url = web.get("startUrl")
    if not start_url or not start_url.startswith(("https://", "http://")):
        sys.exit(f"invalid start url: {start_url!r}")
    min_os = ios.get("minimumOS") or "15.0"
    version = app.get("versionName") or "1.0.0"
    build_no = str(app.get("versionCode") or 1)
    hosts = [h for h in web.get("allowedHosts") or [] if h]
    external = web.get("externalLinks") or "browser"
    fullscreen = bool(look.get("fullscreen"))
    r, g, b = hex_rgb(look.get("themeColor"))
    orient = look.get("orientation") or "portrait"
    orientations = {
        "portrait": ["UIInterfaceOrientationPortrait"],
        "landscape": ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"],
    }.get(orient, ["UIInterfaceOrientationPortrait", "UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"])

    src = out / "App"
    (src / "Assets.xcassets" / "AppIcon.appiconset").mkdir(parents=True, exist_ok=True)
    (src / "Assets.xcassets" / "Contents.json").write_text('{"info":{"author":"apex","version":1}}')
    (src / "Assets.xcassets" / "AppIcon.appiconset" / "Contents.json").write_text(
        '{"images":[{"idiom":"universal","platform":"ios","size":"1024x1024"}],"info":{"author":"apex","version":1}}'
    )

    (src / "AppMain.swift").write_text(f"""import SwiftUI
import WebKit

let kStartURL = URL(string: {swift_str(start_url)})!
let kAllowedHosts: [String] = {json.dumps(hosts)}
let kExternalLinks = {swift_str(external)}
let kTheme = Color(red: {r:.4f}, green: {g:.4f}, blue: {b:.4f})

@main
struct ApeXApp: App {{
    var body: some Scene {{
        WindowGroup {{
            ZStack {{
                kTheme.ignoresSafeArea()
                WebView().ignoresSafeArea({"" if fullscreen else "edges: .bottom"})
            }}
            {".statusBarHidden(true)" if fullscreen else ""}
        }}
    }}
}}

struct WebView: UIViewRepresentable {{
    func makeCoordinator() -> Coordinator {{ Coordinator() }}

    func makeUIView(context: Context) -> WKWebView {{
        let config = WKWebViewConfiguration()
        config.websiteDataStore = .default()
        config.allowsInlineMediaPlayback = true
        let view = WKWebView(frame: .zero, configuration: config)
        view.navigationDelegate = context.coordinator
        view.uiDelegate = context.coordinator
        view.allowsBackForwardNavigationGestures = true
        view.customUserAgent = nil
        view.evaluateJavaScript("navigator.userAgent") {{ ua, _ in
            if let ua = ua as? String {{ view.customUserAgent = ua + " " + {swift_str(web.get("userAgentSuffix") or "ApeX/1.0")} }}
        }}
        let refresh = UIRefreshControl()
        refresh.addTarget(context.coordinator, action: #selector(Coordinator.reload(_:)), for: .valueChanged)
        view.scrollView.refreshControl = refresh
        context.coordinator.webView = view
        view.load(URLRequest(url: kStartURL))
        return view
    }}

    func updateUIView(_ uiView: WKWebView, context: Context) {{}}

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {{
        weak var webView: WKWebView?

        @objc func reload(_ sender: UIRefreshControl) {{
            webView?.reload()
            sender.endRefreshing()
        }}

        private func isInternal(_ url: URL) -> Bool {{
            guard let host = url.host else {{ return true }}
            return kAllowedHosts.isEmpty || kAllowedHosts.contains {{ host == $0 || host.hasSuffix("." + $0) }}
        }}

        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {{
            guard let url = action.request.url else {{ return decisionHandler(.allow) }}
            let scheme = url.scheme?.lowercased() ?? ""
            if !["http", "https", "about", "data", "blob"].contains(scheme) {{
                UIApplication.shared.open(url)
                return decisionHandler(.cancel)
            }}
            if action.targetFrame?.isMainFrame != false, !isInternal(url), kExternalLinks != "inapp" {{
                UIApplication.shared.open(url)
                return decisionHandler(.cancel)
            }}
            decisionHandler(.allow)
        }}

        func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                     for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {{
            if let url = action.request.url {{
                if isInternal(url) || kExternalLinks == "inapp" {{ webView.load(action.request) }}
                else {{ UIApplication.shared.open(url) }}
            }}
            return nil
        }}
    }}
}}
""")

    plist_orient = "".join(f"<string>{o}</string>" for o in orientations)
    (src / "Info.plist").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleDevelopmentRegion</key><string>en</string>
<key>CFBundleDisplayName</key><string>{name.replace('&', '&amp;').replace('<', '&lt;')}</string>
<key>CFBundleExecutable</key><string>$(EXECUTABLE_NAME)</string>
<key>CFBundleIdentifier</key><string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
<key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
<key>CFBundleName</key><string>$(PRODUCT_NAME)</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>{version}</string>
<key>CFBundleVersion</key><string>{build_no}</string>
<key>LSRequiresIPhoneOS</key><true/>
<key>UILaunchScreen</key><dict/>
<key>UIStatusBarHidden</key>{"<true/>" if fullscreen else "<false/>"}
<key>UISupportedInterfaceOrientations</key><array>{plist_orient}</array>
<key>ITSAppUsesNonExemptEncryption</key><false/>
</dict></plist>
""")

    (out / "project.yml").write_text(f"""name: App
options:
  bundleIdPrefix: {bundle.rsplit('.', 1)[0]}
  deploymentTarget:
    iOS: "{min_os}"
targets:
  App:
    type: application
    platform: iOS
    sources: [App]
    settings:
      base:
        PRODUCT_NAME: App
        PRODUCT_BUNDLE_IDENTIFIER: {bundle}
        INFOPLIST_FILE: App/Info.plist
        MARKETING_VERSION: "{version}"
        CURRENT_PROJECT_VERSION: "{build_no}"
        TARGETED_DEVICE_FAMILY: "1,2"
        SWIFT_VERSION: "5.0"
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        CODE_SIGN_STYLE: Manual
        CODE_SIGNING_ALLOWED: "NO"
        CODE_SIGNING_REQUIRED: "NO"
""")
    print(f"generated iOS project for {bundle} -> {out}")


if __name__ == "__main__":
    main()
