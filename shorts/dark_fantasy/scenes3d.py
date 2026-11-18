"""Blender (bpy) scene builder for the 15-second dark-fantasy Short.

Recreates the look of late-1990s CGI fantasy renders: ultra-saturated royal blue / violet worlds,
crunchy fractal-noise textures, glossy plastic-like materials, checkerboard marble, star-patterned
robes, glowing magic (cyan, gold, acid green) and deep one-point-perspective compositions.

Usage (one shot per process):
    python3 scenes3d.py SHOT FRAME_START FRAME_END OUT_DIR [--res 720x1280] [--samples 20]
Shots: sky, path, hall, sorcerer, hoard
"""
import sys, math, random, argparse
import bpy
from mathutils import Vector

FPS = 30
SHOT_FRAMES = {'sky': 99, 'path': 99, 'hall': 99, 'sorcerer': 99, 'hoard': 114}

# ---------------------------------------------------------------- material helpers
def hexcol(h, a=1.0):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)

def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    return m, nt, out

def node(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items():
        if k.startswith('_'):
            setattr(n, k[1:], v)
        else:
            n.inputs[k.replace('__', ' ')].default_value = v
    return n

def link(nt, a, b):
    nt.links.new(a, b)

def ramp(nt, fac, stops, interp='LINEAR'):
    r = nt.nodes.new('ShaderNodeValToRGB')
    r.color_ramp.interpolation = interp
    el = r.color_ramp.elements
    while len(el) > 2:
        el.remove(el[-1])
    for i, (pos, colr) in enumerate(stops):
        e = el[i] if i < 2 else el.new(pos)
        e.position = pos
        e.color = hexcol(colr) if isinstance(colr, str) else colr
    link(nt, fac, r.inputs['Factor'])
    return r.outputs['Color']

def coords(nt, kind='Object', scale=(1, 1, 1)):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = node(nt, 'ShaderNodeMapping', Scale=scale)
    link(nt, tc.outputs[kind], mp.inputs['Vector'])
    return mp.outputs['Vector']

def principled(nt, base=None, rough=0.5, metal=0.0, emit=None, emit_strength=0.0, coat=0.0):
    p = node(nt, 'ShaderNodeBsdfPrincipled', Roughness=rough, Metallic=metal)
    p.inputs['Coat Weight'].default_value = coat
    if base is not None:
        if isinstance(base, str):
            p.inputs['Base Color'].default_value = hexcol(base)
        else:
            link(nt, base, p.inputs['Base Color'])
    if emit is not None:
        if isinstance(emit, str):
            p.inputs['Emission Color'].default_value = hexcol(emit)
        else:
            link(nt, emit, p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value = emit_strength
    return p

def bump(nt, height, strength=0.6, distance=0.1):
    b = node(nt, 'ShaderNodeBump', Strength=strength, Distance=distance)
    link(nt, height, b.inputs['Height'])
    return b.outputs['Normal']

def mat_stone(name, cols=('#05061a', '#1d2a8a', '#6f7cf0', '#c9ccff'), scale=3.0, bump_s=0.8, blocks=0.0, rough=0.45):
    """Crunchy fractal stone in saturated blues."""
    m, nt, out = new_mat(name)
    v = coords(nt, 'Object', (scale, scale, scale))
    nz = node(nt, 'ShaderNodeTexNoise', Detail=15.0, Roughness=0.72, Distortion=0.35)
    link(nt, v, nz.inputs['Vector'])
    fac = nz.outputs['Factor']
    if blocks:
        vo = node(nt, 'ShaderNodeTexVoronoi', Scale=blocks, Randomness=0.6, _feature='DISTANCE_TO_EDGE')
        link(nt, v, vo.inputs['Vector'])
        edge = ramp(nt, vo.outputs['Distance'], [(0.0, '#000000'), (0.06, '#ffffff')])
        mix = node(nt, 'ShaderNodeMath', _operation='MULTIPLY')
        link(nt, fac, mix.inputs[0]); link(nt, edge, mix.inputs[1])
        fac = mix.outputs[0]
    n = len(cols)
    col = ramp(nt, fac, [(0.25 + 0.5 * i / (n - 1), c) for i, c in enumerate(cols)])
    p = principled(nt, col, rough=rough)
    link(nt, bump(nt, fac, bump_s, 0.15), p.inputs['Normal'])
    link(nt, p.outputs[0], out.inputs['Surface'])
    return m

def mat_emit(name, colr, strength=5.0):
    m, nt, out = new_mat(name)
    e = node(nt, 'ShaderNodeEmission', Strength=strength)
    e.inputs['Color'].default_value = hexcol(colr)
    link(nt, e.outputs[0], out.inputs['Surface'])
    return m

def mat_crack(name, glow='#38c8ff', glow2='#2a4bff', strength=8.0, scale=2.5):
    """Dark stone split by glowing magic cracks (voronoi edges)."""
    m, nt, out = new_mat(name)
    v = coords(nt, 'Object', (scale, scale, scale))
    nz = node(nt, 'ShaderNodeTexNoise', Detail=12.0, Roughness=0.7, Distortion=0.8, Scale=2.0)
    link(nt, v, nz.inputs['Vector'])
    vo = node(nt, 'ShaderNodeTexVoronoi', Scale=1.6, _feature='DISTANCE_TO_EDGE')
    link(nt, nz.outputs['Color'], vo.inputs['Vector'])
    mask = ramp(nt, vo.outputs['Distance'], [(0.0, '#ffffff'), (0.035, '#000000')])
    stone = ramp(nt, nz.outputs['Factor'], [(0.3, '#02031a'), (0.55, '#14208a'), (0.75, '#3f58ff')])
    p = principled(nt, stone, rough=0.25)
    link(nt, bump(nt, nz.outputs['Factor'], 0.9, 0.2), p.inputs['Normal'])
    gcol = ramp(nt, nz.outputs['Factor'], [(0.35, glow2), (0.65, glow)])
    e = node(nt, 'ShaderNodeEmission', Strength=strength)
    link(nt, gcol, e.inputs['Color'])
    mx = nt.nodes.new('ShaderNodeMixShader')
    link(nt, mask, mx.inputs['Fac']); link(nt, p.outputs[0], mx.inputs[1]); link(nt, e.outputs[0], mx.inputs[2])
    link(nt, mx.outputs[0], out.inputs['Surface'])
    return m

def mat_checker(name, c1='#0e1a8c', c2='#c7c4ff', scale=8.0):
    """Glossy checkerboard marble with fractal veins."""
    m, nt, out = new_mat(name)
    v = coords(nt, 'Object', (1, 1, 1))
    ch = node(nt, 'ShaderNodeTexChecker', Scale=scale)
    ch.inputs['Color1'].default_value = hexcol(c1); ch.inputs['Color2'].default_value = hexcol(c2)
    link(nt, v, ch.inputs['Vector'])
    nz = node(nt, 'ShaderNodeTexNoise', Scale=1.2, Detail=14.0, Roughness=0.7, Distortion=4.0)
    link(nt, v, nz.inputs['Vector'])
    vein = ramp(nt, nz.outputs['Factor'], [(0.42, '#202060'), (0.5, '#ffffff'), (0.58, '#ffffff')])
    mix = node(nt, 'ShaderNodeMix', _data_type='RGBA', _blend_type='MULTIPLY')
    mix.inputs[0].default_value = 0.75
    link(nt, ch.outputs['Color'], mix.inputs[6]); link(nt, vein, mix.inputs[7])
    p = principled(nt, mix.outputs[2], rough=0.12, coat=0.6)
    link(nt, bump(nt, nz.outputs['Factor'], 0.25, 0.05), p.inputs['Normal'])
    link(nt, p.outputs[0], out.inputs['Surface'])
    return m

def mat_gold(name='gold', base='#ffb32a', rough=0.22, scale=20.0):
    m, nt, out = new_mat(name)
    v = coords(nt, 'Object', (scale, scale, scale))
    nz = node(nt, 'ShaderNodeTexNoise', Detail=15.0, Roughness=0.75, Distortion=0.5)
    link(nt, v, nz.inputs['Vector'])
    col = ramp(nt, nz.outputs['Factor'], [(0.3, '#7a3c00'), (0.5, base), (0.75, '#fff0a0')])
    p = principled(nt, col, rough=rough, metal=1.0)
    link(nt, bump(nt, nz.outputs['Factor'], 0.7, 0.05), p.inputs['Normal'])
    link(nt, p.outputs[0], out.inputs['Surface'])
    return m

def mat_starcloth(name, base='#1428b8', star='#ffd23a', star_scale=9.0, star_strength=3.0):
    """Midnight-blue fabric scattered with glowing golden stars."""
    m, nt, out = new_mat(name)
    v = coords(nt, 'Object', (star_scale, star_scale, star_scale))
    vo = node(nt, 'ShaderNodeTexVoronoi', Randomness=0.9)
    link(nt, v, vo.inputs['Vector'])
    mask = ramp(nt, vo.outputs['Distance'], [(0.0, '#ffffff'), (0.13, '#ffffff'), (0.16, '#000000')])
    nz = node(nt, 'ShaderNodeTexNoise', Scale=1.5, Detail=10.0, Roughness=0.65)
    link(nt, coords(nt, 'Object', (2, 2, 2)), nz.inputs['Vector'])
    cloth = ramp(nt, nz.outputs['Factor'], [(0.3, '#050a40'), (0.55, base), (0.8, '#5a6cff')])
    p = principled(nt, cloth, rough=0.55, coat=0.3)
    link(nt, bump(nt, nz.outputs['Factor'], 0.6, 0.2), p.inputs['Normal'])
    e = node(nt, 'ShaderNodeEmission', Strength=star_strength)
    e.inputs['Color'].default_value = hexcol(star)
    mx = nt.nodes.new('ShaderNodeMixShader')
    link(nt, mask, mx.inputs['Fac']); link(nt, p.outputs[0], mx.inputs[1]); link(nt, e.outputs[0], mx.inputs[2])
    link(nt, mx.outputs[0], out.inputs['Surface'])
    return m

def mat_hair(name='beard', cols=('#5a5ab0', '#c8c8ff', '#ffffff')):
    m, nt, out = new_mat(name)
    v = coords(nt, 'Object', (2, 2, 30))
    nz = node(nt, 'ShaderNodeTexWave', Scale=6.0, Distortion=6.0, Detail=10.0)
    link(nt, v, nz.inputs['Vector'])
    col = ramp(nt, nz.outputs['Factor'], [(0.2, cols[0]), (0.6, cols[1]), (0.9, cols[2])])
    p = principled(nt, col, rough=0.5)
    link(nt, bump(nt, nz.outputs['Factor'], 1.0, 0.1), p.inputs['Normal'])
    link(nt, p.outputs[0], out.inputs['Surface'])
    return m

def mat_glossy(name, colr, rough=0.3, coat=0.5, metal=0.0):
    m, nt, out = new_mat(name)
    p = principled(nt, colr, rough=rough, coat=coat, metal=metal)
    link(nt, p.outputs[0], out.inputs['Surface'])
    return m

def mat_page(name='page', glow='#7dffe8', strength=4.0):
    """Glowing spell-book page with lines of 'text'."""
    m, nt, out = new_mat(name)
    v = coords(nt, 'Generated', (1, 1, 1))
    wv = node(nt, 'ShaderNodeTexWave', Scale=14.0, Distortion=0.0, Detail=0.0, _wave_type='BANDS', _bands_direction='Y')
    link(nt, v, wv.inputs['Vector'])
    nz = node(nt, 'ShaderNodeTexNoise', Scale=60.0, Detail=2.0)
    link(nt, v, nz.inputs['Vector'])
    lines = ramp(nt, wv.outputs['Factor'], [(0.0, '#1a6a60'), (0.25, glow), (1.0, glow)])
    e = node(nt, 'ShaderNodeEmission', Strength=strength)
    link(nt, lines, e.inputs['Color'])
    link(nt, e.outputs[0], out.inputs['Surface'])
    return m

def mat_moon():
    """Pale cratered moon: self-lit but textured, not a white disc."""
    m, nt, out = new_mat('moon')
    v = coords(nt, 'Object', (0.5, 0.5, 0.5))
    nz = node(nt, 'ShaderNodeTexNoise', Detail=14.0, Roughness=0.7, Scale=2.0)
    link(nt, v, nz.inputs['Vector'])
    vo = node(nt, 'ShaderNodeTexVoronoi', Scale=3.0)
    link(nt, v, vo.inputs['Vector'])
    cr = ramp(nt, vo.outputs['Distance'], [(0.0, '#555577'), (0.25, '#ffffff')])
    col = ramp(nt, nz.outputs['Factor'], [(0.3, '#4a4a78'), (0.55, '#b8b8e0'), (0.75, '#f4f4ff')])
    mix = node(nt, 'ShaderNodeMix', _data_type='RGBA', _blend_type='MULTIPLY')
    mix.inputs[0].default_value = 1.0
    link(nt, col, mix.inputs[6]); link(nt, cr, mix.inputs[7])
    e = node(nt, 'ShaderNodeEmission', Strength=0.9)
    link(nt, mix.outputs[2], e.inputs['Color'])
    link(nt, e.outputs[0], out.inputs['Surface'])
    return m

def world_sky(nebula=('#000006', '#0a1260', '#2a33ff', '#7a2cff', '#18c8a0'), stars=True, strength=1.0, swirl=2.5):
    """Swirling blue galaxy sky with dense stars."""
    w = bpy.data.worlds.new('sky')
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    v = coords(nt, 'Generated', (1, 1, 1))
    nz = node(nt, 'ShaderNodeTexNoise', Scale=1.6, Detail=12.0, Roughness=0.62, Distortion=swirl)
    link(nt, v, nz.inputs['Vector'])
    n = len(nebula)
    neb = ramp(nt, nz.outputs['Factor'], [(0.32 + 0.4 * i / (n - 1), c) for i, c in enumerate(nebula)])
    col = neb
    if stars:
        vo = node(nt, 'ShaderNodeTexVoronoi', Scale=220.0)
        link(nt, v, vo.inputs['Vector'])
        st = ramp(nt, vo.outputs['Distance'], [(0.0, '#ffffff'), (0.09, '#000000')])
        vo2 = node(nt, 'ShaderNodeTexVoronoi', Scale=55.0)
        link(nt, v, vo2.inputs['Vector'])
        st2 = ramp(nt, vo2.outputs['Distance'], [(0.0, '#ffe08a'), (0.05, '#000000')])
        add = node(nt, 'ShaderNodeMix', _data_type='RGBA', _blend_type='ADD')
        add.inputs[0].default_value = 1.0
        link(nt, neb, add.inputs[6]); link(nt, st, add.inputs[7])
        add2 = node(nt, 'ShaderNodeMix', _data_type='RGBA', _blend_type='ADD')
        add2.inputs[0].default_value = 1.0
        link(nt, add.outputs[2], add2.inputs[6]); link(nt, st2, add2.inputs[7])
        col = add2.outputs[2]
    bg = node(nt, 'ShaderNodeBackground', Strength=strength)
    link(nt, col, bg.inputs['Color'])
    link(nt, bg.outputs[0], out.inputs['Surface'])
    bpy.context.scene.world = w
    return w

# ---------------------------------------------------------------- geometry helpers
def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj

def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj

def cyl(loc, r, depth, mat, verts=24, r2=None, rot=(0, 0, 0)):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    return assign(smooth(bpy.context.object), mat)

def cone(loc, r, depth, mat, verts=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=0, depth=depth, location=loc, rotation=rot)
    return assign(smooth(bpy.context.object), mat)

def box(loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return assign(o, mat)

def sphere(loc, r, mat, scale=(1, 1, 1), seg=32, ring=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=ring, radius=r, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = scale
    if tuple(scale) != (1, 1, 1):
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return assign(smooth(o), mat)

def limb(p0, p1, r0, r1, mat, verts=16):
    """A tapered cylinder between two points (arms, sleeves, beard)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r0, radius2=r1, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return assign(smooth(o), mat)

def displaced_rock(loc, r, mat, scale=(1, 1, 1), strength=0.6, noise=1.2, sub=4, seed=0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    o = bpy.context.object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    tex = bpy.data.textures.new(f'rock{seed}', 'CLOUDS')
    tex.noise_scale = noise
    tex.noise_depth = 4
    d = o.modifiers.new('disp', 'DISPLACE')
    d.texture = tex
    d.strength = strength
    d.texture_coords = 'GLOBAL'
    return assign(smooth(o), mat)

def point_light(loc, colr, energy, radius=0.1):
    bpy.ops.object.light_add(type='POINT', location=loc)
    l = bpy.context.object
    l.data.color = hexcol(colr)[:3]
    l.data.energy = energy
    l.data.shadow_soft_size = radius
    return l

def area_light(loc, colr, energy, size=4, rot=(0, 0, 0)):
    bpy.ops.object.light_add(type='AREA', location=loc, rotation=rot)
    l = bpy.context.object
    l.data.color = hexcol(colr)[:3]
    l.data.energy = energy
    l.data.size = size
    return l

def camera(path, lens=26, target=None):
    """path: list of (frame, location[, target]) keyframes; camera tracks a target empty."""
    bpy.ops.object.camera_add(location=path[0][1])
    cam = bpy.context.object
    cam.data.lens = lens
    cam.data.sensor_width = 24
    bpy.context.scene.camera = cam
    bpy.ops.object.empty_add(location=path[0][2] if len(path[0]) > 2 else target)
    tgt = bpy.context.object
    tc = cam.constraints.new('TRACK_TO')
    tc.target = tgt
    tc.track_axis = 'TRACK_NEGATIVE_Z'
    tc.up_axis = 'UP_Y'
    for k in path:
        cam.location = k[1]
        cam.keyframe_insert('location', frame=k[0])
        if len(k) > 2:
            tgt.location = k[2]
            tgt.keyframe_insert('location', frame=k[0])
    for ob in (cam, tgt):
        if ob.animation_data and ob.animation_data.action:
            ease(ob)
    return cam

def ease(ob):
    """Smooth (bezier) interpolation on all fcurves of an object, compatible with layered actions."""
    try:
        fcs = ob.animation_data.action.fcurves
    except AttributeError:
        fcs = []
        for layer in ob.animation_data.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    fcs.extend(cb.fcurves)
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.easing = 'AUTO'

# ---------------------------------------------------------------- set pieces
def castle(origin=(0, 0, 0), s=1.0, seed=1, window_mat=None, roof_mat=None, wall_mat=None, gold=None):
    rnd = random.Random(seed)
    ox, oy, oz = origin
    wall_mat = wall_mat or mat_stone('castle_wall', ('#03041a', '#16207a', '#4a5ae0', '#a8b0ff'), scale=6, blocks=6)
    roof_mat = roof_mat or mat_glossy('roof', '#1530ff', 0.25, 0.8)
    window_mat = window_mat or mat_emit('window', '#ffaa2a', 12)
    gold = gold or mat_gold('spire_gold')
    towers = [(0, 0, 1.2, 7.5), (-2.2, 0.6, 0.7, 5.5), (2.3, 0.4, 0.75, 6.0), (-1.2, -1.4, 0.55, 4.6), (1.4, -1.3, 0.6, 5.0),
              (-3.4, -0.5, 0.45, 3.8), (3.5, -0.6, 0.5, 4.2), (0.2, 1.8, 0.6, 6.4)]
    cyl((ox, oy, oz + 1.2 * s), 3.2 * s, 2.4 * s, wall_mat, verts=10)
    for (tx, ty, r, h) in towers:
        x, y = ox + tx * s, oy + ty * s
        cyl((x, y, oz + h * s / 2), r * s, h * s, wall_mat, verts=16)
        cyl((x, y, oz + h * s + 0.1 * s), r * 1.18 * s, 0.25 * s, wall_mat, verts=16)
        sp = h * 0.55
        cone((x, y, oz + (h + sp / 2 + 0.2) * s), r * 1.15 * s, sp * s, roof_mat, verts=16)
        cyl((x, y, oz + (h + sp + 0.45) * s), 0.04 * s, 0.6 * s, gold, verts=6)
        for k in range(int(h * 1.6)):  # glowing windows
            a = rnd.uniform(-1.2, 1.2) - math.pi / 2
            z = rnd.uniform(0.8, h - 0.4)
            box((x + math.cos(a) * r * 1.01 * s, y + math.sin(a) * r * 1.01 * s, oz + z * s), (0.12 * s, 0.12 * s, 0.26 * s), window_mat, rot=(0, 0, a))

def candle(loc, h=0.6, r=0.05, flame_mat=None, wax=None, light=True, energy=6.0):
    wax = wax or mat_glossy('wax', '#e8dcff', 0.4, 0.2)
    flame_mat = flame_mat or mat_emit('flame', '#ffb040', 40)
    x, y, z = loc
    cyl((x, y, z + h / 2), r, h, wax, verts=10)
    sphere((x, y, z + h + r * 1.6), r * 0.7, flame_mat, scale=(1, 1, 2.2), seg=10, ring=6)
    if light:
        point_light((x, y, z + h + 0.25), '#ffae50', energy, 0.05)

def wizard(loc=(0, 0, 0), s=1.0, robe=None, eye_mat=None):
    """Hooded star-robed sorcerer with a long pale beard, glowing eyes and a staff with a violet orb."""
    x, y, z = loc
    robe = robe or mat_starcloth('robe', '#1428b8', '#ffd23a', 3.2, 2.5)
    hat = mat_starcloth('hat', '#1020a0', '#ffd23a', 4.0, 3.0)
    skin = mat_glossy('skin', '#6b6fc8', 0.45, 0.3)
    shadow = mat_glossy('hood_dark', '#02030c', 0.8, 0.0)
    eye_mat = eye_mat or mat_emit('eyes', '#ffd23a', 40)
    beard = mat_hair('beard')
    wood = mat_stone('wood', ('#1a0a04', '#5a2a10', '#a0602a'), scale=8, bump_s=0.9, rough=0.6)
    orb = mat_emit('orb', '#a040ff', 6)
    cyl((x, y, z + 1.3 * s), 1.25 * s, 2.6 * s, robe, verts=32, r2=0.42 * s)                 # robe body
    sphere((x, y, z + 2.6 * s), 0.62 * s, robe, scale=(1.25, 0.9, 0.6))                         # shoulders
    sphere((x, y, z + 3.05 * s), 0.42 * s, skin, scale=(0.95, 0.9, 1.1))                         # head
    sphere((x, y - 0.18 * s, z + 3.08 * s), 0.36 * s, shadow, scale=(1.0, 0.6, 1.0))             # face in shadow
    cyl((x, y, z + 3.42 * s), 0.85 * s, 0.08 * s, hat, verts=32)                                 # hat brim
    cone((x + 0.15 * s, y + 0.1 * s, z + 4.15 * s), 0.5 * s, 1.5 * s, hat, verts=24, rot=(0.15, -0.25, 0))  # bent pointed hat
    for side in (-1, 1):
        sphere((x + side * 0.13 * s, y - 0.37 * s, z + 3.12 * s), 0.055 * s, eye_mat, scale=(1.3, 0.6, 0.8))
        sphere((x + side * 0.25 * s, y - 0.3 * s, z + 3.25 * s), 0.12 * s, hat, scale=(1.5, 0.6, 0.4))   # brows
    limb((x, y - 0.36 * s, z + 2.95 * s), (x + 0.05 * s, y - 0.62 * s, z + 1.15 * s), 0.36 * s, 0.03 * s, beard, verts=24)  # long beard
    for side in (-1, 1):
        sh = (x + side * 0.62 * s, y - 0.05 * s, z + 2.6 * s)
        el = (x + side * 0.95 * s, y - 0.45 * s, z + 2.0 * s)
        hd = (x + side * 0.9 * s, y - 0.95 * s, z + 2.05 * s) if side > 0 else (x - 0.7 * s, y - 1.0 * s, z + 2.3 * s)
        limb(sh, el, 0.24 * s, 0.3 * s, robe)
        limb(el, hd, 0.3 * s, 0.4 * s, robe)        # wide sleeve
        sphere(hd, 0.15 * s, skin)
    cyl((x + 0.9 * s, y - 0.95 * s, z + 2.0 * s), 0.05 * s, 4.0 * s, wood, verts=8)               # staff
    sphere((x + 0.9 * s, y - 0.95 * s, z + 4.15 * s), 0.25 * s, orb)
    point_light((x + 0.9 * s, y - 1.2 * s, z + 4.15 * s), '#b05aff', 220 * s * s, 0.2)
    return (x + 0.9 * s, y - 0.95 * s, z + 4.15 * s)

def book(loc, rot, s=1.0, cover=None, page=None):
    cover = cover or mat_glossy('cover', '#3a1a6a', 0.35, 0.5)
    page = page or mat_page('page')
    x, y, z = loc
    bpy.ops.object.empty_add(location=loc, rotation=rot)
    root = bpy.context.object
    parts = []
    for side in (-1, 1):
        c = box((x + side * 0.2 * s, y, z), (0.4 * s, 0.03 * s, 0.55 * s), cover, rot=(0, 0, side * 0.25))
        p = box((x + side * 0.19 * s, y - 0.025 * s, z), (0.36 * s, 0.01 * s, 0.5 * s), page, rot=(0, 0, side * 0.25))
        parts += [c, p]
    for o in parts:
        o.parent = root
        o.matrix_parent_inverse = root.matrix_world.inverted()
    return root

# ---------------------------------------------------------------- shots
def build_sky(n):
    """Establishing shot: swirling galaxy, giant moon, black-blue castle on a floating crag above violet clouds."""
    world_sky(swirl=3.2, strength=1.0)
    sphere((-6, 60, 30), 9, mat_moon(), seg=64, ring=32)
    rock = mat_stone('crag', ('#02020c', '#141a6a', '#3a48c8', '#8a96ff'), scale=0.8, bump_s=1.2)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=5.2, radius2=0.2, depth=10, location=(0, 18, -2.6), rotation=(math.pi, 0, 0))
    isl = bpy.context.object
    sub = isl.modifiers.new('sub', 'SUBSURF'); sub.levels = 3; sub.render_levels = 3; sub.subdivision_type = 'SIMPLE'
    tex = bpy.data.textures.new('island', 'CLOUDS'); tex.noise_scale = 0.8; tex.noise_depth = 5
    d = isl.modifiers.new('disp', 'DISPLACE'); d.texture = tex; d.strength = 1.8; d.texture_coords = 'GLOBAL'
    assign(smooth(isl), rock)
    for k, (dx, dz) in enumerate(((-3.8, -1.5), (3.6, -2.5), (0.5, -5.5))):
        displaced_rock((dx, 18.5, dz), 1.4, rock, scale=(1, 1, 1.6), strength=0.8, noise=0.6, seed=20 + k)
    castle((0, 18, 2.4), 0.95, seed=3)
    cloud = mat_stone('cloud', ('#06061e', '#3a2a9a', '#8a6aff', '#e0d0ff'), scale=0.35, bump_s=0.6, rough=0.9)
    rnd = random.Random(5)
    for k in range(14):
        displaced_rock((rnd.uniform(-22, 22), rnd.uniform(10, 40), rnd.uniform(-9, -6)), rnd.uniform(2.5, 5), cloud,
                       scale=(2.2, 1.6, 0.55), strength=1.4, noise=1.5, sub=4, seed=10 + k)
    area_light((8, 0, 20), '#4a6aff', 3000, 12, rot=(0.6, 0.6, 0))
    point_light((0, 10, 3), '#ffb060', 600, 0.5)
    camera([(1, (0, -14, -1.5), (0, 18, 14)), (n, (0, -8.5, 1.0), (0, 18, 3.5))], lens=24)

def build_path(n):
    """Glowing cracked magic path between stone parapets toward the castle gate under two moons."""
    world_sky(nebula=('#000004', '#081060', '#2030f0', '#20b090', '#6a20d0'), swirl=2.0)
    crack = mat_crack('crack', '#46d8ff', '#2050ff', 9.0, 0.8)
    box((0, 30, -0.1), (4.0, 80, 0.2), crack)
    wall = mat_stone('parapet', ('#03041a', '#1a2490', '#5866f0', '#c0c6ff'), scale=1.4, blocks=1.8)
    for side in (-1, 1):
        box((side * 2.4, 30, 0.6), (0.8, 80, 1.6), wall)
        for k in range(26):
            box((side * 2.4, -6 + k * 3.0, 1.6), (0.9, 1.4, 0.5), wall)
    castle((0, 74, 0), 2.2, seed=7)
    moon = mat_moon()
    sphere((-18, 120, 45), 10, moon, seg=48, ring=24)
    sphere((22, 130, 58), 6, moon, seg=48, ring=24)
    rnd = random.Random(2)
    green = mat_emit('wisp', '#40ff90', 18)
    for k in range(18):  # floating green wisps
        sphere((rnd.uniform(-1.6, 1.6), rnd.uniform(0, 60), rnd.uniform(0.3, 2.2)), rnd.uniform(0.04, 0.09), green)
    area_light((0, 20, 25), '#3a4aff', 2500, 20, rot=(0, 0, 0))
    camera([(1, (0, -6, 1.6), (0, 40, 2.5)), (n, (0, 6, 1.4), (0, 50, 2.6))], lens=22)

def build_hall(n):
    """Gothic throne hall: checker marble floor, candle rows, floating candles, green braziers, throne."""
    world_sky(nebula=('#000002', '#04082a', '#101a80', '#2a1a90'), swirl=1.5, strength=0.6)
    box((0, 25, -0.05), (14, 70, 0.1), mat_checker('floor', scale=9.0))
    wall = mat_stone('hall_wall', ('#02031a', '#121c80', '#4050d8', '#9aa4ff'), scale=1.0, blocks=1.2)
    for side in (-1, 1):
        box((side * 7.2, 25, 7), (0.6, 70, 14), wall)
        for k in range(9):
            y = -2 + k * 6.5
            cyl((side * 5.6, y, 5), 0.55, 10, wall, verts=12)
            cone((side * 5.6, y, 11.6), 0.8, 3.2, mat_glossy('pillar_cap', '#1a2aff', 0.3, 0.6), verts=12)
    flame = mat_emit('flame', '#ffb040', 45)
    wax = mat_glossy('wax', '#f0e4ff', 0.4, 0.2)
    for side in (-1, 1):
        for k in range(12):  # candle rows on tall stands
            y = 1 + k * 4.0
            cyl((side * 3.6, y, 0.6), 0.06, 1.2, mat_gold('stand_gold'), verts=8)
            candle((side * 3.6, y, 1.2), 0.5, 0.07, flame, wax, light=(k % 2 == 0), energy=18)
    rnd = random.Random(8)
    for k in range(70):  # floating candles high in the air
        candle((rnd.uniform(-5, 5), rnd.uniform(4, 52), rnd.uniform(5.5, 10)), 0.35, 0.05, flame, wax, light=False)
    green = mat_emit('green_fire', '#3aff6a', 30)
    bowl = mat_gold('brazier')
    for side in (-1, 1):
        for y in (14, 30):
            cyl((side * 4.6, y, 0.9), 0.5, 0.4, bowl, verts=16, r2=0.3)
            cone((side * 4.6, y, 1.6), 0.4, 1.2, green, verts=12)
            point_light((side * 4.6, y, 2.0), '#3aff6a', 300, 0.3)
    throne = mat_glossy('throne', '#0a0f6a', 0.25, 0.8)
    box((0, 54, 3), (3.2, 1.0, 6), throne)
    for k in range(5):
        cone((-1.2 + k * 0.6, 54, 6.6 + (0.8 if k == 2 else 0)), 0.18, 1.4 + (0.8 if k == 2 else 0), mat_gold('throne_gold'), verts=8)
    wizard((0, 52.8, 0.6), 0.85, eye_mat=mat_emit('throne_eyes', '#ffd23a', 60))
    chand = mat_emit('chandelier', '#e8e0ff', 35)
    for ring_i, (rr, z) in enumerate(((2.6, 11), (1.7, 11.8), (0.9, 12.6))):
        for k in range(14 - ring_i * 4):
            a = k / (14 - ring_i * 4) * 2 * math.pi
            sphere((math.cos(a) * rr, 26 + math.sin(a) * rr, z), 0.09, chand)
    point_light((0, 26, 11), '#c8c0ff', 2500, 1.0)
    area_light((0, 10, 14), '#3040ff', 1500, 10)
    camera([(1, (0, -4, 2.2), (0, 40, 3.6)), (n, (0, 9, 2.0), (0, 54, 3.8))], lens=22)

def build_sorcerer(n):
    """The sorcerer: star robe, glowing eyes, orbiting luminous spell books, a glowing rune floor."""
    world_sky(nebula=('#000002', '#060c40', '#1420b0', '#3a1aa0'), swirl=2.0, strength=0.5)
    floor = mat_crack('rune_floor', '#5affe0', '#2a7aff', 7.0, 0.6)
    box((0, 0, -0.05), (30, 30, 0.1), floor)
    shelf = mat_stone('shelves', ('#0a0420', '#3a1a6a', '#8a4ac8'), scale=4, blocks=10)
    for side in (-1, 1):
        box((side * 6, 3, 5), (1.0, 14, 10), shelf)
    orb_pos = wizard((0, 2, 0), 1.0)
    page = mat_page('page', '#7dffe8', 5.0)
    cover = mat_glossy('cover', '#2a1060', 0.3, 0.6)
    books = []
    for k in range(7):
        a = k / 7 * 2 * math.pi
        b = book((math.cos(a) * 2.4, 2 + math.sin(a) * 1.6, 2.4 + 0.6 * math.sin(a * 2)), (0.3, 0, a), 0.9, cover, page)
        books.append((b, a))
    for b, a0 in books:  # slow orbit + bob
        for f in range(1, n + 1, 6):
            a = a0 + f / FPS * 0.55
            b.location = (math.cos(a) * 2.4, 2 + math.sin(a) * 1.6, 2.4 + 0.5 * math.sin(a * 2 + f / FPS * 1.5))
            b.rotation_euler = (0.3 + 0.2 * math.sin(f / FPS + a0), 0, a + math.pi / 2)
            b.keyframe_insert('location', frame=f)
            b.keyframe_insert('rotation_euler', frame=f)
    point_light((0, -2, 3), '#5affe0', 600, 1.0)
    area_light((-4, -6, 8), '#2a40ff', 1500, 6, rot=(0.9, 0, -0.5))
    for side in (-1, 1):
        for k in range(3):
            candle((side * 4.6, -1 + k * 2.2, 0), 0.7, 0.07, energy=12)
    camera([(1, (0.6, -7.5, 3.2), (0, 2, 3.0)), (n, (-0.2, -5.6, 3.3), (0, 2, 3.2))], lens=30)

def build_hoard(n):
    """The dragon's hoard: mountains of gold, a crowned skull, and red eyes opening in the dark."""
    world_sky(nebula=('#000000', '#020414', '#0a1050', '#1a0a40'), swirl=1.0, strength=0.25)
    gold = mat_gold('hoard_gold', '#ffcf3a', 0.18)
    displaced_rock((0, 6, -2.2), 5, gold, scale=(2.2, 1.6, 0.7), strength=0.6, noise=0.5, seed=31)
    rnd = random.Random(4)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.12, depth=0.025)
    coin_proto = bpy.context.object
    assign(coin_proto, gold)
    for k in range(260):  # loose coins on the hoard
        a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0, 6)
        o = coin_proto.copy(); bpy.context.collection.objects.link(o)
        o.location = (math.cos(a) * d * 1.4, 4 + math.sin(a) * d * 0.7, max(0.0, 1.6 - d * 0.32) + rnd.uniform(-0.05, 0.1))
        o.rotation_euler = (rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(0, 6))
    bone = mat_stone('bone', ('#4a4870', '#b8b4e8', '#f0eeff'), scale=6, bump_s=0.5, rough=0.35)
    hole = mat_glossy('socket', '#000000', 0.9, 0.0)
    sphere((0, 4.05, 2.45), 0.62, bone, scale=(0.95, 1.0, 1.0))           # cranium
    box((0, 3.62, 1.92), (0.62, 0.45, 0.3), bone)                        # jaw
    for side in (-1, 1):
        sphere((side * 0.24, 3.48, 2.38), 0.17, hole, scale=(1.1, 0.7, 1.0))     # eye sockets
        sphere((side * 0.24, 3.38, 2.38), 0.05, mat_emit('skull_eye', '#ff2030', 40))
    box((0, 3.44, 2.12), (0.12, 0.1, 0.16), hole)                        # nose cavity
    for k in range(-3, 4):
        box((k * 0.075, 3.38, 1.98), (0.06, 0.05, 0.1), mat_glossy('teeth', '#f0eedd', 0.3, 0.3))
    for k in range(7):                                         # crown
        a = k / 7 * 2 * math.pi
        cone((math.cos(a) * 0.55, 4 + math.sin(a) * 0.55, 3.15), 0.13, 0.55, gold, verts=6)
    cyl((0, 4, 2.9), 0.62, 0.22, gold, verts=24)
    cup = mat_gold('goblet', '#ffc84a', 0.15)
    for (x, y) in ((-2.2, 3.0), (2.4, 3.4), (-1.0, 2.0)):
        cyl((x, y, 1.0), 0.25, 0.5, cup, verts=16, r2=0.08)
        cyl((x, y, 0.6), 0.06, 0.4, cup, verts=8)
    eyes = []
    red = mat_emit('red_eyes', '#ff1a2a', 0.0)
    for k in range(16):  # pairs of eyes in the darkness, opening one by one
        x, y, z = rnd.uniform(-6, 6), rnd.uniform(9, 16), rnd.uniform(0.5, 5)
        mat = red.copy()
        e = mat.node_tree.nodes['Emission']
        start = int(n * (0.15 + 0.5 * k / 16))
        e.inputs['Strength'].default_value = 0.0
        e.inputs['Strength'].keyframe_insert('default_value', frame=start)
        e.inputs['Strength'].default_value = 60.0
        e.inputs['Strength'].keyframe_insert('default_value', frame=start + 6)
        for side in (-1, 1):
            sphere((x + side * 0.22, y, z), 0.08, mat, scale=(1.6, 0.6, 0.7))
    # the great eye of the dragon behind the hoard
    dragon_eye = mat_emit('dragon_eye', '#ff3a10', 0.0)
    e = dragon_eye.node_tree.nodes['Emission']
    e.inputs['Strength'].default_value = 0.0
    e.inputs['Strength'].keyframe_insert('default_value', frame=int(n * 0.62))
    e.inputs['Strength'].default_value = 80.0
    e.inputs['Strength'].keyframe_insert('default_value', frame=int(n * 0.72))
    for side in (-1, 1):
        sphere((side * 2.2, 14, 6.5), 0.55, dragon_eye, scale=(1.8, 0.5, 0.55))
    scale_m = mat_stone('dragon_scales', ('#01010a', '#0a1270', '#2a3ae0', '#6a7aff'), scale=6, blocks=14, bump_s=1.2)
    displaced_rock((0, 16, 5), 4.5, scale_m, scale=(2.0, 0.8, 1.2), strength=0.8, noise=0.6, seed=40)
    point_light((0, 1, 4), '#ffe2a0', 1100, 1.5)
    area_light((0, 20, 12), '#3a5aff', 2500, 10, rot=(-0.9, 0, 0))   # rim light reveals the dragon's bulk
    point_light((0, 10, 6), '#ff2030', 300, 2.0)
    area_light((0, -4, 8), '#2a3aff', 600, 8, rot=(0.6, 0, 0))
    camera([(1, (0, -6.5, 2.6), (0, 6, 2.6)), (n, (0, -3.8, 2.4), (0, 8, 3.4))], lens=26)

BUILDERS = {'sky': build_sky, 'path': build_path, 'hall': build_hall, 'sorcerer': build_sorcerer, 'hoard': build_hoard}

def setup_render(res, samples, out_dir, shot):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.use_persistent_data = True
    w, h = res
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.view_settings.view_transform = 'Standard'   # punchy, clipped 90s-render colours
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = f'{out_dir}/{shot}_'

def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('shot'); ap.add_argument('start', type=int); ap.add_argument('end', type=int); ap.add_argument('out')
    ap.add_argument('--res', default='720x1280'); ap.add_argument('--samples', type=int, default=20)
    ap.add_argument('--engine', default='cycles'); ap.add_argument('--step', type=int, default=1)
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    n = SHOT_FRAMES[a.shot]
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, n
    BUILDERS[a.shot](n)
    setup_render(tuple(int(v) for v in a.res.split('x')), a.samples, a.out, a.shot)
    if a.engine == 'eevee':
        sc.render.engine = 'BLENDER_EEVEE'
        sc.eevee.taa_render_samples = a.samples
        try:
            sc.eevee.use_raytracing = True
        except AttributeError:
            pass
    import time
    for f in range(a.start, a.end + 1, a.step):
        t = time.time()
        sc.frame_set(f)
        sc.render.filepath = f'{a.out}/{a.shot}_{f:04d}.png'
        bpy.ops.render.render(write_still=True)
        print(f'FRAME {a.shot} {f} {time.time() - t:.2f}s', flush=True)

if __name__ == '__main__':
    main()
