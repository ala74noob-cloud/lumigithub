# -*- coding: utf-8 -*-
"""Convert NetEase Cloud Music .ncm files to their original audio (mp3/flac).

usage: python3 -I src/ncm2audio.py OUT_DIR file1.ncm [file2.ncm ...]
Prints one JSON line per file: {"src", "out", "title", "artist", "album", "format"}
"""
import base64, json, os, struct, sys
import numpy as np
from Crypto.Cipher import AES

CORE_KEY = bytes.fromhex("687A4852416D736F356B496E62617857")
META_KEY = bytes.fromhex("2331346C6A6B5F215C5D2630553C2728")


def _unpad(b):
    return b[: -b[-1]]


def _keybox(key):
    box = list(range(256))
    c = last = off = 0
    for i in range(256):
        sw = box[i]
        c = (sw + last + key[off]) & 0xFF
        off = (off + 1) % len(key)
        box[i], box[c] = box[c], sw
        last = c
    # final stream table (independent of position mod 256)
    return bytes(box[(box[i] + box[(box[i] + i) & 0xFF]) & 0xFF] for i in range(256))


def _sniff(b):
    if b[:3] == b"ID3" or (len(b) > 1 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0):
        return "mp3"
    if b[:4] == b"fLaC":
        return "flac"
    return None


def decode(path, out_dir):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"CTENFDAM":
        raise ValueError("not an NCM file: " + path)
    p = 10
    (klen,) = struct.unpack_from("<I", data, p); p += 4
    kd = bytes(b ^ 0x64 for b in data[p:p + klen]); p += klen
    key = _unpad(AES.new(CORE_KEY, AES.MODE_ECB).decrypt(kd))[17:]
    (mlen,) = struct.unpack_from("<I", data, p); p += 4
    meta = {}
    if mlen:
        md = bytes(b ^ 0x63 for b in data[p:p + mlen])
        try:
            md = base64.b64decode(md[22:])
            meta = json.loads(_unpad(AES.new(META_KEY, AES.MODE_ECB).decrypt(md))[6:].decode("utf-8"))
        except Exception:
            meta = {}
    p += mlen
    p += 4 + 5  # crc32 + gap
    table = _keybox(key)
    # two known layouts for the cover-art block; pick the one that yields a valid audio header
    cands = []
    (a,) = struct.unpack_from("<I", data, p)
    cands.append(p + 4 + a)                         # [img_size][img]
    if p + 8 <= len(data):
        (b2,) = struct.unpack_from("<I", data, p + 4)
        if b2 <= a:
            cands.append(p + 8 + a)                 # [frame_len][img_size][img ... padded to frame_len]
            cands.append(p + 8 + b2)
    start = None
    for c in cands:
        head = bytes(x ^ table[(i + 1) & 0xFF] for i, x in enumerate(data[c:c + 16]))
        if _sniff(head):
            start = c
            break
    if start is None:
        raise ValueError("could not locate audio stream in " + path)
    enc = data[start:]
    # XOR with repeating 256-byte keystream (index i uses table[(i+1) & 0xff])
    ks = np.frombuffer(table[1:] + table[:1], dtype=np.uint8)
    arr = np.frombuffer(enc, dtype=np.uint8)
    audio = (arr ^ np.resize(ks, len(arr))).tobytes()
    fmt = meta.get("format") or _sniff(audio[:16]) or "mp3"
    title = meta.get("musicName") or os.path.splitext(os.path.basename(path))[0]
    artist = ", ".join(a[0] for a in meta.get("artist", []) if a) if meta.get("artist") else ""
    safe = "".join(ch if ch not in '/\\:*?"<>|' else "_" for ch in os.path.splitext(os.path.basename(path))[0])
    out = os.path.join(out_dir, f"{safe}.{fmt}")
    with open(out, "wb") as f:
        f.write(audio)
    return {"src": path, "out": out, "title": title, "artist": artist, "album": meta.get("album", ""), "format": fmt}


def _selftest():
    """Round-trip a synthetic NCM through an encoder that follows the same spec."""
    import random
    key = b"neteasecloudmusic" + b"0123456789abcdefghijklmnopqrstuv"
    pad = lambda b: b + bytes([16 - len(b) % 16]) * (16 - len(b) % 16)
    kd = bytes(x ^ 0x64 for x in AES.new(CORE_KEY, AES.MODE_ECB).encrypt(pad(key)))
    meta = b"music:" + json.dumps({"musicName": "Test", "artist": [["A", 1]], "format": "mp3"}).encode()
    md = b"163 key(Don't modify):" + base64.b64encode(AES.new(META_KEY, AES.MODE_ECB).encrypt(pad(meta)))
    md = bytes(x ^ 0x63 for x in md)
    audio = b"ID3" + bytes(random.getrandbits(8) for _ in range(5000))
    table = _keybox(key[17:])
    enc = bytes(x ^ table[(i + 1) & 0xFF] for i, x in enumerate(audio))
    img = b"\x89PNG" + b"0" * 100
    blob = (b"CTENFDAM" + b"\x00\x00" + struct.pack("<I", len(kd)) + kd + struct.pack("<I", len(md)) + md +
            b"\x00" * 9 + struct.pack("<I", len(img)) + img + enc)
    import tempfile
    d = tempfile.mkdtemp()
    src = os.path.join(d, "t.ncm")
    open(src, "wb").write(blob)
    r = decode(src, d)
    assert open(r["out"], "rb").read() == audio and r["title"] == "Test", r
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        _selftest(); sys.exit(0)
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    for pth in sys.argv[2:]:
        print(json.dumps(decode(pth, out_dir), ensure_ascii=False))
