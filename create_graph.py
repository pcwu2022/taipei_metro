import networkx as nx
import json
import matplotlib.pyplot as plt

SUPPRESS = False
SIMPLIFY = True
TEST_DATA = False
DAYS = "12345"
# DAYS = "67"

TRAIN = 0
TRANSFER = 1

def get_color(line):
    if "O" in line: return "orange"
    if "G" in line: return "green"
    if "BL" in line: return "blue"
    if "R" in line: return "red"

def display_graph(G):
    plt.figure(figsize=(12, 8))
    # Draw nodes and edges
    # Create custom positions based on time for x-coordinate
    pos = {}
    for node in G.nodes():
        # Use time as x-coordinate and compute y-coordinate with spring layout
        pos[node] = (G.nodes[node]['time'], 0)  # Initial position
    
    # Apply spring layout but only adjust y-coordinates
    pos_y = nx.spring_layout(G, seed=42)
    for node in G.nodes():
        pos[node] = (G.nodes[node]['time'], pos_y[node][1])
    
    nx.draw(G, 
            pos=pos,
            node_color=[get_color(node.split('_')[0]) for node in G.nodes], 
            edge_color=["#DDDDDD" if G[u][v]["type"] == TRANSFER else "black" for u, v in G.edges()],
            node_size=15)
    # Add small text labels
    labels = {node: G.nodes[node]['label'] for node in G.nodes()}
    # nx.draw_networkx_labels(G, pos, labels, font_size=6, font_color='black')
    
    plt.title("Taipei Metro DiGraph")
    plt.tight_layout()
    plt.savefig("output/metro_graph.png", dpi=300)

with open(f"working/{DAYS}.json", 'r') as f:
    raw_data = json.load(f)


with open("working/transfer_time.json", 'r') as f:
    transfer_time = json.load(f)

if SUPPRESS:
    suppressed_data = {}
    for line in raw_data:
        if line not in transfer_time: continue
        suppressed_data[line] = {
            "stations": [],
            "trainSchedules": []
        }
        for _ in range(len(raw_data[line]["trainSchedules"])):
            suppressed_data[line]["trainSchedules"].append([])
        for index, station in enumerate(raw_data[line]["stations"]):
            if (station in transfer_time[line] and len(transfer_time[line][station]) > 1) or station == "O12" or station == "O21" or index == 0 or index == len(raw_data[line]["stations"]) - 1:
                suppressed_data[line]["stations"].append(station)
                for i in range(len(suppressed_data[line]["trainSchedules"])):
                    suppressed_data[line]["trainSchedules"][i].append(raw_data[line]["trainSchedules"][i][index])
    raw_data = suppressed_data
    with open("working/suppressed_data.json", "w") as f:
        f.write(json.dumps(suppressed_data, indent=4))

if TEST_DATA:
    for line in raw_data:
        raw_data[line]["trainSchedules"] = raw_data[line]["trainSchedules"][50:80]
    
for line in raw_data:
    reciprocal = line.replace("_a", "_b") if "_a" in line else line.replace("_b", "_a")
    stations = raw_data[line]["stations"]
    
    if line not in transfer_time:
        transfer_time[line] = {}
    for index, station in enumerate(stations):
        if station not in transfer_time[line]:
            transfer_time[line][station] = {}
        if not SIMPLIFY or (len(transfer_time[line][station]) > 1 or station == "O12" or station == "O21" or index == 0 or index == len(raw_data[line]["stations"]) - 1):
            dest_line_station = f"{reciprocal}_{station}"
            if dest_line_station not in transfer_time[line][station]:
                transfer_time[line][station][dest_line_station] = 0

G = nx.DiGraph()

recorded_stations = []
for line in raw_data:
    stations = raw_data[line]["stations"]
    prev_train = [None] * len(stations)
    for train in raw_data[line]["trainSchedules"]:
        train_head = None
        for index, time in enumerate(train):
            if time == None: continue
            station = stations[index]

            current_node = f"{line}_{station}_{time}"
            G.add_node(current_node, label=f"{line}")
            # G.nodes[current_node]["line"] = line
            # G.nodes[current_node]["station"] = station
            G.nodes[current_node]["time"] = time

            
            if train_head != None:
                G.add_edge(train_head, current_node)
                G[train_head][current_node]["type"] = TRAIN
                G[train_head][current_node]["time"] = G.nodes[current_node]["time"] - G.nodes[train_head]["time"]
            if prev_train[index] != None and not SIMPLIFY:
                G.add_edge(prev_train[index], current_node)
                G[prev_train[index]][current_node]["type"] = TRANSFER
                G[prev_train[index]][current_node]["time"] = G.nodes[current_node]["time"] - G.nodes[prev_train[index]]["time"]

            train_head = current_node
            prev_train[index] = current_node
    
    # transfer
    for index, station in enumerate(raw_data[line]["stations"]):
        if line in transfer_time and station in transfer_time[line]:
            for dest_line_station in transfer_time[line][station]:
                if dest_line_station in recorded_stations:
                    time = transfer_time[line][station][dest_line_station]
                    station_split = dest_line_station.split("_")
                    dest_line = station_split[0] + "_" + station_split[1]
                    dest_station = station_split[2]
                    dest_index = raw_data[dest_line]["stations"].index(dest_station)

                    for train in raw_data[line]["trainSchedules"]:
                        arrival = train[index]
                        if arrival == None: continue

                        reverse_dest_train = None
                        reverse_departure = None

                        for dest_train in raw_data[dest_line]["trainSchedules"]:
                            departure = dest_train[dest_index]
                            if departure == None: continue
                            if arrival - time >= departure:
                                reverse_dest_train = dest_train
                                reverse_departure = departure
                            if departure - time >= arrival:
                                G.add_edge(f"{line}_{station}_{arrival}", f"{dest_line}_{dest_station}_{departure}")
                                G[f"{line}_{station}_{arrival}"][f"{dest_line}_{dest_station}_{departure}"]["type"] = TRANSFER
                                G[f"{line}_{station}_{arrival}"][f"{dest_line}_{dest_station}_{departure}"]["time"] = departure - arrival
                                break
                        if reverse_dest_train != None and reverse_departure != None:
                            G.add_edge(f"{dest_line}_{dest_station}_{reverse_departure}", f"{line}_{station}_{arrival}")
                            G[f"{dest_line}_{dest_station}_{reverse_departure}"][f"{line}_{station}_{arrival}"]["type"] = TRANSFER
                            G[f"{dest_line}_{dest_station}_{reverse_departure}"][f"{line}_{station}_{arrival}"]["time"] = arrival - reverse_departure
                                

    recorded_stations.extend([f"{line}_{station}" for station in raw_data[line]["stations"]])

# if TEST_DATA:
#     display_graph(G)

# Export the graph to JSON file

def graph_to_json(G):
    graph_data = {
        "nodes": [],
        "edges": []
    }
    
    # Add nodes with attributes
    for node in G.nodes():
        node_data = {
            "id": node,
            "label": G.nodes[node].get('label', ''),
            "time": G.nodes[node].get('time', 0)
        }
        graph_data["nodes"].append(node_data)
    
    # Add edges with attributes
    for u, v, data in G.edges(data=True):
        edge_data = {
            "source": u,
            "target": v,
            "type": data.get('type', 0),
            "time": data.get('time', 0)
        }
        graph_data["edges"].append(edge_data)
    
    return graph_data

# Export the graph to a JSON file
graph_data = graph_to_json(G)
with open(f"working/metro_graph{'_test' if TEST_DATA else ''}{'_suppressed' if SUPPRESS else ''}.json", "w") as f:
    json.dump(graph_data, f, indent=2)

print(f"Graph saved with {len(G.nodes())} nodes and {len(G.edges())} edges")