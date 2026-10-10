#!/usr/bin/env python3
"""Real advance widths from a TrueType file.

Chart code kept guessing text widths with a per-character constant, and the
guess kept disagreeing with what actually rendered: the J chart's overlap
checker assumed 7.8px while the renderer drew 13px text, and its badge was
placed after an assumed 300px title that renders at 376px. Both are the same
defect -- a measurement that is not a measurement.

Parses just enough of the font: head (unitsPerEm), cmap format 4 (unicode ->
glyph id), hmtx (advance per glyph). No dependency.
"""
import struct
from functools import lru_cache


class Font:
    def __init__(self, path):
        d = open(path, "rb").read()
        self.d = d
        n = struct.unpack(">H", d[4:6])[0]
        self.tabs = {}
        for i in range(n):
            o = 12 + 16 * i
            tag = d[o:o + 4].decode("latin1")
            off, ln = struct.unpack(">II", d[o + 8:o + 16])
            self.tabs[tag] = (off, ln)
        ho = self.tabs["head"][0]
        self.upem = struct.unpack(">H", d[ho + 18:ho + 20])[0]
        hh = self.tabs["hhea"][0]
        self.n_hm = struct.unpack(">H", d[hh + 34:hh + 36])[0]
        self.cmap = self._cmap()

    def _cmap(self):
        d = self.d
        base = self.tabs["cmap"][0]
        n = struct.unpack(">H", d[base + 2:base + 4])[0]
        sub = None
        for i in range(n):
            pid, eid, off = struct.unpack(">HHI", d[base + 4 + 8 * i:base + 12 + 8 * i])
            if (pid, eid) in ((3, 1), (3, 10), (0, 3), (0, 4)):
                sub = base + off
                if (pid, eid) == (3, 1):
                    break
        if sub is None:
            return {}
        fmt = struct.unpack(">H", d[sub:sub + 2])[0]
        if fmt != 4:
            return {}
        segx2 = struct.unpack(">H", d[sub + 6:sub + 8])[0]
        seg = segx2 // 2
        ends = struct.unpack(">%dH" % seg, d[sub + 14:sub + 14 + segx2])
        so = sub + 16 + segx2
        starts = struct.unpack(">%dH" % seg, d[so:so + segx2])
        do = so + segx2
        deltas = struct.unpack(">%dh" % seg, d[do:do + segx2])
        ro = do + segx2
        ranges = struct.unpack(">%dH" % seg, d[ro:ro + segx2])
        m = {}
        for i in range(seg):
            for c in range(starts[i], min(ends[i], 0xFFFF) + 1):
                if ranges[i] == 0:
                    g = (c + deltas[i]) & 0xFFFF
                else:
                    p = ro + 2 * i + ranges[i] + 2 * (c - starts[i])
                    if p + 2 > len(d):
                        continue
                    g = struct.unpack(">H", d[p:p + 2])[0]
                    if g:
                        g = (g + deltas[i]) & 0xFFFF
                if g:
                    m[c] = g
        return m

    @lru_cache(maxsize=4096)
    def _adv(self, gid):
        ho = self.tabs["hmtx"][0]
        i = min(gid, self.n_hm - 1)
        return struct.unpack(">H", self.d[ho + 4 * i:ho + 4 * i + 2])[0]

    def width(self, text, size):
        """Advance width of `text` at `size` px."""
        total = 0
        for ch in text:
            g = self.cmap.get(ord(ch))
            if g is None:
                g = self.cmap.get(ord("?"), 0)
            total += self._adv(g)
        return total * size / self.upem


_cache = {}


def load(path):
    if path not in _cache:
        _cache[path] = Font(path)
    return _cache[path]
