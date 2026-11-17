
import networkx as nx

from os_ken.base import app_manager
from os_ken.controller.handler import set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.topology import event

# Enable topology discovery
app_manager.require_app("os_ken.topology.switches")


class TopologyController(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create an empty NetworkX graph
        self.graph = nx.Graph()

    # Discover switches
    @set_ev_cls(event.EventSwitchEnter)
    def switch_added(self, ev):

        dpid = ev.switch.dp.id

        self.graph.add_node(dpid)

        self.logger.info("Switch S%s discovered", dpid)
        self.show_topology()

    # Discover links and save port numbers
    @set_ev_cls(event.EventLinkAdd)
    def link_added(self, ev):

        src = ev.link.src.dpid
        dst = ev.link.dst.dpid

        src_port = ev.link.src.port_no
        dst_port = ev.link.dst.port_no

        is_new_link = not self.graph.has_edge(src, dst)

        # Store link and its port numbers
        self.graph.add_edge(
            src,
            dst,
            ports={
                src: src_port,
                dst: dst_port
            }
        )

        if is_new_link:

            self.logger.info(
                "Saved: S%s (port %s) <--> S%s (port %s)",
                src, src_port, dst, dst_port
            )

            # Verify the stored port number
            saved_port = self.graph[src][dst]["ports"][src]

            self.logger.info(
                "Verified: S%s uses port %s",
                src, saved_port
            )

            self.show_topology()

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

            self.show_topology()

    # Detect switch disconnection
    @set_ev_cls(event.EventSwitchLeave)
    def switch_removed(self, ev):

        dpid = ev.switch.dp.id

        if self.graph.has_node(dpid):

            self.graph.remove_node(dpid)

            self.logger.info(
                "Switch S%s removed",
                dpid
            )

            self.show_topology()

    # Display the current topology
    def show_topology(self):

        switches = self.graph.number_of_nodes()
        links = self.graph.number_of_edges()

        self.logger.info(
            "Topology: %s switches, %s links",
            switches, links
        )

        if switches == 6 and links == 7:

            self.logger.info(
                "Discovered 6 switches and 7 links"
            )

            # Display links with their saved ports
            for src, dst in sorted(self.graph.edges()):

                src_port = self.graph[src][dst]["ports"][src]
                dst_port = self.graph[src][dst]["ports"][dst]

                self.logger.info(
                    "S%s (port %s) <--> S%s (port %s)",
                    src, src_port, dst, dst_port
                )

