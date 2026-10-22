#!/usr/bin/env bash
# Re-test the trained agents under three energy-model settings (tank weight counted at 1.0, 0.5 and 0.2 of physics).
# Usage (from ~/component3/c3app):  bash tools/run_energy_retest.sh            -> all 3 agents, sets test + tank40
#                                    bash tools/run_energy_retest.sh quick      -> one agent, set test, 10 fields (about 10-15 min)
cd "$(dirname "$0")/../backend" || exit 1
export C3_BASE=${C3_BASE:-$HOME/component3} C3_DRL=${C3_DRL:-$HOME/component3/drl_agent} PYTHONPATH=$(pwd)
if [ "$1" = "quick" ]; then AGENTS="mission_ppo_v2_s0"; SETS="test"; N=10; else AGENTS="mission_ppo_v2_s0 mission_ppo_v2_s1 mission_ppo_v2_s2"; SETS="test tank40"; N=20; fi
for sc in a10 a05 a02; do
  for ag in $AGENTS; do
    for st in $SETS; do
      echo "=== scenario $sc | $ag | set $st | $N fields"
      C3_SCENARIO=$sc python3 eval_agent.py --model $ag --set $st --n $N | tail -25
    done
  done
done
python3 ../tools/summarise_retest.py
