#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 1) Prefer explicit mini backlog task list
BACKLOG_TASK="$(awk '
  /^### Task/{task=$0}
  /^ Status:/{
    if ($0 !~ /COMPLETED/ && task != "") {
      print task
      exit
    }
  }
' docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md || true)"

if [[ -n "${BACKLOG_TASK:-}" ]]; then
  echo "BACKLOG: ${BACKLOG_TASK}"
  exit 0
fi

# 2) Fallback to first unchecked checklist item in Master Plan roadmap phases
MASTER_TASK="$(awk '
  /^# Roadmap \(Phases \+ Checklists\)/{in_roadmap=1; next}
  in_roadmap && /^## Phase/{phase=$0; next}
  in_roadmap && /^- \[ \] /{
    item=$0
    sub(/^- \[ \] /, "", item)
    if (phase == "") phase="## Phase (unlabeled)"
    print "MASTER_PLAN: " phase " -> " item
    exit
  }
' docs/Master_Plan.md || true)"

if [[ -n "${MASTER_TASK:-}" ]]; then
  echo "$MASTER_TASK"
  exit 0
fi

echo "No incomplete task found in docs/archive/ai-handoffs/GPT5_MINI_EXECUTION_BACKLOG.md or docs/Master_Plan.md"
