#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$0")"
root=$PWD
topology=${2:-grid}
case "$topology" in
    grid) topology=mynetwork ;;
    fattree) topology=fattree4 ;;
    *) echo "Choose grid or fattree." >&2; exit 2 ;;
esac
case "${1:-}" in
    controller)
        export SDN_TOPOLOGY="$topology"
        exec "$HOME/sdn-lab/.venv/bin/osken-manager" --observe-links \
            --ofp-tcp-listen-port 6653 "$root/vm-source/rest_api_controller.py" ;;
    network)
        exec sudo mn --custom "$root/vm-source/custom_topology.py" --topo "$topology" \
            --mac --switch ovs,protocols=OpenFlow13 --link tc \
            --controller=remote,ip=127.0.0.1,port=6653 ;;
    dashboard) exec python3 "$root/dashboard/serve.py" ;;
    *) echo "Usage: bash run.sh {controller|network} [grid|fattree], or bash run.sh dashboard"; exit 2 ;;
esac
