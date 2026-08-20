from pathlib import Path

p = Path('app/src/main/java/com/zhanggua/app/MainActivity.java')
s = p.read_text()

def must_replace(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'missing anchor: {label}')
    s = s.replace(old, new, 1)

# Imports for persisted experience settings, time-based animation, display cutouts, and controls.
must_replace('import android.content.Context;\n', 'import android.content.Context;\nimport android.content.SharedPreferences;\n', 'SharedPreferences import')
must_replace('import android.os.Bundle;\n', 'import android.os.Bundle;\nimport android.os.Build;\nimport android.os.SystemClock;\n', 'Build/SystemClock imports')
must_replace('import android.view.MotionEvent;\n', 'import android.view.DisplayCutout;\nimport android.view.MotionEvent;\n', 'DisplayCutout import')
must_replace('import android.view.Window;\n', 'import android.view.Window;\nimport android.view.WindowInsets;\nimport android.view.WindowInsetsController;\n', 'WindowInsets imports')
must_replace('import android.widget.Button;\n', 'import android.widget.Button;\nimport android.widget.CheckBox;\n', 'CheckBox import')

# Modern immersive mode + cutout policy. Keep the legacy path for Android 8/9 devices.
old_window = '''        Window window = getWindow();
        window.setStatusBarColor(Color.rgb(7, 9, 7));
        window.setNavigationBarColor(Color.BLACK);
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        window.getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
'''
new_window = '''        Window window = getWindow();
        window.setStatusBarColor(Color.BLACK);
        window.setNavigationBarColor(Color.BLACK);
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            WindowManager.LayoutParams lp = window.getAttributes();
            lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            window.setAttributes(lp);
        }
        enterImmersive(window);
'''
must_replace(old_window, new_window, 'window immersive block')

insert_before_destroy = '''    private void enterImmersive(Window window) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false);
            WindowInsetsController controller = window.getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            window.getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        }
    }

    @Override public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) enterImmersive(getWindow());
    }

'''
anchor_destroy = '    @Override protected void onDestroy() {\n'
if anchor_destroy not in s:
    raise SystemExit('missing anchor: onDestroy')
s = s.replace(anchor_destroy, insert_before_destroy + anchor_destroy, 1)

# UI fields.
must_replace('        private final RectF settingsButton = new RectF();\n', '        private final RectF settingsButton = new RectF();\n        private final RectF experienceButton = new RectF();\n', 'experience button field')

field_anchor = '''        private final AudioEngine audio;
        private final Vibrator vibrator;
'''
field_new = '''        private final AudioEngine audio;
        private final Vibrator vibrator;
        private boolean soundEnabled = true;
        private boolean hapticEnabled = true;
        private boolean shakeEnabled = true;
        private boolean manualCasting = false;
        private boolean lineAnimating = false;
        private float safeInsetLeft = 0f;
        private float safeInsetTop = 0f;
        private float safeInsetRight = 0f;
        private float safeInsetBottom = 0f;
'''
must_replace(field_anchor, field_new, 'experience fields')

# Replace constructor with safe-inset listener and smooth boot animation.
start = s.index('        GuaView(Context context, AudioEngine audio) {')
end = s.index('        boolean handleBack() {', start)
new_ctor = '''        GuaView(Context context, AudioEngine audio) {
            super(context);
            this.audio = audio;
            this.vibrator = (Vibrator) context.getSystemService(Context.VIBRATOR_SERVICE);
            zhouYi = new ZhouYiRepository(context);
            paint.setTypeface(mono);
            paint.setDither(true);
            setBackgroundColor(BG);
            setFocusable(true);
            loadExperienceSettings();
            setOnApplyWindowInsetsListener((v, insets) -> applySafeInsets(insets));
            requestApplyInsets();
            startBootAnimation();
        }

        private void startBootAnimation() {
            final long started = SystemClock.uptimeMillis();
            handler.postDelayed(() -> {
                if (soundEnabled) audio.boot();
                pulse(18, 90);
            }, 120L);
            Runnable animator = new Runnable() {
                @Override public void run() {
                    float t = Math.min(1f, (SystemClock.uptimeMillis() - started) / 1250f);
                    float inv = 1f - t;
                    bootSweep = 1f - inv * inv * inv;
                    bootStep = t < .18f ? 0 : t < .38f ? 1 : t < .58f ? 2 : t < .78f ? 3 : 4;
                    postInvalidateOnAnimation();
                    if (t < 1f) {
                        postOnAnimation(this);
                    } else {
                        state = State.IDLE;
                        pulse(28, 120);
                        postInvalidateOnAnimation();
                    }
                }
            };
            postOnAnimation(animator);
        }

        private WindowInsets applySafeInsets(WindowInsets insets) {
            int left = 0, top = 0, right = 0, bottom = 0;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                DisplayCutout cutout = insets.getDisplayCutout();
                if (cutout != null) {
                    left = Math.max(left, cutout.getSafeInsetLeft());
                    top = Math.max(top, cutout.getSafeInsetTop());
                    right = Math.max(right, cutout.getSafeInsetRight());
                    bottom = Math.max(bottom, cutout.getSafeInsetBottom());
                }
            }
            // On older full-screen devices these values also protect software navigation / rounded display areas.
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
                left = Math.max(left, insets.getSystemWindowInsetLeft());
                right = Math.max(right, insets.getSystemWindowInsetRight());
                bottom = Math.max(bottom, insets.getSystemWindowInsetBottom());
            }
            safeInsetLeft = left;
            safeInsetTop = top;
            safeInsetRight = right;
            safeInsetBottom = bottom;
            postInvalidateOnAnimation();
            return insets;
        }

        private void loadExperienceSettings() {
            SharedPreferences pref = getContext().getSharedPreferences("zhanggua_experience", Context.MODE_PRIVATE);
            soundEnabled = pref.getBoolean("sound", true);
            hapticEnabled = pref.getBoolean("haptic", true);
            shakeEnabled = pref.getBoolean("shake", true);
            manualCasting = pref.getBoolean("manual_cast", false);
        }

        private void saveExperienceSettings() {
            getContext().getSharedPreferences("zhanggua_experience", Context.MODE_PRIVATE).edit()
                    .putBoolean("sound", soundEnabled)
                    .putBoolean("haptic", hapticEnabled)
                    .putBoolean("shake", shakeEnabled)
                    .putBoolean("manual_cast", manualCasting)
                    .apply();
        }

'''
s = s[:start] + new_ctor + s[end:]

# Shake now respects the switch and can advance one line while manual casting.
start = s.index('        void onShake() {')
end = s.index('        private float dp(float n)', start)
new_shake = '''        void onShake() {
            if (!shakeEnabled) return;
            if (state == State.IDLE) {
                haptic(HapticFeedbackConstants.CONFIRM);
                pulse(24, 130);
                Toast.makeText(getContext(), manualCasting ? "摇动 · 第一爻" : "摇卦", Toast.LENGTH_SHORT).show();
                startCasting();
                return;
            }
            if (state == State.CASTING && manualCasting && !lineAnimating && castCount < 6) {
                haptic(HapticFeedbackConstants.CLOCK_TICK);
                pulse(15, 90);
                castNext();
            }
        }

'''
s = s[:start] + new_shake + s[end:]

# Gate explicit vibration. Existing performHapticFeedback calls are converted below.
must_replace('''        private void pulse(long ms, int amplitude) {
            if (vibrator == null || !vibrator.hasVibrator()) return;
''', '''        private void pulse(long ms, int amplitude) {
            if (!hapticEnabled || vibrator == null || !vibrator.hasVibrator()) return;
''', 'pulse switch')
must_replace('''        private void ritualPulse() {
            if (vibrator == null || !vibrator.hasVibrator()) return;
''', '''        private void ritualPulse() {
            if (!hapticEnabled || vibrator == null || !vibrator.hasVibrator()) return;
''', 'ritual vibration switch')

# Safe content space: draw inside cutout-safe bounds, while keeping the physical screen black edge-to-edge.
start = s.index('        @Override protected void onDraw(Canvas c) {')
end = s.index('        private void drawGrid(Canvas c, float w, float h) {', start)
new_draw = '''        @Override protected void onDraw(Canvas c) {
            super.onDraw(c);
            float contentW = Math.max(dp(240), getWidth() - safeInsetLeft - safeInsetRight);
            float contentH = Math.max(dp(360), getHeight() - safeInsetTop - safeInsetBottom);
            c.save();
            c.translate(safeInsetLeft, safeInsetTop);
            drawGrid(c, contentW, contentH);
            if (state != State.BOOT) drawHeader(c, contentW);
            switch (state) {
                case BOOT: drawBoot(c, contentW, contentH); break;
                case IDLE: drawIdle(c, contentW, contentH); break;
                case CASTING: drawCasting(c, contentW, contentH); break;
                case RESULT: drawResult(c, contentW, contentH); break;
                case DETAIL: drawDetail(c, contentW, contentH); break;
                case HISTORY: drawHistory(c, contentW, contentH); break;
                case AI: drawAi(c, contentW, contentH); break;
            }
            c.restore();
        }

'''
s = s[:start] + new_draw + s[end:]

# Version labels.
s = s.replace('v0.4 / ritual build', 'v0.5 / adaptive build')
s = s.replace('ZHANG · GUA / 0.4', 'ZHANG · GUA / 0.5')

# Three compact top buttons and mode-aware primary copy.
old_idle_top = '''            settingsButton.set(dp(20), dp(88), dp(112), dp(120));
            historyButton.set(w - dp(100), dp(88), w - dp(20), dp(120));
            button(c, settingsButton, "AI 设置", GOLD, false, 9.5f);
            button(c, historyButton, "历史", MUTED, false, 10);
'''
new_idle_top = '''            float topLeft = dp(20), topRight = w - dp(20), gap = dp(6);
            float cell = (topRight - topLeft - gap * 2f) / 3f;
            settingsButton.set(topLeft, dp(88), topLeft + cell, dp(120));
            experienceButton.set(topLeft + cell + gap, dp(88), topLeft + cell * 2f + gap, dp(120));
            historyButton.set(topLeft + cell * 2f + gap * 2f, dp(88), topRight, dp(120));
            button(c, settingsButton, "AI", GOLD, false, 9.5f);
            button(c, experienceButton, "体验", FG, false, 9.5f);
            button(c, historyButton, "历史", MUTED, false, 9.5f);
'''
must_replace(old_idle_top, new_idle_top, 'idle top buttons')
must_replace('''            primaryButton.set(dp(28), h - dp(122), w - dp(28), h - dp(64));
            button(c, primaryButton, "按下成卦", GOLD, true, 13);
            text(c, "KEY / SHAKE", cx, h - dp(41), 9, GOLD, Paint.Align.CENTER, true);
            text(c, "三钱六掷 · 自下而上", cx, h - dp(21), 8.2f, MUTED, Paint.Align.CENTER, false);
''', '''            primaryButton.set(dp(28), h - dp(122), w - dp(28), h - dp(64));
            button(c, primaryButton, manualCasting ? "按下 · 掷第一爻" : "按下成卦", GOLD, true, 13);
            text(c, shakeEnabled ? "KEY / SHAKE" : "KEY", cx, h - dp(41), 9, GOLD, Paint.Align.CENTER, true);
            text(c, manualCasting ? "逐爻手动 · 一次一掷" : "三钱六掷 · 自动成卦", cx, h - dp(21), 8.2f, MUTED, Paint.Align.CENTER, false);
''', 'mode aware idle copy')

# Casting screen reserves a real button only in manual mode.
start = s.index('        private void drawCasting(Canvas c, float w, float h) {')
end = s.index('        private void drawCoin(Canvas c, float x, float y, String face, int index) {', start)
new_cast_draw = '''        private void drawCasting(Canvas c, float w, float h) {
            float cx = w / 2f;
            int shown = Math.min(castCount + 1, 6);
            text(c, String.format(Locale.CHINA, "第 %d / 6 爻", shown), cx, dp(112), 13, GOLD, Paint.Align.CENTER, true);
            float coinY = dp(177);
            for (int i = 0; i < 3; i++) drawCoin(c, cx + dp((i - 1) * 72), coinY, currentCoins[i], i);

            float reserved = manualCasting ? dp(145) : dp(80);
            RectF frame = new RectF(dp(35), dp(234), w - dp(35), h - reserved);
            panel(c, frame);
            text(c, manualCasting ? "六爻 / 点击或摇动逐爻投掷" : "六爻 / 自动投掷", frame.left + dp(14), frame.top + dp(24), 9.5f, MUTED, Paint.Align.LEFT, false);
            drawStack(c, frame.centerX(), frame.bottom - dp(24), lines, castCount, false, dp(78), dp(32));

            if (manualCasting) {
                if (!toastLine.isEmpty()) text(c, toastLine, cx, h - dp(94), 10.5f, RED, Paint.Align.CENTER, true);
                primaryButton.set(dp(28), h - dp(72), w - dp(28), h - dp(20));
                String label = castCount >= 6 ? "成卦中…" : lineAnimating ? "投掷中…" : "点击 · 下一爻";
                button(c, primaryButton, label, lineAnimating ? MUTED : GOLD, true, 11.5f);
            } else {
                if (!toastLine.isEmpty()) text(c, toastLine, cx, h - dp(42), 11, RED, Paint.Align.CENTER, true);
            }
        }

'''
s = s[:start] + new_cast_draw + s[end:]

# More fluid coin shape while using time-based phase.
must_replace('''            float squash = 0.18f + 0.82f * Math.abs((float) Math.cos(coinPhase + index * 0.65f));
            RectF outer = new RectF(x - dp(26) * squash, y - dp(26), x + dp(26) * squash, y + dp(26));
''', '''            float wave = Math.abs((float) Math.cos(coinPhase + index * 0.72f));
            float squash = 0.12f + 0.88f * wave;
            float lift = (1f - wave) * dp(5);
            RectF outer = new RectF(x - dp(26) * squash, y - dp(26) - lift, x + dp(26) * squash, y + dp(26) - lift);
''', 'smooth coin shape')

# Touch coordinates follow the translated safe content area.
must_replace('''        @Override public boolean onTouchEvent(MotionEvent e) {
            float x = e.getX(), y = e.getY();
''', '''        @Override public boolean onTouchEvent(MotionEvent e) {
            float x = e.getX() - safeInsetLeft, y = e.getY() - safeInsetTop;
''', 'safe touch coordinates')

# Experience settings button on idle.
must_replace('''                if (primaryButton.contains(x, y)) { performHapticFeedback(HapticFeedbackConstants.CONFIRM); pulse(22, 120); startCasting(); return true; }
                if (settingsButton.contains(x, y)) { showAiSettingsDialog(false); return true; }
                if (historyButton.contains(x, y)) { state = State.HISTORY; scrollOffset = 0; invalidate(); return true; }
''', '''                if (primaryButton.contains(x, y)) { haptic(HapticFeedbackConstants.CONFIRM); pulse(22, 120); startCasting(); return true; }
                if (settingsButton.contains(x, y)) { showAiSettingsDialog(false); return true; }
                if (experienceButton.contains(x, y)) { showExperienceSettingsDialog(); return true; }
                if (historyButton.contains(x, y)) { state = State.HISTORY; scrollOffset = 0; postInvalidateOnAnimation(); return true; }
''', 'idle touch buttons')

# Manual casting accepts one explicit click per line.
result_anchor = '            if (state == State.RESULT) {\n'
manual_touch = '''            if (state == State.CASTING && manualCasting) {
                if (primaryButton.contains(x, y) && !lineAnimating && castCount < 6) {
                    haptic(HapticFeedbackConstants.CLOCK_TICK);
                    pulse(15, 90);
                    castNext();
                }
                return true;
            }
'''
if result_anchor not in s:
    raise SystemExit('missing anchor: result touch')
s = s.replace(result_anchor, manual_touch + result_anchor, 1)

# Replace automatic frame-count casting with time-based animation. Manual mode pauses after each line.
start = s.index('        private void startCasting() {')
end = s.index('        private void setCoinFacesForValue(int value) {', start)
new_cast_engine = '''        private void startCasting() {
            handler.removeCallbacksAndMessages(null);
            Arrays.fill(lines, 0);
            castCount = 0;
            toastLine = "";
            coinPhase = 0f;
            lineAnimating = false;
            loadedFromHistory = false;
            state = State.CASTING;
            postInvalidateOnAnimation();
            castNext();
        }

        private void castNext() {
            if (state != State.CASTING || lineAnimating) return;
            if (castCount >= 6) {
                finishCasting();
                return;
            }
            lineAnimating = true;
            final long started = SystemClock.uptimeMillis();
            final int[] lastBucket = {-1};
            Runnable flip = new Runnable() {
                @Override public void run() {
                    float t = Math.min(1f, (SystemClock.uptimeMillis() - started) / 430f);
                    coinPhase = t * (float) (Math.PI * 8.0);
                    int bucket = Math.min(11, (int) (t * 12f));
                    if (bucket != lastBucket[0]) {
                        for (int i = 0; i < 3; i++) currentCoins[i] = Math.random() > 0.5 ? "字" : "背";
                        if ((bucket == 1 || bucket == 5 || bucket == 9) && soundEnabled) audio.coin();
                        if (bucket == 6) pulse(10, 65);
                        lastBucket[0] = bucket;
                    }
                    postInvalidateOnAnimation();
                    if (t < 1f) postOnAnimation(this); else settleLine();
                }
            };
            postOnAnimation(flip);
        }

        private void settleLine() {
            int value = HexagramEngine.castLine();
            setCoinFacesForValue(value);
            lines[castCount] = value;
            toastLine = HexagramEngine.lineText(value);
            if (soundEnabled) audio.settle();
            pulse(HexagramEngine.isMoving(value) ? 30 : 17, HexagramEngine.isMoving(value) ? 155 : 95);
            haptic(HapticFeedbackConstants.CLOCK_TICK);
            castCount++;
            lineAnimating = false;
            postInvalidateOnAnimation();
            if (castCount >= 6) {
                handler.postDelayed(this::finishCasting, manualCasting ? 300L : 240L);
            } else if (!manualCasting) {
                handler.postDelayed(this::castNext, 220L);
            }
        }

        private void finishCasting() {
            if (state != State.CASTING) return;
            state = State.RESULT;
            HistoryStore.add(getContext(), lines);
            if (soundEnabled) audio.complete();
            ritualPulse();
            haptic(HapticFeedbackConstants.CONFIRM);
            postInvalidateOnAnimation();
        }

'''
s = s[:start] + new_cast_engine + s[end:]

# Experience settings dialog. Stored locally and applied immediately.
settings_anchor = '        private void showAiSettingsDialog(boolean startAfterSave) {\n'
experience_method = '''        private void showExperienceSettingsDialog() {
            Context ctx = getContext();
            float density = getResources().getDisplayMetrics().density;
            LinearLayout box = new LinearLayout(ctx);
            box.setOrientation(LinearLayout.VERTICAL);
            int pad = (int) (18 * density);
            box.setPadding(pad, (int) (6 * density), pad, (int) (4 * density));

            TextView note = new TextView(ctx);
            note.setText("体验设置会立即生效，并仅保存在本机。逐爻手动模式开启后，每次点击或摇动只投掷一爻，六次后成卦。");
            note.setTextSize(12);
            note.setPadding(0, 0, 0, (int) (8 * density));
            box.addView(note);

            CheckBox sound = new CheckBox(ctx);
            sound.setText("音效");
            sound.setChecked(soundEnabled);
            box.addView(sound);

            CheckBox haptic = new CheckBox(ctx);
            haptic.setText("震动 / 触感反馈");
            haptic.setChecked(hapticEnabled);
            box.addView(haptic);

            CheckBox shake = new CheckBox(ctx);
            shake.setText("摇动起卦 / 摇动继续投掷");
            shake.setChecked(shakeEnabled);
            box.addView(shake);

            CheckBox manual = new CheckBox(ctx);
            manual.setText("逐爻手动投掷（每次点击 / 摇动只掷一爻）");
            manual.setChecked(manualCasting);
            box.addView(manual);

            new AlertDialog.Builder(ctx)
                    .setTitle("体验设置")
                    .setView(box)
                    .setPositiveButton("保存", (d, which) -> {
                        soundEnabled = sound.isChecked();
                        hapticEnabled = haptic.isChecked();
                        shakeEnabled = shake.isChecked();
                        manualCasting = manual.isChecked();
                        saveExperienceSettings();
                        postInvalidateOnAnimation();
                        Toast.makeText(ctx, "体验设置已保存", Toast.LENGTH_SHORT).show();
                    })
                    .setNegativeButton("取消", null)
                    .show();
        }

'''
if settings_anchor not in s:
    raise SystemExit('missing anchor: AI settings method')
s = s.replace(settings_anchor, experience_method + settings_anchor, 1)

# Convert every remaining system haptic call in GuaView to the gated helper.
s = s.replace('performHapticFeedback(', 'haptic(')

# Add gated helper after pulse(), after the global conversion so it can call the real View method.
pulse_end = '''            vibrator.vibrate(VibrationEffect.createOneShot(ms, Math.max(1, Math.min(255, amplitude))));
        }

'''
haptic_helper = '''            vibrator.vibrate(VibrationEffect.createOneShot(ms, Math.max(1, Math.min(255, amplitude))));
        }

        private void haptic(int feedbackConstant) {
            if (hapticEnabled) performHapticFeedback(feedbackConstant);
        }

'''
must_replace(pulse_end, haptic_helper, 'haptic helper insertion')

# Prefer vsync-aware invalidation throughout the custom view.
s = s.replace('invalidate();', 'postInvalidateOnAnimation();')

p.write_text(s)
print('v0.5 transform applied successfully')
