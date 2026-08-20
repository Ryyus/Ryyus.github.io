package com.zhanggua.app;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.SoundPool;

/** Defensive SoundPool wrapper: audio failure must never crash the app. */
final class AudioEngine {
    private SoundPool pool;
    private int boot;
    private int coin;
    private int settle;
    private int complete;
    private volatile boolean released = false;

    AudioEngine(Context context) {
        try {
            AudioAttributes attrs = new AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .build();
            pool = new SoundPool.Builder().setMaxStreams(4).setAudioAttributes(attrs).build();
            boot = safeLoad(context, R.raw.boot);
            coin = safeLoad(context, R.raw.coin);
            settle = safeLoad(context, R.raw.settle);
            complete = safeLoad(context, R.raw.complete);
        } catch (Throwable ignored) {
            pool = null;
        }
    }

    private int safeLoad(Context context, int resId) {
        try { return pool == null ? 0 : pool.load(context, resId, 1); }
        catch (Throwable ignored) { return 0; }
    }

    void boot() { play(boot, .52f, 1f); }
    void coin() { play(coin, .43f, .96f + (float)Math.random() * .09f); }
    void settle() { play(settle, .48f, .92f + (float)Math.random() * .12f); }
    void complete() { play(complete, .52f, 1f); }

    private void play(int sound, float volume, float rate) {
        try {
            SoundPool p = pool;
            if (!released && p != null && sound != 0) p.play(sound, volume, volume, 1, 0, rate);
        } catch (Throwable ignored) {}
    }

    void release() {
        released = true;
        try {
            if (pool != null) pool.release();
        } catch (Throwable ignored) {}
        pool = null;
    }
}
