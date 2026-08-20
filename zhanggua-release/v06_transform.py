from pathlib import Path

p = Path('app/src/main/java/com/zhanggua/app/MainActivity.java')
s = p.read_text()

def must_replace(old, new, label):
    global s
    if old not in s:
        raise SystemExit('missing anchor: ' + label)
    s = s.replace(old, new, 1)

# Version copy.
s = s.replace('ZHANG · GUA / 0.5', 'ZHANG · GUA / 0.6')
s = s.replace('v0.5 / adaptive build', 'v0.6 / signed build')

# Keep cutout support, but never allow a vendor Window implementation to crash startup.
old_cutout = '''        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            WindowManager.LayoutParams lp = window.getAttributes();
            lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            window.setAttributes(lp);
        }
        enterImmersive(window);
'''
new_cutout = '''        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                WindowManager.LayoutParams lp = window.getAttributes();
                lp.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
                window.setAttributes(lp);
            }
        } catch (Throwable ignored) {}
        enterImmersive(window);
'''
must_replace(old_cutout, new_cutout, 'defensive cutout startup')

# Use broadly compatible immersive flags on every supported Android version.
start = s.find('    private void enterImmersive(Window window) {')
end = s.find('    @Override public void onWindowFocusChanged', start)
if start < 0 or end < 0:
    raise SystemExit('missing enterImmersive method')
new_immersive = '''    private void enterImmersive(Window window) {
        try {
            window.getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        } catch (Throwable ignored) {
            // Fullscreen is cosmetic. A ROM-specific failure must never stop 掌卦 from opening.
        }
    }

'''
s = s[:start] + new_immersive + s[end:]

# Defensive inset hookup.
must_replace(
'''            setOnApplyWindowInsetsListener((v, insets) -> applySafeInsets(insets));
            requestApplyInsets();
            startBootAnimation();
''',
'''            try {
                setOnApplyWindowInsetsListener((v, insets) -> {
                    try { return applySafeInsets(insets); }
                    catch (Throwable ignored) { return insets; }
                });
                requestApplyInsets();
            } catch (Throwable ignored) {}
            startBootAnimation();
''',
'inset listener guard')

# Vibration / haptics are optional hardware: fail open on vendor-specific errors.
pulse_start = s.find('        private void pulse(long ms, int amplitude) {')
ritual_start = s.find('        private void ritualPulse() {', pulse_start)
text_start = s.find('        private void text(Canvas c, String s, float x, float y, float size, int color, Paint.Align align, boolean bold) {', ritual_start)
if pulse_start < 0 or ritual_start < 0 or text_start < 0:
    raise SystemExit('missing vibration methods')
new_vibration = '''        private void pulse(long ms, int amplitude) {
            if (!hapticEnabled || vibrator == null) return;
            try {
                if (!vibrator.hasVibrator()) return;
                vibrator.vibrate(VibrationEffect.createOneShot(ms, Math.max(1, Math.min(255, amplitude))));
            } catch (Throwable ignored) {}
        }

        private void ritualPulse() {
            if (!hapticEnabled || vibrator == null) return;
            try {
                if (!vibrator.hasVibrator()) return;
                long[] timings = {0, 18, 52, 18, 70, 34};
                int[] amps = {0, 85, 0, 115, 0, 165};
                vibrator.vibrate(VibrationEffect.createWaveform(timings, amps, -1));
            } catch (Throwable ignored) {}
        }

        private void haptic(int constant) {
            if (!hapticEnabled) return;
            try { performHapticFeedback(constant); }
            catch (Throwable ignored) {}
        }

'''
s = s[:pulse_start] + new_vibration + s[text_start:]

# Automatic update check after the UI is alive. Network failures stay silent.
must_replace(
'''        setContentView(guaView);

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
''',
'''        setContentView(guaView);
        new Handler(Looper.getMainLooper()).postDelayed(() -> UpdateChecker.check(this, false), 2600L);

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
''',
'automatic update check')

# Add manual update check to the Experience dialog.
exp = s.find('        private void showExperienceSettingsDialog')
if exp < 0:
    raise SystemExit('missing experience settings dialog')
dialog = s.find('AlertDialog dialog =', exp)
if dialog < 0:
    raise SystemExit('missing experience dialog creation')
manual_update = '''            Button versionUpdateButton = new Button(getContext());
            versionUpdateButton.setText("检查更新 · v0.6");
            box.addView(versionUpdateButton);
            versionUpdateButton.setOnClickListener(v -> UpdateChecker.check((Activity) getContext(), true));

'''
s = s[:dialog] + manual_update + s[dialog:]

p.write_text(s)

# Keep a reconstructed source tree self-contained: generate the ritual sound assets too.
from generate_audio import generate
generate(Path('app/src/main/res/raw'))

print('v0.6 transform applied successfully')
