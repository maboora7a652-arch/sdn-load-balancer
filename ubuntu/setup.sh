#!/usr/bin/env bash
set -eu

if [ "$(uname -s)" != Linux ] || ! command -v apt >/dev/null; then
    echo "Run this file inside Ubuntu, not Windows." >&2
    exit 1
fi
if [ "$(id -u)" -eq 0 ]; then
    echo "Run bash setup.sh from your normal Ubuntu account, without sudo." >&2
    exit 1
fi

source_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
project="$HOME/sdn-project"
if [ "$source_dir" != "$project" ]; then
    python3 "$source_dir/install_local.py"
    exec bash "$project/setup.sh"
fi

for file in requirements.txt run.sh vm-source/rest_api_controller.py vm-source/custom_topology.py experiments/grid_demo.py dashboard/serve.py; do
    if [ ! -f "$project/$file" ]; then
        echo "Missing $file. Copy the complete ubuntu folder." >&2
        exit 1
    fi
done

environment="$HOME/sdn-lab/.venv"
manager="$environment/bin/osken-manager"
if [ -e "$environment" ] && [ ! -x "$manager" ]; then
    echo "An existing environment has no osken-manager: $environment" >&2
    echo "It was preserved. Resolve this environment before continuing." >&2
    exit 1
fi

sudo apt update
sudo apt install -y mininet openvswitch-switch iperf iperf3 python3-venv curl
sudo systemctl start openvswitch-switch
if [ ! -x "$manager" ]; then
    mkdir -p -- "$HOME/sdn-lab"
    python3 -m venv "$environment"
    "$environment/bin/python" -m pip install -r "$project/requirements.txt"
else
    echo "Reusing the existing OS-Ken environment; no pip upgrade."
fi

printf '\nReady. Open three Ubuntu terminals and run one command in each:\n'
printf 'bash ~/sdn-project/run.sh controller grid\n'
printf 'bash ~/sdn-project/run.sh network grid\n'
printf 'bash ~/sdn-project/run.sh dashboard\n'
printf 'Then open http://127.0.0.1:8081 inside Ubuntu.\n'
