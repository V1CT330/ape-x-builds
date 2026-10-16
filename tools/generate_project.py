#!/usr/bin/env python3
"""Ape X Android project generator: generate_project.py spec.json OUT_DIR"""
import json, re, sys
from pathlib import Path
from urllib.parse import urlparse

spec = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
app = spec.get("application") or {}
web = spec.get("webview") or {}
look = spec.get("appearance") or {}

pkg = app.get("applicationId") or ""
if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+", pkg):
    sys.exit(f"invalid application id: {pkg!r}")
url = web.get("startUrl") or ""
parsed_url = urlparse(url)
if parsed_url.scheme not in ("https", "http") or not parsed_url.hostname:
    sys.exit(f"invalid start url: {url!r}")
if parsed_url.scheme != "https":
    sys.exit("startUrl must use HTTPS; cleartext HTTP is not supported")
name = str(app.get("name") or "Ape X App")
name = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", name).strip()[:80] or "Ape X App"
name = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
theme = look.get("themeColor") or "#0F172A"
if not re.fullmatch(r"#[0-9a-fA-F]{6}", theme):
    theme = "#0F172A"
def positive_int(value, default, key, maximum):
    try:
        result = int(value if value is not None else default)
    except (TypeError, ValueError):
        sys.exit(f"{key} must be an integer")
    if result < 1 or result > maximum:
        sys.exit(f"{key} must be between 1 and {maximum}")
    return result

min_sdk = positive_int(app.get("minSdk"), 24, "minSdk", 35)
target_sdk = positive_int(app.get("targetSdk"), 35, "targetSdk", 35)
if min_sdk > target_sdk:
    sys.exit("minSdk cannot be greater than targetSdk")
version_code = positive_int(app.get("versionCode"), 1, "versionCode", 2100000000)
version_name = str(app.get("versionName") or "1.0.0")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,49}", version_name):
    sys.exit(f"invalid versionName: {version_name!r}")
orient = {"portrait": "portrait", "landscape": "landscape"}.get(look.get("orientation"), "unspecified")
full = bool(look.get("fullscreen"))
hosts = [str(h).strip().lower() for h in (web.get("allowedHosts") or []) if str(h).strip()]
if not hosts:
    hosts = [parsed_url.hostname.lower()]
for host in hosts:
    if not re.fullmatch(r"[a-z0-9.-]+", host) or host.startswith(".") or host.endswith(".") or ".." in host:
        sys.exit(f"invalid allowed host: {host!r}")
ext = web.get("externalLinks") or "browser"
if ext not in ("browser", "inapp"):
    sys.exit("externalLinks must be 'browser' or 'inapp'")
back = web.get("backButton") or "history"
if back not in ("history", "exit"):
    sys.exit("backButton must be 'history' or 'exit'")
ua = str(web.get("userAgentSuffix") or "ApeX/1.0")
ua = re.sub(r"[\r\n]", "", ua)[:80]

def w(p, s):
    f = out / p
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(s)

w("settings.gradle", """pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "ApeXApp"
include ':app'
""")
w("build.gradle", "plugins { id 'com.android.application' version '8.5.2' apply false }\n")
w("gradle.properties", "android.useAndroidX=true\norg.gradle.jvmargs=-Xmx2g\n")
w("app/build.gradle", f"""plugins {{ id 'com.android.application' }}
android {{
  namespace '{pkg}'
  compileSdk {target_sdk}
  defaultConfig {{
    applicationId '{pkg}'
    minSdk {min_sdk}
    targetSdk {target_sdk}
    versionCode {version_code}
    versionName '{version_name}'
  }}
  signingConfigs {{
    release {{
      storeFile file(System.getenv('APEX_KEYSTORE') ?: 'apex.keystore')
      storePassword System.getenv('APEX_KEYSTORE_PASSWORD') ?: 'apexbuild'
      keyAlias System.getenv('APEX_KEY_ALIAS') ?: 'apex'
      keyPassword System.getenv('APEX_KEY_PASSWORD') ?: 'apexbuild'
    }}
  }}
  buildTypes {{ release {{ minifyEnabled false; signingConfig signingConfigs.release }} }}
  compileOptions {{ sourceCompatibility JavaVersion.VERSION_17; targetCompatibility JavaVersion.VERSION_17 }}
}}
""")
w("app/src/main/AndroidManifest.xml", f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-permission android:name="android.permission.INTERNET"/>
  <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
  <application android:label="@string/app_name" android:icon="@mipmap/ic_launcher" android:usesCleartextTraffic="false"
    android:theme="@android:style/Theme.Material.Light.{'NoActionBar.Fullscreen' if full else 'NoActionBar'}">
    <activity android:name=".MainActivity" android:exported="true" android:screenOrientation="{orient}"
      android:configChanges="orientation|screenSize|keyboardHidden">
      <intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>
    </activity>
  </application>
</manifest>
""")
w("app/src/main/res/values/strings.xml", f"<resources><string name=\"app_name\">{name}</string></resources>\n")
w("app/src/main/res/drawable/ic_fg.xml", f"""<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">
<path android:fillColor="{theme}" android:pathData="M0,0h108v108h-108z"/>
<path android:fillColor="#FFFFFF" android:pathData="M54,30L78,78H66L54,52L42,78H30Z"/></vector>
""")
w("app/src/main/res/mipmap/ic_launcher.xml", f"""<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="48dp" android:height="48dp" android:viewportWidth="108" android:viewportHeight="108"><path android:fillColor="{theme}" android:pathData="M0,0h108v108h-108z"/><path android:fillColor="#FFFFFF" android:pathData="M54,30L78,78H66L54,52L42,78H30Z"/></vector>\n""")
w("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@drawable/ic_fg"/><foreground android:drawable="@drawable/ic_fg"/></adaptive-icon>
""")
pkg_path = pkg.replace(".", "/")
w(f"app/src/main/java/{pkg_path}/MainActivity.java", f"""package {pkg};

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.*;

public class MainActivity extends Activity {{
  private WebView web;
  private static final String[] HOSTS = {"{" + ", ".join(json.dumps(h) for h in hosts) + "}"};

  private boolean internal(Uri u) {{
    String h = u.getHost();
    if (h == null || HOSTS.length == 0) return true;
    for (String a : HOSTS) if (h.equals(a) || h.endsWith("." + a)) return true;
    return false;
  }}

  @Override protected void onCreate(Bundle b) {{
    super.onCreate(b);
    getWindow().setStatusBarColor(Color.parseColor("{theme}"));
    web = new WebView(this);
    WebSettings s = web.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setUserAgentString(s.getUserAgentString() + " " + {json.dumps(ua)});
    CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);
    web.setWebViewClient(new WebViewClient() {{
      @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {{
        Uri u = r.getUrl();
        String sc = u.getScheme() == null ? "" : u.getScheme();
        if (!sc.startsWith("http") || (!internal(u) && !{json.dumps(ext)}.equals("inapp"))) {{
          try {{ startActivity(new Intent(Intent.ACTION_VIEW, u)); }} catch (Exception e) {{}}
          return true;
        }}
        return false;
      }}
    }});
    setContentView(web);
    if (b != null) web.restoreState(b); else web.loadUrl({json.dumps(url)});
  }}

  @Override protected void onSaveInstanceState(Bundle o) {{ super.onSaveInstanceState(o); web.saveState(o); }}

  @Override public void onBackPressed() {{
    if (!{json.dumps(back)}.equals("exit") && web.canGoBack()) web.goBack(); else super.onBackPressed();
  }}
}}
""")
print(f"generated Android project for {pkg} -> {out}")
