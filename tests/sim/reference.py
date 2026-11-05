"""Independent numpy reference for the laminate plate simulator (CLT + FSDT Navier + Tsai-Wu).

Written from the theory (Reddy, Mechanics of Laminated Composite Plates; Jones), not ported from clt.js.
Units: N, mm, MPa internally.

Usage:
  python -I tests/sim/reference.py                 -> analytic checks (isotropic, Reddy cross-ply)
  python -I tests/sim/reference.py --compare F.json -> compare against JS results written by compare.mjs
"""
import json
import sys
import numpy as np


def layer_list(plies, mats):
    out = []
    for i, p in enumerate(plies):
        m = mats[p["mat"]]
        th = float(p.get("angle", 0))
        if m["kind"] == "biax":
            out += [(i, m, th + 45.0, m["t"] / 2, False), (i, m, th - 45.0, m["t"] / 2, False)]
        elif m["kind"] == "core":
            out.append((i, m, th, float(p.get("t") or m["t"]), True))
        else:
            out.append((i, m, th, m["t"], False))
    return out


def q_material(m):
    E1, E2, G12, v12 = m["E1"] * 1e3, m["E2"] * 1e3, m["G12"] * 1e3, m["nu12"]
    S = np.array([[1 / E1, -v12 / E1, 0], [-v12 / E1, 1 / E2, 0], [0, 0, 1 / G12]])
    return np.linalg.inv(S)  # reduced stiffness via compliance inversion


def T_strain(theta_deg):
    """Global engineering strain -> material engineering strain."""
    t = np.radians(theta_deg)
    c, s = np.cos(t), np.sin(t)
    return np.array([[c * c, s * s, c * s], [s * s, c * c, -c * s], [-2 * c * s, 2 * c * s, c * c - s * s]])


def analyze(plies, mats, a, b, load, terms=31, grid=21):
    lays = layer_list(plies, mats)
    h = sum(L[3] for L in lays)
    z = -h / 2
    A = np.zeros((3, 3)); B = np.zeros((3, 3)); D = np.zeros((3, 3))
    Hs_par = np.zeros((2, 2)); Cs_ser = np.zeros((2, 2))
    info = []
    has_core = False
    for (idx, m, th, t, core) in lays:
        Q = q_material(m)
        T = T_strain(th)
        Qb = T.T @ Q @ T  # energy-consistent transformation
        z0, z1 = z, z + t
        A += Qb * (z1 - z0); B += Qb * (z1**2 - z0**2) / 2; D += Qb * (z1**3 - z0**3) / 3
        r = np.radians(th); c, s = np.cos(r), np.sin(r)
        Ts = np.array([[c, -s], [s, c]])  # (gamma_yz, gamma_xz) global -> material (23, 13)
        Cm = np.diag([m["G23"] * 1e3, m["G13"] * 1e3])
        Cg = Ts.T @ Cm @ Ts  # [[Q44, Q45],[Q45, Q55]]
        Hs_par += Cg * t
        Cs_ser += np.diag(t / np.diag(Cg))
        has_core |= core
        info.append(dict(idx=idx, m=m, th=th, t=t, core=core, z0=z0, z1=z1, Q=Q, T=T))
        z = z1
    if has_core:
        Hs = h * h * np.diag(1 / np.diag(Cs_ser))  # series (uniform shear stress) estimate
        A44, A55 = Hs[0, 0], Hs[1, 1]
    else:
        A44, A55 = 5 / 6 * Hs_par[0, 0], 5 / 6 * Hs_par[1, 1]
    sym = np.abs(B).max() <= 1e-9 * np.abs(A).max() * h
    Ai = np.linalg.inv(A)
    Ds = D if sym else D - B @ Ai @ B

    ms = np.arange(1, terms + 1, 2)
    Mm, Nn = np.meshgrid(ms, ms, indexing="ij")
    al, be = Mm * np.pi / a, Nn * np.pi / b
    if load["type"] == "patch":
        c, d, P = load.get("c", 60), load.get("d", 60), 1.0
        Qmn = 16 * P / (np.pi**2 * Mm * Nn * c * d) * np.sin(Mm * np.pi / 2) * np.sin(Nn * np.pi / 2) \
            * np.sin(Mm * np.pi * c / (2 * a)) * np.sin(Nn * np.pi * d / (2 * b))
    else:
        Qmn = 16 * 1e-3 / (np.pi**2 * Mm * Nn)
    K = np.zeros(Mm.shape + (3, 3))
    K[..., 0, 0] = A55 * al**2 + A44 * be**2
    K[..., 0, 1] = K[..., 1, 0] = A55 * al
    K[..., 0, 2] = K[..., 2, 0] = A44 * be
    K[..., 1, 1] = Ds[0, 0] * al**2 + Ds[2, 2] * be**2 + A55
    K[..., 1, 2] = K[..., 2, 1] = (Ds[0, 1] + Ds[2, 2]) * al * be
    K[..., 2, 2] = Ds[2, 2] * al**2 + Ds[1, 1] * be**2 + A44
    rhs = np.zeros(Mm.shape + (3, 1)); rhs[..., 0, 0] = Qmn
    sol = np.linalg.solve(K, rhs)[..., 0]
    W, X, Y = sol[..., 0], sol[..., 1], sol[..., 2]

    x = np.linspace(0, a, grid); y = np.linspace(0, b, grid)
    sx = np.sin(np.outer(ms, x) * np.pi / a); cx = np.cos(np.outer(ms, x) * np.pi / a)
    sy = np.sin(np.outer(ms, y) * np.pi / b); cy = np.cos(np.outer(ms, y) * np.pi / b)
    f = lambda C, X_, Y_: np.einsum("mn,mi,nj->ji", C, X_, Y_)  # result [y, x]
    w = f(W, sx, sy)
    # physical curvatures (z up, w positive downward): kx = d(-phi_x)/dx ...
    kx = f(al * X, sx, sy); ky = f(be * Y, sx, sy); kxy = f(-(be * X + al * Y), cx, cy)
    Mx = Ds[0, 0] * kx + Ds[0, 1] * ky; My = Ds[0, 1] * kx + Ds[1, 1] * ky; Mxy = Ds[2, 2] * kxy
    Qx = A55 * f(al * W + X, cx, sy); Qy = A44 * f(be * W + Y, sx, cy)
    Mv = np.stack([Mx, My, Mxy], -1)  # [y,x,3]
    kap = Mv @ np.linalg.inv(Ds).T
    e0 = np.zeros_like(kap) if sym else -(kap @ (Ai @ B).T)

    best = (np.inf, -1)
    for L in info:
        m = L["m"]
        Xt, Xc, Yt, Yc, S = m["Xt"], m["Xc"], m["Yt"], m["Yc"], m["S"]
        F1, F2 = 1 / Xt - 1 / Xc, 1 / Yt - 1 / Yc
        F11, F22, F66, F12 = 1 / (Xt * Xc), 1 / (Yt * Yc), 1 / S**2, -0.5 / np.sqrt(Xt * Xc * Yt * Yc)
        for zz in (L["z0"], L["z1"]):
            eps = e0 + zz * kap
            sig = (eps @ L["T"].T) @ L["Q"].T
            s1, s2, t6 = sig[..., 0], sig[..., 1], sig[..., 2]
            qa = F11 * s1**2 + F22 * s2**2 + F66 * t6**2 + 2 * F12 * s1 * s2
            qb = F1 * s1 + F2 * s2
            with np.errstate(divide="ignore", invalid="ignore"):
                lam = np.where(qa > 1e-300, (-qb + np.sqrt(qb**2 + 4 * qa)) / (2 * qa), np.where(qb > 0, 1 / qb, np.inf))
            lm = lam.min()
            if lm < best[0]:
                best = (lm, L["idx"])
    if has_core:
        qmax = np.hypot(Qx, Qy).max()
        for L in info:
            if L["core"]:
                tb = L["z0"] + h / 2; tt = h / 2 - L["z1"]
                lm = L["m"]["S"] / (qmax / (L["t"] + (tb + tt) / 2))
                if lm < best[0]:
                    best = (lm, L["idx"])
    di = np.linalg.inv(Ds)
    return dict(h=h, wUnit=w.max(), Ex=1 / (h * Ai[0, 0]) / 1e3, Ey=1 / (h * Ai[1, 1]) / 1e3, D11=D[0, 0],
                fpfUnit=best[0], fpfPly=best[1], Efx=12 / (h**3 * di[0, 0]) / 1e3)


def analytic_checks():
    rows = []
    iso = {"iso": dict(kind="iso", E1=70, E2=70, G12=70 / 2.6, nu12=0.3, G13=70 / 2.6, G23=70 / 2.6,
                       Xt=1, Xc=1, Yt=1, Yc=1, S=1, t=4.0)}
    r = analyze([{"mat": "iso", "angle": 0}], iso, 400, 400, {"type": "pressure"})
    Dz = 70e3 * 4.0**3 / (12 * (1 - 0.09))
    w_cf = 0.00406 * 1e-3 * 400**4 / Dz
    rows.append(("iso a/h=100 w/w_closed", r["wUnit"] / w_cf, 1.0))
    E2 = 1.0
    red = {"r": dict(kind="ud", E1=25 * E2, E2=E2, G12=0.5 * E2, nu12=0.25, G13=0.5 * E2, G23=0.2 * E2,
                     Xt=1, Xc=1, Yt=1, Yc=1, S=1, t=0.25)}
    for ah, exp in ((100, 0.6842), (10, 1.0219)):
        hh = 1.0; aa = ah * hh
        r = analyze([{"mat": "r", "angle": t} for t in (0, 90, 90, 0)], red, aa, aa, {"type": "pressure"})
        wbar = r["wUnit"] * E2 * 1e3 * hh**3 / (1e-3 * aa**4) * 100
        rows.append((f"Reddy [0/90/90/0] a/h={ah} wbar", wbar, exp))
    return rows


def main():
    ok = True
    print("Python analytic checks:")
    for name, val, exp in analytic_checks():
        err = abs(val / exp - 1) * 100
        print(f"  {name:36s} {val:9.4f}  expected {exp:7.4f}  err {err:5.2f} %")
        ok &= err < 1.0
    if "--compare" in sys.argv:
        data = json.load(open(sys.argv[sys.argv.index("--compare") + 1], encoding="utf-8"))
        mats = data["materials"]
        print("\nJS vs Python (rel. diff %):")
        print(f"  {'case':38s} {'wMax':>7s} {'Ex':>7s} {'Ey':>7s} {'D11':>7s} {'FPF':>7s}")
        for c in data["cases"]:
            r = analyze(c["plies"], mats, c["a"], c["b"], c["load"], c.get("terms", 31), c.get("grid", 21))
            L = c["loadMag"]
            py = dict(wMax=r["wUnit"] * L, Ex=r["Ex"], Ey=r["Ey"], D11=r["D11"], fpf=r["fpfUnit"])
            js = c["js"]
            d = {k: abs(js[k] / py[k] - 1) * 100 if py[k] else 0 for k in py}
            worst = max(d.values())
            ok &= worst <= 0.5
            print(f"  {c['name'][:38]:38s} " + " ".join(f"{d[k]:7.3f}" for k in ("wMax", "Ex", "Ey", "D11", "fpf"))
                  + ("  OK" if worst <= 0.5 else "  FAIL"))
        for c in data.get("analytic", []):
            err = abs(c["value"] / c["expected"] - 1) * 100
            print(f"  JS {c['name']:33s} {c['value']:9.4f}  expected {c['expected']:7.4f}  err {err:5.2f} %")
            ok &= err < 1.0
    print("\nRESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
