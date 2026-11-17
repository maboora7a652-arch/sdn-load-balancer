
import networkx as nx

from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import (
    CONFIG_DISPATCHER,
    MAIN_DISPATCHER,
    set_ev_cls
)
from os_ken.ofproto import ofproto_v1_3
from os_ken.topology import event
from os_ken.lib.packet import packet, ethernet, arp

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
        
        # Store connected switches
        self.datapaths = {}
        
        
        # Learn IP and MAC addresses automatically
        self.arp_table = {}




    # Send unknown packets to the controller
    @set_ev_cls(
        ofp_event.EventOFPSwitchFeatures,
        CONFIG_DISPATCHER
    )
    def switch_features(self, ev):

        dp = ev.msg.datapath
        
        # Save switch datapath
        self.datapaths[dp.id] = dp

        self.logger.info(
            "Datapath registered: S%s",
            dp.id
        )

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
        
    
    # Learn hosts and answer ARP requests
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def handle_arp(self, ev):

        msg = ev.msg
        dp = msg.datapath
        in_port = msg.match["in_port"]

        # Wait until topology discovery is complete
        if (
            self.graph.number_of_nodes() != 6
            or self.graph.number_of_edges() != 7
        ):
            return

        # Ignore switch-to-switch ports
        for src, dst, data in self.graph.edges(data=True):
            if dp.id in (src, dst):
                if data["ports"][dp.id] == in_port:
                    return

        # Read the packet
        pkt = packet.Packet(msg.data)

        eth = pkt.get_protocol(ethernet.ethernet)
        arp_msg = pkt.get_protocol(arp.arp)

        if eth is None or arp_msg is None:
            return

        src_mac = arp_msg.src_mac.lower()
        src_ip = arp_msg.src_ip

        # Check that the Ethernet and ARP sources match
        if eth.src.lower() != src_mac:
            return

        # Accept packets from discovered hosts only
        host_info = self.hosts.get(src_mac)

        if host_info is None:
            return

        if (
            host_info["switch"] != dp.id
            or host_info["port"] != in_port
        ):
            return

        # Learn the source IP-to-MAC mapping
        if src_ip != "0.0.0.0":

            if self.arp_table.get(src_ip) != src_mac:

                self.arp_table[src_ip] = src_mac

                self.logger.info(
                    "ARP learned: %s --> %s",
                    src_ip, src_mac
                )

        # Reply only to ARP requests
        if arp_msg.opcode != arp.ARP_REQUEST:
            return

        target_ip = arp_msg.dst_ip

        # Do not reply to a host asking for itself
        if target_ip == src_ip:
            return

        target_mac = self.arp_table.get(target_ip)

        if target_mac is None:
            self.logger.info(
                "ARP target unknown: %s",
                target_ip
            )
            return

        # Build the ARP reply
        reply = packet.Packet()

        reply.add_protocol(
            ethernet.ethernet(
                ethertype=0x0806,
                dst=src_mac,
                src=target_mac
            )
        )

        reply.add_protocol(
            arp.arp(
                opcode=arp.ARP_REPLY,
                src_mac=target_mac,
                src_ip=target_ip,
                dst_mac=src_mac,
                dst_ip=src_ip
            )
        )

        reply.serialize()

        # Send the reply to the requesting host
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        out = parser.OFPPacketOut(
            datapath=dp,
            buffer_id=ofp.OFP_NO_BUFFER,
            in_port=ofp.OFPP_CONTROLLER,
            actions=[
                parser.OFPActionOutput(in_port)
            ],
            data=reply.data
        )

        dp.send_msg(out)

        self.logger.info(
            "Proxy ARP: %s is at %s (reply to %s)",
            target_ip,
            target_mac,
            src_ip
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
                
                
                # Install forward IPv4 flows from H1 to H6
                for index, current in enumerate(path):

                    # Input port
                    if index == 0:
                        in_port = 3
                    else:
                        previous = path[index - 1]
                        in_port = self.graph[current][previous]["ports"][current]

                    # Output port
                    if index == len(path) - 1:
                        out_port = 3
                    else:
                        next_switch = path[index + 1]
                        out_port = self.graph[current][next_switch]["ports"][current]

                    # Get the switch connection
                    dp = self.datapaths.get(current)

                    if dp is not None:
                        self.install_flow(
                            dp,
                            in_port,
                            "00:00:00:00:00:06",
                            out_port
                        )
                        
                # Install reverse flows from H6 to H1
                reverse_path = list(reversed(path))

                for index, current in enumerate(reverse_path):

                    # Input port
                    if index == 0:
                        in_port = 3
                    else:
                        previous = reverse_path[index - 1]
                        in_port = self.graph[current][previous]["ports"][current]

                    # Output port
                    if index == len(reverse_path) - 1:
                        out_port = 3
                    else:
                        next_switch = reverse_path[index + 1]
                        out_port = self.graph[current][next_switch]["ports"][current]

                    # Install the flow
                    dp = self.datapaths.get(current)

                    if dp is not None:
                        self.install_flow(
                            dp,
                            in_port,
                            "00:00:00:00:00:01",
                            out_port
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

        
        if (
            len(self.hosts) == 6
            and self.graph.number_of_edges() == 7
            and "00:00:00:00:00:06" in self.hosts
        ):


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


    # Install an OpenFlow rule
    def install_flow(self, datapath, in_port, dst_mac, out_port):

        ofp = datapath.ofproto
        parser = datapath.ofproto_parser

        # Match incoming IPv4 packets
        match = parser.OFPMatch(
            in_port=in_port,
            eth_type=0x0800,
            eth_dst=dst_mac
        )

        # Forward packet to the selected port
        actions = [
            parser.OFPActionOutput(out_port)
        ]

        instructions = [
            parser.OFPInstructionActions(
                ofp.OFPIT_APPLY_ACTIONS,
                actions
            )
        ]

        # Create the FlowMod message
        flow_mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=10,
            match=match,
            instructions=instructions,
            idle_timeout=0
        )

        # Send the rule to the switch
        datapath.send_msg(flow_mod)

        self.logger.info(
            "Flow installed on S%s: Port %s -> Port %s",
            datapath.id,
            in_port,
            out_port
        )

