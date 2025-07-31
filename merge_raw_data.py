import networkx as nx
import os
import json

DAYS = "12345"
# DAYS = "67"

# load every json file in /data 
def load_json_files():

    data_dir = 'data'
    raw_data = {}

    for filename in os.listdir(data_dir):
        if DAYS in filename and "raw" not in filename and filename.endswith('.json'):
            with open(os.path.join(data_dir, filename), 'r') as f:
                key = filename.replace('.json', '').replace(DAYS, '').replace('__', '_').replace('_schedule', '')
                raw_data[key] = json.load(f)

    return raw_data

def save_raw_data(raw_data, filename=f"data/raw_{DAYS}.json"):
    with open(filename, 'w') as f:
        f.write(json.dumps(raw_data, indent=4))

raw_data = load_json_files()
save_raw_data(raw_data)