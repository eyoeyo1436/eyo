"""Blender sets, lighting, cameras and animation for every shot of the Conjuring Short.

Usage (one shot per process):
    python3 sets3d.py SHOT OUT_DIR MH_DIR [--res 540x960] [--samples 10] [--frames a:b] [--fps 10]
Each shot is animated in its own frame range at --fps; post.py interpolates to 30 fps.
"""
import sys, os, math, random, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

SHOT_LEN = {}          # filled by main() from --dur

# ---------------------------------------------------------------- materials
def hexcol(h, a=1.0):
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple([c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb] + [a])

def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return m, nt, nt.nodes.new('ShaderNodeOutputMaterial')

def N(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items():
        if k.startswith('_'):
            setattr(n, k[1:], v)
        else:
            n.inputs[k.replace('__', ' ')].default_value = v
    return n

def ramp(nt, fac, stops):
    r = nt.nodes.new('ShaderNodeValToRGB')
    el = r.color_ramp.elements
    for i, (pos, c) in enumerate(stops):
        e = el[i] if i < 2 else el.new(pos)
        e.position = pos
        e.color = hexcol(c)
    nt.links.new(fac, r.inputs['Factor'])
    return r.outputs['Color']

def coords(nt, scale=(1, 1, 1), kind='Object'):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = N(nt, 'ShaderNodeMapping', Scale=scale)
    nt.links.new(tc.outputs[kind], mp.inputs['Vector'])
    return mp.outputs['Vector']

def principled(nt, base, rough=0.6, normal=None, spec=0.5):
    p = N(nt, 'ShaderNodeBsdfPrincipled', Roughness=rough)
    p.inputs['Specular IOR Level'].default_value = spec
    if isinstance(base, str):
        p.inputs['Base Color'].default_value = hexcol(base)
    else:
        nt.links.new(base, p.inputs['Base Color'])
    if normal is not None:
        nt.links.new(normal, p.inputs['Normal'])
    return p

def bump(nt, h, s=0.3, d=0.01):
    b = N(nt, 'ShaderNodeBump', Strength=s, Distance=d)
    nt.links.new(h, b.inputs['Height'])
    return b.outputs['Normal']

def finish(nt, out, shader):
    nt.links.new(shader.outputs[0], out.inputs['Surface'])

def mat_plain(name, colr, rough=0.6, noise=0.0, nscale=20.0):
    m, nt, out = new_mat(name)
    base = colr
    nrm = None
    if noise:
        nz = N(nt, 'ShaderNodeTexNoise', Scale=nscale, Detail=10.0, Roughness=0.6)
        nt.links.new(coords(nt), nz.inputs['Vector'])
        c = hexcol(colr)
        dark = '#%02x%02x%02x' % tuple(int(max(0, min(255, (v ** (1 / 2.2)) * 255 * (1 - noise)))) for v in c[:3])
        base = ramp(nt, nz.outputs['Factor'], [(0.3, dark), (0.7, colr)])
        nrm = bump(nt, nz.outputs['Factor'], 0.15, 0.005)
    finish(nt, out, principled(nt, base, rough, nrm))
    return m

def mat_wallpaper(name='wallpaper', c1='#4a5240', c2='#6a6a50', scale=9.0):
    """Faded 1970s damask wallpaper with stains."""
    m, nt, out = new_mat(name)
    v = coords(nt, (scale, scale, scale))
    vo = N(nt, 'ShaderNodeTexVoronoi', _feature='SMOOTH_F1', Randomness=0.0)
    nt.links.new(v, vo.inputs['Vector'])
    wv = N(nt, 'ShaderNodeTexWave', Scale=1.0, Distortion=4.0, Detail=3.0, _bands_direction='Z')
    nt.links.new(v, wv.inputs['Vector'])
    pat = ramp(nt, vo.outputs['Distance'], [(0.25, c2), (0.32, c1), (0.6, c1), (0.66, c2)])
    stain = N(nt, 'ShaderNodeTexNoise', Scale=1.5, Detail=8.0)
    nt.links.new(coords(nt), stain.inputs['Vector'])
    st = ramp(nt, stain.outputs['Factor'], [(0.45, '#ffffff'), (0.75, '#6a5a40')])
    mix = N(nt, 'ShaderNodeMix', _data_type='RGBA', _blend_type='MULTIPLY')
    mix.inputs[0].default_value = 0.8
    nt.links.new(pat, mix.inputs[6]); nt.links.new(st, mix.inputs[7])
    finish(nt, out, principled(nt, mix.outputs[2], 0.75, bump(nt, wv.outputs['Factor'], 0.05, 0.002)))
    return m

def mat_wood(name='floor', c1='#2a1a10', c2='#5a3a22', plank=6.0, rough=0.35):
    """Old varnished floorboards: planks (wave bands) with grain."""
    m, nt, out = new_mat(name)
    v = coords(nt, (1, 1, 1))
    planks = N(nt, 'ShaderNodeTexWave', Scale=plank, Distortion=0.0, Detail=0.0, _bands_direction='X', _wave_profile='SAW')
    nt.links.new(v, planks.inputs['Vector'])
    grain = N(nt, 'ShaderNodeTexWave', Scale=1.2, Distortion=8.0, Detail=10.0, _bands_direction='Y')
    nt.links.new(coords(nt, (1, 12, 1)), grain.inputs['Vector'])
    gcol = ramp(nt, grain.outputs['Factor'], [(0.2, c1), (0.8, c2)])
    seams = ramp(nt, planks.outputs['Factor'], [(0.0, '#000000'), (0.03, '#ffffff')])
    mix = N(nt, 'ShaderNodeMix', _data_type='RGBA', _blend_type='MULTIPLY')
    mix.inputs[0].default_value = 1.0
    nt.links.new(gcol, mix.inputs[6]); nt.links.new(seams, mix.inputs[7])
    finish(nt, out, principled(nt, mix.outputs[2], rough, bump(nt, planks.outputs['Factor'], 0.2, 0.002)))
    return m

def mat_clapboard(name='siding', colr='#b8b4a4'):
    m, nt, out = new_mat(name)
    v = coords(nt, (1, 1, 1))
    wv = N(nt, 'ShaderNodeTexWave', Scale=14.0, Distortion=0.0, Detail=0.0, _bands_direction='Z', _wave_profile='SAW')
    nt.links.new(v, wv.inputs['Vector'])
    dirt = N(nt, 'ShaderNodeTexNoise', Scale=3.0, Detail=10.0)
    nt.links.new(v, dirt.inputs['Vector'])
    col = ramp(nt, dirt.outputs['Factor'], [(0.35, '#6a6658'), (0.7, colr)])
    finish(nt, out, principled(nt, col, 0.8, bump(nt, wv.outputs['Factor'], 0.6, 0.02)))
    return m

def mat_emit(name, colr, strength=5.0):
    m, nt, out = new_mat(name)
    e = N(nt, 'ShaderNodeEmission', Strength=strength)
    e.inputs['Color'].default_value = hexcol(colr)
    nt.links.new(e.outputs[0], out.inputs['Surface'])
    return m

def mat_glass(name='glass'):
    m, nt, out = new_mat(name)
    p = N(nt, 'ShaderNodeBsdfPrincipled', Roughness=0.05)
    p.inputs['Base Color'].default_value = hexcol('#1a2228')
    p.inputs['Coat Weight'].default_value = 1.0
    finish(nt, out, p)
    return m

def mat_curtain(name='curtain', colr='#c8bca0', glow=0.0):
    m, nt, out = new_mat(name)
    p = N(nt, 'ShaderNodeBsdfPrincipled', Roughness=0.9)
    p.inputs['Base Color'].default_value = hexcol(colr)
    p.inputs['Sheen Weight'].default_value = 0.5
    p.inputs['Transmission Weight'].default_value = 0.0
    if glow:
        p.inputs['Emission Color'].default_value = hexcol('#ffcf8a'); p.inputs['Emission Strength'].default_value = glow
    finish(nt, out, p)
    return m

def fog_material(name='fog', density=0.03, colr='#a8b4c0', anisotropy=0.4):
    m, nt, out = new_mat(name)
    v = N(nt, 'ShaderNodeVolumePrincipled', Density=density, Anisotropy=anisotropy)
    v.inputs['Color'].default_value = hexcol(colr)
    nt.links.new(v.outputs[0], out.inputs['Volume'])
    return m

# ---------------------------------------------------------------- geometry
def assign(o, m):
    o.data.materials.clear(); o.data.materials.append(m); return o

def box(loc, size, m, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new('bev', 'BEVEL'); b.width = bevel; b.segments = 2
    return assign(o, m)

def cyl(loc, r, depth, m, verts=24, rot=(0, 0, 0), r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    for p in o.data.polygons:
        p.use_smooth = True
    return assign(o, m)

def plane(loc, size, m, rot=(0, 0, 0), subdiv=0):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = (size[0], size[1], 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if subdiv:
        mod = o.modifiers.new('sub', 'SUBSURF'); mod.levels = subdiv; mod.render_levels = subdiv; mod.subdivision_type = 'SIMPLE'
    return assign(o, m)

def displace(o, strength=0.05, scale=0.5, kind='CLOUDS', seed=0):
    tex = bpy.data.textures.new(f'd{seed}{o.name}', kind)
    if kind == 'CLOUDS':
        tex.noise_scale = scale; tex.noise_depth = 3
    else:
        tex.noise_scale = scale
    d = o.modifiers.new('disp', 'DISPLACE'); d.texture = tex; d.strength = strength; d.texture_coords = 'GLOBAL'
    return o

def light(kind, loc, energy, colr, rot=(0, 0, 0), size=0.2, spot=0.8, blend=0.3):
    bpy.ops.object.light_add(type=kind, location=loc, rotation=rot)
    l = bpy.context.object
    l.data.energy = energy
    l.data.color = hexcol(colr)[:3]
    if kind == 'AREA':
        l.data.size = size
    elif kind == 'SPOT':
        l.data.spot_size = spot; l.data.spot_blend = blend; l.data.shadow_soft_size = size
    elif kind in ('POINT',):
        l.data.shadow_soft_size = size
    elif kind == 'SUN':
        l.data.angle = size
    return l

def aim(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def fog_box(center, size, density, colr='#9aa8b4', aniso=0.45):
    o = box(center, size, fog_material('fog', density, colr, aniso))
    o.visible_shadow = False
    return o

def camera(keys, lens=30, fstop=0.0, focus=None):
    """keys: list of (frame, loc, target)."""
    bpy.ops.object.camera_add(location=keys[0][1])
    cam = bpy.context.object
    cam.data.lens = lens
    cam.data.sensor_width = 24
    cam.data.clip_start = 0.02
    bpy.context.scene.camera = cam
    bpy.ops.object.empty_add(location=keys[0][2])
    tgt = bpy.context.object
    tc = cam.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
    for f, loc, t in keys:
        cam.location = loc; cam.keyframe_insert('location', frame=f)
        tgt.location = t; tgt.keyframe_insert('location', frame=f)
    if fstop:
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = fstop
        if focus is not None:
            if isinstance(focus, (int, float)):
                cam.data.dof.focus_distance = focus
            else:
                bpy.ops.object.empty_add(location=focus); cam.data.dof.focus_object = bpy.context.object
        else:
            cam.data.dof.focus_object = tgt
    return cam

def keyframes(obj, path, items):
    for f, val in items:
        setattr(obj, path, val)
        obj.keyframe_insert(path, frame=f)

def world(colr='#05070a', strength=1.0):
    w = bpy.data.worlds.new('w')
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = hexcol(colr)
    bg.inputs['Strength'].default_value = strength
    bpy.context.scene.world = w

# ---------------------------------------------------------------- set pieces
def holed_box(loc, size, mat, hole_loc, hole_size):
    """A wall slab with a rectangular opening (boolean difference)."""
    o = box(loc, size, mat)
    c = box(hole_loc, hole_size, mat)
    c.hide_render = True; c.hide_viewport = True
    b = o.modifiers.new('hole', 'BOOLEAN'); b.operation = 'DIFFERENCE'; b.object = c; b.solver = 'EXACT'
    return o

def door(loc, w=0.82, h=2.0, rot_z=0.0, open_keys=None, colr='#3a2a1e', hinge_side=1, frame_col='#2a1e16'):
    """Panelled wooden door on a hinge (empty). open_keys: [(frame, angle_rad)]."""
    x, y, z = loc
    bpy.ops.object.empty_add(location=(x - hinge_side * w / 2 * math.cos(rot_z), y - hinge_side * w / 2 * math.sin(rot_z), z), rotation=(0, 0, rot_z))
    hinge = bpy.context.object
    wood = mat_plain('door_wood', colr, 0.5, noise=0.35, nscale=6)
    leaf = box((x, y, z + h / 2), (w, 0.045, h), wood, rot=(0, 0, rot_z), bevel=0.004)
    for k, (pz, ph) in enumerate(((0.32, 0.5), (1.0, 0.75), (1.62, 0.5))):
        for sx in (-0.2, 0.2):
            px = x + sx * math.cos(rot_z); py = y + sx * math.sin(rot_z)
            pn = box((px - 0.025 * math.sin(rot_z), py - 0.025 * math.cos(rot_z), z + pz), (0.26, 0.012, ph * 0.8), wood, rot=(0, 0, rot_z), bevel=0.006)
            pn.parent = hinge; pn.matrix_parent_inverse = hinge.matrix_world.inverted()
    knob = cyl((x + hinge_side * (w / 2 - 0.08) * math.cos(rot_z), y - 0.04, z + 0.98), 0.028, 0.06, mat_plain('brass', '#8a6a30', 0.25), rot=(math.pi / 2, 0, rot_z))
    for o in (leaf, knob):
        o.parent = hinge; o.matrix_parent_inverse = hinge.matrix_world.inverted()
    fr = mat_plain('door_frame', frame_col, 0.5)
    for sx in (-1, 1):
        box((x + sx * (w / 2 + 0.05) * math.cos(rot_z), y + sx * (w / 2 + 0.05) * math.sin(rot_z), z + h / 2), (0.1, 0.16, h + 0.1), fr, rot=(0, 0, rot_z))
    box((x, y, z + h + 0.05), (w + 0.2, 0.16, 0.1), fr, rot=(0, 0, rot_z))
    if open_keys:
        for f, ang in open_keys:
            hinge.rotation_euler = (0, 0, rot_z + hinge_side * ang)
            hinge.keyframe_insert('rotation_euler', frame=f)
    return hinge

def picture_frame(loc, size, rot_z=0.0, seed=0):
    rnd = random.Random(seed)
    fr = mat_plain('pframe', '#3a2a14', 0.35)
    x, y, z = loc
    box(loc, (size[0] + 0.06, 0.03, size[1] + 0.06), fr, rot=(0, 0, rot_z))
    img = mat_plain(f'painting{seed}', rnd.choice(['#4a4a3a', '#3a4248', '#504036']), 0.8, noise=0.6, nscale=4)
    box((x - 0.018 * math.sin(rot_z), y - 0.018 * math.cos(rot_z), z), (size[0], 0.01, size[1]), img, rot=(0, 0, rot_z))

def hallway(length=8.0, width=1.5, height=2.5, doors=(), window_end=True, seed=1):
    """Corridor along +Y from y=0 to y=length. Returns nothing; walls, floor, ceiling, trim, frames."""
    wp = mat_wallpaper()
    floor = mat_wood()
    ceil = mat_plain('ceiling', '#7a7666', 0.9, noise=0.4, nscale=2)
    trim = mat_plain('trim', '#4a3828', 0.4)
    box((0, length / 2, -0.05), (width, length + 2, 0.1), floor)
    box((0, length / 2, height + 0.05), (width, length + 2, 0.1), ceil)
    for side in (-1, 1):
        box((side * (width / 2 + 0.05), length / 2, height / 2), (0.1, length + 2, height), wp)
        box((side * (width / 2 - 0.01), length / 2, 0.06), (0.03, length + 2, 0.12), trim)
        box((side * (width / 2 - 0.01), length / 2, 0.9), (0.025, length + 2, 0.04), trim)
    holed_box((0, length + 1.0, height / 2), (width, 0.1, height), wp, (0, length + 1.0, 1.45), (0.75, 0.4, 1.1))
    rnd = random.Random(seed)
    for k in range(int(length / 1.8)):
        side = 1 if k % 2 else -1
        y = 0.8 + k * 1.8
        if any(abs(y - dy) < 0.8 for dy, _ in doors):
            continue
        picture_frame((side * (width / 2 - 0.02), y, 1.6 + rnd.uniform(-0.1, 0.1)), (rnd.uniform(0.3, 0.5), rnd.uniform(0.35, 0.55)),
                      rot_z=side * math.pi / 2, seed=k)
    if window_end:
        fr = mat_plain('winframe', '#d8d4c8', 0.6)
        for dz in (-0.55, 0.0, 0.55):
            box((0, length + 0.92, 1.45 + dz), (0.8, 0.06, 0.05), fr)
        for dx in (-0.4, 0.0, 0.4):
            box((dx, length + 0.92, 1.45), (0.05, 0.06, 1.15), fr)
        light('AREA', (0, length + 1.6, 1.7), 900, '#8fa8c8', rot=(-math.pi / 2 + 0.25, 0, 0), size=1.2)

def bed(loc, rot_z=0.0):
    x, y, z = loc
    frame = mat_plain('bedframe', '#3a2618', 0.45, noise=0.3)
    sheet = mat_plain('sheet', '#b8b4a8', 0.85, noise=0.25, nscale=8)
    box((x, y, 0.25), (1.0, 2.0, 0.3), frame, rot=(0, 0, rot_z))
    box((x, y - 1.0, 0.55), (1.05, 0.06, 0.9), frame, rot=(0, 0, rot_z))
    s = plane((x, y + 0.1, 0.48), (1.15, 1.9), sheet, subdiv=5)
    displace(s, 0.06, 0.25, seed=3)
    box((x, y - 0.75, 0.5), (0.6, 0.3, 0.12), sheet, bevel=0.05)

def wardrobe(loc, rot_z=0.0, door_open=0.0, open_keys=None):
    """Hollow wardrobe (back, sides, top, bottom) with two hinged doors; the right one can open."""
    x, y, z = loc
    wood = mat_plain('wardrobe_wood', '#2e2016', 0.45, noise=0.35, nscale=5)
    dark = mat_plain('wardrobe_inside', '#0a0806', 0.9)
    box((x, y + 0.28, 1.0), (1.1, 0.04, 2.0), dark)
    for sx in (-1, 1):
        box((x + sx * 0.53, y, 1.0), (0.04, 0.6, 2.0), wood, bevel=0.005)
    box((x, y, 2.05), (1.2, 0.66, 0.1), wood, bevel=0.01)
    box((x, y, 0.05), (1.1, 0.6, 0.1), wood)
    hinges = []
    for side in (-1, 1):
        bpy.ops.object.empty_add(location=(x + side * 0.51, y - 0.31, 0.1))
        h = bpy.context.object
        leaf = box((x + side * 0.255, y - 0.31, 1.05), (0.5, 0.03, 1.85), wood, bevel=0.005)
        leaf.parent = h; leaf.matrix_parent_inverse = h.matrix_world.inverted()
        if side == 1:
            h.rotation_euler = (0, 0, door_open)
            if open_keys:
                for f, a in open_keys:
                    h.rotation_euler = (0, 0, a); h.keyframe_insert('rotation_euler', frame=f)
        hinges.append(h)
    return hinges

def farmhouse(loc=(0, 0, 0), window_lit=True):
    """Two-storey white clapboard farmhouse with gable roof, porch and an upstairs window."""
    x, y, z = loc
    siding = mat_clapboard()
    roof = mat_plain('shingles', '#2a2a2c', 0.8, noise=0.6, nscale=30)
    trim = mat_plain('house_trim', '#d0ccc0', 0.6)
    house = box((x, y, 3.0), (9.0, 7.0, 6.0), siding)
    tx, tz = x - 3.2 + 2 * 2.15, 4.6
    cutter = box((tx, y - 3.0, tz), (0.9, 1.6, 1.4), siding)
    cutter.hide_render = True; cutter.hide_viewport = True
    bo = house.modifiers.new('win', 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.object = cutter; bo.solver = 'EXACT'
    room_glow = mat_emit('room_glow', '#ffb46a', 1.3)
    box((tx, y - 2.0, tz), (2.0, 0.05, 2.2), room_glow)                       # lit back wall of the room
    for sx in (-1, 1):
        box((tx + sx * 0.9, y - 2.75, tz), (0.05, 1.5, 2.2), mat_plain('room_wall', '#5a4a3a', 0.8))
    box((tx, y - 2.75, tz - 0.75), (1.8, 1.5, 0.05), mat_plain('room_floor', '#3a2a1e', 0.8))
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=6.6, radius2=0.0, depth=3.4, location=(x, y, 7.7), rotation=(0, 0, math.pi / 4))
    r = bpy.context.object; r.scale = (1.0, 0.82, 1.0); assign(r, roof)
    box((x + 2.6, y + 1.0, 8.6), (0.8, 0.8, 2.6), mat_plain('chimney', '#4a2e26', 0.8, noise=0.5, nscale=12))
    box((x, y - 4.2, 0.25), (9.6, 1.6, 0.5), mat_wood('porch_floor', '#2a2620', '#4a4236', 3.0, 0.7))
    pr = box((x, y - 4.3, 3.1), (9.8, 1.9, 0.18), roof, rot=(0.18, 0, 0))
    for k in range(6):
        cyl((x - 4.5 + k * 1.8, y - 4.9, 1.6), 0.08, 2.8, trim, verts=12)
    lit = mat_emit('window_lit', '#ffb860', 2.5)
    dark = mat_glass()
    wins = []
    for row, wz in ((0, 1.9), (1, 4.6)):
        for col in range(4):
            wx = x - 3.2 + col * 2.15
            is_target = (row == 1 and col == 2)
            mat = (mat_emit('window_dim', '#ff9a40', 0.6) if (row == 0 and col == 1) else dark)
            if not is_target:
                wins.append(box((wx, y - 3.52, wz), (0.9, 0.05, 1.4), mat))
            for dx in (-0.5, 0.5):
                box((wx + dx, y - 3.55, wz), (0.12, 0.08, 1.5), trim)
            box((wx, y - 3.55, wz + 0.75), (1.1, 0.1, 0.1), trim)
            box((wx, y - 3.55, wz), (0.05, 0.07, 1.4), trim)
    box((x - 0.9, y - 3.52, 1.25), (1.0, 0.08, 2.2), mat_plain('front_door', '#2a1a14', 0.5))
    return (tx, y - 3.5, tz)

def bare_tree(loc, height=11.0, seed=2):
    """The gnarled tree beside the farmhouse: recursive branching cylinders."""
    bark = mat_plain('bark', '#2a241e', 0.9, noise=0.6, nscale=30)
    rnd = random.Random(seed)
    def branch(p, d, length, radius, depth):
        end = p + d * length
        mid = (p + end) / 2
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=radius, radius2=radius * 0.65, depth=length, location=mid)
        o = bpy.context.object
        o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
        assign(o, bark)
        if depth == 0:
            return
        for k in range(rnd.choice((2, 3))):
            nd = (d + Vector((rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), rnd.uniform(-0.1, 0.5)))).normalized()
            branch(end, nd, length * rnd.uniform(0.55, 0.75), radius * 0.62, depth - 1)
    branch(Vector(loc), Vector((0.05, 0.0, 1.0)).normalized(), height * 0.42, 0.45, 5)

def entity(loc, rot_z=0.0, scale=1.0, mh_dir='', silhouette=True, expr=None, look=(0, 0)):
    import human
    human.MH_DIR = mh_dir
    return human.build_character('entity', loc=loc, rot_z=rot_z, scale=scale, silhouette=silhouette, outfit=False,
                                 hair_n=3500, expr=expr or {'mouth_open': 0.3, 'eyes_wide': 1.0}, look=look,
                                 arms={'down': 0.62})

def warren(who, loc, rot_z=0.0, mh_dir='', expr=None, look=(0, 0), arms=None, hair_n=None):
    import human
    human.MH_DIR = mh_dir
    return human.build_character(who, loc=loc, rot_z=rot_z, expr=expr, look=look, arms=arms, hair_n=hair_n)

def flashlight(loc, target, energy=180, spot=0.42, body=True):
    l = light('SPOT', loc, energy, '#fff1d6', size=0.02, spot=spot, blend=0.35)
    aim(l, target)
    if body:
        d = (Vector(target) - Vector(loc)).normalized()
        o = cyl(tuple(Vector(loc) - d * 0.14), 0.022, 0.2, mat_plain('torch', '#2a2a2a', 0.3), verts=12)
        o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return l

# ---------------------------------------------------------------- shots
def s_farm_ext(n, mh):
    world('#141c28', 1.0)
    win = farmhouse((0, 14, 0))
    bare_tree((-4.8, 8.5, 0), height=12.0)
    light('AREA', (0, 2, 9), 900, '#8aa0c0', rot=(math.radians(40), 0, 0), size=12)
    ground = plane((0, 8, 0), (80, 80), mat_plain('grass', '#1c2218', 0.95, noise=0.6, nscale=3), subdiv=4)
    displace(ground, 0.25, 4.0, seed=5)
    light('SUN', (0, 0, 20), 1.6, '#7d94b8', rot=(math.radians(55), 0, math.radians(-30)), size=0.02)
    light('POINT', (-0.9, 9.6, 2.6), 150, '#ffb060', size=0.15)          # porch light
    light('POINT', (win[0], win[1] + 1.2, win[2] + 0.6), 120, '#ffb060', size=0.3)
    # silhouette in the upstairs window (appears, then gone)
    fig = entity((win[0], win[1] + 0.55, win[2] - 2.2), rot_z=0.0, scale=1.0, mh_dir=mh)
    objs = [o for o in bpy.data.objects if o.name.startswith('entity')]
    appear, gone = int(n * 0.28), int(n * 0.86)
    for o in objs:
        for f, hide in ((1, True), (appear, False), (gone, True)):
            o.hide_render = hide
            o.keyframe_insert('hide_render', frame=f)
    fog_box((0, 6, 1.5), (60, 40, 3.0), 0.025, '#8a98a8')
    camera([(1, (-1.0, -5.5, 1.4), (win[0] - 0.6, 14, 4.3)), (n, (-0.2, -3.6, 1.5), (win[0] - 0.2, 14, 4.4))], lens=26)

def s_window_close(n, mh):
    world('#141c28', 0.8)
    win = farmhouse((0, 14, 0))
    light('SUN', (0, 0, 20), 1.6, '#7d94b8', rot=(math.radians(55), 0, math.radians(-30)), size=0.02)
    light('AREA', (win[0], win[1] - 6, win[2] + 3), 400, '#8aa0c0', rot=(math.radians(60), 0, 0), size=6)
    light('POINT', (win[0], win[1] + 1.2, win[2] + 0.6), 120, '#ffb060', size=0.3)
    # curtain behind the glass, swaying
    cur = plane((win[0] + 0.15, win[1] + 0.25, win[2]), (0.5, 1.4), mat_curtain('curtain', '#d8c8a0', 0.4), rot=(math.pi / 2, 0, 0), subdiv=4)
    displace(cur, 0.06, 0.3, seed=9)
    keyframes(cur, 'location', [(1, cur.location.copy()), (n, Vector((win[0] + 0.05, win[1] + 0.2, win[2])))])
    fog_box((0, 6, 3.0), (30, 30, 6.0), 0.02, '#8a98a8')
    camera([(1, (win[0] - 1.6, win[1] - 7.0, win[2] - 0.8), win), (n, (win[0] - 1.0, win[1] - 4.6, win[2] - 0.5), win)], lens=35)

def s_hallway(n, mh):
    world('#020304', 1.0)
    hallway(9.0, doors=((4.5, 1),))
    door((0.76, 4.5, 0), rot_z=math.pi / 2, hinge_side=-1)
    light('POINT', (0, 2.5, 2.35), 70, '#ffc680', size=0.08)
    fog_box((0, 4.5, 1.25), (1.6, 12, 2.6), 0.05, '#9aa6b4')
    camera([(1, (0.25, -0.6, 1.55), (0, 9, 1.4)), (n, (0.15, 1.6, 1.5), (0, 9, 1.45))], lens=24, fstop=4.0, focus=6.0)

def s_door_opens(n, mh):
    world('#020304', 1.0)
    hallway(9.0, doors=((3.0, 1),))
    door((0.76, 3.0, 0), rot_z=math.pi / 2, hinge_side=-1,
         open_keys=[(1, 0.0), (int(n * 0.2), 0.02), (int(n * 0.85), 0.75), (n, 0.8)])
    box((2.2, 3.0, 1.25), (2.6, 2.6, 2.6), mat_plain('void', '#000000', 1.0))     # darkness beyond
    light('POINT', (-0.3, 1.0, 2.3), 55, '#ffc680', size=0.08)
    l = light('SPOT', (-0.6, 0.0, 1.9), 120, '#ffd7a0', size=0.1, spot=0.6, blend=0.6)
    aim(l, (0.7, 3.0, 1.1))
    fog_box((0, 4.5, 1.25), (1.6, 12, 2.6), 0.05, '#9aa6b4')
    camera([(1, (-0.55, 0.6, 1.45), (0.7, 3.0, 1.2)), (n, (-0.45, 1.3, 1.4), (0.7, 3.05, 1.15))], lens=30, fstop=2.8)

def s_shadow_wall(n, mh):
    world('#020304', 1.0)
    hallway(9.0, doors=())
    light('POINT', (-0.62, 3.0, 1.15), 90, '#ffcf96', size=0.04)               # a table lamp on the left
    box((-0.6, 3.0, 0.4), (0.3, 0.4, 0.8), mat_plain('table', '#3a2a1c', 0.5))
    light('POINT', (0, 0.0, 2.35), 12, '#ffc680', size=0.08)
    entity((0, 0, 0.0), rot_z=math.pi / 2, scale=1.02, mh_dir=mh)
    objs = [o for o in bpy.data.objects if o.name.startswith('entity')]
    bpy.ops.object.empty_add(location=(0, 0, 0))
    mover = bpy.context.object
    for o in objs:
        o.visible_camera = False
        o.parent = mover
    keyframes(mover, 'location', [(1, Vector((-0.25, 5.2, 0))), (n, Vector((-0.2, 0.6, 0)))])
    fog_box((0, 4.5, 1.25), (1.6, 12, 2.6), 0.03, '#9aa6b4')
    camera([(1, (-0.5, -0.6, 1.5), (0.75, 2.8, 1.35)), (n, (-0.48, -0.1, 1.5), (0.75, 2.6, 1.35))], lens=26)

def bedroom(window=True):
    wp = mat_wallpaper('bed_wallpaper', '#3e4a4e', '#5a6666', 11.0)
    box((0, 0, -0.05), (6, 6, 0.1), mat_wood('bed_floor'))
    box((0, 0, 2.65), (6, 6, 0.1), mat_plain('bceil', '#6a6a60', 0.9))
    for (x, y, sx, sy) in ((0, 3.0, 6, 0.1), (0, -3.0, 6, 0.1), (3.0, 0, 0.1, 6)):
        box((x, y, 1.3), (sx, sy, 2.6), wp)
    if window:
        holed_box((-3.0, 0, 1.3), (0.1, 6, 2.6), wp, (-3.0, 0.4, 1.5), (0.4, 0.9, 1.2))
        light('AREA', (-3.6, 0.4, 2.0), 700, '#8aa4c8', rot=(0, math.radians(-90) + 0.35, 0), size=1.2)
        light('AREA', (0, 0, 2.55), 20, '#6a7a90', size=4.0)
        for dz in (-0.6, 0, 0.6):
            box((-2.94, 0.4, 1.5 + dz), (0.06, 0.95, 0.05), mat_plain('wf', '#c8c4b8'))
        for dy in (-0.45, 0, 0.45):
            box((-2.94, 0.4 + dy, 1.5), (0.06, 0.05, 1.25), mat_plain('wf', '#c8c4b8'))

def s_bedroom(n, mh):
    world('#020304', 1.0)
    bedroom()
    bed((-0.6, 0.6, 0))
    wardrobe((1.9, 2.55, 0), door_open=0.25)
    box((0.6, -0.6, 0.35), (0.45, 0.4, 0.7), mat_plain('nightstand', '#3a2a1c', 0.5))
    cyl((0.6, -0.6, 0.85), 0.08, 0.3, mat_plain('lampbase', '#6a5a40', 0.3))
    fog_box((0, 0, 1.3), (5.8, 5.8, 2.6), 0.045, '#8e9cac')
    camera([(1, (2.4, -2.6, 1.7), (-0.4, 1.4, 0.8)), (n, (2.0, -2.1, 1.6), (-0.2, 1.6, 0.9))], lens=22, fstop=5.6, focus=3.5)

def s_wardrobe(n, mh):
    world('#020304', 1.0)
    bedroom()
    wardrobe((0, 2.55, 0), open_keys=[(1, 1.05), (n, 1.4)])
    # the figure behind the wardrobe door: a pale face edge and an eye catch the moonlight
    entity((0.22, 2.6, 0.0), rot_z=0.15, scale=0.98, mh_dir=mh, silhouette=False,
           expr={'mouth_open': 0.45, 'eyes_wide': 1.0, 'brow_up': -0.5}, look=(-0.25, 0.0))
    l = light('SPOT', (1.3, 1.7, 2.2), 140, '#9ab4d8', size=0.05, spot=0.35, blend=0.5)
    aim(l, (0.3, 2.35, 1.55))
    fog_box((0, 2.2, 1.3), (5.8, 1.5, 2.6), 0.03, '#8e9cac')
    camera([(1, (-0.35, 0.55, 1.6), (0.2, 2.45, 1.52)), (n, (-0.22, 0.9, 1.62), (0.2, 2.45, 1.55))], lens=40, fstop=2.8)

def s_corner(n, mh):
    world('#020304', 1.0)
    bedroom()
    bed((0.8, 0.4, 0))
    entity((-2.55, 2.5, 0.0), rot_z=math.radians(-135) + math.pi, scale=1.06, mh_dir=mh)
    fog_box((0, 0, 1.3), (5.8, 5.8, 2.6), 0.05, '#8e9cac')
    l = light('AREA', (-0.8, 1.0, 2.5), 160, '#8aa4c8', size=1.2)            # moonlight washing the corner walls
    aim(l, (-2.8, 2.8, 1.2))
    camera([(1, (2.2, -2.4, 1.5), (-2.4, 2.4, 1.3)), (n, (1.7, -1.9, 1.5), (-2.4, 2.4, 1.35))], lens=30, fstop=5.6, focus=6.0)

def s_warrens_enter(n, mh):
    world('#020304', 1.0)
    hallway(9.0, window_end=True)
    ed = warren('ed', (0.32, 2.2, 0), rot_z=math.radians(-8), mh_dir=mh, expr={'brow_up': 0.7, 'brow_in': 0.5, 'corners': 0.3},
                look=(0.25, 0.08), arms={'down': 0.55, 'elbow': 1.25, 'elbow_r': 0.0}, hair_n=4000)
    lo = warren('lorraine', (-0.28, 2.6, 0), rot_z=math.radians(10), mh_dir=mh,
                expr={'brow_up': 0.9, 'brow_in': 0.6, 'eyes_wide': 0.4, 'mouth_open': 0.15}, look=(-0.2, 0.1),
                arms={'down': 0.58, 'elbow': 0.25}, hair_n=5000)
    # Ed's flashlight beam leads into the dark; a dim bulb behind them
    flashlight((0.48, 1.85, 1.25), (1.5, -3.0, 0.6), energy=90, spot=0.5)
    light('AREA', (0.2, 0.6, 1.6), 18, '#ffd8a8', rot=(math.radians(80), 0, 0), size=0.8)   # bounce from the beam
    light('POINT', (0, 6.0, 2.35), 25, '#ffc680', size=0.08)
    fog_box((0, 4.5, 1.25), (1.6, 12, 2.6), 0.05, '#9aa6b4')
    keyframes(ed['hair'], 'location', [(1, Vector((0, 0, 0))), (n, Vector((0, 0, 0)))])
    camera([(1, (0.05, -0.35, 1.55), (0.0, 2.4, 1.45)), (n, (0.02, 0.25, 1.55), (0.0, 2.4, 1.48))], lens=32, fstop=3.2, focus=2.3)

def s_lorraine_close(n, mh):
    world('#020304', 1.0)
    hallway(9.0)
    warren('lorraine', (0, 0, 0), rot_z=math.radians(12), mh_dir=mh,
           expr={'brow_up': 1.0, 'brow_in': 0.7, 'eyes_wide': 0.6, 'mouth_open': 0.25, 'corners': 0.2}, look=(-0.15, 0.22),
           arms={'down': 0.58, 'elbow': 0.2})
    l = light('SPOT', (0.5, -0.8, 1.1), 40, '#fff0d4', size=0.05, spot=0.5, blend=0.5)
    aim(l, (0, 0, 1.55))
    light('AREA', (-0.6, 0.6, 1.9), 12, '#7f98c0', rot=(math.radians(-120), 0, math.radians(-140)), size=0.6)
    fog_box((0, 2.0, 1.25), (1.6, 8, 2.6), 0.04, '#9aa6b4')
    camera([(1, (0.22, -1.3, 1.5), (0, 0, 1.5)), (n, (0.16, -1.08, 1.51), (0, 0, 1.51))], lens=50, fstop=2.2)

def s_ed_close(n, mh):
    world('#020304', 1.0)
    hallway(9.0)
    warren('ed', (0, 0, 0), rot_z=math.radians(-15), mh_dir=mh, expr={'brow_up': 0.8, 'brow_in': 0.8, 'corners': 0.35, 'eyes_wide': 0.3},
           look=(0.3, 0.05), arms={'down': 0.55, 'elbow': 1.2, 'elbow_r': 0.0})
    flashlight((0.2, -0.25, 1.22), (0.6, -3.0, 1.4), energy=60, spot=0.5)
    l = light('SPOT', (-0.6, -0.6, 1.25), 25, '#ffe8c4', size=0.05, spot=0.6, blend=0.6)
    aim(l, (0, 0, 1.6))
    light('AREA', (0.6, 0.7, 1.9), 14, '#7f98c0', rot=(math.radians(-120), 0, math.radians(140)), size=0.6)
    fog_box((0, 2.0, 1.25), (1.6, 8, 2.6), 0.04, '#9aa6b4')
    camera([(1, (-0.3, -1.35, 1.6), (0, 0, 1.58)), (n, (-0.24, -1.12, 1.6), (0, 0, 1.59))], lens=50, fstop=2.2)

def s_warrens_back(n, mh):
    world('#020304', 1.0)
    hallway(12.0)
    warren('ed', (0.3, 0.6, 0), rot_z=math.pi, mh_dir=mh, arms={'down': 0.55, 'elbow': 1.2, 'elbow_r': 0.0}, hair_n=3500)
    warren('lorraine', (-0.3, 0.75, 0), rot_z=math.pi, mh_dir=mh, arms={'down': 0.58, 'elbow': 0.2}, hair_n=4500)
    flashlight((0.45, 0.95, 1.25), (0.0, 12.0, 1.0), energy=260, spot=0.38)
    light('POINT', (0, 6.0, 2.35), 30, '#ffc680', size=0.08)
    fog_box((0, 6, 1.25), (1.6, 16, 2.6), 0.06, '#9aa6b4')
    camera([(1, (0.0, -1.3, 1.65), (0, 10, 1.3)), (n, (0.0, -0.9, 1.65), (0, 10, 1.3))], lens=26, fstop=4.0, focus=2.0)

def s_hall_end(n, mh):
    world('#020304', 1.0)
    hallway(12.0, window_end=True)
    entity((0, 11.8, 0), rot_z=math.pi, scale=1.05, mh_dir=mh)       # faces the camera, motionless
    light('POINT', (0, 3.0, 2.35), 25, '#ffc680', size=0.08)
    fog_box((0, 6, 1.25), (1.6, 16, 2.6), 0.06, '#9aa6b4')
    camera([(1, (0.0, -0.8, 1.6), (0, 12, 1.35)), (int(n * 0.6), (0.0, 3.6, 1.58), (0, 12, 1.4)), (n, (0.0, 7.4, 1.55), (0, 12, 1.5))], lens=26)

SHOTS = {
    'farm_ext': s_farm_ext, 'window_close': s_window_close, 'hallway': s_hallway, 'door_opens': s_door_opens,
    'shadow_wall': s_shadow_wall, 'bedroom': s_bedroom, 'wardrobe': s_wardrobe, 'corner': s_corner,
    'warrens_enter': s_warrens_enter, 'lorraine_close': s_lorraine_close, 'ed_close': s_ed_close,
    'warrens_back': s_warrens_back, 'hall_end': s_hall_end,
}

def setup(res, samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.volume_bounces = 1
    sc.cycles.transparent_max_bounces = 32
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.volume_step_rate = 4.0
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.view_settings.exposure = 0.6
    sc.render.image_settings.file_format = 'PNG'
    for o in bpy.data.objects:          # lamps light the scene but are never seen directly
        if o.type == 'LIGHT':
            o.visible_camera = False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shot'); ap.add_argument('out'); ap.add_argument('mh')
    ap.add_argument('--res', default='540x960'); ap.add_argument('--samples', type=int, default=10)
    ap.add_argument('--dur', type=float, required=True); ap.add_argument('--fps', type=int, default=10)
    ap.add_argument('--frames', default=None); ap.add_argument('--step', type=int, default=1)
    a = ap.parse_args(sys.argv[1:])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    n = int(math.ceil(a.dur * a.fps)) + 1
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, n
    sc.render.fps = a.fps
    t = time.time()
    SHOTS[a.shot](n, a.mh)
    print(f'BUILD {a.shot} {time.time() - t:.1f}s frames={n}', flush=True)
    setup(tuple(int(v) for v in a.res.split('x')), a.samples)
    f0, f1 = (1, n) if not a.frames else tuple(int(v) for v in a.frames.split(':'))
    for f in range(f0, f1 + 1, a.step):
        t = time.time()
        sc.frame_set(f)
        sc.render.filepath = os.path.join(a.out, f'{a.shot}_{f:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'FRAME {a.shot} {f}/{n} {time.time() - t:.2f}s', flush=True)

if __name__ == '__main__':
    main()
