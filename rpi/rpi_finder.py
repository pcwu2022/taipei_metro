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
OUTPUT_PROGRESS = True

STOP_TIME = 2

STATION_MULTIPLIER = 1
PATH_MULTIPLIER = 0.5
TIME_MULTIPLIER = 0.25

TRAIN = 0
TRANSFER = 1

with open(f"{DAYS}.json", 'r') as f:
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
    with open("suppressed_data.json", "w") as f:
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
        if random.random() < 0.001 and OUTPUT_PROGRESS:
            print(f"[{str(sum(history))}] " + '->'.join([n.split('_')[2] for n in path]) + ": " + str(tup[0]))
        if sum(history) > current_best:
            current_best = sum(history)
            best_path = path
            with open("best_path.json", "w") as f:
                f.write(json.dumps(path, indent=4))
        # print(f"[{str(sum(history))}] " + '->'.join([n.split('_')[2] for n in path]) + ": " + str(tup[0]))
        if sum(history) == STATION_NUM: 
            print("===== FINISHED =====")
            best_path = path
            with open("best_path.json", "w") as f:
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