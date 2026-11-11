"""RED SKIES: Blender model pass (V1.8.0.0).

Builds the drone, the helicopter and the transport aircraft in Blender, bakes ambient occlusion into their
vertex colours with Cycles, makes a low-detail copy with the Decimate modifier, and writes the result to
src/models_blender_data.js (plain JavaScript data: no loader, no extra request, still one offline page).
src/models_blender.js turns that data into three.js meshes.

Run it (needs Blender's Python module, `pip install bpy`, or a full Blender with `blender -b -P`):

    python tools/blender/build_models.py            # writes src/models_blender_data.js
    node build.js                                   # then rebuild the page

Axes while modelling: x = right, f = forward (nose), z = up, metres, origin near the centre of mass.
Blender's y is -f. The exporter turns that into the game's axes (+Y up, +Z forward).
All designs are fictional.
"""
import base64
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'src', 'models_blender_data.js')
AO_SAMPLES = 48
SEG = 14                       # sides of a fuselage ring

# ---------------------------------------------------------------- paint
# a face's "zone" picks its paint: (r, g, b) or the name of a camouflage scheme
SCHEMES = {
    # top colours (noise picks between them), belly colour, noise scale
    'olive':  dict(top=[(0.37, 0.42, 0.25), (0.52, 0.48, 0.32), (0.25, 0.31, 0.20)], belly=(0.58, 0.62, 0.64), scale=0.34),
    'grey':   dict(top=[(0.47, 0.50, 0.52), (0.40, 0.43, 0.46), (0.52, 0.55, 0.56)], belly=(0.66, 0.68, 0.70), scale=0.09),
    'sand':   dict(top=[(0.62, 0.58, 0.47), (0.52, 0.49, 0.40), (0.66, 0.63, 0.54)], belly=(0.70, 0.70, 0.68), scale=1.6),
}
DARK = (0.07, 0.07, 0.08)
TYRE = (0.05, 0.05, 0.05)
METAL = (0.36, 0.35, 0.33)
BURNT = (0.20, 0.17, 0.15)
BLADE = (0.10, 0.10, 0.11)
TIP = (0.85, 0.66, 0.10)
RED = (0.62, 0.10, 0.08)
WHITE = (0.82, 0.82, 0.80)
GLASS = (0.13, 0.22, 0.28)


class Builder:
    """Collects closed shapes into one bmesh; every face remembers its paint zone and part name."""

    def __init__(self, scheme):
        self.bm = bmesh.new()
        self.zone = self.bm.faces.layers.int.new('zone')
        self.zones = []                  # index -> paint
        self.scheme = scheme
        self.paint = scheme
        self.part = 'body'
        self.partl = self.bm.faces.layers.int.new('part')
        self.parts = ['body']

    def use(self, paint=None, part=None):
        self.paint = self.scheme if paint is None else paint
        if part is not None:
            if part not in self.parts:
                self.parts.append(part)
            self.part = part
        return self

    def _zi(self):
        if self.paint not in self.zones:
            self.zones.append(self.paint)
        return self.zones.index(self.paint)

    def _add(self, tmp):
        """Merge a finished closed shape: fix its normals, tag its faces, append to the main mesh."""
        bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces[:])
        zi, pi = self._zi(), self.parts.index(self.part)
        vmap = {}
        for v in tmp.verts:
            vmap[v] = self.bm.verts.new(v.co)
        for fc in tmp.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in fc.verts])
            except ValueError:
                continue
            nf[self.zone] = zi
            nf[self.partl] = pi
            nf.smooth = True
        tmp.free()

    # ---- lofted body: rings along the forward axis -------------------------------------------------
    def loft(self, stations, seg=SEG, p=2.4, axis='f'):
        """stations: dicts with f (or z when axis='z'), w, h, and optional x, z (centre), hb (belly half-height), p.
        w <= 0 closes the end to a point. axis 'z' lofts upward (masts, pylons): then w is along x and h along f."""
        tmp = bmesh.new()
        rings = []
        for s in stations:
            cx, pw = s.get('x', 0.0), s.get('p', p)
            w, ht = s['w'], s['h']
            hb = s.get('hb', ht)
            if axis == 'f':
                cf, cz = s['f'], s.get('z', 0.0)
            else:
                cf, cz = s.get('f', 0.0), s['z']
            if w <= 1e-5:
                rings.append([tmp.verts.new((cx, -cf, cz))])
                continue
            r = []
            for i in range(seg):
                a = 2 * math.pi * i / seg
                c, sn = math.cos(a), math.sin(a)
                u = math.copysign(abs(c) ** (2 / pw), c) * w
                vv = math.copysign(abs(sn) ** (2 / pw), sn)
                vv *= ht if vv >= 0 else hb
                if axis == 'f':
                    r.append(tmp.verts.new((cx + u, -cf, cz + vv)))
                else:
                    r.append(tmp.verts.new((cx + u, -(cf + vv), cz)))
            rings.append(r)
        for a, b in zip(rings, rings[1:]):
            if len(a) == 1 and len(b) == 1:
                continue
            n = max(len(a), len(b))
            for i in range(n):
                j = (i + 1) % n
                if len(a) == 1:
                    tmp.faces.new([a[0], b[i], b[j]])
                elif len(b) == 1:
                    tmp.faces.new([a[i], a[j], b[0]])
                else:
                    tmp.faces.new([a[i], a[j], b[j], b[i]])
        for r in (rings[0], rings[-1]):
            if len(r) > 1:
                tmp.faces.new(r)
        self._add(tmp)

    # ---- wing, tail, fin, blade: an aerofoil lofted from root to tip -----------------------------
    XS = [0.0, 0.025, 0.09, 0.22, 0.42, 0.68, 1.0]

    def foil(self, root, tip, croot, ctip, t=0.11, steps=4, chord=(0, -1, 0), round_tip=True, tt=None):
        """root, tip: leading-edge points (x, f, z). croot/ctip: chord lengths. t: thickness ratio (tt at the tip).
        chord: direction the chord runs, in (x, f, z); default straight back."""
        tmp = bmesh.new()
        r0, r1 = Vector((root[0], -root[1], root[2])), Vector((tip[0], -tip[1], tip[2]))
        cd = Vector((chord[0], -chord[1], chord[2])).normalized()
        span = (r1 - r0)
        td = span.cross(cd).normalized()
        tt = t if tt is None else tt
        fr = [i / steps for i in range(steps + 1)]
        if round_tip:
            fr.append(1.015)
        rings = []
        for k, u in enumerate(fr):
            le = r0.lerp(r1, min(u, 1.0)) + span.normalized() * (max(0.0, u - 1.0) * span.length)
            c = croot + (ctip - croot) * min(u, 1.0)
            th = t + (tt - t) * min(u, 1.0)
            if u > 1.0:                                   # small rounded cap past the tip
                le = le + cd * (c * 0.18)
                c *= 0.62
                th *= 0.5
            up, dn = [], []
            for x in self.XS:
                yt = 5 * th * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1036 * x ** 4)
                pt = le + cd * (c * x)
                up.append(pt + td * (c * yt))
                dn.append(pt - td * (c * yt))
            ring = [tmp.verts.new(v) for v in up] + [tmp.verts.new(v) for v in reversed(dn[1:-1])]
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                tmp.faces.new([a[i], a[j], b[j], b[i]])
        tmp.faces.new(rings[0])
        tmp.faces.new(rings[-1])
        self._add(tmp)

    def box(self, centre, size, rot=None, bevel=0.0):
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0)
        m = Matrix.Translation((centre[0], -centre[1], centre[2]))
        if rot:
            m = m @ Matrix.Rotation(rot[0], 4, 'X') @ Matrix.Rotation(rot[1], 4, 'Y') @ Matrix.Rotation(rot[2], 4, 'Z')
        m = m @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
        bmesh.ops.transform(tmp, matrix=m, verts=tmp.verts[:])
        if bevel > 0:
            bmesh.ops.bevel(tmp, geom=tmp.edges[:], offset=bevel, segments=1, affect='EDGES')
        self._add(tmp)

    def tube(self, a, b, r, seg=8, r2=None):
        """Straight round bar from a to b (x, f, z)."""
        tmp = bmesh.new()
        pa, pb = Vector((a[0], -a[1], a[2])), Vector((b[0], -b[1], b[2]))
        d = (pb - pa).normalized()
        n1 = d.orthogonal().normalized()
        n2 = d.cross(n1)
        rings = []
        for pt, rr in ((pa, r), (pb, r if r2 is None else r2)):
            rings.append([tmp.verts.new(pt + (n1 * math.cos(2 * math.pi * i / seg) + n2 * math.sin(2 * math.pi * i / seg)) * rr) for i in range(seg)])
        for i in range(seg):
            j = (i + 1) % seg
            tmp.faces.new([rings[0][i], rings[0][j], rings[1][j], rings[1][i]])
        tmp.faces.new(rings[0])
        tmp.faces.new(rings[1])
        self._add(tmp)

    def wheel(self, centre, r, w):
        self.use(TYRE)
        self.tube((centre[0] - w / 2, centre[1], centre[2]), (centre[0] + w / 2, centre[1], centre[2]), r, seg=10)
        self.use(METAL)
        self.tube((centre[0] - w / 2 - 0.01, centre[1], centre[2]), (centre[0] + w / 2 + 0.01, centre[1], centre[2]), r * 0.5, seg=8)
        self.use()

    def nacelle(self, x, f, z, r, length, lip=0.86, tail=0.62):
        """Jet engine pod: painted cowl, dark intake face, burnt exhaust."""
        self.use()
        self.loft([dict(f=f + length * 0.5, x=x, z=z, w=r * lip, h=r * lip), dict(f=f + length * 0.42, x=x, z=z, w=r, h=r),
                   dict(f=f - length * 0.1, x=x, z=z, w=r, h=r), dict(f=f - length * 0.42, x=x, z=z, w=r * tail, h=r * tail)], seg=12, p=2.0)
        self.use(DARK)
        self.loft([dict(f=f + length * 0.505, x=x, z=z, w=r * lip * 0.82, h=r * lip * 0.82), dict(f=f + length * 0.46, x=x, z=z, w=r * lip * 0.8, h=r * lip * 0.8)], seg=12, p=2.0)
        self.use(WHITE)
        self.loft([dict(f=f + length * 0.56, x=x, z=z, w=0, h=0), dict(f=f + length * 0.49, x=x, z=z, w=r * 0.3, h=r * 0.3)], seg=8, p=2.0)
        self.use(BURNT)
        self.loft([dict(f=f - length * 0.40, x=x, z=z, w=r * tail * 0.9, h=r * tail * 0.9), dict(f=f - length * 0.56, x=x, z=z, w=r * tail * 0.55, h=r * tail * 0.55)], seg=12, p=2.0)
        self.use()


# ---------------------------------------------------------------- the three aircraft
def build_drone():
    """Small pusher-propeller attack drone: about 3.2 m span."""
    b = Builder('sand')
    b.loft([dict(f=1.25, w=0, h=0), dict(f=1.17, w=0.07, h=0.07), dict(f=0.95, w=0.14, h=0.13), dict(f=0.5, w=0.19, h=0.17, hb=0.19),
            dict(f=0.0, w=0.2, h=0.18, hb=0.2), dict(f=-0.5, w=0.17, h=0.16), dict(f=-0.85, w=0.13, h=0.13), dict(f=-0.98, w=0.1, h=0.1)], seg=12)
    b.use(DARK)                                                              # nose seeker window and sensor ball
    b.loft([dict(f=1.26, w=0, h=0), dict(f=1.2, w=0.055, h=0.055), dict(f=1.165, w=0.072, h=0.072)], seg=12, p=2.0)
    b.loft([dict(z=-0.31, w=0, h=0), dict(z=-0.27, w=0.07, h=0.07, f=0.62), dict(z=-0.2, w=0.085, h=0.085, f=0.62), dict(z=-0.15, w=0.06, h=0.06, f=0.62)], seg=10, p=2.0, axis='z')
    b.use()
    for s in (-1, 1):
        b.foil((s * 0.15, 0.3, 0.06), (s * 1.5, 0.08, 0.13), 0.52, 0.26, t=0.12, steps=4)
        b.foil((s * 1.5, 0.08, 0.13), (s * 1.6, -0.02, 0.36), 0.26, 0.12, t=0.1, steps=1)          # upturned tip
        b.foil((s * 0.06, -0.62, 0.08), (s * 0.5, -0.82, 0.5), 0.3, 0.17, t=0.1, steps=2)          # V tail
    b.use(METAL)
    b.loft([dict(f=-0.97, w=0.085, h=0.085), dict(f=-1.06, w=0.07, h=0.07), dict(f=-1.12, w=0, h=0)], seg=10, p=2.0)   # spinner
    b.tube((0, 0.15, -0.16), (0, 0.15, -0.3), 0.012, seg=6)                                       # antenna
    # propeller: its own part; the game spins it around the part's local up axis, so it is built flat and stood up by the loader
    b.use(BLADE, part='rotor')
    for a in (0, math.pi):
        d = Vector((math.cos(a), 0, math.sin(a)))
        b.foil((d.x * 0.03, -1.06, d.z * 0.03), (d.x * 0.36, -1.06, d.z * 0.36), 0.075, 0.045, t=0.16, steps=2,
               chord=(-d.z * 0.5, -1, d.x * 0.5))
    return b, dict(rotor=dict(pivot=(0, -1.06, 0), axis='f'), length=2.4, low=0.45)


def build_helo():
    """Two-seat battlefield helicopter, tandem cockpit, stub wings, five-blade rotor: about 15 m long."""
    b = Builder('olive')
    # fuselage: nose to the start of the tail boom
    b.loft([dict(f=6.3, z=-0.55, w=0, h=0), dict(f=6.05, z=-0.5, w=0.28, h=0.26), dict(f=5.3, z=-0.3, w=0.55, h=0.5, hb=0.62),
            dict(f=4.2, z=-0.05, w=0.72, h=0.72, hb=0.9), dict(f=2.9, z=0.15, w=0.8, h=0.95, hb=1.12), dict(f=1.4, z=0.2, w=0.84, h=1.0, hb=1.18),
            dict(f=-0.2, z=0.2, w=0.82, h=0.98, hb=1.12), dict(f=-1.6, z=0.3, w=0.62, h=0.78, hb=0.86), dict(f=-2.6, z=0.42, w=0.42, h=0.52, hb=0.52)], seg=14, p=2.7)
    # tail boom and fin
    b.loft([dict(f=-2.4, z=0.45, w=0.4, h=0.48), dict(f=-5.0, z=0.62, w=0.27, h=0.32), dict(f=-7.6, z=0.8, w=0.17, h=0.22), dict(f=-8.5, z=0.9, w=0.1, h=0.16)], seg=10, p=2.3)
    b.foil((0, -6.9, 0.85), (0, -8.2, 2.75), 1.5, 0.85, t=0.1, steps=3)                           # fin, swept back
    for s in (-1, 1):
        b.foil((s * 0.15, -6.7, 0.78), (s * 1.55, -6.95, 0.78), 0.8, 0.55, t=0.1, steps=2)          # tailplane
        b.foil((s * 0.7, 1.75, -0.28), (s * 2.5, 1.55, -0.42), 1.25, 0.95, t=0.13, steps=3)         # stub wing
    # engines on the shoulders, with intakes and exhausts
    for s in (-1, 1):
        b.use()
        b.loft([dict(f=2.15, x=s * 0.78, z=1.0, w=0.3, h=0.32), dict(f=1.7, x=s * 0.8, z=1.02, w=0.4, h=0.42), dict(f=-0.6, x=s * 0.8, z=1.02, w=0.4, h=0.42),
                dict(f=-1.45, x=s * 0.74, z=0.98, w=0.3, h=0.32)], seg=10, p=2.6)
        b.use(DARK)
        b.loft([dict(f=2.2, x=s * 0.78, z=1.0, w=0.24, h=0.26), dict(f=2.1, x=s * 0.78, z=1.0, w=0.25, h=0.27)], seg=10, p=2.6)
        b.use(BURNT)
        b.loft([dict(f=-1.35, x=s * 0.76, z=0.98, w=0.27, h=0.29), dict(f=-1.8, x=s * 0.9, z=1.02, w=0.2, h=0.22)], seg=10, p=2.2)
    # rotor pylon between the engines
    b.use()
    b.loft([dict(f=1.9, z=1.05, w=0.3, h=0.2), dict(f=1.0, z=1.25, w=0.42, h=0.34), dict(f=-0.6, z=1.25, w=0.4, h=0.32), dict(f=-1.9, z=1.0, w=0.2, h=0.18)], seg=10, p=2.4)
    b.use(METAL)
    b.loft([dict(z=1.4, w=0.13, h=0.13, f=0.4), dict(z=2.02, w=0.1, h=0.1, f=0.4)], seg=8, p=2.0, axis='z')      # mast
    # stepped tandem canopy (glass) and its frame
    b.use(GLASS, part='glass')
    b.loft([dict(f=5.35, z=0.12, w=0.1, h=0.05), dict(f=4.85, z=0.42, w=0.42, h=0.3, hb=0.2), dict(f=4.1, z=0.72, w=0.52, h=0.4, hb=0.3),
            dict(f=3.55, z=0.86, w=0.5, h=0.3, hb=0.3)], seg=10, p=2.2)
    b.loft([dict(f=3.75, z=1.0, w=0.3, h=0.2, hb=0.2), dict(f=3.3, z=1.3, w=0.52, h=0.36, hb=0.3), dict(f=2.5, z=1.42, w=0.55, h=0.38, hb=0.3),
            dict(f=1.95, z=1.3, w=0.42, h=0.22, hb=0.3)], seg=10, p=2.2)
    b.use(part='body')
    # chin gun turret and barrel
    b.use(DARK)
    b.loft([dict(z=-1.42, w=0, h=0, f=4.5), dict(z=-1.3, w=0.26, h=0.3, f=4.5), dict(z=-1.02, w=0.3, h=0.34, f=4.5), dict(z=-0.9, w=0.22, h=0.26, f=4.5)], seg=10, p=2.0, axis='z')
    b.tube((0, 4.6, -1.18), (0, 6.2, -1.22), 0.055, seg=8)
    b.tube((0, 5.9, -1.21), (0, 6.3, -1.225), 0.085, seg=8)
    # nose sensor turret
    b.loft([dict(f=6.32, z=-0.55, w=0, h=0), dict(f=6.22, z=-0.55, w=0.19, h=0.19), dict(f=6.02, z=-0.53, w=0.26, h=0.25)], seg=10, p=2.0)
    # stores: rocket pods inboard, missile rails at the tips
    for s in (-1, 1):
        b.use(METAL)
        b.loft([dict(f=2.2, x=s * 1.35, z=-0.72, w=0, h=0), dict(f=2.0, x=s * 1.35, z=-0.72, w=0.21, h=0.21), dict(f=0.6, x=s * 1.35, z=-0.72, w=0.21, h=0.21),
                dict(f=0.35, x=s * 1.35, z=-0.72, w=0.12, h=0.12)], seg=10, p=2.0)
        b.box((s * 1.35, 1.2, -0.5), (0.08, 0.7, 0.2))
        b.use(WHITE)
        for dx in (-0.16, 0.16):
            b.loft([dict(f=2.05, x=s * 2.2 + dx, z=-0.72, w=0, h=0), dict(f=1.85, x=s * 2.2 + dx, z=-0.72, w=0.075, h=0.075),
                    dict(f=0.5, x=s * 2.2 + dx, z=-0.72, w=0.075, h=0.075)], seg=8, p=2.0)
        b.use(METAL)
        b.box((s * 2.2, 1.2, -0.56), (0.5, 0.9, 0.07))
        b.box((s * 2.2, 1.2, -0.48), (0.08, 0.6, 0.14))
    # fixed landing gear: two main legs and a tail wheel
    for s in (-1, 1):
        b.use(METAL)
        b.tube((s * 0.7, 2.2, -0.75), (s * 1.12, 2.35, -1.55), 0.07, seg=6)
        b.tube((s * 0.72, 1.4, -0.7), (s * 1.12, 2.3, -1.5), 0.045, seg=6)
        b.wheel((s * 1.2, 2.35, -1.6), 0.33, 0.2)
    b.use(METAL)
    b.tube((0, -7.5, 0.6), (0, -7.8, 0.05), 0.05, seg=6)
    b.wheel((0, -7.82, -0.05), 0.2, 0.12)
    # tail rotor: four blades on the right side of the fin
    b.use(METAL)
    b.tube((0.05, -7.85, 2.05), (0.34, -7.85, 2.05), 0.07, seg=8)
    b.use(BLADE)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = (math.cos(a), math.sin(a))
        b.foil((0.3, -7.85 + d[0] * 0.08 + 0.07, 2.05 + d[1] * 0.08), (0.3, -7.85 + d[0] * 1.05 + 0.07, 2.05 + d[1] * 1.05), 0.2, 0.16, t=0.12, steps=1,
               chord=(0, -d[1], d[0]), round_tip=False)
    # main rotor: hub and five blades, its own spinning part (pivot on the mast top)
    b.use(METAL, part='rotor')
    b.loft([dict(z=1.98, w=0.3, h=0.3, f=0.4), dict(z=2.1, w=0.34, h=0.34, f=0.4), dict(z=2.22, w=0.2, h=0.2, f=0.4), dict(z=2.3, w=0, h=0, f=0.4)], seg=10, p=2.0, axis='z')
    for k in range(5):
        a = k * 2 * math.pi / 5
        d = Vector((math.cos(a), math.sin(a)))
        cd = (d.y, -d.x, 0)                                                                    # chord at right angles to the blade
        b.use(METAL, part='rotor')
        b.tube((d.x * 0.2, 0.4 + d.y * 0.2, 2.1), (d.x * 0.9, 0.4 + d.y * 0.9, 2.1), 0.06, seg=6)
        b.use(BLADE, part='rotor')
        le = lambda r, c: (d.x * r - cd[0] * c * 0.3, 0.4 + d.y * r - cd[1] * c * 0.3, 2.1 - r * 0.012)
        b.foil(le(0.85, 0.42), le(6.7, 0.42), 0.42, 0.42, t=0.1, steps=3, chord=cd, round_tip=False)
        b.use(TIP, part='rotor')
        b.foil(le(6.7, 0.42), le(7.15, 0.42), 0.42, 0.3, t=0.1, steps=1, chord=cd)
    return b, dict(rotor=dict(pivot=(0, 0.4, 2.1), axis='z'), length=15.0, low=0.4)


def build_transport():
    """Four-engine high-wing military airlifter with a T-tail: about 39 m span, 35 m long."""
    b = Builder('grey')
    b.loft([dict(f=17.6, z=-0.5, w=0, h=0), dict(f=17.2, z=-0.45, w=0.62, h=0.55), dict(f=16.2, z=-0.25, w=1.3, h=1.15, hb=1.2),
            dict(f=14.6, z=0.05, w=1.95, h=1.85, hb=1.8), dict(f=12.4, z=0.2, w=2.3, h=2.25, hb=2.2), dict(f=9.0, z=0.2, w=2.4, h=2.35, hb=2.3),
            dict(f=-3.0, z=0.2, w=2.4, h=2.35, hb=2.3), dict(f=-7.0, z=0.5, w=2.25, h=2.1, hb=1.85), dict(f=-11.0, z=1.15, w=1.7, h=1.55, hb=1.0),
            dict(f=-14.5, z=1.85, w=1.0, h=1.0, hb=0.45), dict(f=-17.0, z=2.3, w=0.4, h=0.5, hb=0.2), dict(f=-17.7, z=2.4, w=0, h=0)], seg=16, p=2.3)
    b.use(DARK)                                                               # radome
    b.loft([dict(f=17.62, z=-0.5, w=0, h=0), dict(f=17.25, z=-0.455, w=0.6, h=0.53), dict(f=16.75, z=-0.36, w=0.98, h=0.86, hb=0.9)], seg=16, p=2.3)
    # flight-deck glazing: a dark band wrapped round the nose
    b.use(GLASS, part='glass')
    b.loft([dict(f=15.95, z=0.78, w=1.2, h=0.2, hb=0.12), dict(f=15.3, z=1.12, w=1.58, h=0.36, hb=0.2), dict(f=14.55, z=1.42, w=1.72, h=0.3, hb=0.2),
            dict(f=14.2, z=1.5, w=1.6, h=0.16, hb=0.2)], seg=12, p=3.2)
    b.use(part='body')
    # wing: high, swept, with a centre fairing over the fuselage
    b.loft([dict(f=8.2, z=2.45, w=1.2, h=0.25, hb=0.3), dict(f=6.0, z=2.6, w=2.1, h=0.62, hb=0.4), dict(f=0.0, z=2.6, w=2.15, h=0.62, hb=0.4),
            dict(f=-3.2, z=2.45, w=1.3, h=0.25, hb=0.3)], seg=12, p=3.0)
    for s in (-1, 1):
        b.foil((s * 1.6, 6.6, 2.75), (s * 9.5, 3.4, 2.35), 7.2, 4.6, t=0.13, steps=4, round_tip=False)
        b.foil((s * 9.5, 3.4, 2.35), (s * 19.3, -0.6, 1.85), 4.6, 2.1, t=0.11, steps=5, tt=0.09)
        b.foil((s * 19.3, -0.6, 1.85), (s * 19.7, -1.7, 3.1), 2.1, 0.9, t=0.08, steps=2)          # winglet
        for x, f, z in ((6.2, 4.6, 0.55), (12.4, 2.2, 0.35)):                                     # engines on pylons
            b.use()
            b.foil((s * x, f + 2.2, z + 0.75), (s * x, f - 0.3, z + 1.95), 3.0, 3.4, t=0.07, steps=1, round_tip=False)
            b.nacelle(s * x, f + 1.2, z, 0.95, 4.6)
        # main landing gear fairings along the lower fuselage
        b.use()
        b.loft([dict(f=4.6, x=s * 2.25, z=-1.55, w=0, h=0), dict(f=3.4, x=s * 2.4, z=-1.6, w=0.62, h=0.7), dict(f=-1.2, x=s * 2.45, z=-1.6, w=0.72, h=0.8),
                dict(f=-4.2, x=s * 2.35, z=-1.5, w=0.5, h=0.6), dict(f=-5.6, x=s * 2.2, z=-1.4, w=0, h=0)], seg=10, p=2.4)
    # T-tail
    fin0, fin1, c0, c1 = Vector((0, -10.6, 2.5)), Vector((0, -15.4, 9.3)), 6.6, 3.9
    for u0, u1, paint in ((0.0, 0.62, None), (0.62, 0.78, RED), (0.78, 1.0, None)):               # fin with a red band
        b.use(paint)
        b.foil(tuple(fin0.lerp(fin1, u0)), tuple(fin0.lerp(fin1, u1)), c0 + (c1 - c0) * u0, c0 + (c1 - c0) * u1, t=0.11, steps=2, round_tip=False)
    b.use()
    b.loft([dict(f=-14.3, z=9.35, w=0, h=0), dict(f=-15.2, z=9.35, w=0.34, h=0.3), dict(f=-18.4, z=9.35, w=0.36, h=0.32), dict(f=-19.9, z=9.35, w=0, h=0)], seg=10, p=2.2)
    for s in (-1, 1):
        b.foil((s * 0.2, -15.5, 9.35), (s * 6.6, -17.9, 9.45), 3.9, 1.8, t=0.1, steps=3)
    b.use(DARK)
    for s in (-1, 1):                                                         # cabin door outlines read as dark panels
        b.box((s * 2.36, 11.2, 0.1), (0.12, 0.95, 1.7))
    b.use()
    return b, dict(rotor=None, length=35.0, low=0.4)


# ---------------------------------------------------------------- paint, bake, export
def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def camo(scheme, co, n):
    s = SCHEMES[scheme]
    v = noise.noise(Vector((co.x, co.y, co.z * 1.7)) * s['scale'] + Vector((7.3, 1.9, 4.2)))
    v2 = noise.noise(Vector((co.x, co.y, co.z)) * s['scale'] * 2.3 + Vector((31.0, 17.0, 5.0)))
    c = mix(s['top'][0], s['top'][1], smooth(0.02, 0.12, v))
    c = mix(c, s['top'][2], smooth(0.12, 0.22, v2 - 0.4 * v))
    return mix(c, s['belly'], smooth(0.25, 0.7, -n.z))


def make_object(name, b):
    """bmesh -> Blender object with a painted corner colour attribute."""
    bm = b.bm
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    col = bm.loops.layers.color.new('paint')
    for fc in bm.faces:
        paint = b.zones[fc[b.zone]]
        for lp in fc.loops:
            c = camo(paint, lp.vert.co, lp.vert.normal if fc.smooth else fc.normal) if isinstance(paint, str) else paint
            lp[col] = (c[0], c[1], c[2], 1.0)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.set_sharp_from_angle(angle=math.radians(38))
    return ob


def bake_ao(ob):
    """Cycles ambient occlusion into a corner colour attribute 'ao'."""
    me = ob.data
    ao = me.color_attributes.new('ao', 'BYTE_COLOR', 'CORNER')
    me.color_attributes.active_color = ao
    mat = bpy.data.materials.new('bake')
    me.materials.append(mat)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = AO_SAMPLES
    sc.render.bake.target = 'VERTEX_COLORS'
    for o in bpy.context.scene.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='AO')


def decimated(ob, ratio):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.duplicate()
    lo = bpy.context.view_layer.objects.active
    m = lo.modifiers.new('dec', 'DECIMATE')
    m.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='dec')
    lo.data.set_sharp_from_angle(angle=math.radians(45))
    return lo


def b64(fmt_bytes):
    return base64.b64encode(fmt_bytes).decode('ascii')


def export(ob, b, meta):
    """Split into parts, weld equal corners, quantise. Returns a JSON-able dict."""
    import numpy as np
    me = ob.data
    me.calc_loop_triangles()
    paint, ao = me.color_attributes['paint'], me.color_attributes['ao']
    partattr = me.attributes['part']
    normals = me.corner_normals
    pivot = Vector((0, 0, 0))
    out = {}
    ext = max(max(abs(c) for c in v.co) for v in me.vertices) * 1.001
    for pi, pname in enumerate(b.parts):
        key, verts, idx = {}, [], []
        piv = Vector(meta['rotor']['pivot']) if (pname == 'rotor' and meta.get('rotor')) else pivot
        pv = Vector((piv[0], -piv[1], piv[2]))                    # pivot in Blender axes
        for tri in me.loop_triangles:
            if partattr.data[tri.polygon_index].value != pi:
                continue
            for li in tri.loops:
                co = me.vertices[me.loops[li].vertex_index].co - pv
                n = normals[li].vector
                pc, a = paint.data[li].color, ao.data[li].color[0]
                shade = 0.42 + 0.58 * min(1.0, a * 1.15)
                c = [max(0, min(255, round(255 * (pc[i] ** (1 / 2.2)) * shade))) for i in range(3)]
                # game axes: x, y(up) = z, z(forward) = -y
                p = (round(co.x / ext * 32767), round(co.z / ext * 32767), round(-co.y / ext * 32767))
                q = (round(n.x * 127), round(n.z * 127), round(-n.y * 127))
                k = (p, q, tuple(c))
                i = key.get(k)
                if i is None:
                    i = key[k] = len(verts)
                    verts.append(k)
                idx.append(i)
        if not verts:
            continue
        if len(verts) > 65535:
            raise SystemExit(ob.name + '/' + pname + ': too many vertices for 16-bit indices')
        out[pname] = dict(
            n=len(verts), t=len(idx) // 3,
            p=b64(np.array([v[0] for v in verts], dtype='<i2').tobytes()),
            q=b64(np.array([v[1] for v in verts], dtype='i1').tobytes()),
            c=b64(np.array([v[2] for v in verts], dtype='u1').tobytes()),
            i=b64(np.array(idx, dtype='<u2').tobytes()))
        if pname == 'rotor' and meta.get('rotor'):
            out[pname]['pivot'] = [round(piv[0], 4), round(piv[2], 4), round(piv[1], 4)]      # game axes (x, up, forward)
            out[pname]['axis'] = meta['rotor']['axis']
    return dict(ext=round(ext, 5), parts=out)


def main():
    import json
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data, report = {}, []
    for kind, fn in (('drone', build_drone), ('helo_attack', build_helo), ('transport', build_transport)):
        b, meta = fn()
        ob = make_object(kind, b)
        bake_ao(ob)
        lo = decimated(ob, meta['low'])
        hi_d, lo_d = export(ob, b, meta), export(lo, b, meta)
        data[kind] = dict(length=meta['length'], high=hi_d, low=lo_d)
        aos = [c.color[0] for c in ob.data.color_attributes['ao'].data]
        report.append('%s: ambient occlusion min %.2f, mean %.2f' % (kind, min(aos), sum(aos) / len(aos)))
        tri = lambda d: sum(p['t'] for p in d['parts'].values())
        report.append('%s: high %d tris, low %d tris' % (kind, tri(hi_d), tri(lo_d)))
    js = ('/* =====================================================================\n'
          '   RED SKIES — models_blender_data.js   GENERATED by tools/blender/build_models.py. Do not edit by hand.\n'
          '   Blender-built aircraft (drone, helo_attack, transport): quantised positions (p, int16 × ext / 32767),\n'
          '   normals (q, int8 / 127), vertex colours with baked ambient occlusion (c, uint8 sRGB) and indices (i, uint16),\n'
          '   all base64. Game axes: +Y up, +Z forward, metres. Read by models_blender.js.\n'
          '   ===================================================================== */\n'
          '(function () {\n  window.RS = window.RS || {};\n  window.RS.blenderData = ' + json.dumps(data, separators=(',', ':')) + ';\n})();\n')
    with open(OUT, 'w') as fh:
        fh.write(js)
    print('\n'.join(report))
    print('wrote %s (%.0f KB)' % (os.path.relpath(OUT, ROOT), len(js) / 1024))


if __name__ == '__main__':
    main()
