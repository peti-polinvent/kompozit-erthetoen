"""
infusion_layout.py – a vákuuminfúziós összeállítás GEOMETRIÁJA, eszközfüggetlenül
===================================================================================

Ez a modul NEM használ sem Blendert, sem Fusiont: tiszta Python, ami a
params.json-ból kiszámolja, hogy melyik test hol van és mekkora (mm-ben).
Ugyanezt a modult importálja

  * a Fusion 360 szkript  (fusion/KompozitInfuzio/KompozitInfuzio.py)  → CAD testek
  * a Blender építő        (blender/build_infusion.py)                 → primitívek
  * a Blender animáló      (blender/animate_fusion_export.py)          → Fusion-export anim.

Így egyetlen helyen van a "mi hol van" tudás; ha a rétegrend vagy a
szerszám változik, mindhárom eszköz ugyanazt az összeállítást adja.

Koordináta-rendszer: X = a panel hossza (gyanta a -X oldalon lép be, a +X
oldalon szívjuk el), Y = szélesség, Z = fel. Origó: az asztal közepe, padlószint.
Minden méret mm.

Egy "item" szótár mezői:
  key         ASCII azonosító (fájlnév az exporthoz, pl. "L03_glass")
  name        megjelenített (magyar) név
  kind        "box" | "cyl" | "tube"
  collection  Blender-gyűjtemény / Fusion-komponens neve
  color, alpha, roughness, metallic   megjelenés
  box:  size_mm [x,y,z], center_mm [x,y,z]
  cyl:  radius_mm, p1_mm, p2_mm   (a tengely két végpontja)
  tube: radius_mm, points_mm [...] (töröttvonal, a csövezéshez)
  rétegeknél: layer_index, layer_type, thickness_mm (valós)
"""

# ráhagyások rétegtípusonként: (túlnyúlás -X, túlnyúlás +X, túlnyúlás Y) mm
# A gyantavezető háló az elszívó oldal ELŐTT 40 mm-rel véget ér – így a gyanta
# nem rohan egyből a vákuumcsőbe, előbb átitatja a laminátumot.
OVERSIZE = {
    "release": (40, 40, 40),
    "gelcoat": (0, 0, 0),
    "glass": (0, 0, 0),
    "carbon": (0, 0, 0),
    "peelply": (15, 15, 15),
    "flowmesh": (15, -40, 10),
    "bag": (120, 120, 100),
}

ROUGH = {"glass": 0.9, "carbon": 0.8, "peelply": 0.9, "release": 0.4,
         "gelcoat": 0.3, "flowmesh": 0.6, "bag": 0.2}


def _box(key, name, size, center, collection, color, alpha=1.0, roughness=0.6, metallic=0.0,
         dir_len=(1, 0, 0), dir_wid=(0, 1, 0), **extra):
    """dir_len / dir_wid: a hasáb hossz- és szélességi iránya (egységvektor, egymásra
    merőleges). Alapból X és Y; döntött lapokhoz (vákuumfólia oldalai) más."""
    d = dict(key=key, name=name, kind="box", size_mm=list(size), center_mm=list(center),
             dir_len=list(dir_len), dir_wid=list(dir_wid),
             collection=collection, color=color, alpha=alpha, roughness=roughness, metallic=metallic)
    d.update(extra)
    return d


def _cyl(key, name, radius, p1, p2, collection, color, alpha=1.0, roughness=0.6, metallic=0.0, **extra):
    d = dict(key=key, name=name, kind="cyl", radius_mm=radius, p1_mm=list(p1), p2_mm=list(p2),
             collection=collection, color=color, alpha=alpha, roughness=roughness, metallic=metallic)
    d.update(extra)
    return d


def _tube(key, name, radius, points, collection, color, alpha=1.0, roughness=0.3, **extra):
    d = dict(key=key, name=name, kind="tube", radius_mm=radius, points_mm=[list(p) for p in points],
             collection=collection, color=color, alpha=alpha, roughness=roughness, metallic=0.0)
    d.update(extra)
    return d


def compute_layout(P):
    """params.json szótár → {"items": [...], "geo": {...}, "frames": {...}}"""
    items = []
    L = P["panel"]["length_mm"]
    W = P["panel"]["width_mm"]

    # ---- Asztal -----------------------------------------------------------
    T = P["equipment"]["table"]
    tl, tw, th, tt = T["length_mm"], T["width_mm"], T["height_mm"], T["top_thickness_mm"]
    items.append(_box("table_top", "Asztallap", (tl, tw, tt), (0, 0, th - tt / 2),
                      "00_Asztal", T["color"], roughness=0.8))
    leg = 50
    for sx, sy, tag in ((-1, -1, "a"), (1, -1, "b"), (1, 1, "c"), (-1, 1, "d")):
        items.append(_box(f"table_leg_{tag}", f"Asztalláb {tag}", (leg, leg, th - tt),
                          (sx * (tl / 2 - leg), sy * (tw / 2 - leg), (th - tt) / 2),
                          "00_Asztal", T["color"], roughness=0.8))
    table_top = th

    # ---- Szerszám -----------------------------------------------------------
    TL = P["tool"]
    tool_t = TL["thickness_mm"]
    items.append(_box("tool", TL["name"], (TL["length_mm"], TL["width_mm"], tool_t),
                      (0, 0, table_top + tool_t / 2), "01_Szerszam", TL["color"],
                      roughness=0.35, metallic=0.8))
    tool_top = table_top + tool_t

    # ---- Rétegrend ----------------------------------------------------------
    z = tool_top
    laminate_bottom = None
    laminate_top = None
    bag_layer = None
    for i, Ld in enumerate(P["layup"]):
        t = Ld["display_thickness_mm"]
        if Ld["type"] == "bag":
            bag_layer = (i, Ld, z)      # a köteg teteje már ismert; a fóliát a végén építjük
            z += t
            continue
        ox0, ox1, oy = OVERSIZE.get(Ld["type"], (0, 0, 0))
        size = (L + ox0 + ox1, W + 2 * oy, t)
        cx = (ox1 - ox0) / 2
        items.append(_box(f"L{i+1:02d}_{Ld['type']}", f"{i+1:02d} {Ld['name']}", size,
                          (cx, 0, z + t / 2), "02_Retegrend", Ld["color"],
                          alpha=Ld.get("alpha", 1.0), roughness=ROUGH.get(Ld["type"], 0.6),
                          layer_index=i, layer_type=Ld["type"], thickness_mm=Ld["thickness_mm"]))
        if Ld["type"] in ("glass", "carbon") and laminate_bottom is None:
            laminate_bottom = z
        if Ld["type"] == "flowmesh":
            laminate_top = z + t
        z += t
    stack_top = z
    laminate_bottom = tool_top if laminate_bottom is None else laminate_bottom
    laminate_top = stack_top if laminate_top is None else laminate_top

    # ---- Tömítőszalag: a SZERSZÁMLAPON, annak szélétől 30 mm-re befelé ---------
    C = P["consumables"]
    tape = C["sealant_tape"]
    tw_, th_ = tape["width_mm"], tape["height_mm"]
    fx = min(TL["length_mm"] / 2 - 30, L / 2 + OVERSIZE["bag"][0])
    fy = min(TL["width_mm"] / 2 - 30, W / 2 + OVERSIZE["bag"][2])
    for key, name, size, loc in [
        ("tape_xm", "Tömítőszalag -X", (tw_, 2 * fy + tw_, th_), (-fx, 0, tool_top + th_ / 2)),
        ("tape_xp", "Tömítőszalag +X", (tw_, 2 * fy + tw_, th_), (fx, 0, tool_top + th_ / 2)),
        ("tape_ym", "Tömítőszalag -Y", (2 * fx + tw_, tw_, th_), (0, -fy, tool_top + th_ / 2)),
        ("tape_yp", "Tömítőszalag +Y", (2 * fx + tw_, tw_, th_), (0, fy, tool_top + th_ / 2)),
    ]:
        items.append(_box(key, name, size, loc, "03_Segedanyagok", tape["color"], roughness=0.9))

    sp_in, sp_vac = C["inlet_spiral"], C["vacuum_spiral"]
    r_in, r_vac = sp_in["diameter_mm"] / 2, sp_vac["diameter_mm"] / 2
    x_in, x_vac = -(L / 2 + 35), L / 2 + 35
    half = W / 2 + 10
    items.append(_cyl("spiral_inlet", sp_in["name"], r_in,
                      (x_in, -half, tool_top + r_in), (x_in, half, tool_top + r_in),
                      "03_Segedanyagok", sp_in["color"], roughness=0.5))
    items.append(_cyl("spiral_vacuum", sp_vac["name"], r_vac,
                      (x_vac, -half, tool_top + r_vac), (x_vac, half, tool_top + r_vac),
                      "03_Segedanyagok", sp_vac["color"], roughness=0.5))

    # ---- Vákuumfólia: felveszi a köteg alakját -------------------------------
    # Tető a köteg felett (a tépőszövet kiterjedésével), négy lejtős oldal a
    # szerszámlapig, ahol a tömítőszalag belső vonalán ér le. Az összes rész
    # ugyanazt a layer_index-et kapja, így az animációban együtt mozog.
    if bag_layer:
        bi_, Ld, zb = bag_layer
        tb = Ld["display_thickness_mm"]
        pp = OVERSIZE["peelply"]
        tx, ty = L / 2 + pp[0] + 5, W / 2 + pp[2] + 5        # tető fél-kiterjedése
        ztop = zb + tb / 2
        zfoot = tool_top + th_ + tb / 2                        # a szalag tetején
        common = dict(collection="02_Retegrend", color=Ld["color"], alpha=Ld.get("alpha", 1.0),
                      roughness=ROUGH["bag"], layer_index=bi_, layer_type="bag",
                      thickness_mm=Ld["thickness_mm"])
        items.append(_box(f"L{bi_+1:02d}_bag_top", f"{bi_+1:02d} {Ld['name']} – tető",
                          (2 * tx, 2 * ty, tb), (0, 0, ztop), **common))
        import math as _m
        fxi, fyi = fx - tw_ / 2, fy - tw_ / 2                  # a szalag belső széle
        # X-irányú oldalak (a -X és +X végen), Y-irányúak (a -Y és +Y oldalon)
        for tag, sgn in (("xm", -1), ("xp", 1)):
            dx, dz = sgn * (fxi - tx), zfoot - ztop
            ln = _m.hypot(dx, dz)
            items.append(_box(f"L{bi_+1:02d}_bag_{tag}", f"{bi_+1:02d} {Ld['name']} – oldal {tag}",
                              (ln, 2 * ty, tb), (sgn * (tx + fxi) / 2, 0, (ztop + zfoot) / 2),
                              dir_len=(dx / ln, 0, dz / ln), dir_wid=(0, 1, 0), **common))
        for tag, sgn in (("ym", -1), ("yp", 1)):
            dy, dz = sgn * (fyi - ty), zfoot - ztop
            ln = _m.hypot(dy, dz)
            items.append(_box(f"L{bi_+1:02d}_bag_{tag}", f"{bi_+1:02d} {Ld['name']} – oldal {tag}",
                              (2 * fxi, ln, tb), (0, sgn * (ty + fyi) / 2, (ztop + zfoot) / 2),
                              dir_len=(1, 0, 0), dir_wid=(0, dy / ln, dz / ln), **common))
        # Perem: a fólia ráfekszik a tömítőszalagra, és 15 mm-rel túl is lóg rajta
        over = 15
        fxo, fyo = fx + tw_ / 2 + over, fy + tw_ / 2 + over      # a perem külső széle
        for tag, sgn in (("xm", -1), ("xp", 1)):
            items.append(_box(f"L{bi_+1:02d}_bag_flange_{tag}", f"{bi_+1:02d} {Ld['name']} – perem {tag}",
                              (fxo - fxi, 2 * fyo, tb), (sgn * (fxi + fxo) / 2, 0, zfoot), **common))
        for tag, sgn in (("ym", -1), ("yp", 1)):
            items.append(_box(f"L{bi_+1:02d}_bag_flange_{tag}", f"{bi_+1:02d} {Ld['name']} – perem {tag}",
                              (2 * fxi, fyo - fyi, tb), (0, sgn * (fyi + fyo) / 2, zfoot), **common))

    # ---- Berendezések --------------------------------------------------------
    E = P["equipment"]
    pot, trap, pump = E["resin_pot"], E["resin_trap"], E["pump"]
    buf = E.get("buffer_tank")
    pot_r, pot_h = pot["diameter_mm"] / 2, pot["height_mm"]
    trap_r, trap_h = trap["diameter_mm"] / 2, trap["height_mm"]
    pot_pos = (-(TL["length_mm"] / 2 + 170), -120, table_top)
    trap_pos = (TL["length_mm"] / 2 + 170, -100, table_top)
    pump_pos = (TL["length_mm"] / 2 + 170, 230, table_top)
    items.append(_cyl("resin_pot", pot["name"], pot_r, pot_pos,
                      (pot_pos[0], pot_pos[1], table_top + pot_h),
                      "04_Berendezesek", pot["color"], alpha=0.45, roughness=0.2))
    items.append(_cyl("resin_trap", trap["name"], trap_r, trap_pos,
                      (trap_pos[0], trap_pos[1], table_top + trap_h),
                      "04_Berendezesek", trap["color"], alpha=0.5, roughness=0.3, metallic=0.3))
    trap_top = table_top + trap_h
    pot_top = table_top + pot_h
    steel = pump["color"]

    def _port(key, name, x, y, z0, r=9, h=16):
        """Csőcsonk: rövid henger, a cső a tetejéhez csatlakozik (z0+h)."""
        items.append(_cyl(key, name, r, (x, y, z0 - 2), (x, y, z0 + h), "04_Berendezesek",
                          steel, roughness=0.5, metallic=0.5))
        return (x, y, z0 + h)

    def _gauge(key, name, x, y, z0):
        """Vákuum-nyomásmérő: függőleges szár, rá merőleges (a nézőnek, -Y felé néző)
        számlap fehér előlappal és fekete mutatóval."""
        items.append(_cyl(key + "_stem", name + " – szár", 5, (x, y, z0 - 2), (x, y, z0 + 22),
                          "04_Berendezesek", steel, roughness=0.5, metallic=0.5))
        zc = z0 + 22 + 22
        items.append(_cyl(key + "_case", name + " – ház", 24, (x, y - 5, zc), (x, y + 7, zc),
                          "04_Berendezesek", "#263238", roughness=0.6, metallic=0.3))
        items.append(_cyl(key + "_face", name + " – számlap", 20, (x, y - 7, zc), (x, y - 5, zc),
                          "04_Berendezesek", "#f5f5f5", roughness=0.4))
        items.append(_box(key + "_needle", name + " – mutató", (3, 1.5, 16), (x - 4, y - 7.5, zc + 3),
                          "04_Berendezesek", "#c62828", roughness=0.5,
                          dir_len=(0.5, 0, 0.866), dir_wid=(0, 1, 0)))   # ~ -0,65 bar állás
        return (x, y, zc)

    # gyantatartály: fedél, csonk, merülőcső a gyantába
    items.append(_cyl("resin_pot_lid", "Gyantatartály fedél", pot_r * 1.06, (pot_pos[0], pot_pos[1], pot_top),
                      (pot_pos[0], pot_pos[1], pot_top + 6), "04_Berendezesek", steel, roughness=0.6, metallic=0.4))
    pot_port = _port("resin_pot_port", "Gyantatartály csonk", pot_pos[0], pot_pos[1], pot_top + 6)
    items.append(_cyl("resin_pot_diptube", "Merülőcső a gyantában", 4, (pot_pos[0], pot_pos[1], pot_top + 6),
                      (pot_pos[0], pot_pos[1], table_top + 12), "04_Berendezesek", "#cfd8dc", alpha=0.9, roughness=0.3))

    # gyantacsapda: fedél, két csonk (be a zsákból, ki a puffer felé), merülőcső
    items.append(_cyl("resin_trap_lid", "Gyantacsapda fedél", trap_r * 1.06, (trap_pos[0], trap_pos[1], trap_top),
                      (trap_pos[0], trap_pos[1], trap_top + 8), "04_Berendezesek", steel, roughness=0.6, metallic=0.4))
    trap_in = _port("resin_trap_port_in", "Gyantacsapda csonk (be)", trap_pos[0] - 38, trap_pos[1], trap_top + 8)
    trap_out = _port("resin_trap_port_out", "Gyantacsapda csonk (ki)", trap_pos[0] + 38, trap_pos[1], trap_top + 8)
    _gauge("gauge_trap", "Vákuummérő – zsákoldal (csapda)", trap_pos[0], trap_pos[1] - 32, trap_top + 8)
    items.append(_cyl("resin_trap_diptube", "Merülőcső a csapdában", 4, (trap_pos[0] - 38, trap_pos[1], trap_top + 8),
                      (trap_pos[0] - 38, trap_pos[1], trap_top - trap_h * 0.55), "04_Berendezesek", "#cfd8dc", alpha=0.9, roughness=0.3))

    # vákuumszivattyú (forgólapátos): talp, hengeres motor, ventilátorfedél, szivattyúfej, szívócsonk, kipufogó
    px, py = pump_pos[0], pump_pos[1]
    base_h = 12
    items.append(_box("pump_base", "Szivattyú talp", (pump["length_mm"], pump["width_mm"], base_h),
                      (px, py, table_top + base_h / 2), "04_Berendezesek", steel, roughness=0.7, metallic=0.3))
    mr = 52
    mz = table_top + base_h + mr + 8
    items.append(_cyl("pump_motor", "Szivattyú motor", mr, (px - 105, py, mz), (px + 30, py, mz),
                      "04_Berendezesek", steel, roughness=0.5, metallic=0.5))
    items.append(_cyl("pump_fan_cover", "Ventilátorfedél", mr + 5, (px - 112, py, mz), (px - 100, py, mz),
                      "04_Berendezesek", "#263238", roughness=0.8))
    items.append(_box("pump_feet", "Motortartó", (120, 60, mr + 8 - 10), (px - 40, py, table_top + base_h + (mr + 8 - 10) / 2),
                      "04_Berendezesek", steel, roughness=0.7, metallic=0.3))
    hz = table_top + base_h + 55
    items.append(_box("pump_head", "Szivattyúfej", (70, 112, 110), (px + 65, py, hz), "04_Berendezesek",
                      "#455a64", roughness=0.5, metallic=0.5))
    # szívócsonk a fej +X (puffertartály felőli) oldalán, vízszintesen – a cső innen jön
    pin_z = hz + 25
    items.append(_cyl("pump_port_in", "Szivattyú szívócsonk", 11, (px + 98, py, pin_z), (px + 128, py, pin_z),
                      "04_Berendezesek", steel, roughness=0.5, metallic=0.5))
    pump_in = (px + 128, py, pin_z)          # a csonk külső vége
    _gauge("gauge_pump", "Vákuummérő – szivattyú szívóoldal", px + 65 - 24, py - 36, hz + 55)
    items.append(_cyl("pump_exhaust", "Kipufogó/olajköd-leválasztó", 14, (px + 65, py + 56, hz + 20),
                      (px + 65, py + 56 + 40, hz + 20), "04_Berendezesek", "#90a4ae", roughness=0.5, metallic=0.4))
    items.append(_cyl("pump_sight_glass", "Olajszint-ablak", 10, (px + 65, py - 56, hz - 25),
                      (px + 65, py - 56 - 4, hz - 25), "04_Berendezesek", "#eceff1", alpha=0.8, roughness=0.2))

    # ---- Puffertartály (vákuumtartály) a csapda és a szivattyú között ----------
    # A Polinvent gyakorlata: a puffertartály simítja a vákuumot, így a szivattyú
    # ciklikus működése / rövid megszakadása nem jut el a zsákig.
    buf_c = None
    if buf:
        buf_r, buf_len = buf["diameter_mm"] / 2, buf["length_mm"]
        bx = TL["length_mm"] / 2 + 170 + pump["length_mm"] / 2 + buf_r + 30   # a szivattyú mögött
        by0, by1 = -200, -200 + buf_len
        bz = table_top + 12 + buf_r
        buf_c = (bx, (by0 + by1) / 2, bz)
        items.append(_cyl("buffer_tank", buf["name"], buf_r, (bx, by0, bz), (bx, by1, bz),
                          "04_Berendezesek", buf["color"], roughness=0.35, metallic=0.6))
        for tag, y in (("a", by0 + 50), ("b", by1 - 50)):
            items.append(_box(f"buffer_cradle_{tag}", f"Tartálybak {tag}", (60, 30, 12 + buf_r * 0.3),
                              (bx, y, table_top + (12 + buf_r * 0.3) / 2),
                              "04_Berendezesek", pump["color"], roughness=0.6, metallic=0.4))
        _gauge("gauge_buffer", "Vákuummérő – puffertartály", bx, buf_c[1], bz + buf_r)
        port_in, port_out = (bx, by0 + 60, bz + buf_r), (bx, by1 - 60, bz + buf_r)
        for key, name, pp_ in (("buffer_port_in", "Csonk (be)", port_in), ("buffer_port_out", "Csonk (ki)", port_out)):
            items.append(_cyl(key, name, 9, (pp_[0], pp_[1], pp_[2] - 2), (pp_[0], pp_[1], pp_[2] + 14),
                              "04_Berendezesek", pump["color"], roughness=0.5, metallic=0.5))

    # ---- Csövek -------------------------------------------------------------
    tube = C["tube"]
    r_t = tube["diameter_mm"] / 2
    y_out = -(fy + 40)                      # a fólián/szalagon kívül, a szerszámon

    def _leave(port):
        """Cső indul egy csonkból: a csonk BELSEJÉBEN kezdődik, függőlegesen lép ki.
        Három egy vonalba eső pont → az illesztett spline itt egyenes és tengelyirányú."""
        x, y, z = port
        return [(x, y, z - 10), (x, y, z + 12), (x, y, z + 40)]

    def _enter(port):
        return list(reversed(_leave(port)))

    def _axial(p_end, direction, run=60):
        """Spirálcső végébe tengelyirányból érkező cső: egyenes befutás + 10 mm átfedés."""
        x, y, z = p_end
        dx, dy = direction
        return [(x - dx * run, y - dy * run, z), (x - dx * 25, y - dy * 25, z), (x + dx * 10, y + dy * 10, z)]

    sp_in_end = (x_in, -half, tool_top + r_in)
    sp_vac_end = (x_vac, -half, tool_top + r_vac)
    items.append(_tube("hose_pot_inlet", "Cső: tartály → bevezető spirálcső", r_t,
        _leave(pot_port) + [
        (pot_pos[0] + 40, pot_pos[1] - 40, table_top + pot_h + 100),
        (x_in - 20, y_out - 80, tool_top + 60),
        (x_in, y_out - 20, tool_top + r_in + 6),
        ] + _axial(sp_in_end, (0, 1)),            # +Y irányból lép a spirálcső végébe
        "04_Berendezesek", tube["color"], alpha=tube.get("alpha", 1.0)))
    items.append(_tube("hose_vacuum_trap", "Cső: elszívó spirálcső → gyantacsapda", r_t,
        list(reversed(_axial(sp_vac_end, (0, 1)))) + [
        (x_vac, y_out - 20, tool_top + r_vac + 6),
        (x_vac + 20, y_out - 80, tool_top + 60),
        (trap_in[0] - 20, trap_in[1] - 60, trap_in[2] + 100),
        ] + _enter(trap_in),
        "04_Berendezesek", tube["color"], alpha=tube.get("alpha", 1.0)))
    if buf_c:
        bx, by, bz = buf_c
        items.append(_tube("hose_trap_buffer", "Cső: gyantacsapda → puffertartály", r_t,
            _leave(trap_out) + [
            (trap_out[0] + 70, trap_out[1] + 10, trap_out[2] + 90),
            ] + _enter(port_in),
            "04_Berendezesek", tube["color"], alpha=tube.get("alpha", 1.0)))
        # a puffertartály kimenő csonkjából fel, ív, majd +X irányból vízszintesen a szívócsonkba
        items.append(_tube("hose_buffer_pump", "Cső: puffertartály → szivattyú", r_t,
            _leave(port_out) + [
            ((port_out[0] + pump_in[0] + 60) / 2, (port_out[1] + pump_in[1]) / 2, port_out[2] + 95),
            ] + _axial(pump_in, (-1, 0), run=70),
            "04_Berendezesek", tube["color"], alpha=tube.get("alpha", 1.0)))
    else:
        items.append(_tube("hose_trap_pump", "Cső: csapda → szivattyú", r_t,
            _leave(trap_out) + [
            (trap_out[0] + 60, (trap_out[1] + pump_in[1]) / 2, trap_out[2] + 80),
            ] + _axial(pump_in, (-1, 0), run=70),
            "04_Berendezesek", tube["color"], alpha=tube.get("alpha", 1.0)))

    # ---- Animációs időzítés -------------------------------------------------
    A = P["animation"]
    f_assemble_start = 1 + A["hold_exploded_frames"]
    f_assemble_end = f_assemble_start + A["assemble_frames"]
    f_infuse_start = f_assemble_end + A["hold_assembled_frames"]
    f_infuse_end = f_infuse_start + A["infuse_frames"]
    f_end = f_infuse_end + A["hold_end_frames"]
    frames = dict(exploded_hold=[1, f_assemble_start], assemble=[f_assemble_start, f_assemble_end],
                  assembled_hold=[f_assemble_end, f_infuse_start], infuse=[f_infuse_start, f_infuse_end],
                  end=f_end, fps=A["fps"], explode_gap_mm=A["explode_gap_mm"],
                  assemble_frames=A["assemble_frames"], infuse_frames=A["infuse_frames"])

    # ---- Csak animációhoz (Blender építi): gyantafront, gyantaszintek ---------
    fm = OVERSIZE["flowmesh"]
    geo = dict(
        L=L, W=W, table_top=table_top, tool_top=tool_top, stack_top=stack_top,
        laminate_bottom=laminate_bottom, laminate_top=laminate_top,
        pot_pos=list(pot_pos), pot_r=pot_r, pot_h=pot_h, pot_level=pot["resin_level"],
        trap_pos=list(trap_pos), trap_r=trap_r, trap_h=trap_h,
        resin_front=dict(x0=-(L / 2 + fm[0]), length=L + fm[0] + 15,
                         width=W + 2 * 15 + 1, height=(laminate_top - laminate_bottom) + 0.3,
                         z_center=(laminate_top + laminate_bottom) / 2 + 0.15),
        resin_color=P["resin"]["color"], resin_alpha=P["resin"]["alpha"],
        n_layers=len(P["layup"]),
    )
    if bag_layer:
        bi_, Ld, zb = bag_layer
        tb = Ld["display_thickness_mm"]
        pp = OVERSIZE["peelply"]
        geo["bag"] = dict(layer_index=bi_, color=Ld["color"], alpha=Ld.get("alpha", 1.0),
                          thickness_mm=Ld["thickness_mm"], name=Ld["name"],
                          tx=L / 2 + pp[0] + 5, ty=W / 2 + pp[2] + 5,          # a köteg teteje
                          fxi=fx - tw_ / 2, fyi=fy - tw_ / 2,                   # a szalag belső éle
                          fxo=fx + tw_ / 2 + 15, fyo=fy + tw_ / 2 + 15,         # a perem külső széle
                          ztop=zb + tb / 2, zfoot=tool_top + th_ + tb / 2, puff_mm=28)
    return {"items": items, "geo": geo, "frames": frames}


if __name__ == "__main__":
    import json, os, sys
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "params.json"), encoding="utf-8") as f:
        lay = compute_layout(json.load(f))
    print(f"{len(lay['items'])} test; rétegköteg {lay['geo']['stack_top']-lay['geo']['tool_top']:.1f} mm; "
          f"animáció {lay['frames']['end']} képkocka @ {lay['frames']['fps']} fps")
    for it in lay["items"]:
        print(f"  {it['key']:18s} {it['kind']:4s} {it['collection']:16s} {it['name']}")
