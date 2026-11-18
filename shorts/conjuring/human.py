"""Stylised 3D characters for the Conjuring Short, built on the CC0 MakeHuman base mesh.

Body shape comes from MakeHuman macro targets (gender / age / weight); expressions are sculpted
procedurally around facial landmarks; hair and eyebrows are generated as Blender hair curves and
rendered with the Principled Hair BSDF; clothes are shells fitted to the morphed body.

MakeHuman coordinates: decimetres, Y up, +Z forward. Blender: metres, Z up, character faces -Y.
"""
import math, os
import numpy as np
import bpy

MH_DIR = os.environ.get('MH_DIR', '')
_CACHE = {}

# ---------------------------------------------------------------- loading
def load_base():
    if 'base' in _CACHE:
        return _CACHE['base']
    V, VT, groups, guv = [], [], {}, {}
    g = None
    for line in open(os.path.join(MH_DIR, 'base.obj')):
        if line.startswith('v '):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('vt '):
            VT.append([float(x) for x in line.split()[1:3]])
        elif line.startswith('g '):
            g = line.split()[1]
        elif line.startswith('f '):
            toks = line.split()[1:]
            groups.setdefault(g, []).append([int(t.split('/')[0]) - 1 for t in toks])
            guv.setdefault(g, []).append([int(t.split('/')[1]) - 1 if '/' in t and t.split('/')[1] else 0 for t in toks])
    base = dict(V=np.array(V, np.float64), VT=np.array(VT), groups=groups, guv=guv)
    _CACHE['base'] = base
    return base

def load_target(name):
    key = 't:' + name
    if key not in _CACHE:
        idx, d = [], []
        for line in open(os.path.join(MH_DIR, name + '.target')):
            if line[:1].isdigit():
                p = line.split()
                idx.append(int(p[0])); d.append([float(p[1]), float(p[2]), float(p[3])])
        _CACHE[key] = (np.array(idx, int), np.array(d))
    return _CACHE[key]

def morph(weights):
    base = load_base()
    V = base['V'].copy()
    for name, w in weights.items():
        idx, d = load_target(name)
        V[idx] += w * d
    return V

def group_verts(name):
    base = load_base()
    return np.unique(np.array([i for f in base['groups'][name] for i in f]))

# ---------------------------------------------------------------- landmarks & expression
def landmarks(V):
    le, re_ = V[group_verts('helper-l-eye')], V[group_verts('helper-r-eye')]
    ut = V[group_verts('helper-upper-teeth')]
    eye_r = (le.max(0) - le.min(0))[0] / 2
    top = V[group_verts('body')]
    tw = (ut.max(0) - ut.min(0))[0]
    lips = top[(np.abs(top[:, 0]) < tw * 0.45) & (np.abs(top[:, 1] - ut.min(0)[1]) < 0.18) & (top[:, 2] > ut.max(0)[2])]
    front = lips[lips[:, 2] > lips[:, 2].max() - 0.12]
    L = dict(eye_l=le.mean(0), eye_r=re_.mean(0), eye_rad=eye_r,
             mouth=np.array([0.0, front[:, 1].mean(), front[:, 2].max()]),
             mouth_w=tw * 0.62)
    head = top[top[:, 1] > L['eye_l'][1] + 0.25]
    c = head.mean(0)                       # fit a sphere to the top of the skull
    A = np.c_[2 * head, np.ones(len(head))]
    b = (head ** 2).sum(1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    L['skull_c'] = sol[:3]
    L['skull_r'] = math.sqrt(sol[3] + (sol[:3] ** 2).sum())
    return L

def _field(V, mask, center, radius, disp, front_only=True, zmin=None):
    d2 = ((V - center) ** 2).sum(1) / radius ** 2
    w = np.exp(-d2) * mask
    if front_only and zmin is not None:
        w *= np.clip((V[:, 2] - zmin) / 0.25, 0, 1)
    return w[:, None] * np.asarray(disp)[None, :]

def expression(V, brow_up=0.0, brow_in=0.0, frown=0.0, mouth_open=0.0, corners=0.0, eyes_wide=0.0, smirk=0.0):
    """Procedural facial expression (MakeHuman units). Positive brow_up = worried inner brows."""
    L = landmarks(V)
    out = V.copy()
    face = np.zeros(len(V)); face[group_verts('body')] = 1.0
    for side, eye in ((1, L['eye_l']), (-1, L['eye_r'])):
        zf = eye[2] - 0.15
        inner = eye + np.array([-side * 0.12, 0.27, 0.13])
        outer = eye + np.array([side * 0.15, 0.25, 0.05])
        out += _field(V, face, inner, 0.13, (-side * 0.025 * brow_in, 0.075 * brow_up - 0.05 * frown, 0), zmin=zf)
        out += _field(V, face, outer, 0.13, (0, -0.025 * brow_up + 0.02 * eyes_wide, 0), zmin=zf)
        lid = eye + np.array([0, 0.13, 0.1])
        out += _field(V, face, lid, 0.08, (0, 0.03 * eyes_wide, 0.0), zmin=zf)
    m = L['mouth']
    for side in (1, -1):
        corner = m + np.array([side * L['mouth_w'], 0, -0.05])
        out += _field(V, face, corner, 0.1, (side * 0.01 * smirk, -0.035 * corners + 0.03 * smirk * (side > 0), 0), zmin=m[2] - 0.5)
    if mouth_open:
        jaw = (V[:, 1] < m[1] - 0.01) & (V[:, 1] > m[1] - 0.95) & (np.abs(V[:, 0]) < 0.75) & (V[:, 2] > m[2] - 0.9)
        w = np.clip((m[1] - V[:, 1]) / 0.12, 0, 1) * jaw * np.clip(1 - np.abs(V[:, 0]) / 0.8, 0, 1) ** 0.5
        out[:, 1] -= w * 0.11 * mouth_open
        out[:, 2] -= w * 0.025 * mouth_open
    return out

def _rot(P, C, axis, ang, w):
    """Rotate points P about point C around a coordinate axis by ang*w (per-point weights)."""
    a = ang * w
    c, s = np.cos(a), np.sin(a)
    Q = P - C
    out = Q.copy()
    i, j = {'z': (0, 1), 'x': (1, 2), 'y': (2, 0)}[axis]
    out[:, i] = Q[:, i] * c - Q[:, j] * s
    out[:, j] = Q[:, i] * s + Q[:, j] * c
    return out + C

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def _seg_dist(P, A, B):
    ab = B - A
    t = np.clip(((P - A) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(P - (A + np.outer(t, ab)), axis=1)

def arm_chain(V, side):
    tag = 'l' if side > 0 else 'r'
    S = V[group_verts(f'joint-{tag}-shoulder')].mean(0)
    E = V[group_verts(f'joint-{tag}-elbow')].mean(0)
    Hd = V[group_verts(f'joint-{tag}-hand')].mean(0)
    tip = Hd + (Hd - E) * 1.9
    return S, E, Hd, tip

def pose_arms(V, down=0.55, elbow=0.0, elbow_r=None):
    """Lower the A-pose arms (rotation about the shoulder) and bend elbows forward."""
    out = V.copy()
    for side in (1, -1):
        S, E, Hd, tip = arm_chain(V, side)
        member = ((_seg_dist(V, S, E) < 0.75) | (_seg_dist(V, E, Hd) < 0.8) | (_seg_dist(V, Hd, tip) < 1.25)) \
                 & (side * V[:, 0] > side * S[0] * 0.75)
        u = (E - S) / np.linalg.norm(E - S)
        t = ((V - S) @ u) / np.linalg.norm(E - S)
        w = smoothstep(-0.05, 0.3, t) * member
        out = _rot(out, S, 'z', -side * down, w)
        eb = elbow if (elbow_r is None or side > 0) else elbow_r
        if eb:
            E2 = _rot(E[None, :], S, 'z', -side * down, np.ones(1))[0]
            w2 = smoothstep(0.88, 1.08, t) * member
            out = _rot(out, E2, 'x', -eb, w2)
    return out

# ---------------------------------------------------------------- materials
def hexcol(h):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple([c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb] + [1.0])

def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return m, nt, nt.nodes.new('ShaderNodeOutputMaterial')

def skin_material(name, base='#d9a487', blush='#c86a6a', lip='#a8524e', sss=0.35, rough=0.48):
    m, nt, out = _mat(name)
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    attr = nt.nodes.new('ShaderNodeAttribute'); attr.attribute_name = 'lipmask'
    battr = nt.nodes.new('ShaderNodeAttribute'); battr.attribute_name = 'blushmask'
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 900; nz.inputs['Detail'].default_value = 4
    nz2 = nt.nodes.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 40; nz2.inputs['Detail'].default_value = 6
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(tc.outputs['Object'], nz2.inputs['Vector'])
    c1 = nt.nodes.new('ShaderNodeMix'); c1.data_type = 'RGBA'
    c1.inputs[6].default_value = hexcol(base); c1.inputs[7].default_value = hexcol(blush)
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 0.25
    nt.links.new(battr.outputs['Fac'], mul.inputs[0]); nt.links.new(mul.outputs[0], c1.inputs[0])
    c2 = nt.nodes.new('ShaderNodeMix'); c2.data_type = 'RGBA'
    nt.links.new(c1.outputs[2], c2.inputs[6]); c2.inputs[7].default_value = hexcol(lip)
    nt.links.new(attr.outputs['Fac'], c2.inputs[0])
    blot = nt.nodes.new('ShaderNodeMix'); blot.data_type = 'RGBA'; blot.blend_type = 'OVERLAY'
    blot.inputs[0].default_value = 0.18
    nt.links.new(c2.outputs[2], blot.inputs[6]); nt.links.new(nz2.outputs['Color'], blot.inputs[7])
    nt.links.new(blot.outputs[2], p.inputs['Base Color'])
    p.inputs['Subsurface Weight'].default_value = sss
    p.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.2)
    p.inputs['Subsurface Scale'].default_value = 0.006
    rr = nt.nodes.new('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value = rough - 0.08; rr.inputs['To Max'].default_value = rough + 0.08
    nt.links.new(nz.outputs['Factor'], rr.inputs['Value']); nt.links.new(rr.outputs['Result'], p.inputs['Roughness'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12; bump.inputs['Distance'].default_value = 0.0005
    nt.links.new(nz.outputs['Factor'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    nt.links.new(p.outputs[0], out.inputs['Surface'])
    return m

def eye_material(name, iris='#5a3a22'):
    """Eyeball: sclera, limbal ring, iris, pupil from the object-space front direction (-Y); glossy cornea."""
    m, nt, out = _mat(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Normal'], sep.inputs[0])
    neg = nt.nodes.new('ShaderNodeMath'); neg.operation = 'MULTIPLY'; neg.inputs[1].default_value = -1
    nt.links.new(sep.outputs['Y'], neg.inputs[0])
    r = nt.nodes.new('ShaderNodeValToRGB')
    el = r.color_ramp.elements
    el[0].position = 0.80; el[0].color = hexcol('#e8ddd6')
    el[1].position = 0.995; el[1].color = hexcol('#050302')
    for pos, c in ((0.875, '#d8ccc4'), (0.885, '#1e140c'), (0.90, iris), (0.965, iris), (0.972, '#0a0603')):
        e = el.new(pos); e.color = hexcol(c)
    nt.links.new(neg.outputs[0], r.inputs['Factor'])
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(r.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.35
    p.inputs['Coat Weight'].default_value = 1.0
    p.inputs['Coat Roughness'].default_value = 0.02
    nt.links.new(p.outputs[0], out.inputs['Surface'])
    return m

def simple_material(name, colr, rough=0.6, sheen=0.0, noise_scale=0.0, bump=0.0, metal=0.0, cut=False):
    m, nt, out = _mat(name)
    p = nt.nodes.new('ShaderNodeBsdfPrincipled')
    if cut:   # smooth garment edges: keep only where the 'cut' attribute is positive
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'cut'
        gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.0
        nt.links.new(at.outputs['Fac'], gt.inputs[0]); nt.links.new(gt.outputs[0], p.inputs['Alpha'])
    p.inputs['Base Color'].default_value = hexcol(colr)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Sheen Weight'].default_value = sheen
    if noise_scale:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexWave'); nz.inputs['Scale'].default_value = noise_scale
        nz.inputs['Distortion'].default_value = 3.0; nz.inputs['Detail'].default_value = 6
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        b = nt.nodes.new('ShaderNodeBump'); b.inputs['Strength'].default_value = bump
        nt.links.new(nz.outputs['Factor'], b.inputs['Height']); nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
    nt.links.new(p.outputs[0], out.inputs['Surface'])
    return m

def hair_material(name, melanin=0.85, redness=0.3, rough=0.35):
    m, nt, out = _mat(name)
    h = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
    try:
        h.parametrization = 'MELANIN'
    except Exception:
        pass
    h.inputs['Melanin'].default_value = melanin
    h.inputs['Melanin Redness'].default_value = redness
    h.inputs['Roughness'].default_value = rough
    h.inputs['Radial Roughness'].default_value = 0.4
    h.inputs['Random Color'].default_value = 0.15
    h.inputs['Random Roughness'].default_value = 0.15
    nt.links.new(h.outputs[0], out.inputs['Surface'])
    return m

# ---------------------------------------------------------------- mesh building
def to_blender(V, loc=(0, 0, 0), scale=1.0, rot_z=0.0):
    """MH (dm, Y up, +Z fwd) -> Blender (m, Z up, facing -Y), feet on the ground."""
    P = np.c_[V[:, 0], -V[:, 2], V[:, 1] + 8.17] * 0.1 * scale
    if rot_z:
        c, s = math.cos(rot_z), math.sin(rot_z)
        P = np.c_[P[:, 0] * c - P[:, 1] * s, P[:, 0] * s + P[:, 1] * c, P[:, 2]]
    return P + np.asarray(loc)

def mesh_from_groups(name, V, P, group_names, mat, subsurf=2, extra_attrs=None, hide=None):
    base = load_base()
    faces = [f for gname in group_names for f in base['groups'][gname]]
    if hide is not None:
        faces = [f for f in faces if not hide[f].all()]
    used = np.unique(np.array([i for f in faces for i in f]))
    remap = -np.ones(len(V), int); remap[used] = np.arange(len(used))
    me = bpy.data.meshes.new(name)
    me.from_pydata(P[used].tolist(), [], [[int(remap[i]) for i in f] for f in faces])
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    if extra_attrs:
        for an, vals in extra_attrs.items():
            a = me.attributes.new(an, 'FLOAT', 'POINT')
            a.data.foreach_set('value', vals[used].astype(np.float32))
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if subsurf:
        mod = ob.modifiers.new('sub', 'SUBSURF'); mod.levels = 1; mod.render_levels = subsurf
    return ob, used

def vertex_normals(Pv, faces):
    n = np.zeros_like(Pv)
    for f in faces:
        a, b, c = Pv[f[0]], Pv[f[1]], Pv[f[2]]
        fn = np.cross(b - a, c - a)
        for i in f:
            n[i] += fn
    l = np.linalg.norm(n, axis=1, keepdims=True); l[l == 0] = 1
    return n / l

def shell(name, V, P, region, offset, mat, subsurf=2, solid=0.004, folds=0.0, seed=0, extra_offset=None, cut=None, smooth_iter=18):
    """Clothing shell: body faces where `region(V)` is true for all verts, pushed out along normals."""
    base = load_base()
    body_faces = base['groups']['body']
    keep = region(V)
    faces = [f for f in body_faces if keep[f].all()]
    used = np.unique(np.array([i for f in faces for i in f]))
    remap = -np.ones(len(V), int); remap[used] = np.arange(len(used))
    loc_faces = [[int(remap[i]) for i in f] for f in faces]
    Pv = P[used].copy()
    nrm = vertex_normals(Pv, loc_faces)
    off = np.full(len(used), offset)
    if extra_offset is not None:
        off = off + extra_offset(V[used])
    if folds:
        rng = np.random.default_rng(seed)
        k = rng.normal(size=(3, 3))
        off = off + folds * (np.sin(Pv @ k[0] * 40) * 0.5 + np.sin(Pv @ k[1] * 23) * 0.5)
    Pv = Pv + nrm * off[:, None]
    me = bpy.data.meshes.new(name)
    me.from_pydata(Pv.tolist(), [], loc_faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    if cut is not None:
        a = me.attributes.new('cut', 'FLOAT', 'POINT')
        a.data.foreach_set('value', cut(V[used]).astype(np.float32))
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if smooth_iter:   # cloth bridges over body detail instead of shrink-wrapping it
        sm = ob.modifiers.new('drape', 'SMOOTH'); sm.factor = 0.9; sm.iterations = smooth_iter
    if solid:
        so = ob.modifiers.new('solid', 'SOLIDIFY'); so.thickness = solid; so.offset = 1.0
    if subsurf:
        mod = ob.modifiers.new('sub', 'SUBSURF'); mod.levels = 1; mod.render_levels = subsurf
    return ob

# ---------------------------------------------------------------- hair curves
def _scalp_faces(V, L, front_y, side_y, back_y):
    base = load_base()
    C = L['skull_c']
    sel = []
    for f in base['groups']['body']:
        p = V[f].mean(0)
        d = p - C
        n = np.linalg.norm(d)
        if n < L['skull_r'] * 0.75:
            continue
        d /= n
        if d[2] > 0.25:
            ok = p[1] > front_y
        elif d[2] < -0.2:
            ok = p[1] > back_y
        else:
            ok = p[1] > side_y
        if ok and abs(p[0]) < L['skull_r'] * 1.15:
            sel.append(f)
    return sel

def _sample_roots(V, faces, n, rng):
    tri = []
    for f in faces:
        tri.append((f[0], f[1], f[2]))
        if len(f) == 4:
            tri.append((f[0], f[2], f[3]))
    tri = np.array(tri)
    A, B, Cc = V[tri[:, 0]], V[tri[:, 1]], V[tri[:, 2]]
    area = np.linalg.norm(np.cross(B - A, Cc - A), axis=1) / 2
    pick = rng.choice(len(tri), n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    return A[pick] + (B[pick] - A[pick]) * u[:, None] + (Cc[pick] - A[pick]) * v[:, None]

def hair_strands(V, L, style, n=6000, seed=1):
    """Generate strand polylines (MH units). style: 'long_center' (Lorraine), 'short_side' (Ed), 'wild' (entity)."""
    rng = np.random.default_rng(seed)
    C, R = L['skull_c'], L['skull_r']
    ye = L['eye_l'][1]
    if style == 'short_side':
        faces = _scalp_faces(V, L, ye + 0.5, ye - 0.15, ye - 0.85)
    else:
        faces = _scalp_faces(V, L, ye + 0.58, ye - 0.05, ye - 0.95)
    roots = _sample_roots(V, faces, n, rng)
    strands = []
    seg = 16
    for r0 in roots:
        if style == 'long_center':
            side = 1.0 if r0[0] + rng.normal(0, 0.03) >= 0 else -1.0
            length = rng.uniform(6.0, 7.2)
            hang_y = ye - rng.uniform(0.0, 0.6)
            base_off = 0.05
        elif style == 'short_side':
            side = 1.0 if r0[0] > 0.33 else -1.0
            length = rng.uniform(0.6, 1.0)
            hang_y = ye - 0.6
            base_off = 0.035
        else:  # wild, matted
            side = 1.0 if r0[0] >= 0 else -1.0
            length = rng.uniform(4.5, 7.0)
            hang_y = ye + 0.2
            base_off = 0.07
        pts = [r0.copy()]
        p = r0.copy()
        step = length / seg
        for k in range(seg):
            d = p - C
            nrm = d / np.linalg.norm(d)
            if p[1] > hang_y:
                want = np.array([side, -0.55, -0.35 if style == 'short_side' else -0.1])
                if style == 'short_side' and r0[2] < C[2] - 0.2:
                    want = np.array([side * 0.3, -1.0, -0.6])
                tan = want - nrm * (want @ nrm)
                tan /= np.linalg.norm(tan) + 1e-9
                p = p + tan * step
                d = p - C
                rad = max(np.linalg.norm(d), R + base_off + (0.005 if style == 'short_side' else 0.012) * k)
                p = C + d / np.linalg.norm(d) * rad
            else:
                drift = np.array([side * 0.12, -1.0, 0.0])
                if style == 'wild':
                    drift += rng.normal(0, 0.35, 3)
                p = p + drift / np.linalg.norm(drift) * step
                if style != 'short_side' and p[2] > C[2] + 0.05 and abs(p[0] - C[0]) < 1.05:
                    p[0] = C[0] + side * 1.05          # curtains fall beside the face, never across the neck
                # keep clear of the neck and shoulders
                r_xz = math.hypot(p[0] - C[0], p[2] - (C[2] - 0.15))
                need = 0.95 if p[1] > ye - 1.6 else 1.45 + 0.6 * np.clip((ye - 1.6 - p[1]) / 0.8, 0, 1)
                if r_xz < need:
                    ang = math.atan2(p[2] - (C[2] - 0.15), p[0] - C[0])
                    p[0] = C[0] + math.cos(ang) * need
                    p[2] = (C[2] - 0.15) + math.sin(ang) * need
            p = p + rng.normal(0, 0.012, 3)
            pts.append(p.copy())
        strands.append(np.array(pts))
    # clumping toward guide strands for a groomed look
    S = np.array(strands)
    guides = S[rng.choice(len(S), max(8, n // 40), replace=False)]
    for i in range(len(S)):
        g = guides[np.argmin(((guides[:, 0] - S[i, 0]) ** 2).sum(1))]
        t = np.linspace(0, 1, seg + 1)[:, None] ** 1.5
        S[i] = S[i] * (1 - 0.45 * t) + (g + (S[i, 0] - g[0])) * 0.45 * t
    return S

def brow_strands(V, L, n=260, seed=3, thick=1.0):
    rng = np.random.default_rng(seed)
    body = V[group_verts('body')]
    out = []
    for side, eye in ((1, L['eye_l']), (-1, L['eye_r'])):
        for _ in range(n):
            t = rng.random()
            x = eye[0] + side * (-0.16 + 0.34 * t)
            y = eye[1] + 0.23 + 0.06 * math.sin(math.pi * t) * thick - 0.03 * t + rng.normal(0, 0.012) * thick
            near = body[(np.abs(body[:, 0] - x) < 0.04) & (np.abs(body[:, 1] - y) < 0.04)]
            if not len(near):
                continue
            z = near[:, 2].max() + 0.012
            p0 = np.array([x, y, z])
            d = np.array([side * 0.9, 0.35 - 0.6 * t, 0.15])
            d /= np.linalg.norm(d)
            out.append(np.array([p0, p0 + d * 0.035, p0 + d * 0.07 + np.array([0, -0.01, 0.005])]))
    return out

def make_curves(name, strands, mat, radius_m=0.0004, loc=(0, 0, 0), scale=1.0, rot_z=0.0, tip=0.3):
    hc = bpy.data.hair_curves.new(name)
    npts = [len(s) for s in strands]
    hc.add_curves(npts)
    P = np.concatenate([to_blender(s, loc, scale, rot_z) for s in strands])
    hc.attributes['position'].data.foreach_set('vector', P.astype(np.float32).ravel())
    rad = np.concatenate([np.linspace(radius_m, radius_m * tip, k) for k in npts]).astype(np.float32)
    if 'radius' not in hc.attributes:
        hc.attributes.new('radius', 'FLOAT', 'POINT')
    hc.attributes['radius'].data.foreach_set('value', rad)
    hc.materials.append(mat)
    ob = bpy.data.objects.new(name, hc)
    bpy.context.collection.objects.link(ob)
    return ob

# ---------------------------------------------------------------- characters
def eyes(V, L, loc, scale, rot_z, look=(0.0, 0.0), iris='#5a3a22', name='eye'):
    mat = eye_material(name + '_mat', iris)
    obs = []
    for key in ('eye_l', 'eye_r'):
        c = to_blender(L[key][None, :], loc, scale, rot_z)[0]
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=L['eye_rad'] * 0.1 * scale * 0.98, location=c)
        ob = bpy.context.object
        for p in ob.data.polygons:
            p.use_smooth = True
        ob.data.materials.append(mat)
        ob.rotation_euler = (look[1], 0, rot_z + look[0])
        obs.append(ob)
    return obs

def masks(V, L):
    m = L['mouth']
    lip = np.exp(-(((V[:, 0] - m[0]) / (L['mouth_w'] * 1.0)) ** 2 + ((V[:, 1] - m[1]) / 0.06) ** 2)) * (V[:, 2] > m[2] - 0.12)
    lip = np.clip((lip - 0.45) * 2.5, 0, 1)
    bl = np.zeros(len(V))
    for eye in (L['eye_l'], L['eye_r']):
        bl += np.exp(-(((V[:, 0] - eye[0] * 1.35) / 0.25) ** 2 + ((V[:, 1] - (eye[1] - 0.35)) / 0.22) ** 2)) * (V[:, 2] > eye[2] - 0.3)
    return {'lipmask': lip, 'blushmask': np.clip(bl, 0, 1)}

CHARACTERS = {
    'lorraine': dict(targets={'caucasian-female-young': 0.9, 'caucasian-female-old': 0.1,
                              'universal-female-young-averagemuscle-minweight': 0.25},
                     skin='#e2ae92', lip='#a85456', iris='#4a6a3a', hair='long_center', melanin=0.88, redness=0.35),
    'ed': dict(targets={'caucasian-male-young': 0.85, 'caucasian-male-old': 0.15,
                        'universal-male-young-averagemuscle-maxweight': 0.3, 'universal-male-young-maxmuscle-averageweight': 0.2},
               skin='#d8a588', lip='#b57a68', iris='#4a3018', hair='short_side', melanin=0.8, redness=0.25),
    'entity': dict(targets={'caucasian-female-old': 1.0, 'universal-female-old-averagemuscle-minweight': 0.9},
                   skin='#8a8a80', lip='#5a3a3a', iris='#d8d0b0', hair='wild', melanin=0.95, redness=0.05),
}

def build_character(who, loc=(0, 0, 0), rot_z=0.0, scale=1.0, expr=None, look=(0, 0), outfit=True, hair_n=None,
                    seed=1, silhouette=False, arms=None):
    cfg = CHARACTERS[who]
    V0 = morph(cfg['targets'])
    V = expression(V0, **(expr or {}))
    V = pose_arms(V, **(arms or {'down': 0.55}))
    if who == 'entity':                       # gaunt, too tall
        V = V.copy(); V[:, 1] = V[:, 1] * 1.12
    L = landmarks(V)
    P = to_blender(V, loc, scale, rot_z)
    if silhouette:
        skin = simple_material(who + '_void', '#020203', rough=0.9)
    else:
        skin = skin_material(who + '_skin', cfg['skin'], lip=cfg['lip'], sss=0.35)
    hidden = None
    if outfit and not silhouette and who in ('ed', 'lorraine'):
        neck_y = L['eye_l'][1] - 1.25
        fr = np.clip(V[:, 2] / 0.6, 0, 1); bk = np.clip(-V[:, 2] / 0.5, 0, 1)
        top = (neck_y + 0.22 - 0.14 * fr + 0.1 * bk) if who == 'ed' else np.full(len(V), neck_y + 0.45)
        hidden = (V[:, 1] < top - 0.08) & (hand_dist(V, hand_centers(V)) > 0.65)
    body, used = mesh_from_groups(who + '_body', V, P, ['body'], skin, extra_attrs=masks(V, L), hide=hidden)
    teeth_m = simple_material(who + '_teeth', '#e8e0cc', rough=0.3)
    mesh_from_groups(who + '_teeth', V, P, ['helper-upper-teeth', 'helper-lower-teeth'], teeth_m, subsurf=1)
    parts = {'body': body}
    if not silhouette:
        parts['eyes'] = eyes(V, L, loc, scale, rot_z, look, cfg['iris'], who + '_eye')
        brow_m = hair_material(who + '_brow', cfg['melanin'], cfg['redness'], 0.5)
        parts['brows'] = make_curves(who + '_brows', brow_strands(V, L, thick=1.2 if who == 'ed' else 0.9, seed=seed),
                                     brow_m, 0.00018, loc, scale, rot_z)
    hm = hair_material(who + '_hair', cfg['melanin'], cfg['redness'], 0.3) if not silhouette else simple_material('void_hair', '#020203')
    n = hair_n or (7000 if cfg['hair'] == 'long_center' else 5000)
    parts['hair'] = make_curves(who + '_hair', hair_strands(V, L, cfg['hair'], n, seed), hm,
                                0.00045 if cfg['hair'] != 'short_side' else 0.0004, loc, scale, rot_z)
    if outfit and not silhouette:
        parts['clothes'] = clothes(who, V, P, L)
    if who == 'entity' and not silhouette:     # a ragged dark dress for the apparition
        neck_y = L['eye_l'][1] - 1.25 * 1.12
        dress = simple_material('entity_dress', '#16130f', 0.85, sheen=0.3, noise_scale=40, bump=0.2, cut=True)
        HC = hand_centers(V)
        parts['dress'] = shell('entity_dress', V, P, lambda X: X[:, 1] < neck_y + 0.4, 0.02, dress, folds=0.006, seed=11,
                               cut=lambda X: np.minimum((neck_y + 0.15) - X[:, 1], hand_dist(X, HC) - 0.5))
    parts['L'] = L
    parts['P'] = P
    parts['V'] = V
    return parts

def hand_centers(V):
    out = []
    for side in (1, -1):
        S, E, Hd, tip = arm_chain(V, side)
        out.append((Hd + (Hd - E) * 0.1, Hd + (Hd - E) * 1.3))
    return out

def hand_dist(X, centers):
    d = np.full(len(X), 9.0)
    for a, b in centers:
        d = np.minimum(d, _seg_dist(X, a, b))
    return d

def clothes(who, V, P, L):
    neck_y = L['eye_l'][1] - 1.25
    out = []
    HC = hand_centers(V)
    hd = lambda X: hand_dist(X, HC)
    def wrist(X, c):
        return np.minimum(c, hd(X) - 0.55)
    waist = neck_y - 4.2
    pants_m = simple_material(who + '_pants', '#2a2622' if who == 'ed' else '#2c2a30', 0.8, sheen=0.3, cut=True)
    shoes_m = simple_material(who + '_shoes', '#14100e', 0.35)
    out.append(shell(who + '_pants', V, P, lambda X: (X[:, 1] < waist + 0.4) & (X[:, 1] > -7.5) & (hd(X) > 0.4),
                     0.012, pants_m, folds=0.002, seed=7, cut=lambda X: np.minimum((waist + 0.15) - X[:, 1], hd(X) - 0.55)))
    out.append(shell(who + '_shoes', V, P, lambda X: X[:, 1] < -7.25, 0.008, shoes_m, smooth_iter=4))
    front = lambda X: np.clip(X[:, 2] / 0.6, 0, 1)
    back = lambda X: np.clip(-X[:, 2] / 0.5, 0, 1)
    broad = lambda X: (X[:, 1] < neck_y + 0.5) & (X[:, 1] > neck_y - 5.2) & ~((X[:, 1] > neck_y + 0.12) & (X[:, 2] > 0.5))
    if who == 'ed':
        shirt = simple_material('ed_shirt', '#8f9aa6', 0.75, sheen=0.3, cut=True)
        jacket = simple_material('ed_jacket', '#4e3524', 0.75, sheen=0.4, noise_scale=60, bump=0.05, cut=True)
        tie = simple_material('ed_tie', '#3a1c18', 0.5, cut=True)
        out.append(shell('ed_shirt', V, P, broad, 0.009, shirt, folds=0.0015, seed=1,
                         cut=lambda X: wrist(X, (neck_y + 0.22 - 0.14 * front(X) + 0.1 * back(X)) - X[:, 1])))
        def jacket_cut(X):
            depth = np.clip((neck_y - X[:, 1]) / 1.7, 0, 1)
            v_open = np.where(X[:, 2] > 0.3, np.abs(X[:, 0]) - (0.12 + 0.3 * depth), 1.0)
            return wrist(X, np.minimum((neck_y + 0.08 + 0.3 * back(X)) - X[:, 1], v_open))
        out.append(shell('ed_jacket', V, P, broad, 0.022, jacket, folds=0.003, seed=2, solid=0.006, cut=jacket_cut))
        tie_reg = lambda X: (np.abs(X[:, 0]) < 0.25) & (X[:, 1] < neck_y + 0.2) & (X[:, 1] > neck_y - 2.6) & (X[:, 2] > 0.3)
        tie_cut = lambda X: np.minimum((0.07 + 0.05 * np.clip((neck_y - X[:, 1]) / 2.2, 0, 1)) - np.abs(X[:, 0]),
                                       (neck_y + 0.05) - X[:, 1])
        out.append(shell('ed_tie', V, P, tie_reg, 0.016, tie, solid=0.002, smooth_iter=6, cut=tie_cut))
    elif who == 'lorraine':
        knit = simple_material('lo_turtleneck', '#9a8c78', 0.85, sheen=0.6, noise_scale=180, bump=0.12, cut=True)
        coat = simple_material('lo_coat', '#3a3236', 0.7, sheen=0.4, noise_scale=70, bump=0.05, cut=True)
        roll = lambda X: 0.004 * smoothstep(neck_y + 0.15, neck_y + 0.4, X[:, 1])
        out.append(shell('lo_knit', V, P, broad, 0.01, knit, folds=0.0015, seed=3, extra_offset=roll,
                         cut=lambda X: wrist(X, (neck_y + 0.45) - X[:, 1])))
        def coat_cut(X):
            depth = np.clip((neck_y - X[:, 1]) / 1.9, 0, 1)
            v_open = np.where(X[:, 2] > 0.25, np.abs(X[:, 0]) - (0.3 + 0.25 * depth), 1.0)
            return wrist(X, np.minimum((neck_y - 0.05 + 0.35 * back(X)) - X[:, 1], v_open))
        out.append(shell('lo_coat', V, P, broad, 0.026, coat, folds=0.004, seed=4, solid=0.007, cut=coat_cut))
    return out
