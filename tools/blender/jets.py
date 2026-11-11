"""RED SKIES: Blender jets (V1.9.0.0), used by build_models.py.

The four jets the game flies: the hostile Kestrel (twin-engine fighter), Wasp (light single-engine fighter) and
Shade (faceted stealth jet), and the friendly Gyrfalcon. Same layouts, sizes, colours and markings as the
procedural models in src/models_jets.js and src/jet_friend.js (those stay as the fallback and for the bomber and
the AWACS), rebuilt as smooth lofted shapes with ambient occlusion baked in Blender.

Camouflage is not painted into the vertices here: faces painted SHADER carry a flag, and the game draws the
camouflage and panel lines per pixel (src/models_blender.js), so it stays crisp on the tracker camera.

Axes as in build_models.py: x = across (+x is the aircraft's left), f = forward (nose), z = up, metres,
origin at the aircraft's centre.
Every design is fictional.
"""
import math

from build_models import Builder, SHADER

def hexc(h, k=1.0):
    """'#rrggbb' (sRGB, as the game's other models use them) -> the linear colour the exporter expects."""
    h = h.lstrip('#')
    return tuple(((int(h[i:i + 2], 16) / 255.0) * k) ** 2.2 for i in (0, 2, 4))


# ---------------------------------------------------------------- colours (match the procedural models)
RADOME = hexc('#5b6066')
NOZ = hexc('#77716a')
PETAL = hexc('#5c5852')
BURNT = hexc('#3e3833')
DUCT = hexc('#1d2023')
DARK = hexc('#24272a')
TUB = hexc('#1a1c1e')
HELMET = hexc('#8a8e86')
GLASS_C = hexc('#3d5566')
GLASS_G = hexc('#8a7336')
GLASS_F = hexc('#5f8aa8')
RED = hexc('#b02a1f')
WHITE = hexc('#dcdbd2')
BLACK = hexc('#141414')
LVA = hexc('#2c3036')
LVB = hexc('#5c626a')
HOT = hexc('#c2501a')
FLAME_O = hexc('#ff6a18', 0.5)
FLAME_I = hexc('#fff1c8', 0.8)
# hostile stores (models_weapons.js)
W_BODY = hexc('#d8d5ca')
W_SEEK = hexc('#2b3f4d')
W_DOME = hexc('#2a2c2e')
W_YEL = hexc('#d4ad1e')
W_BRN = hexc('#6e4726')
W_FIN = hexc('#c6cbc4')
W_RACK = hexc('#5c6258')
# friendly airframe trim and stores (jet_friend.js, models_weapons_east.js)
F_RADOME = hexc('#7d8b96')
F_POD = hexc('#8b969e')
F_DARK = hexc('#15181b')
E_BODY = hexc('#e4e6e1')
E_FIN = hexc('#c8ccc6')
E_SEEK = hexc('#26282a')
E_RED = hexc('#a32f28')
E_YEL = hexc('#cfa41d')
E_OLIVE = hexc('#5c6646')
E_OLIVE2 = hexc('#444c35')
C_BLUE = hexc('#1f4478')
C_RING = hexc('#f2f2ef')
C_STAR = hexc('#e5b44a')


# ---------------------------------------------------------------- small parts
def rev(b, x, z, prof, seg=10):
    """Body of revolution along f. prof: [(f, r, paint for the band that starts here)], nose first; r 0 = a point."""
    rings, paints = [], []
    for f, r, p in prof:
        if r <= 1e-5:
            rings.append([(x, f, z)])
        else:
            rings.append([(x + r * math.cos(2 * math.pi * i / seg), f, z + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)])
        paints.append(p)
    b.rings(rings, paints[:-1])


def plate(b, root_le, tip_le, croot, ctip, thick, back=(0, -1, 0)):
    """A thin trapezoid plate (missile fins, blade antennas): 12 triangles. Thickness across the span/chord plane."""
    sx, sf, sz = tip_le[0] - root_le[0], tip_le[1] - root_le[1], tip_le[2] - root_le[2]
    cx, cf, cz = back
    nx, nf, nz = sf * cz - sz * cf, sz * cx - sx * cz, sx * cf - sf * cx
    L = math.sqrt(nx * nx + nf * nf + nz * nz) or 1.0
    nx, nf, nz = nx / L * thick / 2, nf / L * thick / 2, nz / L * thick / 2

    def ring(le, c):
        te = (le[0] + cx * c, le[1] + cf * c, le[2] + cz * c)
        return [(le[0] + nx, le[1] + nf, le[2] + nz), (te[0] + nx, te[1] + nf, te[2] + nz),
                (te[0] - nx, te[1] - nf, te[2] - nz), (le[0] - nx, le[1] - nf, le[2] - nz)]
    b.rings([ring(root_le, croot), ring(tip_le, ctip)])


def cross_fins(b, x, f_le, z, r, span, croot, ctip, sweep, paint, n=4, a0=math.pi / 4):
    """Fins round a body (X layout), leading edge at f_le: single quads (the game draws both faces)."""
    b.use(paint)
    for k in range(n):
        a = a0 + k * 2 * math.pi / n
        c, s = math.cos(a), math.sin(a)
        r0, r1 = (x + c * r * 0.85, f_le, z + s * r * 0.85), (x + c * (r + span), f_le - sweep, z + s * (r + span))
        b.rings([[r0, (r0[0], r0[1] - croot, r0[2])], [r1, (r1[0], r1[1] - ctip, r1[2])]], cap=(False, False))


def missile(b, x, f, z, L, r, body, nose, bands, fin, span, wings=None, canards=None, nl=None, seg=6, nose_round=False):
    """A missile centred at (x, f, z), nose forward. bands: [(fraction from the nose, paint, width)].
    wings / canards: (fraction from the nose of the leading edge, span, root chord, tip chord, sweep)."""
    nl = nl or r * 4.6
    top = f + L / 2
    prof = [(top, 0, nose)]
    if nose_round:
        prof += [(top - nl * 0.08, r * 0.55, nose), (top - nl * 0.35, r * 0.9, nose)]
    else:
        prof += [(top - nl * 0.2, r * 0.42, nose), (top - nl * 0.55, r * 0.8, nose)]
    prof.append((top - nl, r, body))
    for fr, p, w in sorted(bands):
        fb = top - fr * L
        prof += [(fb + w / 2, r * 1.01, p), (fb - w / 2, r * 1.01, body)]
    prof += [(f - L / 2 + 0.03, r * 0.97, DARK), (f - L / 2, r * 0.8, DARK)]
    b.use(body)
    rev(b, x, z, prof, seg)
    cross_fins(b, x, f - L / 2 + 0.05 + span * 1.3, z, r, span, span * 1.3, span * 0.6, span * 0.65, fin)
    for spec in (wings, canards):
        if spec:
            fr, sp, cr, ct, sw = spec
            cross_fins(b, x, top - fr * L, z, r, sp, cr, ct, sw, fin)
    b.use()


def pylon(b, x, f, z_top, length, h, paint=SHADER):
    """Wing or belly pylon from z_top (inside the skin) down h metres; f is its centre."""
    b.use(paint)
    b.foil((x, f + length / 2, z_top + 0.06), (x, f + length / 2 - 0.12, z_top - h), length, length * 0.88, t=0.1, steps=1, round_tip=False)
    b.use()


def rack(b, x, f, z, length, store):
    """Twin-store rack (grey beam) with two stores below it, side by side. store(x, z) draws one."""
    b.use(W_RACK)
    b.loft([dict(f=f + length * 0.48, x=x, z=z, w=0.13, h=0.05, hb=0.08), dict(f=f + length * 0.4, x=x, z=z, w=0.2, h=0.07, hb=0.09),
            dict(f=f - length * 0.42, x=x, z=z, w=0.2, h=0.07, hb=0.09), dict(f=f - length * 0.5, x=x, z=z, w=0.12, h=0.05, hb=0.06)], seg=8, p=4.0)
    for dx in (-0.155, 0.155):
        b.box((x + dx, f + 0.3, z - 0.08), (0.03, 0.18, 0.06))
        b.box((x + dx, f - 0.35, z - 0.08), (0.03, 0.18, 0.06))
        store(x + dx, z - 0.2)
    b.use()


def tank(b, x, f, z, L, r, paint=SHADER):
    b.use(paint)
    rev(b, x, z, [(f + L / 2, 0, paint), (f + L / 2 - L * 0.08, r * 0.55, paint), (f + L / 2 - L * 0.25, r * 0.95, paint), (f + L * 0.05, r, paint),
                  (f - L * 0.25, r * 0.92, paint), (f - L / 2 + L * 0.07, r * 0.45, paint), (f - L / 2, 0, paint)], seg=10)
    cross_fins(b, x, f - L / 2 + L * 0.2, z, r * 0.5, r * 0.85, L * 0.14, L * 0.08, L * 0.05, paint, n=3, a0=math.pi / 2)
    b.use()


def canopy(b, f, z, half, w, h, paint, frames=(), seg=12, sink=0.16, faceted=False):
    """Glass bubble (own part 'glass') centred at f, base at z; frames: f positions of the dark bows."""
    b.use(paint, part='glass')
    st = []
    for deg in (0, 14, 32, 55, 80, 100, 125, 150, 168, 180):
        t = math.radians(deg)
        st.append(dict(f=f + half * math.cos(t), z=z, w=w * math.sin(t), h=h * math.sin(t) ** 0.85, hb=sink * math.sin(t), p=2.0 if not faceted else 2.0))
    st[0].update(w=0, h=0, hb=0)
    st[-1].update(w=0, h=0, hb=0)
    b.loft(st, seg=8 if faceted else seg, p=2.0)
    b.use(DARK, part='body')
    for fb in frames:
        k = math.sqrt(max(0.0, 1 - ((fb - f) / half) ** 2))
        b.loft([dict(f=fb + 0.035, z=z, w=w * k * 1.03, h=h * k ** 0.85 * 1.03, hb=sink * k), dict(f=fb - 0.035, z=z, w=w * k * 1.03, h=h * k ** 0.85 * 1.03, hb=sink * k)],
               seg=seg, p=2.0)
    b.use()


def cockpit(b, f, z_deck, width, length, hz):
    """Dark cockpit opening, seat headbox and helmet, seen through the glass. hz: helmet centre height."""
    b.use(TUB)
    b.box((0, f, z_deck), (width, length, 0.14), bevel=0.03)
    b.box((0, f - 0.55, hz - 0.1), (0.36, 0.14, 0.46), rot=(-0.28, 0, 0))
    b.use(HELMET)
    b.loft([dict(f=f - 0.32, z=hz, w=0, h=0), dict(f=f - 0.38, z=hz, w=0.1, h=0.1), dict(f=f - 0.5, z=hz, w=0.14, h=0.14),
            dict(f=f - 0.62, z=hz, w=0.12, h=0.12), dict(f=f - 0.68, z=hz, w=0, h=0)], seg=10, p=2.0)
    b.use()


def nozzle(b, x, f, z, r, length, petals=True):
    """Round afterburning nozzle: metal outside, burnt inside, glowing face deep inside (part 'hot')."""
    st = [dict(f=f + length * 0.3, x=x, z=z, w=r * 1.02, h=r * 1.02, paint=NOZ), dict(f=f - length * 0.35, x=x, z=z, w=r, h=r),
          dict(f=f - length * 0.5, x=x, z=z, w=r * 0.98, h=r * 0.98, paint=PETAL if petals else NOZ, c=1),
          dict(f=f - length, x=x, z=z, w=r * 0.88, h=r * 0.88, c=1, paint=BURNT), dict(f=f - length + 0.02, x=x, z=z, w=r * 0.8, h=r * 0.8, c=1),
          dict(f=f - length * 0.45, x=x, z=z, w=r * 0.76, h=r * 0.76, c=1)]
    b.sloft(st, step=0.5, seg=12, p=2.0)
    b.use(HOT, part='hot')
    b.loft([dict(f=f - length * 0.47, x=x, z=z, w=r * 0.72, h=r * 0.72), dict(f=f - length * 0.49, x=x, z=z, w=r * 0.72, h=r * 0.72)], seg=10, p=2.0)
    b.use(BURNT, part='body')
    b.loft([dict(f=f - length * 0.44, x=x, z=z, w=0, h=0), dict(f=f - length * 0.5, x=x, z=z, w=r * 0.25, h=r * 0.25), dict(f=f - length * 0.52, x=x, z=z, w=0, h=0)], seg=8, p=2.0)
    b.use()
    return (x, f - length, z)


def flame(b, x, f, z, r):
    """Cruise-power exhaust glow (part 'flame', drawn additive): an outer and an inner cone."""
    b.use(FLAME_O, part='flame')
    rev(b, x, z, [(f + 0.05, r * 0.9, FLAME_O), (f - r * 1.2, r * 0.75, FLAME_O), (f - r * 3.6, 0, FLAME_O)], seg=8)
    b.use(FLAME_I, part='flame')
    rev(b, x, z, [(f + 0.04, r * 0.55, FLAME_I), (f - r * 0.8, r * 0.45, FLAME_I), (f - r * 2.1, 0, FLAME_I)], seg=6)
    b.use(part='body')


def intake(b, st, deep, lip_paint=SHADER):
    """A cup-shaped intake: dark duct going in from the lip, then the outer skin going back.
    st: the outer stations, front first; deep: how far the duct goes in (metres)."""
    s0 = dict(st[0])
    inner = dict(s0, w=s0['w'] * 0.8, h=s0['h'] * 0.8, hb=s0.get('hb', s0['h']) * 0.8)
    rings = [dict(inner, f=s0['f'] - deep, paint=DUCT), dict(inner, f=s0['f'] - 0.03, c=1),
             dict(s0, f=s0['f'] + 0.02, w=s0['w'] * 0.91, h=s0['h'] * 0.91, hb=s0.get('hb', s0['h']) * 0.91, c=1, paint=lip_paint),
             dict(s0, c=1, paint=SHADER)] + [dict(s) for s in st[1:]]
    b.sloft(rings, step=0.8, seg=12)


def roundel_hostile(r, low=False):
    """Red disc, white ring, dark forward-pointing triangle (low-visibility greys on the Shade)."""
    a, w, k = (LVA, LVB, LVB) if low else (RED, WHITE, BLACK)
    q = r * 0.42
    tri = [(-q * 0.87, -q * 0.5), (q * 0.87, -q * 0.5), (0, q)]
    return [(a, Builder.circle(r)), (w, Builder.circle(r * 0.66, r0=r * 0.52)), (k, [tri])]


def roundel_friend(r):
    """Compass: blue disc, white ring, yellow four-point star."""
    star = []
    for i in range(8):
        a = math.pi / 2 + i * math.pi / 4
        rr = r * 0.83 if i % 2 == 0 else r * 0.26
        star.append((rr * math.cos(a), rr * math.sin(a)))
    return [(C_BLUE, Builder.circle(r)), (C_RING, Builder.circle(r * 0.95, r0=r * 0.81)), (C_STAR, [star])]


def flash_hostile(w, h, low=False):
    a, c = (LVA, LVB) if low else (RED, WHITE)
    return [(a, [[(-w / 2, 0), (w / 2, 0), (w / 2, h / 2), (-w / 2, h / 2)]]), (c, [[(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, 0), (-w / 2, 0)]])]


def flash_friend(w, h, mirror=False):
    """Blue panel with a white and a yellow slanted band (jet_friend.js flashTex)."""
    def P(px, py):
        u = (px / 256.0 - 0.5) * w
        return (-u if mirror else u, (0.5 - py / 128.0) * h)

    def poly(pts):
        pp = [P(*q) for q in pts]
        return list(reversed(pp)) if mirror else pp
    return [(C_BLUE, [poly([(0, 0), (0, 128), (256, 128), (256, 0)])]), (C_RING, [poly([(96, 0), (0, 128), (80, 128), (176, 0)])]),
            (C_STAR, [poly([(208, 0), (96, 128), (112, 128), (256, 64), (256, 0)])])]


# seven-segment digits for the bort number: segment boxes in a 1 x 2 cell
SEGS = {'a': (0, 1, 1, 0.2), 'b': (0.8, 0.5, 0.2, 1.0), 'c': (0.8, -0.5, 0.2, 1.0), 'd': (0, -1, 1, 0.2), 'e': (-0.8, -0.5, 0.2, 1.0),
        'f': (-0.8, 0.5, 0.2, 1.0), 'g': (0, 0, 1, 0.2)}
DIGITS = {'1': 'bc', '2': 'abged'}


def number(text, height, mirror=False, grow=0.0):
    s, polys = height / 2.0, []
    for i, ch in enumerate(text):
        cx = (i - (len(text) - 1) / 2.0) * 1.35 * s
        for sg in DIGITS[ch]:
            x, y, w, h = SEGS[sg]
            x0, x1 = cx + (x - w) * s * 0.5 - grow, cx + (x + w) * s * 0.5 + grow
            y0, y1 = (y - h / 2) * s - grow, (y + h / 2) * s + grow
            if mirror:
                x0, x1 = -x1, -x0
            polys.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    return polys


# ---------------------------------------------------------------- hostile stores (strike)
def aam_short(b, x, f, z):
    missile(b, x, f, z, 2.93, 0.064, W_BODY, W_SEEK, [(0.45, W_YEL, 0.06), (0.6, W_BRN, 0.06)], W_FIN, 0.11, canards=(0.12, 0.07, 0.14, 0.08, 0.04), nose_round=True)


def aam_long(b, x, f, z):
    missile(b, x, f, z, 3.7, 0.089, W_BODY, W_DOME, [(0.3, W_YEL, 0.07), (0.45, W_BRN, 0.07)], W_FIN, 0.13, wings=(0.35, 0.09, 0.7, 0.35, 0.3))


def glide_bomb(b, x, z, f=0.0):
    missile(b, x, f, z, 1.8, 0.1, W_BODY, W_BODY, [(0.4, W_YEL, 0.08)], W_FIN, 0.12, nl=0.55, nose_round=True)


def agm_light(b, x, z, f=0.0):
    missile(b, x, f, z, 1.83, 0.089, W_BODY, hexc('#8a6d25'), [(0.32, W_YEL, 0.07), (0.45, W_BRN, 0.06)], W_FIN, 0.11, wings=(0.4, 0.08, 0.5, 0.3, 0.2), nl=0.4, nose_round=True)


# ---------------------------------------------------------------- Kestrel
def build_fighter():
    """Kestrel: twin-engine, twin-tail air-superiority fighter, ~20 m. Strike loadout."""
    b = Builder(SHADER)
    fus = [dict(f=9.75, w=0, h=0, z=0.12, paint=RADOME), dict(f=9.2, w=0.24, h=0.23, hb=0.22, z=0.12), dict(f=8.2, w=0.46, h=0.44, hb=0.4, z=0.12),
           dict(f=7.0, w=0.63, h=0.59, hb=0.53, z=0.12, paint=SHADER), dict(f=5.6, w=0.74, h=0.74, hb=0.62, z=0.14, p=2.2),
           dict(f=4.0, w=0.84, h=0.9, hb=0.66, z=0.14, p=2.4), dict(f=2.4, w=1.35, h=0.8, hb=0.66, z=0.08, p=2.8),
           dict(f=0.5, w=1.95, h=0.66, hb=0.6, z=0.02, p=3.2), dict(f=-3.0, w=2.0, h=0.58, hb=0.58, z=0, p=3.4),
           dict(f=-6.0, w=1.85, h=0.52, hb=0.55, z=0, p=3.4), dict(f=-8.1, w=1.58, h=0.47, hb=0.5, z=0, p=3.2),
           dict(f=-9.1, w=1.45, h=0.44, hb=0.46, z=0, p=3.0)]
    b.sloft(fus, step=0.6, seg=20)
    for s in (-1, 1):
        intake(b, [dict(f=3.9, x=s * 1.28, w=0.46, h=0.52, hb=0.56, z=-0.08, p=5), dict(f=2.8, x=s * 1.3, w=0.5, h=0.55, hb=0.6, z=-0.06, p=5),
                   dict(f=0.0, x=s * 1.3, w=0.52, h=0.55, hb=0.6, z=-0.02, p=5), dict(f=-2.2, x=s * 1.2, w=0.4, h=0.4, hb=0.5, z=0, p=4)], 0.9)
        b.box((s * 0.83, 3.45, -0.08), (0.04, 0.9, 1.05), bevel=0.01)                                         # splitter plate
        b.foil((s * 1.5, 2.3, 0.05), (s * 6.5, -2.3, -0.02), 6.2, 1.5, t=0.05, tt=0.04, steps=3)                 # wing
        b.foil((s * 1.4, -6.4, 0.0), (s * 4.3, -8.7, -0.05), 3.1, 1.3, t=0.05, tt=0.04, steps=3)                # stabilator
        b.foil((s * 1.32, -4.9, 0.44), (s * 1.91, -7.6, 3.33), 3.7, 1.3, t=0.05, tt=0.04, steps=2, round_tip=False)   # fin, canted out
        b.foil((s * 1.05, -5.7, -0.36), (s * 1.24, -6.2, -1.0), 1.5, 0.8, t=0.05, steps=1, round_tip=False)  # ventral fin
        b.use(DARK)
        b.tube((s * 1.915, -7.3, 3.36), (s * 1.915, -8.85, 3.36), 0.07, seg=8)                                  # fin-tip cap
        b.box((s * 6.55, -2.6, -0.02), (0.1, 2.4, 0.12), bevel=0.02)                                             # wing-tip rail
        b.use()
        b.loft([dict(f=-8.2, x=s * 1.55, w=0.2, h=0.2), dict(f=-9.6, x=s * 1.55, w=0.17, h=0.17), dict(f=-10.2, x=s * 1.55, w=0.1, h=0.1)], seg=10, p=2.0)   # tail stinger
        nozzle(b, s * 0.72, -8.95, 0.0, 0.56, 1.0)
        flame(b, s * 0.72, -9.95, 0.0, 0.48)
    canopy(b, 5.3, 0.86, 1.75, 0.5, 0.62, GLASS_C, frames=(6.2, 5.1))
    cockpit(b, 5.25, 0.82, 0.72, 2.3, 1.18)
    b.use(GLASS_C)
    b.loft([dict(f=7.42, x=0.25, z=0.86, w=0, h=0), dict(f=7.35, x=0.25, z=0.86, w=0.1, h=0.1), dict(f=7.2, x=0.25, z=0.86, w=0.1, h=0.1)], seg=8, p=2.0)   # IRST ball
    b.use(NOZ)
    b.tube((0, 9.7, 0.12), (0, 11.0, 0.12), 0.022, seg=6, r2=0.012)                                           # pitot
    b.use(DARK)
    plate(b, (0, 1.75, 0.75), (0, 1.55, 1.05), 0.4, 0.2, 0.03)                                                  # blade antennas
    plate(b, (0, -4.85, 0.5), (0, -5.0, 0.72), 0.3, 0.16, 0.03)
    plate(b, (0, 3.35, -0.6), (0, 3.2, -0.84), 0.3, 0.15, 0.03)
    b.use()
    # markings, laid on the finished airframe before the stores go on
    for s in (-1, 1):
        for d in (1, -1):
            b.decal((s * 5.13, -2.19, 4 * d), (0, 0, -d), roundel_hostile(0.62))
        for side in (1, -1):
            b.decal((s * 1.69 + side * 3, -7.57, 2.23), (-side, 0, 0), flash_hostile(0.8, 1.2), fwd=(0, 0, 1))
    # strike stores (own part, so the game can leave them off)
    b.use(part='stores_strike')
    for s in (-1, 1):
        aam_short(b, s * 6.6, -2.6, -0.17)
        pylon(b, s * 3.2, -0.4, 0.0, 1.8, 0.37)
        rack(b, s * 3.2, -0.5, -0.43, 1.6, lambda x, z: glide_bomb(b, x, z - 0.02, -0.5))
        pylon(b, s * 4.8, -1.6, 0.0, 1.4, 0.33)
        rack(b, s * 4.8, -1.5, -0.39, 1.5, lambda x, z: agm_light(b, x, z, -1.5))
        aam_long(b, s * 1.25, 1.1, -0.77)
        aam_long(b, s * 1.25, -3.4, -0.77)
    pylon(b, 0, -1.2, -0.5, 2.0, 0.36)
    tank(b, 0, -1.0, -1.2, 4.4, 0.36)
    b.use(part='body')
    return b, dict(jet=True, sharp=61, length=19.9, span=13.3, height=5.5, low=0.36, nozzles=[(s * 0.72, -9.95, 0.0) for s in (1, -1)])


# ---------------------------------------------------------------- Wasp
def build_light():
    """Wasp: single-engine light multirole fighter, ~15.6 m. Strike loadout."""
    b = Builder(SHADER)
    fus = [dict(f=7.75, w=0, h=0, z=0.1, paint=RADOME), dict(f=7.2, w=0.2, h=0.2, hb=0.2, z=0.1), dict(f=6.2, w=0.4, h=0.42, hb=0.4, z=0.1),
           dict(f=5.8, w=0.45, h=0.48, hb=0.44, z=0.11, paint=SHADER), dict(f=5.1, w=0.52, h=0.56, hb=0.5, z=0.12),
           dict(f=3.8, w=0.58, h=0.72, hb=0.55, z=0.14, p=2.3), dict(f=2.2, w=0.68, h=0.74, hb=0.6, z=0.12, p=2.6),
           dict(f=0.0, w=0.82, h=0.66, hb=0.62, z=0.05, p=2.8), dict(f=-3.0, w=0.8, h=0.6, hb=0.6, z=0.05, p=2.6),
           dict(f=-5.8, w=0.62, h=0.56, hb=0.56, z=0.05, p=2.3), dict(f=-6.9, w=0.56, h=0.54, hb=0.54, z=0.05, p=2.0)]
    b.sloft(fus, step=0.6, seg=20)
    b.sloft([dict(f=1.9, w=0.3, h=0.35, hb=0.1, z=0.7), dict(f=-2.5, w=0.3, h=0.2, hb=0.1, z=0.62), dict(f=-4.8, w=0.2, h=0.02, hb=0.1, z=0.58)], step=0.9, seg=10)   # spine
    intake(b, [dict(f=3.2, w=0.55, h=0.25, hb=0.45, z=-0.72, p=2.6), dict(f=2.0, w=0.56, h=0.3, hb=0.46, z=-0.68, p=2.6),
               dict(f=-1.5, w=0.5, h=0.3, hb=0.35, z=-0.5, p=2.4), dict(f=-3.0, w=0.4, h=0.2, hb=0.12, z=-0.4, p=2.2)], 0.8)
    for s in (-1, 1):
        b.foil((s * 0.5, 3.6, 0.05), (s * 1.1, 0.6, 0.05), 4.6, 1.6, t=0.03, steps=2, round_tip=False)            # LERX
        b.foil((s * 0.7, 1.0, 0.05), (s * 4.7, -2.3, 0.05), 4.7, 1.45, t=0.045, tt=0.04, steps=3)                # wing
        b.foil((s * 0.6, -4.6, 0.0), (s * 2.9, -6.1, -0.28), 2.6, 1.15, t=0.05, tt=0.04, steps=3)               # stabilator
        b.foil((s * 0.35, -3.7, -0.5), (s * 0.62, -4.1, -0.98), 1.3, 0.7, t=0.05, steps=1, round_tip=False)     # ventral fin
        b.use(DARK)
        b.box((s * 4.75, -2.5, 0.02), (0.1, 2.3, 0.12), bevel=0.02)
        b.use()
    b.foil((0, -3.2, 0.62), (0, -5.7, 3.6), 3.5, 1.3, t=0.05, tt=0.04, steps=2, round_tip=False)                  # fin
    b.loft([dict(f=-5.3, z=1.2, w=0.1, h=0.1), dict(f=-6.0, z=1.2, w=0.13, h=0.13), dict(f=-6.65, z=1.2, w=0.1, h=0.1)], seg=10, p=2.0)   # fin fairing
    b.use(DARK)
    b.tube((0, -5.1, 3.6), (0, -5.95, 3.6), 0.07, seg=8)
    b.use(NOZ)
    b.tube((0, 7.7, 0.1), (0, 8.7, 0.1), 0.018, seg=6, r2=0.01)
    b.use(DARK)
    b.tube((-0.6, 2.4, 0.35), (-0.6, 2.0, 0.35), 0.04, seg=8)
    plate(b, (0, 0.95, -0.7), (0, 0.8, -0.92), 0.35, 0.15, 0.03)
    plate(b, (0, -1.85, -0.55), (0, -1.95, -0.73), 0.3, 0.13, 0.03)
    b.use()
    canopy(b, 3.6, 0.78, 1.8, 0.42, 0.62, GLASS_G, frames=(2.7,))
    cockpit(b, 3.65, 0.82, 0.62, 2.4, 1.1)
    nozzle(b, 0, -6.85, 0.05, 0.52, 0.95)
    flame(b, 0, -7.8, 0.05, 0.44)
    for s in (-1, 1):
        for d in (1, -1):
            b.decal((s * 3.34, -2.33, 4 * d), (0, 0, -d), roundel_hostile(0.46))
        b.decal((s * 3, -5.72, 2.32), (-s, 0, 0), flash_hostile(0.7, 1.0), fwd=(0, 0, 1))
    b.use(part='stores_strike')
    for s in (-1, 1):
        aam_short(b, s * 4.8, -2.5, -0.13)
        pylon(b, s * 2.0, -0.3, 0.02, 1.6, 0.32)
        rack(b, s * 2.0, -0.4, -0.36, 1.6, lambda x, z: glide_bomb(b, x, z - 0.02, -0.4))
        pylon(b, s * 3.4, -1.4, 0.02, 1.3, 0.3)
        rack(b, s * 3.4, -1.3, -0.34, 1.5, lambda x, z: agm_light(b, x, z, -1.3))
    pylon(b, 0, -1.8, -0.82, 1.8, 0.2)
    tank(b, 0, -1.6, -1.3, 3.4, 0.3)
    b.use(part='body')
    return b, dict(jet=True, sharp=61, length=15.6, span=9.8, height=5.0, low=0.36, nozzles=[(0, -7.8, 0.05)])


# ---------------------------------------------------------------- Shade
def chine(s):
    w, t, bb, x, z, f = s['w'], s['h'], s['hb'], s['x'], s['z'], s['f']
    w = max(w, 0.003)
    return [(x + p[0], f, z + p[1]) for p in ((w, 0), (0.55 * w, 0.78 * t), (0.18 * w, t), (-0.18 * w, t), (-0.55 * w, 0.78 * t),
                                                (-w, 0), (-0.5 * w, -bb), (0.5 * w, -bb))]


def build_stealth():
    """Shade: faceted low-observable strike jet, ~17 m, internal weapons (no stores)."""
    b = Builder(SHADER)
    fus = [dict(f=8.45, w=0, h=0, hb=0, z=0.05), dict(f=7.2, w=0.55, h=0.34, hb=0.28, z=0.05), dict(f=5.4, w=1.05, h=0.7, hb=0.45, z=0.05),
           dict(f=3.0, w=1.6, h=0.82, hb=0.55, z=0.05), dict(f=0.5, w=2.35, h=0.72, hb=0.6, z=0.02), dict(f=-3.0, w=2.4, h=0.62, hb=0.58, z=0),
           dict(f=-6.4, w=2.1, h=0.5, hb=0.5, z=0), dict(f=-7.9, w=1.8, h=0.42, hb=0.44, z=0)]
    b.sloft(fus, step=0.55, ring=chine, flat=True)
    for s in (-1, 1):
        def ring(f, k, inset=1.0):
            pts = [(1.4 * k + 0.2, 0.05), (1.9, 0.1 + 0.5 * k), (1.9, -0.5 * k), (1.3, -0.45 * k - 0.05), (1.2, 0.25 * k)]
            cx, cz = sum(p[0] for p in pts) / 5, sum(p[1] for p in pts) / 5
            return [(s * (cx + (p[0] - cx) * inset), f, cz + (p[1] - cz) * inset) for p in pts]
        b.rings([ring(3.0, 0.92, 0.8), ring(3.57, 0.92, 0.8), ring(3.62, 1.0, 0.92), ring(3.6, 1.0), ring(2.4, 1.05), ring(0.2, 1.0), ring(-2.0, 0.6)],
                [DUCT, DUCT, SHADER, SHADER, SHADER, SHADER], flat=True)
        b.foil((s * 1.9, 1.4, 0.05), (s * 6.1, -2.7, 0.05), 6.0, 1.75, t=0.035, tt=0.03, steps=2, flat=True, round_tip=False)
        b.foil((s * 1.7, -5.0, 0.0), (s * 4.0, -6.9, 0.0), 2.9, 1.2, t=0.035, tt=0.03, steps=1, flat=True, round_tip=False)
        b.foil((s * 1.69, -3.8, 0.62), (s * 2.73, -5.8, 2.67), 3.2, 1.2, t=0.035, tt=0.03, steps=1, flat=True, round_tip=False)
        # shrouded flat nozzle: skin, burnt inside, glowing slot
        sq = lambda f, k, dz=0.0: [(s * (0.7 + (q[0] - 0.7) * k), f, (q[1] + dz) * k) for q in ((1.08, 0.3), (0.33, 0.3), (0.32, -0.3), (1.1, -0.3))]
        b.rings([sq(-6.9, 1.0), sq(-8.6, 0.78), sq(-8.62, 0.66), sq(-8.25, 0.62)], [SHADER, BURNT, BURNT], flat=True)
        b.use(HOT, part='hot')
        b.box((s * 0.7, -8.28, 0), (0.6, 0.03, 0.26))
        b.use(part='body')
        flame(b, s * 0.7, -8.6, 0.0, 0.26)
        b.use(LVA)
        b.box((s * 0.55, -0.8, -0.6), (0.7, 3.6, 0.03))                                                         # weapon-bay door
        b.use()
    b.use(GLASS_G, part='glass')
    st = []
    for deg in (0, 30, 60, 90, 120, 150, 180):
        t = math.radians(deg)
        st.append(dict(f=4.5 + 1.9 * math.cos(t), z=0.72, w=0.5 * math.sin(t), h=0.56 * math.sin(t), hb=0.1 * math.sin(t)))
    st[0].update(w=0, h=0, hb=0)
    st[-1].update(w=0, h=0, hb=0)
    b.sloft(st, step=0.9, ring=lambda s: [(s['x'] + p[0], s['f'], s['z'] + p[1]) for p in
                                           ((s['w'], 0), (0.7 * s['w'], 0.7 * s['h']), (0, s['h']), (-0.7 * s['w'], 0.7 * s['h']), (-s['w'], 0), (0, -s['hb']))], flat=True)
    b.use(part='body')
    cockpit(b, 4.6, 0.8, 0.6, 2.4, 1.05)
    b.use(LVA)
    b.box((0, 1.8, 0.83), (0.8, 0.9, 0.03))                                                                     # refuel door
    b.tube((0, 8.3, 0.05), (0, 8.9, 0.05), 0.02, seg=6, r2=0.012)
    b.use()
    for s in (-1, 1):
        for d in (1, -1):
            b.decal((s * 4.84, -2.83, 4 * d), (0, 0, -d), roundel_hostile(0.42, low=True))
        b.decal((s * 2.21 + s * 3, -5.79, 1.64), (-s, 0, 0), roundel_hostile(0.3, low=True), fwd=(0, 1, 0))
    return b, dict(jet=True, sharp=61, length=17.0, span=12.2, height=4.4, low=0.45, nozzles=[(s * 0.7, -8.6, 0.0) for s in (1, -1)])


# ---------------------------------------------------------------- Gyrfalcon
WING = dict(rx=2.5, tx=7.2, rLE=0.6, tLE=-3.6, rH=-4.1, tH=-4.95, rTE=-5.35, tTE=-5.55, ry=-0.08, ty=-0.12)


def wing_at(x, key):
    k = (x - WING['rx']) / (WING['tx'] - WING['rx'])
    return WING['r' + key] + (WING['t' + key] - WING['r' + key]) * k


def east(b, kind, x, f, z_rail):
    """One friendly store hung from a rail or pylon bottom at z_rail."""
    if kind == 'aam_short':
        r = 0.085
        missile(b, x, f, z_rail - r - 0.035, 2.92, r, E_BODY, W_SEEK, [(0.36, E_RED, 0.05), (0.42, E_YEL, 0.05)], E_FIN, 0.13,
                canards=(0.1, 0.12, 0.14, 0.08, 0.03), nose_round=True)
    elif kind == 'aam_long':
        r = 0.1
        missile(b, x, f, z_rail - r - 0.035, 3.63, r, E_BODY, E_SEEK, [(0.33, E_RED, 0.06), (0.38, E_YEL, 0.06)], E_FIN, 0.12, wings=(0.4, 0.06, 0.9, 0.5, 0.35))
    elif kind == 'aam_heavy':
        r = 0.19
        missile(b, x, f, z_rail - r - 0.035, 4.26, r, E_BODY, E_SEEK, [(0.3, E_RED, 0.07), (0.36, E_YEL, 0.07)], E_FIN, 0.2, wings=(0.45, 0.07, 1.0, 0.6, 0.4), seg=8)
    elif kind == 'agm_light':
        b.use(W_RACK)
        b.box((x, f, z_rail - 0.065), (0.08, 1.6, 0.13), bevel=0.02)
        r = 0.13
        missile(b, x, f, z_rail - 0.13 - r - 0.035, 2.93, r, E_OLIVE, hexc('#8a6d25'), [(0.3, E_YEL, 0.06), (0.35, E_RED, 0.05)], E_OLIVE, 0.17,
                wings=(0.35, 0.1, 0.8, 0.5, 0.3), nose_round=True, seg=8)
    elif kind == 'guided_bomb':
        r = 0.2
        missile(b, x, f, z_rail - r - 0.035, 2.98, r, E_OLIVE, W_SEEK, [(0.36, E_YEL, 0.07), (0.41, E_RED, 0.05)], E_OLIVE, 0.2, nl=0.9, nose_round=True, seg=8)
    elif kind == 'cruise':
        r = 0.26
        missile(b, x, f, z_rail - r - 0.035, 6.0, r, E_OLIVE2, E_OLIVE2, [(0.25, E_YEL, 0.08)], E_OLIVE2, 0.26, wings=(0.4, 0.15, 0.5, 0.4, 0.05), nl=1.2, nose_round=True, seg=8)


LOADOUTS = {
    'cap': dict(tip='aam_short', outer='aam_short', inner='aam_long', intake='aam_long', tunF='aam_heavy', tunA='aam_heavy'),
    'strike': dict(tip='aam_short', outer='agm_light', inner='guided_bomb', intake='aam_long', tunnel='cruise'),
}
HP = dict(tip=(7.3, -3.9, -0.18), outer=(5.8, -3.2, -0.46), inner=(4.2, -2.2, -0.52), intake=(1.5, -1.0, -1.57))


def build_friend(loadout='cap'):
    """Gyrfalcon: heavy twin-engine air-superiority fighter, ~22.6 m, blue-grey digital camouflage, Compass markings."""
    b = Builder(SHADER)
    fus = [dict(f=10.9, w=0, h=0, z=-0.18, paint=F_RADOME), dict(f=10.4, w=0.16, h=0.16, z=-0.16), dict(f=10.0, w=0.27, h=0.27, z=-0.13),
           dict(f=9.4, w=0.41, h=0.41, z=-0.09), dict(f=8.8, w=0.51, h=0.51, z=-0.05), dict(f=8.2, w=0.58, h=0.58, hb=0.56, z=-0.02, paint=SHADER),
           dict(f=7.0, w=0.68, h=0.66, hb=0.64, p=2.2), dict(f=5.8, w=0.76, h=0.68, hb=0.7, p=2.4), dict(f=4.2, w=0.86, h=0.8, hb=0.74, p=2.6),
           dict(f=2.6, w=0.95, h=0.92, hb=0.7, p=2.6), dict(f=0.5, w=0.98, h=0.88, hb=0.62, p=2.8), dict(f=-2.5, w=0.92, h=0.78, hb=0.55, p=2.8),
           dict(f=-5.5, w=0.78, h=0.62, hb=0.5, p=2.6), dict(f=-8.0, w=0.56, h=0.46, hb=0.4, z=0.02, p=2.4), dict(f=-9.8, w=0.33, h=0.28, hb=0.26, z=0.05),
           dict(f=-10.6, w=0.22, h=0.18, z=0.06), dict(f=-10.9, w=0, h=0, z=0.06)]
    b.sloft(fus, step=0.6, seg=20)
    half = [(6.6, 0.0), (6.2, 0.7), (5.0, 1.15), (3.6, 1.6), (2.0, 2.1), (0.5, 2.6), (-5.2, 2.62), (-7.4, 2.45), (-8.6, 1.3), (-8.9, 0.6), (-9.0, 0.0)]
    b.sloft([dict(f=f, w=w + (0.14 if w > 0 else 0), h=0.15, hb=0.15, z=-0.06, p=3.2, c=1) for f, w in half], seg=16)   # blended planform
    for s in (-1, 1):
        intake(b, [dict(f=2.9, x=s * 1.5, w=0.6, h=0.5, hb=0.52, z=-0.72, p=5), dict(f=1.2, x=s * 1.5, w=0.62, h=0.5, hb=0.58, z=-0.74, p=4),
                   dict(f=-2.0, x=s * 1.5, w=0.62, h=0.48, hb=0.58, z=-0.72, p=3.4), dict(f=-5.0, x=s * 1.5, w=0.6, h=0.5, hb=0.56, z=-0.66, p=2.8),
                   dict(f=-7.4, x=s * 1.5, w=0.54, h=0.5, hb=0.52, z=-0.6, p=2.2), dict(f=-8.6, x=s * 1.5, w=0.5, h=0.5, hb=0.5, z=-0.58, p=2.0)], 0.9, lip_paint=F_POD)
        b.sloft([dict(f=-4.6, x=s * 2.35, w=0.12, h=0.12, hb=0.1, z=-0.05), dict(f=-5.3, x=s * 2.35, w=0.22, h=0.2, hb=0.2, z=-0.05),
                 dict(f=-8.8, x=s * 2.35, w=0.2, h=0.18, hb=0.18, z=-0.03), dict(f=-9.8, x=s * 2.35, w=0.1, h=0.08, hb=0.08, z=-0.02),
                 dict(f=-10.0, x=s * 2.35, w=0, h=0, z=-0.02)], step=1.0, seg=10)                                   # tail boom
        b.foil((s * 2.4, 0.6, -0.08), (s * 7.2, -3.6, -0.12), 5.95, 1.95, t=0.06, tt=0.046, steps=3)                # wing
        b.foil((s * 2.35, -4.4, 0.1), (s * 2.62, -7.35, 3.95), 3.4, 1.45, t=0.059, tt=0.048, steps=2, round_tip=False)   # fin
        b.foil((s * 2.4, -6.3, -0.35), (s * 6.3, -8.5, -0.4), 3.0, 1.15, t=0.053, steps=3)                          # taileron
        b.foil((s * 2.05, -5.0, -0.9), (s * 2.2, -5.9, -1.85), 1.7, 1.0, t=0.047, steps=1, round_tip=False)        # ventral fin
        b.use(F_POD)
        b.loft([dict(f=-6.85, x=s * 2.62, z=3.96, w=0, h=0), dict(f=-7.2, x=s * 2.62, z=3.96, w=0.08, h=0.08),
                dict(f=-8.5, x=s * 2.62, z=3.96, w=0.065, h=0.065), dict(f=-8.55, x=s * 2.62, z=3.96, w=0, h=0)], seg=8, p=2.0)   # fin-tip pod
        b.box((s * 7.25, -2.95, -0.08), (0.12, 0.3, 0.1))
        b.use()
        b.box((s * 7.25, -4.2, -0.12), (0.1, 2.6, 0.12), bevel=0.02)                                               # wing-tip rail
        b.box((s * 4.2, -2.4, -0.37), (0.1, 2.0, 0.3), bevel=0.02)                                                 # pylons
        b.box((s * 5.8, -3.45, -0.33), (0.1, 1.6, 0.26), bevel=0.02)
        b.box((s * 1.5, -1.2, -1.42), (0.12, 1.9, 0.3), bevel=0.02)
        nozzle(b, s * 1.5, -8.6, -0.58, 0.5, 1.05)
    b.box((0, 0.9, -0.66), (0.12, 1.8, 0.3), bevel=0.02)
    b.box((0, -3.5, -0.62), (0.12, 1.8, 0.3), bevel=0.02)
    b.use(F_DARK)
    b.box((-1.5, 3.4, 0.02), (0.16, 0.6, 0.14), bevel=0.02)                                                       # gun port
    b.use(F_RADOME)
    b.loft([dict(z=0.58, f=6.5, x=-0.14, w=0.17, h=0.17), dict(z=0.73, f=6.5, x=-0.14, w=0.12, h=0.12)], seg=12, p=2.0, axis='z')
    b.use(F_DARK)
    b.loft([dict(f=6.66, x=-0.14, z=0.82, w=0, h=0), dict(f=6.6, x=-0.14, z=0.82, w=0.11, h=0.11), dict(f=6.5, x=-0.14, z=0.82, w=0.14, h=0.14),
            dict(f=6.38, x=-0.14, z=0.82, w=0.11, h=0.11), dict(f=6.34, x=-0.14, z=0.82, w=0, h=0)], seg=10, p=2.0)   # sensor ball
    b.use(hexc('#3a3f44'))
    b.tube((0, 10.85, -0.18), (0, 11.8, -0.18), 0.03, seg=6, r2=0.018)                                              # probe
    b.use()
    canopy(b, 5.2, 0.47, 1.95, 0.54, 0.66, GLASS_F, frames=(6.05, 4.35), sink=0.05)
    cockpit(b, 5.15, 0.74, 0.78, 2.6, 0.92)
    # markings: Compass roundels on both wing faces, fin flashes on both fin faces, bort number on the intakes
    zc = wing_at(5.0, 'H') + 0.5 * (wing_at(5.0, 'LE') - wing_at(5.0, 'H'))
    for s in (-1, 1):
        for d in (1, -1):
            b.decal((s * 5.0, zc, 4 * d), (0, 0, -d), roundel_friend(0.69))
        for side in (1, -1):
            b.decal((s * 2.5 + side * 3, -7.07, 2.6), (-side, 0, 0), flash_friend(1.0, 0.5, mirror=(side > 0)), fwd=(0, 0, 1))
        m = s < 0                                   # +x is the jet's left side: text there reads nose-to-the-left
        b.decal((s * 4, 0.3, -0.72), (-s, 0, 0), [(C_RING, number('21', 0.36, mirror=m, grow=0.025)), (C_BLUE, number('21', 0.36, mirror=m))], fwd=(0, 0, 1))
    # stores
    spec = LOADOUTS[loadout]
    b.use(part='stores_' + loadout)
    for s in (-1, 1):
        for k in ('tip', 'outer', 'inner', 'intake'):
            if spec.get(k):
                x, f, z = HP[k]
                east(b, spec[k], s * x, f + (0.3 if spec[k] == 'guided_bomb' else 0), z)
    if spec.get('tunF'):
        east(b, spec['tunF'], 0, 1.0, -0.81)
    if spec.get('tunA'):
        east(b, spec['tunA'], 0, -3.4, -0.77)
    if spec.get('tunnel'):
        east(b, spec['tunnel'], 0, -1.3, -0.79)
    b.use(part='body')
    return b, dict(jet=True, sharp=61, length=22.6, span=14.9, height=5.1, low=0.36, nozzles=[(s * 1.5, -9.65, -0.58) for s in (1, -1)])


JETS = (('jet_fighter', build_fighter), ('jet_light', build_light), ('jet_stealth', build_stealth), ('jet_friend', build_friend))
