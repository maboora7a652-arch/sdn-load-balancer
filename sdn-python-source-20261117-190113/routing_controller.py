
import networkx as nx

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER,
    set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3
from os_ken.topology import event

# Enable topology discovery
app_manager.require_app("os_ken.topology.switches")


class HostDiscoveryController(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Store switches and links
        self.graph = nx.Graph()

        # Store discovered hosts
        self.hosts = {}

    # Send unknown packets to the controller
    @set_ev_cls(
        ofp_event.EventOFPSwitchFeatures,
        CONFIG_DISPATCHER
    )
    def switch_features(self, ev):

        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()

        actions = [
            parser.OFPActionOutput(
                ofp.OFPP_CONTROLLER,
                ofp.OFPCML_NO_BUFFER
            )
        ]

        instructions = [
            parser.OFPInstructionActions(
                ofp.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        flow = parser.OFPFlowMod(
            datapath=dp,
            priority=0,
            match=match,
            instructions=instructions
        )

        dp.send_msg(flow)

        self.logger.info(
            "Table-miss rule installed on S%s", dp.id
        )

    # Discover switches
    @set_ev_cls(event.EventSwitchEnter)
    def switch_added(self, ev):

        dpid = ev.switch.dp.id

        self.graph.add_node(dpid)

        self.logger.info(
            "Switch S%s discovered", dpid
        )

    # Discover links and save ports
    @set_ev_cls(event.EventLinkAdd)
    def link_added(self, ev):

        src = ev.link.src.dpid
        dst = ev.link.dst.dpid

        src_port = ev.link.src.port_no
        dst_port = ev.link.dst.port_no

        is_new = not self.graph.has_edge(src, dst)

        self.graph.add_edge(
            src,
            dst,
            ports={
                src: src_port,
                dst: dst_port
            }
        )
        
        # Remove false hosts learned on switch-to-switch ports
        for mac, info in list(self.hosts.items()):

            on_src = (
                info["switch"] == src
                and info["port"] == src_port
            )

            on_dst = (
                info["switch"] == dst
                and info["port"] == dst_port
            )

            if on_src or on_dst:
                del self.hosts[mac]
                self.logger.info(
                    "Removed false host: %s", mac
                )


        if is_new:
            self.logger.info(
                "Link: S%s(port %s) <--> S%s(port %s)",
                src, src_port, dst, dst_port
            )

            self.logger.info(
                "Topology: %s switches, %s links",
                self.graph.number_of_nodes(),
                self.graph.number_of_edges()
            )
            
            # Calculate the shortest path when topology is ready
            if (
                self.graph.number_of_nodes() == 6
                and self.graph.number_of_edges() == 7
            ):

                path = nx.dijkstra_path(
                    self.graph,
                    source=1,
                    target=6
                )

                route = " -> ".join(
                    "S{}".format(switch) for switch in path
                )

                self.logger.info(
                    "Shortest path from H1 to H6: %s",
                    route
                )

                self.logger.info(
                    "Hop count: %s",
                    len(path) - 1
                )
                
                # Display output ports along the path
                for current, next_switch in zip(path, path[1:]):

                    out_port = self.graph[current][next_switch]["ports"][current]

                    self.logger.info(
                        "S%s: Output Port %s --> S%s",
                        current, out_port, next_switch
                    )



    # Detect link failure
    @set_ev_cls(event.EventLinkDelete)
    def link_removed(self, ev):

        src = ev.link.src.dpid
        dst = ev.link.dst.dpid

        if self.graph.has_edge(src, dst):
            self.graph.remove_edge(src, dst)

            self.logger.info(
                "Link removed: S%s - S%s",
                src, dst
            )

    # Detect switch disconnection
    @set_ev_cls(event.EventSwitchLeave)
    def switch_removed(self, ev):

        dpid = ev.switch.dp.id

        if self.graph.has_node(dpid):
            self.graph.remove_node(dpid)

        # Remove hosts attached to this switch
        for mac, info in list(self.hosts.items()):
            if info["switch"] == dpid:
                del self.hosts[mac]

        self.logger.info(
            "Switch S%s removed", dpid
        )

    # Discover hosts
    @set_ev_cls(event.EventHostAdd)
    def host_added(self, ev):

        host = ev.host

        mac = host.mac
        dpid = host.port.dpid
        port = host.port.port_no
        
        # Ignore known switch-to-switch ports
        for src, dst, data in self.graph.edges(data=True):

            if dpid in (src, dst):
                if data["ports"][dpid] == port:
                    self.logger.info(
                        "Ignored switch-link MAC: %s", mac
                    )
                    return


        self.hosts[mac] = {
            "switch": dpid,
            "port": port
        }

        self.logger.info(
            "Host discovered: MAC=%s, Switch=S%s, Port=%s",
            mac, dpid, port
        )

        self.logger.info(
            "Hosts discovered: %s",
            len(self.hosts)
        )

        if len(self.hosts) == 6 and self.graph.number_of_edges() == 7:

            self.logger.info(
                "All 6 hosts discovered!"
            )

            for mac, info in sorted(self.hosts.items()):
                self.logger.info(
                    "%s --> S%s (port %s)",
                    mac,
                    info["switch"],
                    info["port"]
                )
                
            # Find the destination host
            h6_mac = "00:00:00:00:00:06"

            destination = self.hosts[h6_mac]

            # Get the switch and port connected to H6
            dst_switch = destination["switch"]
            dst_port = destination["port"]

            self.logger.info(
                "Final step: S%s --> Output Port %s --> H6",
                dst_switch,
                dst_port
            )


