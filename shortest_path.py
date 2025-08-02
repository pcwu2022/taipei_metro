import networkx as nx
import json
import heapq
import copy
import re
import random

SUPPRESS = False
TEST_DATA = False
DAYS = "12345"
SOURCE = True
SIMPLIFY = True
EVERY_STOP = False
OUTPUT_BEST_PATH = True

STOP_TIME = 2

STATION_MULTIPLIER = 1
PATH_MULTIPLIER = 0.5
TIME_MULTIPLIER = 0.25

TRAIN = 0
TRANSFER = 1

def json_to_graph(graph_data):
    """
    Convert a JSON graph representation back to a NetworkX graph.
    
    Args:
        graph_data (dict): Dictionary containing nodes and edges data
        
    Returns:
        nx.Graph: A NetworkX graph reconstructed from the JSON data
    """
    G = nx.DiGraph()
    
    # Add nodes with attributes
    for node_data in graph_data["nodes"]:
        G.add_node(
            node_data["id"],
            label=node_data.get("label", ""),
            time=node_data.get("time", 0)
        )
    
    # Add edges with attributes
    for edge_data in graph_data["edges"]:
        G.add_edge(
            edge_data["source"],
            edge_data["target"],
            type=edge_data.get("type", 0),
            time=edge_data.get("time", 0)
        )
    
    return G

with open(f"working/metro_graph{'_test' if TEST_DATA else ''}{'_suppressed' if SUPPRESS else ''}{'_simplified' if SIMPLIFY else ''}.json", "r") as f:
    graph_data = json.load(f)

with open(f"working/{DAYS}.json", 'r') as f:
    raw_data = json.load(f)

with open("working/transfer_time.json", 'r') as f:
    transfer_time = json.load(f)

stations_index = {}
current_index = 0
for line in raw_data:
    for station in raw_data[line]["stations"]:
        if station in stations_index: continue
        if line in transfer_time and station in transfer_time[line]:
            dest_ids = set()
            for dest_station in transfer_time[line][station]:
                dest_id = dest_station.split("_")[2]
                if dest_id not in dest_ids:
                    dest_ids.add(dest_id)
            
            for dest_id in dest_ids:
                if dest_id in stations_index:
                    stations_index[station] = stations_index[dest_id]
                    break
        if station not in stations_index:
            stations_index[station] = current_index
            current_index += 1

STATION_NUM = current_index

def generate_source(G: nx.DiGraph):
    START_TIME_MULTIPLIER = 0.000001

    global STATION_NUM
    global stations_index
    source = "source"
    source_node = "S_a_source_000"
    G.add_node(source_node)
    stations_index[source] = STATION_NUM
    STATION_NUM = STATION_NUM + 1

    # find all nodes without in-edges with type TRAIN
    for node in G.nodes():
        type_train = False
        for pred in G.predecessors(node):
            if G[pred][node]["type"] == TRAIN: 
                type_train = True
                break
        if not type_train:
            G.add_edge(source_node, node)
            raw_time = int(node.split("_")[3])
            G[source_node][node]["type"] = TRANSFER
            G[source_node][node]["time"] = (raw_time - 6*60) * START_TIME_MULTIPLIER
    return source_node

G = json_to_graph(graph_data)
    
def a_star(G: nx.DiGraph, source):
    q = []
    
    history = [False] * STATION_NUM
    history[stations_index[source.split("_")[2]]] = True
    traversed = 0
    path = [source]
    total_time = 0

    heapq.heappush(q, (0, [source, total_time, copy.deepcopy(history), copy.deepcopy(path), copy.deepcopy(traversed)]))

    current_best = 0
    best_path = []
    score_cache = set()
    while len(q) > 0:
        tup = heapq.heappop(q)
        node, total_time, history, path, traversed = tup[1]
        if not OUTPUT_BEST_PATH:
            if random.random() < 0.001:
                with open("working/best_path.json", "w") as f:
                    f.write(json.dumps(path, indent=4))
        if sum(history) > current_best:
            current_best = sum(history)
            best_path = path
            if OUTPUT_BEST_PATH:
                with open("working/best_path.json", "w") as f:
                    f.write(json.dumps(path, indent=4))
        # print(f"[{str(sum(history))}] " + '->'.join([n.split('_')[2] for n in path]) + ": " + str(tup[0]))
        if sum(history) == STATION_NUM: 
            print("===== FINISHED =====")
            best_path = path
            with open("working/best_path.json", "w") as f:
                f.write(json.dumps(path, indent=4))
            break
        for successor in G.successors(node):
            if successor in path: continue
            new_time = total_time + G[node][successor]["time"]
            new_station_index = stations_index[successor.split("_")[2]]
            new_history = copy.deepcopy(history)
            if EVERY_STOP:
                if history[new_station_index] == False:
                    station_index = stations_index[node.split("_")[2]]
                    if station_index == new_station_index and G[node][successor]["time"] > STOP_TIME:
                        new_history[new_station_index] = True
            else:
                new_history[new_station_index] = True
            new_path = copy.deepcopy(path)
            new_path.append(successor)

            delta_stations = 0

            if SUPPRESS:
                if history[new_station_index] == False:
                    line, number = re.match(r"([A-Za-z]{1,2})(\d{2})", node.split("_")[2]).groups()
                    new_line, new_number = re.match(r"([A-Za-z]{1,2})(\d{2})", successor.split("_")[2]).groups()
                    if line == new_line:
                        if (node.split("_")[2] == "O54" and successor.split("_")[2] == "O12") or (node.split("_")[2] == "O12" and successor.split("_")[2] == "O54"):
                            delta_stations = 5
                        else:
                            delta_stations = abs(int(number) - int(new_number))
            else:
                if history[new_station_index] == False:
                    delta_stations = 1

            new_traversed = traversed + delta_stations
            score = new_time * TIME_MULTIPLIER + (STATION_NUM - new_traversed) * STATION_MULTIPLIER + len(new_path) * PATH_MULTIPLIER
            # score = new_time * TIME_MULTIPLIER * (STATION_NUM - new_traversed) * STATION_MULTIPLIER + len(new_path) * PATH_MULTIPLIER
            
            if (successor, score) in score_cache: continue
            heapq.heappush(q, (score, [successor, new_time, new_history, new_path, new_traversed]))
            score_cache.add((successor, score))
    print(best_path)

a_star(G, generate_source(G) if SOURCE else "R_b_R28_480")