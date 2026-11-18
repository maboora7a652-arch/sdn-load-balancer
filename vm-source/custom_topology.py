
from mininet.topo import Topo
from mininet.link import TCLink

class MyNetwork(Topo):

    def build(self):

        # Create switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        s5 = self.addSwitch('s5')
        s6 = self.addSwitch('s6')
        
        # Create hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')
        
        # Connect switches
        self.addLink(s1, s2, cls=TCLink, bw=100, delay='2ms')
        self.addLink(s2, s3, cls=TCLink, bw=100, delay='2ms')
        self.addLink(s3, s6, cls=TCLink, bw=100, delay='2ms')
        self.addLink(s6, s5, cls=TCLink, bw=100, delay='2ms')
        self.addLink(s2, s5, cls=TCLink, bw=100, delay='2ms')
        self.addLink(s4, s5, cls=TCLink, bw=100, delay='2ms')
        self.addLink(s1, s4, cls=TCLink, bw=100, delay='2ms')

        # Connect hosts
        self.addLink(h1, s1)
        self.addLink(h2, s4)
        self.addLink(h3, s2)
        self.addLink(h4, s5)
        self.addLink(h5, s3)
        self.addLink(h6, s6)
        

class FatTree4(Topo):
    """Four pods, each with two edge switches and two aggregation switches."""

    def build(self):
        core = [self.addSwitch('s%d' % i) for i in range(17, 21)]
        trunk = dict(cls=TCLink, bw=100, delay='2ms')
        for pod in range(4):
            edges = [self.addSwitch('s%d' % (2 * pod + i)) for i in (1, 2)]
            aggregation = [self.addSwitch('s%d' % (9 + 2 * pod + i)) for i in (0, 1)]
            for index, edge in enumerate(edges):
                for offset in (1, 2):
                    host = self.addHost('h%d' % (4 * pod + 2 * index + offset))
                    self.addLink(host, edge)
                for switch in aggregation:
                    self.addLink(edge, switch, **trunk)
            for index, switch in enumerate(aggregation):
                for uplink in core[2 * index:2 * index + 2]:
                    self.addLink(switch, uplink, **trunk)


topos = {'mynetwork': MyNetwork, 'fattree4': FatTree4}
