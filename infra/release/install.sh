#!/bin/bash
# Existing authenticated operator account; explicit cutover authorization required.
set -euo pipefail
if [[ $(id -u) -ne 1000 || $# -ne 1 ]]; then
  echo 'Usage: install.sh /absolute/path/to/reviewed-inactive-config.json (operator UID 1000)' >&2
  exit 2
fi
release_source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
release_config=$1
[[ $release_config = /* && -f $release_config && ! -L $release_config ]]
# Existing linger-enabled user manager, no new root account or Docker membership.
[[ $(loginctl show-user "$(id -un)" -p Linger --value) = yes ]]
[[ ! -e $HOME/.config/workoutapp-release/config.json ]]
python3 - "$release_config" <<'PY'
import json,sys
from pathlib import Path
value=json.loads(Path(sys.argv[1]).read_text())
assert value['enabled'] is False and value['automatic_rollback'] is False
assert value['state_dir']==str(Path.home()/'.local/state/workoutapp-release')
assert all(Path(item['path']).is_absolute() for item in value['compose_files'])
PY
install -d -m 0700 "$HOME/.local/libexec/workoutapp-release" "$HOME/.config/workoutapp-release" "$HOME/.local/state/workoutapp-release"
install -d -m 0755 "$HOME/.config/systemd/user"
install -m 0700 "$release_source_dir/release.py" "$HOME/.local/libexec/workoutapp-release/release.py"
install -m 0600 "$release_config" "$HOME/.config/workoutapp-release/config.json"
install -m 0644 "$release_source_dir/workoutapp-release.service" "$HOME/.config/systemd/user/workoutapp-release.service"
install -m 0644 "$release_source_dir/workoutapp-release.timer" "$HOME/.config/systemd/user/workoutapp-release.timer"
systemctl --user daemon-reload
echo 'Installed inactive operator-owned executor; timer was not enabled; no application changed.'
