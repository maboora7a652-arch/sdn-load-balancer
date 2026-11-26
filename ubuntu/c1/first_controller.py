
from os_ken.base import app_manager
from os_ken.controller import ofp_event
from os_ken.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from os_ken.ofproto import ofproto_v1_3
from os_ken.lib.packet import packet, ethernet


class LearningSwitch(app_manager.OSKenApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_connected(self, ev):
        dp = ev.msg.datapath
        p = dp.ofproto_parser
        o = dp.ofproto

        match = p.OFPMatch()
        actions = [p.OFPActionOutput(o.OFPP_CONTROLLER, o.OFPCML_NO_BUFFER)]
        inst = [p.OFPInstructionActions(o.OFPIT_APPLY_ACTIONS, actions)]

        dp.send_msg(p.OFPFlowMod(
            datapath=dp, priority=0,
            match=match, instructions=inst
        ))

        self.logger.info("Switch %s connected", dp.id)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        p = dp.ofproto_parser
        o = dp.ofproto

        in_port = msg.match["in_port"]
        eth = packet.Packet(msg.data).get_protocol(ethernet.ethernet)

        if eth is None:
            return

        src = eth.src
        dst = eth.dst

        self.mac_to_port.setdefault(dp.id, {})[src] = in_port

        out_port = self.mac_to_port[dp.id].get(dst, o.OFPP_FLOOD)
        actions = [p.OFPActionOutput(out_port)]

        if out_port != o.OFPP_FLOOD:
            match = p.OFPMatch(in_port=in_port, eth_dst=dst)
            inst = [p.OFPInstructionActions(o.OFPIT_APPLY_ACTIONS, actions)]

            dp.send_msg(p.OFPFlowMod(
                datapath=dp, priority=1,
                match=match, instructions=inst
            ))

        dp.send_msg(p.OFPPacketOut(
            datapath=dp,
            buffer_id=o.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=msg.data
        ))
