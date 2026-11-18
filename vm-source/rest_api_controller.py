
import networkx as nx
import time
import os
from itertools import islice
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
        self.topology_name = os.environ.get("SDN_TOPOLOGY", "mynetwork")
        if self.topology_name not in ("mynetwork", "fattree4"):
            raise ValueError("SDN_TOPOLOGY must be mynetwork or fattree4")
        self.expected_switches = 20 if self.topology_name == "fattree4" else 6
        self.fat_tree_discovered = False

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

        # Store flow statistics for REST API
        self.flow_data = {}
        self.flow_details = {}
        self.flow_sample_time = {}
        self.flow_detail_snapshot = {}

        self.port_snapshot = {}
        self.port_sample_time = {}

        
        # Store latest bandwidth measurements for REST API
        self.bandwidth_data = {}
        self.link_load = {}
        self.installed_paths = {}
        self.path_attachments = {}
        self.route_priorities = {}
        self.last_reroute = {}
        self.reroute_state = None
        self.poll_interval = float(os.environ.get("SDN_POLL_INTERVAL", "5"))
        if not 2 <= self.poll_interval <= 5:
            raise ValueError("SDN_POLL_INTERVAL must be between 2 and 5 seconds")        

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
        if self.graph.number_of_nodes() != self.expected_switches:
            return
        if self.topology_name == "fattree4" and not self.fat_tree_discovered:
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
            if (self.topology_name == "fattree4"
                    and self.graph.number_of_nodes() == self.expected_switches
                    and self.graph.number_of_edges() == 32):
                self.fat_tree_discovered = True

            if (
                self.topology_name == "mynetwork"
                and self.graph.number_of_nodes() == 6
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
            self.topology_name == "mynetwork"
            and len(self.hosts) == 6
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
    def install_flow(self, datapath, in_port, dst_mac, out_port, src_mac=None, priority=None):

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
            priority=priority if priority is not None else (20 if src_mac is not None else 10),
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
        return flow_mod.xid
        
    def cached_path_valid(self, src, dst):
        path = self.installed_paths.get((src, dst))
        source, target = self.hosts.get(src), self.hosts.get(dst)
        if not path or source is None or target is None:
            return False
        endpoints = ((source["switch"], source["port"]),
                     (target["switch"], target["port"]))
        return (self.path_attachments.get((src, dst)) == endpoints
                and path[0] == source["switch"] and path[-1] == target["switch"]
                and all(switch in self.datapaths for switch in path)
                and all(self.graph.has_edge(a, b) for a, b in zip(path, path[1:])))

    # Install a path between any two hosts
    def install_dynamic_route(self, src_mac, dst_mac):

        src_host = self.hosts.get(src_mac)
        dst_host = self.hosts.get(dst_mac)

        # ARP refresh must not reinstall valid routes or reset their counters.
        if self.reroute_state is not None:
            return False
        if (self.cached_path_valid(src_mac, dst_mac)
                and self.cached_path_valid(dst_mac, src_mac)):
            return True
        if (self.route_priorities.get((src_mac, dst_mac), 20) > 20
                or self.route_priorities.get((dst_mac, src_mac), 20) > 20):
            self.rebuild_routes()
            return (self.cached_path_valid(src_mac, dst_mac)
                    and self.cached_path_valid(dst_mac, src_mac))

        # Both hosts must be discovered
        if src_host is None or dst_host is None:
            self.logger.info("Host location not found")
            return False

        src_switch = src_host["switch"]
        dst_switch = dst_host["switch"]

        # Canonical edge order makes equal-hop initial routes reproducible.
        routing_graph = nx.Graph()
        routing_graph.add_nodes_from(sorted(self.graph.nodes()))
        routing_graph.add_edges_from(sorted(
            tuple(sorted((a, b))) for a, b in self.graph.edges()))
        # Calculate shortest path using Dijkstra.
        try:
            path = nx.dijkstra_path(
                routing_graph,
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


        self.installed_paths[(src_mac, dst_mac)] = list(path)
        self.installed_paths[(dst_mac, src_mac)] = list(reversed(path))
        endpoints = ((src_host["switch"], src_host["port"]),
                     (dst_host["switch"], dst_host["port"]))
        self.path_attachments[(src_mac, dst_mac)] = endpoints
        self.path_attachments[(dst_mac, src_mac)] = tuple(reversed(endpoints))
        self.route_priorities[(src_mac, dst_mac)] = 20
        self.route_priorities[(dst_mac, src_mac)] = 20
        route_text = " -> ".join(
            "S{}".format(switch) for switch in path
        )

        self.logger.info(
            "Dynamic route installed: %s",
            route_text
        )

        return True

    # Estimate offered demand once per ingress host pair. Port TX can be
    # lower than offered demand when the current path is dropping packets.
    def ingress_demands(self, src, dst, rate_mbps):
        now = time.monotonic()
        rates = {}
        for switch, flows in self.flow_details.items():
            if now - self.flow_sample_time.get(switch, float("-inf")) > 2 * self.poll_interval:
                continue
            for flow in flows:
                rate = flow.get("rate_mbps")
                if rate is not None:
                    rates[(flow["src_mac"], flow["dst_mac"])] = rate
        rates[(src, dst)] = rate_mbps
        demand = {}
        for key, rate in rates.items():
            route = self.installed_paths.get(key, [])
            for edge in zip(route, route[1:]):
                demand[edge] = demand.get(edge, 0.0) + rate
        return demand

    # Read-only scoring; this method never sends OpenFlow messages.
    def evaluate_paths(self, src_mac, dst_mac, rate_mbps):
        old_path = self.installed_paths.get((src_mac, dst_mac))
        result = {"current_path": old_path, "candidates": [],
                  "best_path": None, "improvement_pp": None, "ready": False,
                  "load_model": "max(port_tx, ingress_demand)"}
        if not old_path or rate_mbps is None or rate_mbps <= 0:
            return result
        if not all(self.graph.has_edge(a, b) for a, b in zip(old_path, old_path[1:])):
            return result
        old_edges = set(zip(old_path, old_path[1:]))
        old_physical = {frozenset(edge) for edge in old_edges}
        demand = self.ingress_demands(src_mac, dst_mac, rate_mbps)
        now = time.monotonic()

        def measurement(a, b):
            port = self.graph[a][b]["ports"][a]
            key = (a, port)
            value = self.bandwidth_data.get(key)
            if (not value or value.get("neighbor") != b
                    or now - self.port_sample_time.get(key, float("-inf")) > 2 * self.poll_interval):
                return None
            return max(value["tx_mbps"], demand.get((a, b), 0.0)), value["capacity_mbps"]

        old_loads = [measurement(a, b) for a, b in old_edges]
        if any(value is None or value[1] <= 0 for value in old_loads):
            return result
        current_bottleneck = max((rate / capacity for rate, capacity in old_loads), default=0)
        try:
            paths = list(islice(nx.shortest_simple_paths(
                self.graph, old_path[0], old_path[-1]), 3))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return result
        raw_costs = {}
        for path in paths:
            projected = []
            edges = list(zip(path, path[1:]))
            for a, b in edges:
                reading = measurement(a, b)
                if reading is None or reading[1] <= 0:
                    break
                load, capacity = reading
                background = max(0, load - rate_mbps) if (a, b) in old_edges else load
                projected.append((background + rate_mbps) / capacity)
            else:
                raw_costs[tuple(path)] = max(projected, default=0)
                result["candidates"].append({
                    "path": list(path),
                    # Compare costs at 0.001 percentage-point resolution.
                    "projected_bottleneck_percent": round(raw_costs[tuple(path)] * 100, 3),
                    "hops": len(edges),
                    "shared_links": len({frozenset(e) for e in edges} & old_physical)
                })
        if len(result["candidates"]) != len(paths) or not paths:
            return result
        result["candidates"].sort(key=lambda item: (
            item["projected_bottleneck_percent"], item["hops"],
            item["shared_links"], item["path"]))
        best = result["candidates"][0]
        result.update({"best_path": best["path"],
                       "current_bottleneck_percent": round(current_bottleneck * 100, 3),
                       "improvement_pp": (current_bottleneck - raw_costs[tuple(best["path"])]) * 100,
                       "ready": True})
        return result

    def rebalance_network(self):
        if self.reroute_state is not None:
            return
        now = time.monotonic()
        if any(now - self.flow_sample_time.get(switch, float("-inf")) > 2 * self.poll_interval
               for switch in self.datapaths):
            return
        elephants = [flow for flows in self.flow_details.values() for flow in flows
                     if flow["elephant"] and flow.get("rate_mbps") is not None]
        # Decide once per polling round, largest elephant first, not reply order.
        for flow in sorted(elephants, key=lambda item: (
                -item["rate_mbps"], item["src_mac"], item["dst_mac"])):
            choice = self.evaluate_paths(flow["src_mac"], flow["dst_mac"], flow["rate_mbps"])
            self.maybe_reroute(flow["src_mac"], flow["dst_mac"], choice)
            if self.reroute_state is not None:
                break

    def path_hops(self, path, src, dst):
        hops = []
        for i, switch in enumerate(path):
            in_port = (self.hosts[src]["port"] if i == 0 else
                       self.graph[switch][path[i - 1]]["ports"][switch])
            out_port = (self.hosts[dst]["port"] if i == len(path) - 1 else
                        self.graph[switch][path[i + 1]]["ports"][switch])
            hops.append((switch, in_port, out_port))
        return hops

    def maybe_reroute(self, src, dst, choice):
        if self.reroute_state is not None or not choice["ready"]:
            return
        key = (src, dst)
        old_path = choice["current_path"]
        new_path = choice["best_path"]
        if new_path == old_path or choice["improvement_pp"] < 15:
            return
        if time.monotonic() - self.last_reroute.get(key, float("-inf")) < 30:
            return
        # Congestion must be present on an old-path direction for two periods.
        if not any(self.link_load.get(
                (a, self.graph[a][b]["ports"][a]), (0, 0))[1] >= 2
                for a, b in zip(old_path, old_path[1:])):
            return
        if src not in self.hosts or dst not in self.hosts:
            return
        if any(switch not in self.datapaths for switch in set(old_path + new_path)):
            return
        priority = self.route_priorities.get(key, 20)
        if priority >= 65534:
            return
        self.reroute_state = {
            "src": src, "dst": dst, "old_path": list(old_path),
            "new_path": list(new_path), "old_priority": priority,
            "priority": priority + 1,
            "old_hops": self.path_hops(old_path, src, dst),
            "new_hops": list(reversed(self.path_hops(new_path, src, dst))),
            "index": 0, "sent_hops": [], "requests": set(),
            "barrier": None, "started": time.monotonic(),
            "improvement_pp": choice["improvement_pp"]
        }
        self.send_reroute_hop()

    def send_reroute_hop(self):
        state = self.reroute_state
        if state is None:
            return
        if state["index"] == len(state["new_hops"]):
            # All new hops acknowledged, including ingress. Retire only old rules.
            for hop in state["old_hops"]:
                self.delete_path_rule(state, hop, state["old_priority"])
            key = (state["src"], state["dst"])
            self.installed_paths[key] = state["new_path"]
            self.route_priorities[key] = state["priority"]
            self.last_reroute[key] = time.monotonic()
            self.logger.info(
                "REROUTE %s -> %s: %s => %s; improvement %.3f pp",
                state["src"], state["dst"], state["old_path"],
                state["new_path"], state["improvement_pp"])
            self.reroute_state = None
            return
        hop = state["new_hops"][state["index"]]
        switch, in_port, out_port = hop
        dp = self.datapaths.get(switch)
        if dp is None:
            self.abort_reroute("switch disconnected")
            return
        state["sent_hops"].append(hop)
        xid = self.install_flow(dp, in_port, state["dst"], out_port,
                                state["src"], priority=state["priority"])
        state["requests"].add((switch, xid))
        barrier = dp.ofproto_parser.OFPBarrierRequest(dp)
        dp.set_xid(barrier)
        state["barrier"] = (switch, barrier.xid)
        dp.send_msg(barrier)

    @set_ev_cls(ofp_event.EventOFPBarrierReply, MAIN_DISPATCHER)
    def reroute_barrier_reply(self, ev):
        state = self.reroute_state
        if state is None or state["barrier"] != (ev.msg.datapath.id, ev.msg.xid):
            return
        state["index"] += 1
        self.send_reroute_hop()

    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def reroute_error(self, ev):
        state = self.reroute_state
        if state is not None:
            request = (ev.msg.datapath.id, ev.msg.xid)
            if request in state["requests"] or request == state["barrier"]:
                self.abort_reroute("OpenFlow rejected a reroute request")

    def delete_path_rule(self, state, hop, priority):
        switch, in_port, _ = hop
        dp = self.datapaths.get(switch)
        if dp is None:
            return
        parser, ofp = dp.ofproto_parser, dp.ofproto
        dp.send_msg(parser.OFPFlowMod(
            datapath=dp, table_id=0, command=ofp.OFPFC_DELETE_STRICT,
            priority=priority, out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
            match=parser.OFPMatch(in_port=in_port, eth_type=0x0800,
                                  eth_src=state["src"], eth_dst=state["dst"])))

    def abort_reroute(self, reason):
        state = self.reroute_state
        if state is None:
            return
        for hop in state["sent_hops"]:
            self.delete_path_rule(state, hop, state["priority"])
        self.logger.warning("Reroute cancelled: %s", reason)
        self.reroute_state = None

    # Request statistics from all connected switches
    def monitor_network(self):

        while True:
            if (self.reroute_state is not None
                    and time.monotonic() - self.reroute_state["started"] > 10):
                self.abort_reroute("barrier timeout")
            self.rebalance_network()

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

            hub.sleep(self.poll_interval)


    # Receive flow statistics
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply(self, ev):

        dp = ev.msg.datapath

        # Monitor the dynamic IPv4 forwarding rules
        flows = [
            stat for stat in ev.msg.body
            if 20 <= stat.priority < 65535
            and stat.match.get("eth_type") == 0x0800
            and stat.match.get("eth_src") is not None
        ]

        self.update_flow_details(dp, flows)

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

        self.flow_snapshot[dp.id] = (
            total_packets,
            total_bytes
        )

        # Save flow totals for REST API
        self.flow_data[dp.id] = {
            "switch": dp.id,
            "flow_count": len(flows),
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "new_packets": 0,
            "new_bytes": 0
        }

        if previous is None:
            return
 

        packet_change = total_packets - previous[0]
        byte_change = total_bytes - previous[1]

        # Counters may reset when routes are rebuilt
        if packet_change < 0 or byte_change < 0:
            return

        # Counters may reset when routes are rebuilt
        if packet_change < 0 or byte_change < 0:
            return

        # Save changes since the previous measurement
        self.flow_data[dp.id]["new_packets"] = packet_change
        self.flow_data[dp.id]["new_bytes"] = byte_change

        if packet_change > 0:
            self.logger.info(
                "C4 FLOW S%s: +%s packets, +%s bytes",
                dp.id,
                packet_change,
                byte_change
            )
            

        if packet_change > 0:
            self.logger.info(
                "C4 FLOW S%s: +%s packets, +%s bytes",
                dp.id,
                packet_change,
                byte_change
            )


    # Measure each directed host pair once, at its ingress switch.
    def update_flow_details(self, dp, flows):
        records = []
        active_keys = set()
        for stat in flows:
            src = stat.match.get("eth_src")
            dst = stat.match.get("eth_dst")
            in_port = stat.match.get("in_port")
            host = self.hosts.get(src)
            if host is None or host["switch"] != dp.id or host["port"] != in_port:
                continue
            key = (dp.id, src, dst, in_port)
            active_keys.add(key)
            duration = stat.duration_sec + stat.duration_nsec / 1e9
            previous = self.flow_detail_snapshot.get(key)
            rate_mbps = None
            streak = 0
            if previous is not None:
                old_bytes, old_duration, old_streak = previous
                elapsed = duration - old_duration
                changed = stat.byte_count - old_bytes
                if elapsed > 0 and changed >= 0:
                    rate_mbps = changed * 8 / (elapsed * 1000000)
                    if rate_mbps > 10.0:
                        streak = old_streak + 1
            self.flow_detail_snapshot[key] = (stat.byte_count, duration, streak)
            records.append({
                "switch": dp.id,
                "src_mac": src,
                "dst_mac": dst,
                "in_port": in_port,
                "installed_path": self.installed_paths.get((src, dst)),
                "installed_priority": self.route_priorities.get((src, dst)),
                "rate_mbps": None if rate_mbps is None else round(rate_mbps, 6),
                "consecutive_periods": streak,
                "elephant": streak >= 2
            })
            if streak >= 2:
                records[-1]["path_selection"] = self.evaluate_paths(src, dst, rate_mbps)
            if streak == 2:
                self.logger.info(
                    "ELEPHANT %s -> %s at S%s: %.3f Mbps for 2 periods",
                    src, dst, dp.id, rate_mbps
                )
        # Drop snapshots for entries no longer present on this switch.
        for key in list(self.flow_detail_snapshot):
            if key[0] == dp.id and key not in active_keys:
                del self.flow_detail_snapshot[key]
        self.flow_details[dp.id] = records
        self.flow_sample_time[dp.id] = time.monotonic()

    # Receive port statistics
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply(self, ev):

        dp = ev.msg.datapath

        # Map each inter-switch port to its neighboring switch
        link_ports = {}
        for src, dst, data in self.graph.edges(data=True):
            if dp.id in (src, dst):
                neighbor = dst if dp.id == src else src
                link_ports[data["ports"][dp.id]] = neighbor

        # Identify ports connected to discovered hosts
        host_ports = {
            info["port"]
            for info in self.hosts.values()
            if info["switch"] == dp.id
        }

        for stat in ev.msg.body:

            if stat.port_no not in host_ports and stat.port_no not in link_ports:
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
                self.link_load.pop(key, None)
                self.port_sample_time.pop(key, None)
                self.bandwidth_data.pop(key, None)
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

            self.port_sample_time[key] = now

            # Capacity is 100 Mbps on the configured inter-switch links
            if stat.port_no in link_ports:
                utilization = tx_mbps / 100.0
                old_ewma, old_streak = self.link_load.get(key, (utilization, 0))
                ewma = 0.5 * utilization + 0.5 * old_ewma
                streak = old_streak + 1 if ewma > 0.70 else 0
                self.link_load[key] = (ewma, streak)
                if streak == 2:
                    self.logger.info(
                        "CONGESTION S%s P%s -> S%s: EWMA %.2f%% for 2 periods",
                        dp.id, stat.port_no, link_ports[stat.port_no], ewma * 100
                    )
                self.bandwidth_data[key].update({
                    "neighbor": link_ports[stat.port_no],
                    "capacity_mbps": 100,
                    "utilization": round(utilization, 6),
                    "utilization_percent": round(utilization * 100, 3),
                    "ewma_utilization_percent": round(ewma * 100, 3),
                    "congested_periods": streak,
                    "congested": streak >= 2
                })

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
        self.abort_reroute("topology changed")
        self.installed_paths.clear()
        self.path_attachments.clear()
        self.route_priorities.clear()
        self.link_load.clear()
        self.port_snapshot.clear()
        self.bandwidth_data.clear()
        self.port_sample_time.clear()
        self.flow_sample_time.clear()
        self.flow_detail_snapshot.clear()
        self.flow_details.clear()

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
        path = {
            "/topology": "/sdn/topology",
            "/links": "/sdn/links",
            "/flows": "/sdn/flows"
        }.get(path, path)

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
        if method == "GET" and path in ("/sdn/topology", "/sdn/links"):

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
            if path == "/sdn/links":
                data = {"count": len(links), "links": links}

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

        # Return latest OpenFlow statistics
        if method == "GET" and path == "/sdn/flows":

            switches = sorted(
                self.flow_data.values(),
                key=lambda item: item["switch"]
            )

            data = {
                "count": len(switches),
                "total_flows": sum(
                    item["flow_count"] for item in switches
                ),
                "switches": switches,
                "flow_scope": "directed_host_pair",
                "elephant_threshold_mbps": 10,
                "flows": sorted(
                    [item for dpid, items in self.flow_details.items()
                     if dpid in self.graph for item in items],
                    key=lambda item: (item["src_mac"], item["dst_mac"])
                )
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

