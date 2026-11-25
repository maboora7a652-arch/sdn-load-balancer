# Ubuntu demo

From the Ubuntu account, open three terminals. Start the controller first.
Use the same topology for the controller and Mininet.

    bash ~/sdn-project/run.sh controller grid
    bash ~/sdn-project/run.sh network grid
    bash ~/sdn-project/run.sh dashboard

Open http://127.0.0.1:8081 in Ubuntu. Select H1 to H6. After discovery shows six switches and seven links, type the following lines in Mininet, one at a time. The launcher starts Mininet in the local project directory.

The browser requests another snapshot one second after the preceding request finishes. Link discovery and counter polling have their own timing; traffic measurements use the controller polling period (five seconds by default).

    pingall
    py __import__('runpy').run_path('experiments/grid_demo.py', init_globals=dict(h1=h1,h3=h3,h5=h5,h6=h6)) and None

The second command generates two UDP streams for 60 seconds. Watch the path, utilization and priority. A move depends on measured congestion and improvement. If H1 to H6 finishes on S1–S4–S5–S6 at priority 21 or higher, the optional failure demonstration temporarily takes S5–S6 down during ping and restores it.

    py __import__('runpy').run_path('experiments/link_failure_demo.py', init_globals=dict(net=net)) and None

This interactive command uses presentation timing: about 60 seconds of ping, eight seconds before the cut, and at least 15 seconds with the link down. The restored path is printed five seconds after requesting link-up. Standalone repeated recovery experiments keep their original short timing. The JSON records presentation_mode.

Type `exit` in Mininet and press Ctrl+C in the controller and dashboard terminals to stop. For the fat-tree, start the same launchers using `fattree` in place of `grid`. Wait for 20 switches and 32 links. In Mininet:

    pingall 2
    py __import__('runpy').run_path('experiments/bandwidth_accuracy.py', init_globals=dict(net=net)) and None

The five UDP trials compare H1 to H16 sender rate with the first link, using the installed iperf3. Results and previously recorded trials are under `experiments/results/`. To see the standalone batch tests after stopping the interactive controller and Mininet:

    sudo python3 ~/sdn-project/experiments/compare_grid.py --help

For example, `--ten-flows` compares three routing modes on fresh grids. The `c1/` directory contains the learning switch and original Wireshark capture. OS-Ken runs from the existing Ubuntu environment in `~/sdn-lab/.venv`. Mininet, Open vSwitch, iperf and iperf3 are Ubuntu installations. After setup, these commands read the Ubuntu project copy and save results there.
