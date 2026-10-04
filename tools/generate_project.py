#!/usr/bin/env python3
"""Ape X Android project generator: generate_project.py spec.json OUT_DIR"""
import json, re, sys
from pathlib import Path

spec = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
app = spec.get("application") or {}
web = spec.get("webview") or {}
look = spec.get("appearance") or {}

pkg = app.get("applicationId") or ""
if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+", pkg):
    sys.exit(f"invalid application id: {pkg!r}")
url = web.get("startUrl") or ""
if not url.startswith(("https://", "http://")):
    sys.exit(f"invalid start url: {url!r}")
name = (app.get("name") or "Ape X App").replace("&", "&amp;").replace("<", "&lt;").replace("'", "\\'")
theme = look.get("themeColor") or "#0F172A"
if not re.fullmatch(r"#[0-9a-fA-F]{6}", theme):
    theme = "#0F172A"
orient = {"portrait": "portrait", "landscape": "landscape"}.get(look.get("orientation"), "unspecified")
full = bool(look.get("fullscreen"))
hosts = [h for h in web.get("allowedHosts") or [] if h]
ext = web.get("externalLinks") or "browser"
back = web.get("backButton") or "history"
ua = web.get("userAgentSuffix") or "ApeX/1.0"

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
  compileSdk {app.get('targetSdk', 35)}
  defaultConfig {{
    applicationId '{pkg}'
    minSdk {app.get('minSdk', 24)}
    targetSdk {app.get('targetSdk', 35)}
    versionCode {int(app.get('versionCode') or 1)}
    versionName '{app.get('versionName') or '1.0.0'}'
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
