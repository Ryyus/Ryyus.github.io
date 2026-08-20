from pathlib import Path
import math
import random
import struct
import wave

SR = 22050


def generate(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    random.seed(406)

    def write(name, samples):
        mx = max(1.0, max(abs(x) for x in samples))
        scale = 0.82 * 32767 / mx
        vals = [max(-32767, min(32767, int(x * scale))) for x in samples]
        with wave.open(str(out / name), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(b''.join(struct.pack('<h', v) for v in vals))

    def env(t, duration, attack=.005, release=.06):
        if t < attack:
            return t / attack
        if t > duration - release:
            return max(0.0, (duration - t) / release)
        return 1.0

    def tone(freq, duration, harmonics=(1,)):
        return [
            sum((1 / h) * math.sin(2 * math.pi * freq * h * (i / SR)) for h in harmonics)
            * env(i / SR, duration)
            for i in range(int(SR * duration))
        ]

    def mix(parts, duration):
        arr = [0.0] * int(SR * duration)
        for offset, wav, gain in parts:
            start = int(offset * SR)
            for i, sample in enumerate(wav):
                if start + i < len(arr):
                    arr[start + i] += sample * gain
        return arr

    write('boot.wav', mix([
        (0, tone(420, .12, (1, 2, 3)), .8),
        (.13, tone(720, .16, (1, 2)), .7),
    ], .33))

    n = int(SR * .18)
    coin = []
    for i in range(n):
        t = i / SR
        decay = math.exp(-25 * t)
        sample = (
            math.sin(2 * math.pi * 1550 * t)
            + .55 * math.sin(2 * math.pi * 2480 * t)
            + .3 * math.sin(2 * math.pi * 3320 * t)
        ) * decay
        sample += random.uniform(-1, 1) * math.exp(-45 * t) * .35
        coin.append(sample)
    write('coin.wav', coin)

    write('settle.wav', mix([
        (0, tone(260, .10, (1, 2, 4)), .7),
        (.03, tone(520, .08, (1, 3)), .25),
    ], .14))

    write('complete.wav', mix([
        (0, tone(330, .13, (1, 2)), .55),
        (.09, tone(495, .14, (1, 2)), .5),
        (.18, tone(660, .18, (1, 2)), .45),
    ], .39))


if __name__ == '__main__':
    generate(Path('app/src/main/res/raw'))
