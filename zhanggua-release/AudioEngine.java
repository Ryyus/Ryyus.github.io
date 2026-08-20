package com.zhanggua.app;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.SoundPool;

final class AudioEngine {
    private final SoundPool pool;
    private final int boot;
    private final int coin;
    private final int settle;
    private final int complete;
    private volatile boolean released = false;

    AudioEngine(Context context) {
        AudioAttributes attrs = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANCE_SONIFICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build();
        pool = new SoundPool.Builder().setMaxStreams(4).setAudioAttributes(attrs).build();
        boot = pool.load(context, R.raw.boot, 1);
        coin = pool.load(context, R.raw.coin, 1);
        settle = pool.load(context, R.raw.settle, 1);
        complete = pool.load(context, R.raw.complete, 1);
    }

    void boot() { play(boot, .52f, 1f); }
    void coin() { play(coin, .43f, .96f + (float)Math.random() * .09f); }
    void settle() { play(settle, .48f, .92f + (float)Math.random() * .12f); }
    void complete() { play(complete, .52f, 1f); }

    private void play(int sound, float volume, float rate) {
        if (!released) pool.play(sound, volume, volume, 1, 0, rate);
    }

    void release() {
        released = true;
        pool.release();
    }
}
