"""Synthesize narration per segment (Kokoro, local) and align words with faster-whisper.
Output: build/vo/<id>.wav (48 kHz mono) + build/vo/timing.json {id: {dur, words:[[start,end,word],...], tokens:[...]}}"""
import json, os, re, sys, difflib
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.text import parse_card
from film.script import SEGMENTS

VOICE = os.environ.get("VOICE", "af_heart")
SPEED = float(os.environ.get("SPEED", "1.08"))
OUT = "build/vo"
only = set(sys.argv[1:])
# Russian stress: Sary-Shagan = sa-RY sha-GAN
PHONEME_FIX = {"sˈɑːɹɹi ʃˈæɡən": "sɑːɹˈi ʃɐɡˈɑːn"}


def spoken_tokens(cards):
    toks = []
    for ci, c in enumerate(cards):
        for li, ln in enumerate(parse_card(c)):
            for t in ln:
                toks.append(dict(card=ci, line=li, text=t["text"], spoken=t["spoken"]))
    return toks


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def main():
    from kokoro_onnx import Kokoro
    from faster_whisper import WhisperModel
    k = Kokoro("/opt/spy/models/kokoro-v1.0.onnx", "/opt/spy/models/voices-v1.0.bin")
    wm = WhisperModel("small.en", device="cpu", compute_type="int8")
    tp = os.path.join(OUT, "timing.json")
    timing = json.load(open(tp)) if os.path.exists(tp) else {}
    for sid, _, cards in SEGMENTS:
        if only and sid not in only:
            continue
        toks = spoken_tokens(cards)
        text = " ".join(t["spoken"] for t in toks).replace("— ", ", ").replace("—", ",")
        if text[-1] not in ".!?":
            text += "."
        ph = k.tokenizer.phonemize(text, "en-us")
        for a_, b_ in PHONEME_FIX.items():
            ph = ph.replace(a_, b_)
        audio, sr = k.create(ph, voice=VOICE, speed=SPEED, lang="en-us", is_phonemes=True)
        a = resample_poly(audio.astype(np.float64), 2, 1) if sr == 24000 else audio
        a = a.astype(np.float32)
        # trim to speech with 40 ms margins
        env = np.convolve(np.abs(a), np.ones(480) / 480, "same")
        idx = np.where(env > 0.004)[0]
        s0, s1 = max(0, idx[0] - 1920), min(len(a), idx[-1] + 1920)
        a = a[s0:s1]
        sf.write(os.path.join(OUT, f"{sid}.wav"), a, 48000)
        a16 = resample_poly(a, 1, 3).astype(np.float32)
        segs, _ = wm.transcribe(a16, word_timestamps=True, language="en", beam_size=5)
        words = [[round(w.start, 3), round(w.end, 3), w.word.strip()] for s in segs for w in s.words]
        # align spoken words (expanded) to whisper words
        exp = []
        for ti, t in enumerate(toks):
            for w in t["spoken"].split():
                exp.append((ti, norm(w)))
        sm = difflib.SequenceMatcher(a=[e[1] for e in exp], b=[norm(w[2]) for w in words], autojunk=False)
        times = [None] * len(exp)
        for blk in sm.get_matching_blocks():
            for j in range(blk.size):
                times[blk.a + j] = words[blk.b + j][:2]
        # fill gaps by interpolation between known neighbours
        known = [i for i, x in enumerate(times) if x]
        dur = len(a) / 48000
        for i in range(len(times)):
            if times[i] is None:
                prv = max([j for j in known if j < i], default=None)
                nxt = min([j for j in known if j > i], default=None)
                t0 = times[prv][1] if prv is not None else 0.0
                t1 = times[nxt][0] if nxt is not None else dur
                lo = prv if prv is not None else -1
                hi = nxt if nxt is not None else len(times)
                f = (i - lo) / (hi - lo)
                times[i] = [t0 + (t1 - t0) * f, t0 + (t1 - t0) * min(1, f + 1 / (hi - lo))]
        for ti, t in enumerate(toks):
            ws = [times[i] for i, e in enumerate(exp) if e[0] == ti]
            t["t0"], t["t1"] = ws[0][0], ws[-1][1]
        matched = sum(1 for x in sm.get_matching_blocks() for _ in range(x.size))
        timing[sid] = dict(dur=dur, text=text, heard=" ".join(w[2] for w in words), words=words, tokens=toks,
                           match=f"{matched}/{len(exp)}")
        print(f"{sid:9s} {dur:5.2f}s match {matched}/{len(exp)} | {timing[sid]['heard']}", flush=True)
        json.dump(timing, open(tp, "w"), indent=1)


if __name__ == "__main__":
    main()
