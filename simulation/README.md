# Simulation (PX4 + Gazebo Harmonic, WSL Ubuntu 24.04)

## C2 - wind-adaptive spraying in the simulator

Runs Component 2 (`recommend()` from the backend) live while a simulated x500 drone flies in wind.

### One-time setup
1. PX4 + Gazebo Harmonic installed in `~/PX4-Autopilot`, and `export GZ_IP=127.0.0.1` in `~/.bashrc`.
2. Copy the C2 worlds into PX4:
   `cp <repo>/simulation/gazebo/worlds/c2_*.sdf ~/PX4-Autopilot/Tools/simulation/gz/worlds/`
3. Python environment:
   `python3 -m venv ~/c2_sim/.venv && source ~/c2_sim/.venv/bin/activate && pip install -r requirements-c2.txt`

### Run
Terminal 1 (no venv): `cd ~/PX4-Autopilot && PX4_GZ_WORLD=c2_windy make px4_sitl gz_x500`
then at `pxh>`: `commander takeoff` (simulator only, if arming is denied: `param set NAV_DLL_ACT 0`)

Terminal 2 (venv on), from this `simulation` folder:
- fixed wind: `python3 c2_live.py --world c2_windy`
- one-flight demo (calm -> moderate -> strong -> moderate, 60 s each): `python3 c2_live.py --world c2_windy --timeline`

Worlds: `c2_calm` (0.3 m/s), `c2_windy` (2.24 m/s), `c2_strong` (5.39 m/s).
CSV logs are saved to `simulation/logs/` (not committed to Git).