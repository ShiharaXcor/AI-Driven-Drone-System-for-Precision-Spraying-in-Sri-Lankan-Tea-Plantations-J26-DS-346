# tea_spray_env.py
# Component 3 - Gymnasium training environment (Stage 1: terrain-level simulator)
#
# A spray drone flies over a 200 m x 200 m patch of the Ouvahkelle Estate.
#   terrain   : real SRTM elevation (3 arc-second tile, ~92.77 m cells) cubic-interpolated
#               to a 5 m grid (interpolated, NOT new data)
#   energy    : calibrated energy model (Kenilworth fit + SULEKO level scale)
#   obstacles : random shade-tree canopies (circles)
#   action    : continuous [vx, vy, vz] in [-1, 1]
#   step      : 1 s of flight
#
# State vector (16 values, all scaled to 0..1)
#   Energy / mass (6): battery, liquid, total mass, slope here,
#                      slope ahead, predicted drain rate
#   Spatial (10)     : 8 obstacle-sector distances + 2 for the direction
#                      to the nearest unsprayed ground
#
# Options (all default to the original behaviour):
#   v_max_kmh : spraying speed cap.  Dose per hectare stays fixed (litres per metre
#               does not depend on speed), so this only changes flight time.
#   transit   : mission starts at a base 100-400 m away (real SRTM height difference);
#               energy of the outbound leg (full tank) is charged at start and the
#               return leg (current tank) is reserved, so the drone must stop spraying
#               while it can still fly home with a safety reserve.
#   r_crash   : crash penalty.
#   obs_mode  : spec16 | ext24 | ext26 (ext24 + battery margin + distance home)
#   use_mass  : False = ablation of the WORLD: the energy model treats the tank as
#               always half full, so payload depletion has no physical effect.
#   hide_mass : True  = ablation of the AGENT: the physics still uses the real tank
#               level, but the observation no longer shows it. The liquid fraction,
#               total mass and predicted drain rate (and, in ext26, the battery
#               margin) are computed from a fixed half-full tank.
#               Remaining indirect cues the agent can still use: the battery level,
#               and in ext24/ext26 the coverage sectors (they fill up as it sprays,
#               which tracks liquid used). So "hide_mass" means "mass inputs removed",
#               not a perfectly mass-blind agent. Report it that way.
#
# Run self-check:  cd ~/component3 && source venv/bin/activate
#                  python3 drl_agent/tea_spray_env.py
# Leak check only: python3 drl_agent/tea_spray_env.py --check-blind

import os, sys, glob, json
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from scipy.ndimage import zoom, map_coordinates

BASE = os.environ.get("C3_BASE", os.path.expanduser("~/component3"))
sys.path.insert(0, f"{BASE}/energy_model")
from energy_model import EnergyModel

# ---- geometry -------------------------------------------------------------
PATCH_M    = 200.0          # patch side length (m)
TERRAIN_DX = 5.0            # terrain grid spacing (m)
SRTM_DX    = 92.77          # ground size of one SRTM cell (m): srtm_53_11 is the 3 arc-second (90 m) tile,
                            # 0.000833 deg x 111320 m/deg, the same value terrain_processor.py used for slope_grid_srtm.npy
COV_DX     = 2.0            # coverage grid spacing (m)
SWATH_M    = 6.0            # spray width (SULEKO: ~5.8 m of sprayed width)
# ---- operating limits (the SAME for agent and baseline) -------------------
V_MAX      = 6.4 / 3.6      # m/s  (SULEKO cruise speed, assumption)
H_MIN, H_MAX = 2.0, 6.0     # height above ground (m)
VZ_MAX     = 1.0            # m/s
LIQUID_L   = 20.0
L_PER_M    = 0.0306         # litres per metre of spraying (SULEKO ~51 L/ha at 6 m)
RTH_BATT   = 20.0           # return-to-home battery (%)
SENSE_M    = 15.0           # obstacle sensor range
COV_WIN_M  = 12.0           # radius for the coverage-sector feature (ext24 only)
COLLIDE_M  = 1.0            # canopy contact margin
WARN_M     = 3.0            # warning distance (proposal: stop within 3 m)
N_TREES    = 8
MAX_STEPS  = 600
# ---- reward weights ---------------------------------------------------------
R_COVER    = 400.0          # reward per hectare newly sprayed
R_ENERGY   = 1.0            # penalty per battery-% used
R_TIME     = 0.01           # small per-step penalty
R_WARN     = 0.2            # penalty per metre inside the warning distance
R_CRASH    = 20.0           # penalty for canopy contact (default)
# ---- whole-mission option (transit=True) ----------------------------------
V_REF       = 6.4 / 3.6     # reference spraying speed (m/s)
TRANSIT_V   = 7.0           # m/s base <-> field transit speed (assumption)
BASE_D      = (100.0, 400.0)  # distance base -> field (m)
RESERVE_BATT = 10.0         # battery % that must remain after flying home
BLIND_LIQUID = LIQUID_L / 2  # tank level shown to a hide_mass agent (constant)


def load_model():
    m = EnergyModel()
    p = f"{BASE}/energy_model/calibrated_model.json"
    with open(p) as f:
        c = json.load(f)
    m.mass_empty_kg = c["mass_empty_kg"]
    m.battery_wh    = c["battery_wh_effective"]
    m.level_scale   = c["suleko_level_scale"]
    return m


def load_elevation():
    hits = glob.glob(f"{BASE}/**/elevation_srtm.npy", recursive=True)
    if not hits:
        raise FileNotFoundError("elevation_srtm.npy not found - run terrain_processor.py")
    z = np.load(hits[0]).astype(float)
    return z, hits[0]


class TeaSprayEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, seed=None, terminate_on_collision=True, use_mass=True, obs_mode="spec16",
                 v_max_kmh=6.4, transit=False, r_crash=R_CRASH, hide_mass=False):
        super().__init__()
        self.v_max = v_max_kmh / 3.6
        self.transit = transit
        self.r_crash = r_crash
        self.obs_mode = obs_mode        # 'spec16' = proposal state; 'ext24' = + 8 coverage sectors
        self.model = load_model()
        self.z_srtm, self.z_path = load_elevation()
        self.terminate_on_collision = terminate_on_collision
        self.use_mass = use_mass        # False = world ablation: energy model ignores m(t)
        self.hide_mass = hide_mass      # True  = agent ablation: observation hides m(t)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)
        n_obs = {"spec16": 16, "ext24": 24, "ext26": 26}[obs_mode]
        self.observation_space = spaces.Box(0.0, 1.0, shape=(n_obs,), dtype=np.float32)
        k = int(COV_WIN_M / COV_DX)
        oy, ox = np.mgrid[-k:k + 1, -k:k + 1]
        ang = np.arctan2(oy, ox)
        self._cov_k = k
        self._cov_sec = (((ang + np.pi / 8) % (2 * np.pi)) // (np.pi / 4)).astype(int)
        self._cov_ok = (ox ** 2 + oy ** 2) > 0
        self.n_t = int(PATCH_M / TERRAIN_DX)
        self.n_c = int(PATCH_M / COV_DX)
        cc = (np.arange(self.n_c) + 0.5) * COV_DX
        self.cx, self.cy = np.meshgrid(cc, cc, indexing="ij")
        self.reset(seed=seed if seed is not None else 0)

    # ---- terrain ----------------------------------------------------------
    def _make_patch(self):
        w = int(np.ceil(PATCH_M / SRTM_DX)) + 1           # SRTM cells needed to cover the patch (4)
        R, C = self.z_srtm.shape
        for _ in range(50):
            r0 = self._rng.integers(0, max(1, R - w + 1))
            c0 = self._rng.integers(0, max(1, C - w + 1))
            win = self.z_srtm[r0:r0 + w, c0:c0 + w]
            if not np.isnan(win).any():
                break
        else:
            win = np.nan_to_num(win, nan=np.nanmean(self.z_srtm))
        self._rc = (r0, c0)                               # window origin in the SRTM grid
        pos = (np.arange(self.n_t) + 0.5) * TERRAIN_DX / SRTM_DX      # fine-grid centres in SRTM cell units
        ii, jj = np.meshgrid(pos, pos, indexing="ij")
        self.z = map_coordinates(win, [ii, jj], order=3, mode="nearest")   # interpolated, NOT new data

    def _elev(self, x, y):
        return map_coordinates(self.z, [[x / TERRAIN_DX - 0.5], [y / TERRAIN_DX - 0.5]],
                               order=1, mode="nearest")[0]

    def _slope_dir(self, x, y, ux, uy, d=10.0):
        """climb angle (deg, signed) looking d metres along unit vector (ux, uy)"""
        dz = self._elev(np.clip(x + ux * d, 0, PATCH_M), np.clip(y + uy * d, 0, PATCH_M)) \
             - self._elev(x, y)
        return float(np.degrees(np.arctan2(dz, d)))

    def _slope_mag(self, x, y):
        a = self._slope_dir(x, y, 1, 0, 5.0)
        b = self._slope_dir(x, y, 0, 1, 5.0)
        return float(np.hypot(a, b))

    # ---- obstacles --------------------------------------------------------
    def _make_trees(self):
        pts = self._rng.uniform(15, PATCH_M - 15, size=(N_TREES, 2))
        rad = self._rng.uniform(1.5, 3.0, size=N_TREES)
        # keep the start corner clear
        keep = np.hypot(pts[:, 0] - 5, pts[:, 1] - 5) > 12
        self.trees, self.tree_r = pts[keep], rad[keep]

    def _sector_dists(self):
        out = np.full(8, SENSE_M)
        if len(self.trees) == 0:
            return out
        dx = self.trees[:, 0] - self.x
        dy = self.trees[:, 1] - self.y
        d  = np.hypot(dx, dy)
        gap = d - self.tree_r
        ang = np.arctan2(dy, dx)
        half = np.arcsin(np.clip(self.tree_r / np.maximum(d, 1e-6), 0, 1))
        centres = np.arange(8) * (np.pi / 4)
        for s in range(8):
            diff = np.abs((ang - centres[s] + np.pi) % (2 * np.pi) - np.pi)
            hit = diff <= (np.pi / 8 + half)
            if hit.any():
                out[s] = min(SENSE_M, gap[hit].min())
        return out

    def _min_gap(self):
        if len(self.trees) == 0:
            return SENSE_M
        return float((np.hypot(self.trees[:, 0] - self.x, self.trees[:, 1] - self.y)
                      - self.tree_r).min())

    # ---- coverage ---------------------------------------------------------
    def _spray_at(self, x, y):
        near = (self.cx - x) ** 2 + (self.cy - y) ** 2 <= (SWATH_M / 2) ** 2     # circular footprint
        new = near & ~self.covered
        self.covered |= near
        return int(new.sum()) * COV_DX ** 2 / 10000.0      # hectares

    def _nearest_uncovered_dir(self):
        idx = ~self.covered
        if not idx.any():
            return 0.0, 0.0
        dx = self.cx[idx] - self.x
        dy = self.cy[idx] - self.y
        i  = np.argmin(dx * dx + dy * dy)
        n  = np.hypot(dx[i], dy[i]) + 1e-6
        return dx[i] / n, dy[i] / n

    def _coverage_sectors(self):
        """fraction of ground still to spray in 8 sectors around the drone (ext24)"""
        k = self._cov_k
        pad = np.pad(self.covered, k, constant_values=True)      # walls count as done
        i = int(np.clip(self.x / COV_DX, 0, self.n_c - 1))
        j = int(np.clip(self.y / COV_DX, 0, self.n_c - 1))
        win = (~pad[i:i + 2 * k + 1, j:j + 2 * k + 1]).T         # rows = y, cols = x
        out = np.zeros(8)
        for sct in range(8):
            m = (self._cov_sec == sct) & self._cov_ok
            out[sct] = win[m].mean()
        return out

    # ---- energy -----------------------------------------------------------
    def _drain_pct(self, speed, rise_rate, dt, liquid=None):
        """battery % used. `liquid` overrides the tank level (used only to build the
        observation for a hide_mass agent); the physics always calls it without it."""
        ang = np.degrees(np.arctan2(max(rise_rate, 0.0), max(speed, 0.2)))
        if liquid is None:
            liquid = self.liquid if self.use_mass else LIQUID_L / 2
        return self.model.energy_cost(liquid, min(ang, 60.0), max(speed, 0.0), dt=dt)

    # ---- whole mission: base <-> field transit ----------------------------
    def _leg_cost(self, liquid, ang_deg, dist, speed):
        """battery % to fly `dist` metres at `speed` with the given tank and climb angle"""
        liq = liquid if self.use_mass else LIQUID_L / 2
        return self.model.energy_cost(liq, float(np.clip(ang_deg, 0, 60)), speed,
                                      dt=dist / speed)

    def _setup_transit(self):
        self.out_cost, self.home_ang, self.home_d = 0.0, 0.0, 0.0
        if not self.transit:
            return
        self.home_d = float(self._rng.uniform(*BASE_D))
        z = np.nan_to_num(self.z_srtm, nan=float(np.nanmean(self.z_srtm)))
        R, C = z.shape
        r0, c0 = self._rc
        dz = 0.0
        for _ in range(40):                       # find a base location inside the SRTM tile
            th = self._rng.uniform(0, 2 * np.pi)
            rr = r0 + self.home_d / SRTM_DX * np.sin(th)
            cc = c0 + self.home_d / SRTM_DX * np.cos(th)
            if 0 <= rr <= R - 1 and 0 <= cc <= C - 1:
                zb = map_coordinates(z, [[rr], [cc]], order=1)[0]
                dz = float(z[min(r0, R - 1), min(c0, C - 1)] - zb)   # >0: field is uphill of base
                break
        self.home_ang = float(np.degrees(np.arctan2(dz, self.home_d)))
        self.out_cost = self._leg_cost(LIQUID_L, self.home_ang, self.home_d, TRANSIT_V)
        self.battery -= self.out_cost

    def _return_cost(self, liquid=None):
        """battery % needed to fly home from here with the tank as it is now
        (`liquid` overrides the tank level, used only for a hide_mass observation)"""
        if not self.transit:
            return 0.0
        liq = self.liquid if liquid is None else liquid
        d_in = float(np.hypot(self.x - 5.0, self.y - 5.0))
        c_in = self._leg_cost(liq, 0.0, d_in, TRANSIT_V) if d_in > 0.5 else 0.0   # not spraying on the way home
        c_tr = self._leg_cost(liq, -self.home_ang, self.home_d, TRANSIT_V)
        return c_in + c_tr

    # ---- gym API ----------------------------------------------------------
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._rng = self.np_random
        self._make_patch(); self._make_trees()
        self.covered = np.zeros((self.n_c, self.n_c), dtype=bool)
        self.x, self.y, self.h = 5.0, 5.0, 3.0
        self.vx = self.vy = 0.0
        self.liquid, self.battery = LIQUID_L, 100.0
        self.t, self.area_ha, self.path_m, self.collisions = 0, 0.0, 0.0, 0
        self._setup_transit()
        return self._obs(), {}

    def _obs(self):
        speed = float(np.hypot(self.vx, self.vy))
        if speed > 0.1:
            ux, uy = self.vx / speed, self.vy / speed
        else:
            ux, uy = self._nearest_uncovered_dir()
        here  = self._slope_mag(self.x, self.y)
        ahead = self._slope_dir(self.x, self.y, ux, uy)
        rise  = max(0.0, np.tan(np.radians(ahead)) * self.v_max)

        # tank level the agent is allowed to see: the real one, or a constant if hidden
        seen_liquid = BLIND_LIQUID if self.hide_mass else None
        drain = self._drain_pct(self.v_max, rise, 60.0, liquid=seen_liquid)    # %/min estimate
        liq_for_mass = BLIND_LIQUID if self.hide_mass else self.liquid
        m = self.model.current_mass(liq_for_mass)
        m_max = self.model.current_mass(LIQUID_L)
        liq_feat = liq_for_mass / LIQUID_L

        ndx, ndy = self._nearest_uncovered_dir()
        obs = np.concatenate([
            [self.battery / 100.0, liq_feat, m / m_max,
             min(here, 45.0) / 45.0, (np.clip(ahead, -45, 45) + 45) / 90.0,
             min(drain, 30.0) / 30.0],
            self._sector_dists() / SENSE_M,
            [(ndx + 1) / 2, (ndy + 1) / 2]])
        if self.obs_mode in ("ext24", "ext26"):
            obs = np.concatenate([obs, self._coverage_sectors()])
        if self.obs_mode == "ext26":
            floor = RESERVE_BATT if self.transit else RTH_BATT
            margin = (self.battery - self._return_cost(liquid=seen_liquid) - floor) / 100.0
            dhome = np.hypot(self.x - 5.0, self.y - 5.0) / (PATCH_M * 1.42)
            obs = np.concatenate([obs, [np.clip(margin, 0, 1), np.clip(dhome, 0, 1)]])
        return np.clip(obs, 0, 1).astype(np.float32)

    def step(self, action):
        a = np.clip(np.asarray(action, dtype=float), -1, 1)
        tvx, tvy = a[0] * self.v_max, a[1] * self.v_max
        sp = np.hypot(tvx, tvy)
        if sp > self.v_max:
            tvx, tvy = tvx * self.v_max / sp, tvy * self.v_max / sp
        self.vx += 0.6 * (tvx - self.vx)
        self.vy += 0.6 * (tvy - self.vy)
        vz = a[2] * VZ_MAX

        x0, y0, z0 = self.x, self.y, self._elev(self.x, self.y) + self.h
        nx = float(np.clip(x0 + self.vx, 0, PATCH_M))
        ny = float(np.clip(y0 + self.vy, 0, PATCH_M))
        nh = float(np.clip(self.h + vz, H_MIN, H_MAX))
        dist = float(np.hypot(nx - x0, ny - y0))
        speed = dist                                      # 1 s step
        rise = (self._elev(nx, ny) + nh) - z0             # m per s
        cost = self._drain_pct(speed, rise, 1.0)          # physics: always the real tank

        # spray along the segment (start, middle, end)
        new_ha = 0.0
        if dist > 0.3 and self.liquid > 0:
            for f in (0.0, 0.5, 1.0):
                new_ha += self._spray_at(x0 + f * (nx - x0), y0 + f * (ny - y0))
            self.liquid = max(0.0, self.liquid - L_PER_M * dist)
        self.x, self.y, self.h = nx, ny, nh
        self.battery -= cost
        self.area_ha += new_ha
        self.path_m += dist
        self.t += 1

        gap = self._min_gap()
        crashed = gap < COLLIDE_M
        if crashed:
            self.collisions += 1

        reward = R_COVER * new_ha - R_ENERGY * cost - R_TIME
        if gap < WARN_M:
            reward -= R_WARN * (WARN_M - gap)
        if crashed:
            reward -= self.r_crash

        terminated = (self.liquid <= 0.05) or (crashed and self.terminate_on_collision)
        if self.transit:
            rc = self._return_cost()                      # physics: always the real tank
            low = (self.battery - rc) <= RESERVE_BATT
        else:
            rc, low = 0.0, self.battery <= RTH_BATT
        truncated = low or (self.t >= MAX_STEPS)
        if self.transit and (terminated or truncated):
            reward -= R_ENERGY * rc                      # the flight home is part of the cost
        used = 100.0 - self.battery + rc                 # outbound + spraying + return
        info = dict(area_ha=self.area_ha, battery_used=used,
                    liquid_left=self.liquid, collisions=self.collisions,
                    return_pct=rc, transit_out_pct=self.out_cost,
                    coverage_per_charge=(self.area_ha * 100.0 / max(used, 1e-6)))
        return self._obs(), float(reward), terminated, truncated, info


# =====================================================================
# Fixed-route baseline: serpentine "lawnmower" (what the field visit saw)
# =====================================================================
class LawnmowerPolicy:
    """Sweep along x at fixed y, step across by one swath width, sweep back."""
    def __init__(self, spacing=SWATH_M):
        self.spacing = spacing

    def reset(self):
        self.row, self.dir, self.phase = 0, 1, "sweep"

    def act(self, env):
        k = env.v_max / V_REF                      # thresholds scale with the speed cap
        y_row = 3.0 + self.row * self.spacing
        x_end = PATCH_M - 3.0 if self.dir == 1 else 3.0
        if self.phase == "sweep":
            if abs(env.x - x_end) < 1.5 * k:
                self.phase = "shift"
            vx = float(np.sign(x_end - env.x))
            vy = float(np.clip(0.3 * (y_row - env.y), -0.3, 0.3))
        else:
            y_next = 3.0 + (self.row + 1) * self.spacing
            if abs(env.y - y_next) < 0.8 * k:
                self.row += 1; self.dir *= -1; self.phase = "sweep"
            vx, vy = 0.0, float(np.sign(y_next - env.y))
        n = max(np.hypot(vx, vy), 1e-6)
        return np.array([vx / n, vy / n, 0.0])


def run_episode(env, policy_fn, seed):
    obs, _ = env.reset(seed=seed)
    done = False
    info = {}
    while not done:
        obs, r, term, trunc, info = env.step(policy_fn(obs))
        done = term or trunc
    return info


def evaluate_lawnmower(n=30):
    env = TeaSprayEnv(terminate_on_collision=False)
    pol = LawnmowerPolicy()
    res = []
    for s in range(n):
        pol.reset()
        res.append(run_episode(env, lambda o: pol.act(env), 1000 + s))
    return res


def check_blind(obs_mode="ext24"):
    """Confirms hide_mass removes the direct mass inputs (first 6 features) from the
    observation. Expect a clearly nonzero change for hide_mass=False and exactly 0.0
    for hide_mass=True. Any other value means there is another leak."""
    for hide in (False, True):
        e = TeaSprayEnv(seed=0, hide_mass=hide, obs_mode=obs_mode)
        e.reset(seed=0)
        e.liquid = LIQUID_L
        a = e._obs()
        e.liquid = 0.1 * LIQUID_L
        b = e._obs()
        print(f"hide_mass={hide!s:5} | max change in first 6 features when the tank "
              f"goes from 100% to 10%: {np.abs(a[:6] - b[:6]).max():.6f}")
        if obs_mode == "ext26":
            print(f"            | change in ext26 battery margin: {abs(a[24] - b[24]):.6f}")


if __name__ == "__main__":
    if "--check-blind" in sys.argv:
        check_blind("ext24")
        sys.exit(0)

    from gymnasium.utils.env_checker import check_env
    env = TeaSprayEnv(seed=0)
    check_env(env, skip_render_check=True)
    print("Gymnasium check_env: PASSED")
    obs, _ = env.reset(seed=0)
    print("Observation shape:", obs.shape, " range:", float(obs.min()), "to", float(obs.max()))

    # random-action sanity
    rng = np.random.default_rng(0)
    cov = []
    for s in range(10):
        info = run_episode(TeaSprayEnv(), lambda o: rng.uniform(-1, 1, 3), s)
        cov.append(info["coverage_per_charge"])
    print(f"Random policy       : coverage per charge {np.mean(cov):.3f} ha")

    res = evaluate_lawnmower(30)
    cpc = [r["coverage_per_charge"] for r in res]
    print(f"Lawnmower baseline  : coverage per charge {np.mean(cpc):.3f} ha "
          f"(std {np.std(cpc):.3f})")
    print(f"   area per mission {np.mean([r['area_ha'] for r in res]):.3f} ha, "
          f"battery used {np.mean([r['battery_used'] for r in res]):.1f} %, "
          f"collisions/mission {np.mean([r['collisions'] for r in res]):.1f}")
    print("SULEKO T20P real    : coverage per charge 0.506 ha, battery used 78.4 %")
    print()
    check_blind("ext24")