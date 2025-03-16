import simpy
import random
import networkx as nx
import matplotlib.pyplot as plt

SIMULATION_TIME = 60
PACKET_SIZE = 2048
PROPAGATION_DELAY = 0.001 
PACKET_DROP_RATE = 0.01

LINK_CAPACITY = {
    'A-R1': 1_000_000,  
    'A-R2': 1_000_000,  
    'B-R1': 1_000_000, 
    'B-R3': 2_000_000, 
    'C-R3': 1_000_000,  
    'C-R1': 3_000_000, 
    'C-R4': 2_000_000, 
    'D-R1': 2_000_000,  
    'D-R4': 1_000_000, 
    'E-R2': 1_000_000, 
    'E-R3': 1_000_000, 
    'E-R4': 3_000_000, 
    'F-R2': 1_000_000, 
    'F-R3': 2_000_000, 
    'F-R4': 2_000_000, 
    'R1-R2': 3_000_000, 
    'R2-R3': 1_000_000,  
    'R2-R1': 1_000_000, 

    'R1-A': 1_000_000, 
    'R2-A': 1_000_000, 
    'R1-B': 1_000_000, 
    'R3-B': 2_000_000,
    'R3-C': 1_000_000, 
    'R1-C': 3_000_000, 
    'R4-C': 2_000_000, 
    'R1-D': 2_000_000, 
    'R4-D': 1_000_000, 
    'R2-E': 1_000_000,  
    'R3-E': 1_000_000, 
    'R4-E': 3_000_000,  
    'R2-F': 1_000_000, 
    'R3-F': 2_000_000,  
    'R4-F': 2_000_000, 
    'R2-R1': 3_000_000,  
    'R3-R2': 1_000_000, 
    'R1-R2': 1_000_000  
}

TRAFFIC_MATRIX = {
    'A': {'B': 50, 'C': 40, 'D': 60, 'E': 20, 'F': 30},
    'B': {'A': 55, 'C': 70, 'D': 30, 'E': 50, 'F': 20},
    'C': {'A': 35, 'B': 75, 'D': 65, 'E': 30, 'F': 40},
    'D': {'A': 60, 'B': 20, 'C': 80, 'E': 40, 'F': 50},
    'E': {'A': 30, 'B': 45, 'C': 25, 'D': 35, 'F': 65},
    'F': {'A': 25, 'B': 60, 'C': 55, 'D': 50, 'E': 45}
}

ROUTING_TABLE = {
    'A': {'B': 'R1', 'C': 'R1', 'D': 'R1', 'E': 'R2', 'F': 'R2'},
    'B': {'A': 'R1', 'C': 'R1', 'D': 'R1', 'E': 'R3', 'F': 'R3'},
    'C': {'A': 'R1', 'B': 'R1', 'D': 'R4', 'E': 'R3', 'F': 'R3'},
    'D': {'A': 'R1', 'B': 'R1', 'C': 'R4', 'E': 'R4', 'F': 'R4'},
    'E': {'A': 'R2', 'B': 'R3', 'C': 'R3', 'D': 'R4', 'F': 'R4'},
    'F': {'A': 'R2', 'B': 'R3', 'C': 'R3', 'D': 'R4', 'E': 'R4'},
    
    'R1': {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'R2', 'F': 'R2'},
    'R2': {'A': 'A', 'B': 'R3', 'C': 'R3', 'D': 'D', 'E': 'E', 'F': 'F'},
    'R3': {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F'},
    'R4': {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D', 'E': 'E', 'F': 'F'}
}

class Network:
    def __init__(self, env):
        self.env = env
        self.packet_drops = {src: {dest: 0 for dest in TRAFFIC_MATRIX} for src in TRAFFIC_MATRIX}
        self.delays = {src: {dest: [] for dest in TRAFFIC_MATRIX} for src in TRAFFIC_MATRIX}
        
        self.queues = {node: {neighbor: [] for neighbor in ROUTING_TABLE[node] if neighbor.startswith('R')}
                       for node in ROUTING_TABLE if node.startswith('R')}
        
        for node in TRAFFIC_MATRIX:
            if node not in self.queues:
                self.queues[node] = {neighbor: [] for neighbor in TRAFFIC_MATRIX[node]}

    def send_packet(self, src, dest):
        path = self.get_path(src, dest)
        delay = 0
        for i in range(len(path) - 1):
            src_node, dest_node = path[i], path[i + 1]
            link = f'{src_node}-{dest_node}'
            capacity = LINK_CAPACITY.get(link, 1_000_000)
            
            transmission_delay = PACKET_SIZE / capacity
            delay += transmission_delay + PROPAGATION_DELAY

            if random.random() < PACKET_DROP_RATE:
                self.packet_drops[src][dest] += 1
                return

            if dest_node not in self.queues:
                self.queues[dest_node] = {}
            if src_node not in self.queues[dest_node]:
                self.queues[dest_node][src_node] = []

            self.queues[dest_node][src_node].append(len(self.queues[dest_node][src_node]))

        self.delays[src][dest].append(delay)

    def get_path(self, src, dest):
        path = [src]
        while path[-1] != dest:
            current_node = path[-1]
            try:
                next_hop = ROUTING_TABLE[current_node][dest]
            except KeyError as e:
                raise ValueError(f"Routing table entry missing for {current_node} to {dest}") from e
            path.append(next_hop)
        return path

def generate_traffic(env, network, src, dest, rate):
    while env.now < SIMULATION_TIME:
        yield env.timeout(random.expovariate(rate))
        network.send_packet(src, dest)

env = simpy.Environment()
network = Network(env)

for src in TRAFFIC_MATRIX:
    for dest, rate in TRAFFIC_MATRIX[src].items():
        if rate > 0:
            env.process(generate_traffic(env, network, src, dest, rate))

env.run(until=SIMULATION_TIME)
print("End-to-End Delays:")
for src in network.delays:
    for dest, delays in network.delays[src].items():
        if delays:
            avg_delay = sum(delays) / len(delays)
            variance = sum((x - avg_delay) ** 2 for x in delays) / len(delays)
            print(f"From {src} to {dest}: Avg={avg_delay} s, Variance={variance} s^2, Count={len(delays)}")

print("\nPacket Drops:")
for src in network.packet_drops:
    for dest, drops in network.packet_drops[src].items():
        print(f"From {src} to {dest}: {drops} packets")

print("\nQueue Lengths:")
for router in network.queues:
    for link, lengths in network.queues[router].items():
        avg_length = sum(lengths) / len(lengths) if lengths else 0
        print(f"{router} to {link}: Avg Queue Length={avg_length}")

print("\nAll Possible Paths from A, B, C to D, E, F:")
for src in ['A', 'B', 'C']:
    for dest in ['D', 'E', 'F']:
        path = network.get_path(src, dest)
        print(f"Packet from {src} to {dest}. Path: {' -> '.join(path)}")

G = nx.Graph()
G.add_nodes_from(['A', 'B', 'C', 'D', 'E', 'F'])
G.add_nodes_from(['R1', 'R2', 'R3', 'R4'])
for src in ROUTING_TABLE:
    for dest, router in ROUTING_TABLE[src].items():
        if src != dest and router != '-' and router != src and router != dest:
            G.add_edge(src, router)
            G.add_edge(router, dest)
print("Edges in the graph:", G.edges())
plt.figure(figsize=(10, 8))
nx.draw(G, with_labels=True, node_size=3000, node_color="skyblue", font_size=10, font_weight="bold")
plt.title("Network Topology (Workstations connected through Routers)")
plt.show()