
import networkx as nx
import time
import json

from eventlet import listen, wsgi



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
from os_ken.lib import hub

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
        
        # Store pending ARP requests
        self.pending_arp = {}
        
        # Store all physical switch ports
        self.switch_ports = {}

        # Save previous statistics for comparison
        self.flow_snapshot = {}
        self.port_snapshot = {}
        
        # Store latest bandwidth measurements for REST API
        self.bandwidth_data = {}        

        # Start monitoring every 5 seconds
        self.monitor_thread = hub.spawn(self.monitor_network)
        
        # Start REST API server
        self.rest_thread = hub.spawn(self.start_rest_api)
        
        






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

        
        # Wait until all switches are discovered
        if self.graph.number_of_nodes() != 6:
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
                
        # Resolve requests waiting for this IP address
        if src_ip != "0.0.0.0" and src_ip in self.pending_arp:
            self.resolve_pending_arp(src_ip, src_mac)


        # Reply only to ARP requests
        if arp_msg.opcode != arp.ARP_REQUEST:
            return

        target_ip = arp_msg.dst_ip

        # Do not reply to a host asking for itself
        if target_ip == src_ip:
            return

        
        
        target_mac = self.arp_table.get(target_ip)

        if target_mac is None:

            # Save the ARP request until the target is discovered
            request = {
                "switch": dp.id,
                "port": in_port,
                "src_ip": src_ip,
                "src_mac": src_mac
            }

            pending = self.pending_arp.setdefault(
                target_ip, []
            )

            # Avoid saving duplicate requests
            if request not in pending:
                pending.append(request)

            self.logger.info(
                "ARP pending: %s requested by %s",
                target_ip,
                src_ip
            )
            # Search for the unknown target
            self.send_arp_probe(target_ip)
            return
            
        # Install the route for a known destination
        if not self.install_dynamic_route(src_mac, target_mac):
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
        
    # Send ARP probes only through host-facing ports
    def send_arp_probe(self, target_ip):

        probe_mac = "02:00:00:00:00:fe"
        probe_ip = "10.0.0.254"

        # Build ARP request
        probe = packet.Packet()

        probe.add_protocol(
            ethernet.ethernet(
                dst="ff:ff:ff:ff:ff:ff",
                src=probe_mac,
                ethertype=0x0806
            )
        )

        probe.add_protocol(
            arp.arp(
                opcode=arp.ARP_REQUEST,
                src_mac=probe_mac,
                src_ip=probe_ip,
                dst_mac="00:00:00:00:00:00",
                dst_ip=target_ip
            )
        )

        probe.serialize()

        # Send probes to host-facing ports only
        for dpid, ports in self.switch_ports.items():

            dp = self.datapaths.get(dpid)

            if dp is None:
                continue

            # Find ports connected to other switches
            link_ports = set()

            for src, dst, data in self.graph.edges(data=True):

                if dpid in (src, dst):
                    link_ports.add(data["ports"][dpid])

            # Exclude switch-to-switch ports
            host_ports = ports - link_ports

            if not host_ports:
                continue

            parser = dp.ofproto_parser
            ofp = dp.ofproto

            actions = [
                parser.OFPActionOutput(port)
                for port in sorted(host_ports)
            ]

            out = parser.OFPPacketOut(
                datapath=dp,
                buffer_id=ofp.OFP_NO_BUFFER,
                in_port=ofp.OFPP_CONTROLLER,
                actions=actions,
                data=probe.data
            )

            dp.send_msg(out)

            self.logger.info(
                "ARP Probe: Who has %s? S%s ports %s",
                target_ip,
                dpid,
                sorted(host_ports)
            )
            
    # Resolve saved ARP requests after discovering a host
    def resolve_pending_arp(self, target_ip, target_mac):

        waiting_requests = self.pending_arp.pop(target_ip, [])

        for request in waiting_requests:

            src_ip = request["src_ip"]
            src_mac = request["src_mac"]
            switch_id = request["switch"]
            host_port = request["port"]

            # Verify the original requesting host
            host_info = self.hosts.get(src_mac)

            if host_info is None:
                continue

            if (
                host_info["switch"] != switch_id
                or host_info["port"] != host_port
            ):
                continue

            dp = self.datapaths.get(switch_id)

            if dp is None:
                continue

            # Install the route before answering ARP
            if not self.install_dynamic_route(src_mac, target_mac):

                self.pending_arp.setdefault(
                    target_ip, []
                ).append(request)

                continue

            # Build a Proxy ARP reply
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

            parser = dp.ofproto_parser
            ofp = dp.ofproto

            out = parser.OFPPacketOut(
                datapath=dp,
                buffer_id=ofp.OFP_NO_BUFFER,
                in_port=ofp.OFPP_CONTROLLER,
                actions=[
                    parser.OFPActionOutput(host_port)
                ],
                data=reply.data
            )

            dp.send_msg(out)

            self.logger.info(
                "Pending ARP resolved: %s is at %s (reply to %s)",
                target_ip,
                target_mac,
                src_ip
            )





    # Discover switches
    @set_ev_cls(event.EventSwitchEnter)
    def switch_added(self, ev):

        dpid = ev.switch.dp.id
        
        self.switch_ports[dpid] = {
            port.port_no
            for port in ev.switch.ports
            if not port.is_reserved() and port.is_live()
        }


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
            # Rebuild routes when a link comes back
            if self.arp_table:
                self.rebuild_routes()


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
    # Recalculate routes without the failed link
            self.rebuild_routes()
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
    def install_flow(self, datapath, in_port, dst_mac, out_port, src_mac=None):

        ofp = datapath.ofproto
        parser = datapath.ofproto_parser


        # Match incoming IPv4 packets
        match_fields = {
            "in_port": in_port,
            "eth_type": 0x0800,
            "eth_dst": dst_mac
        }

        if src_mac is not None:
            match_fields["eth_src"] = src_mac

        match = parser.OFPMatch(**match_fields)


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
            priority=20 if src_mac is not None else 10,
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
        
    # Install a path between any two hosts
    def install_dynamic_route(self, src_mac, dst_mac):

        src_host = self.hosts.get(src_mac)
        dst_host = self.hosts.get(dst_mac)

        # Both hosts must be discovered
        if src_host is None or dst_host is None:
            self.logger.info("Host location not found")
            return False

        src_switch = src_host["switch"]
        dst_switch = dst_host["switch"]

        # Calculate shortest path using Dijkstra
        try:
            path = nx.dijkstra_path(
                self.graph,
                source=src_switch,
                target=dst_switch
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.logger.info("No path available")
            return False

        # Check switch connections
        for switch in path:
            if switch not in self.datapaths:
                return False


        # Install forward and reverse paths
        directions = [
            (path, src_host, dst_host, src_mac, dst_mac),
            (list(reversed(path)), dst_host, src_host, dst_mac, src_mac)
        ]

        for route, start_host, end_host, source_mac, target_mac in directions:


            for index, current in enumerate(route):

                # Input port
                if index == 0:
                    in_port = start_host["port"]
                else:
                    previous = route[index - 1]
                    in_port = self.graph[current][previous]["ports"][current]

                # Output port
                if index == len(route) - 1:
                    out_port = end_host["port"]
                else:
                    next_switch = route[index + 1]
                    out_port = self.graph[current][next_switch]["ports"][current]

                dp = self.datapaths[current]


                self.install_flow(
                    dp,
                    in_port,
                    target_mac,
                    out_port,
                    source_mac
                )


        route_text = " -> ".join(
            "S{}".format(switch) for switch in path
        )

        self.logger.info(
            "Dynamic route installed: %s",
            route_text
        )

        return True

    # Request statistics from all connected switches
    def monitor_network(self):

        while True:

            for dp in list(self.datapaths.values()):

                parser = dp.ofproto_parser
                ofp = dp.ofproto

                # Request flow statistics
                flow_request = parser.OFPFlowStatsRequest(dp)
                dp.send_msg(flow_request)

                # Request statistics for all ports
                port_request = parser.OFPPortStatsRequest(
                    dp, 0, ofp.OFPP_ANY
                )
                dp.send_msg(port_request)

            hub.sleep(5)


    # Receive flow statistics
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply(self, ev):

        dp = ev.msg.datapath

        # Monitor the dynamic IPv4 forwarding rules
        flows = [
            stat for stat in ev.msg.body
            if stat.priority == 20
        ]

        total_packets = sum(
            stat.packet_count for stat in flows
        )

        total_bytes = sum(
            stat.byte_count for stat in flows
        )

        previous = self.flow_snapshot.get(dp.id)

        self.flow_snapshot[dp.id] = (
            total_packets,
            total_bytes
        )

        if previous is None:
            return

        packet_change = total_packets - previous[0]
        byte_change = total_bytes - previous[1]

        # Counters may reset when routes are rebuilt
        if packet_change < 0 or byte_change < 0:
            return

        if packet_change > 0:
            self.logger.info(
                "C4 FLOW S%s: +%s packets, +%s bytes",
                dp.id,
                packet_change,
                byte_change
            )


    # Receive port statistics
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply(self, ev):

        dp = ev.msg.datapath

        # Identify ports connected to discovered hosts
        host_ports = {
            info["port"]
            for info in self.hosts.values()
            if info["switch"] == dp.id
        }

        for stat in ev.msg.body:

            if stat.port_no not in host_ports:
                continue

            key = (dp.id, stat.port_no)


            previous = self.port_snapshot.get(key)

            # Save current counters and time
            now = time.monotonic()

            self.port_snapshot[key] = (
                stat.rx_bytes,
                stat.tx_bytes,
                now
            )

            # First measurement is a baseline
            if previous is None:
                continue

            rx_change = stat.rx_bytes - previous[0]
            tx_change = stat.tx_bytes - previous[1]
            elapsed = now - previous[2]

            # Ignore counter resets or invalid time
            if (
                rx_change < 0
                or tx_change < 0
                or elapsed <= 0
            ):
                continue

            # Calculate bandwidth in Mbps
            rx_mbps = (rx_change * 8) / (elapsed * 1000000)
            tx_mbps = (tx_change * 8) / (elapsed * 1000000)

            # Save the latest bandwidth for the REST API
            self.bandwidth_data[key] = {
                "switch": dp.id,
                "port": stat.port_no,
                "rx_mbps": round(rx_mbps, 6),
                "tx_mbps": round(tx_mbps, 6)
            }

            if rx_change + tx_change > 0:
                self.logger.info(
                    "C4 BANDWIDTH S%s P%s: "
                    "RX %.6f Mbps, TX %.6f Mbps",
                    dp.id,
                    stat.port_no,
                    rx_mbps,
                    tx_mbps
                )

 

    # Remove stale IPv4 flows and rebuild available routes
    def rebuild_routes(self):

        self.logger.info("Rebuilding routes after topology change")

        # Delete old IPv4 forwarding rules
        for dp in self.datapaths.values():

            ofp = dp.ofproto
            parser = dp.ofproto_parser

            delete_flow = parser.OFPFlowMod(
                datapath=dp,
                table_id=ofp.OFPTT_ALL,
                command=ofp.OFPFC_DELETE,
                out_port=ofp.OFPP_ANY,
                out_group=ofp.OFPG_ANY,
                match=parser.OFPMatch(
                    eth_type=0x0800
                )
            )

            dp.send_msg(delete_flow)

        # Select learned and discovered hosts
        known_macs = sorted({
            mac
            for mac in self.arp_table.values()
            if mac in self.hosts
        })

        rebuilt = 0

        # Reinstall a bidirectional route for each host pair
        for i, src_mac in enumerate(known_macs):

            for dst_mac in known_macs[i + 1:]:

                if self.install_dynamic_route(src_mac, dst_mac):
                    rebuilt += 1

        self.logger.info(
            "Route rebuild requested for %s host pairs",
            rebuilt
        )

 
    # Start a local HTTP server
    def start_rest_api(self):

        server_socket = listen(("127.0.0.1", 8080))

        self.logger.info(
            "C5 REST API started at http://127.0.0.1:8080"
        )

        wsgi.server(
            server_socket,
            self.rest_application,
            log_output=False
        )


    # Handle HTTP requests
    def rest_application(self, environ, start_response):

        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")

        # Return status of the SDN network
        if method == "GET" and path == "/sdn/status":

            learned_hosts = [
                mac for mac in self.hosts
                if mac in self.arp_table.values()
            ]

            data = {
                "status": "running",
                "switches": len(self.datapaths),
                "links": self.graph.number_of_edges(),
                "hosts": len(learned_hosts)
            }

            body = json.dumps(data).encode("utf-8")

            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(body)))
                ]
            )

            return [body]

        # Return discovered network topology
        if method == "GET" and path == "/sdn/topology":

            switches = sorted(self.graph.nodes())

            links = []

            for src, dst, info in self.graph.edges(data=True):

                # Keep switch order consistent
                src, dst = sorted((src, dst))

                ports = info["ports"]

                links.append({
                    "source": src,
                    "source_port": ports[src],
                    "destination": dst,
                    "destination_port": ports[dst]
                })

            # Sort links by switch ID
            links.sort(
                key=lambda link: (
                    link["source"],
                    link["destination"]
                )
            )

            data = {
                "switches": switches,
                "links": links
            }

            body = json.dumps(data).encode("utf-8")

            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(body)))
                ]
            )

            return [body]

        # Return discovered hosts with their locations
        if method == "GET" and path == "/sdn/hosts":

            hosts = []

            for ip, mac in self.arp_table.items():

                host_info = self.hosts.get(mac)

                if host_info is None:
                    continue

                hosts.append({
                    "ip": ip,
                    "mac": mac,
                    "switch": host_info["switch"],
                    "port": host_info["port"]
                })

            hosts.sort(key=lambda host: host["mac"])

            data = {
                "count": len(hosts),
                "hosts": hosts
            }

            body = json.dumps(data).encode("utf-8")

            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(body)))
                ]
            )


            return [body]

        # Return latest bandwidth measurements
        if method == "GET" and path == "/sdn/bandwidth":

            ports = sorted(
                self.bandwidth_data.values(),
                key=lambda item: (
                    item["switch"],
                    item["port"]
                )
            )

            data = {
                "count": len(ports),
                "unit": "Mbps",
                "ports": ports
            }

            body = json.dumps(data).encode("utf-8")

            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(body)))
                ]
            )

            return [body]

        # Unknown API endpoint
        body = b'{"error": "Not Found"}'

        start_response(
            "404 Not Found",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body)))
            ]
        )

        return [body]

