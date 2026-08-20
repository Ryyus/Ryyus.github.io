package com.zhanggua.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.net.Uri;
import android.os.Build;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/** Lightweight update checker for the public ZhangGua release channel. */
final class UpdateChecker {
    private static final String META_URL = "https://raw.githubusercontent.com/Ryyus/Ryyus.github.io/main/zhanggua/latest.json";
    private static final String PREF = "zhanggua_updates";
    private static final long AUTO_INTERVAL_MS = 12L * 60L * 60L * 1000L;

    private UpdateChecker() {}

    static void check(Activity activity, boolean manual) {
        if (activity == null || activity.isFinishing()) return;
        SharedPreferences p = activity.getSharedPreferences(PREF, Context.MODE_PRIVATE);
        long now = System.currentTimeMillis();
        if (!manual && now - p.getLong("last_check", 0L) < AUTO_INTERVAL_MS) return;
        p.edit().putLong("last_check", now).apply();
        if (manual) Toast.makeText(activity, "正在检查更新…", Toast.LENGTH_SHORT).show();

        new Thread(() -> {
            HttpURLConnection conn = null;
            try {
                conn = (HttpURLConnection) new URL(META_URL).openConnection();
                conn.setConnectTimeout(7000);
                conn.setReadTimeout(7000);
                conn.setUseCaches(false);
                conn.setRequestProperty("Accept", "application/json");
                conn.setRequestProperty("User-Agent", "ZhangGua-Android");
                int code = conn.getResponseCode();
                if (code < 200 || code >= 300) throw new IllegalStateException("HTTP " + code);
                String body = readAll(conn.getInputStream());
                JSONObject json = new JSONObject(body);
                int remoteCode = json.optInt("versionCode", 0);
                String remoteName = json.optString("versionName", "");
                String title = json.optString("title", "发现新版本");
                String notes = json.optString("notes", "");
                String releasePage = json.optString("releasePage", "https://github.com/Ryyus/Ryyus.github.io/releases");
                int localCode = currentVersionCode(activity);

                activity.runOnUiThread(() -> {
                    if (activity.isFinishing() || (Build.VERSION.SDK_INT >= 17 && activity.isDestroyed())) return;
                    if (remoteCode > localCode) {
                        String message = "v" + remoteName + " 可用\n\n" + notes;
                        new AlertDialog.Builder(activity)
                                .setTitle(title)
                                .setMessage(message.trim())
                                .setPositiveButton("前往更新", (d, w) -> open(activity, releasePage))
                                .setNegativeButton("稍后", null)
                                .show();
                    } else if (manual) {
                        Toast.makeText(activity, "当前已是最新版本", Toast.LENGTH_SHORT).show();
                    }
                });
            } catch (Exception ex) {
                if (manual) activity.runOnUiThread(() -> {
                    if (!activity.isFinishing()) Toast.makeText(activity, "检查更新失败，请稍后重试", Toast.LENGTH_SHORT).show();
                });
            } finally {
                if (conn != null) conn.disconnect();
            }
        }, "zhanggua-update-check").start();
    }

    private static int currentVersionCode(Context context) throws Exception {
        PackageInfo info = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
        long code = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P ? info.getLongVersionCode() : info.versionCode;
        return (int) Math.min(Integer.MAX_VALUE, code);
    }

    private static String readAll(InputStream in) throws Exception {
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) sb.append(line).append('\n');
        }
        return sb.toString();
    }

    private static void open(Context context, String url) {
        try {
            context.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (Exception ex) {
            Toast.makeText(context, "无法打开更新页面", Toast.LENGTH_SHORT).show();
        }
    }
}
