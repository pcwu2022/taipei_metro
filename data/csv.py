import json

files = ["RBR_a_12345.csv", "RBR_b_12345.csv", "RBR_a_67.csv", "RBR_b_67.csv"]

for file in files:
    with open(file, 'r') as f:
        data = f.read()
    
    while ',\n' in data:
        data = data.replace(',\n', '\n')

    lines = data.splitlines()
    num_cols = len(lines[0].split(',')) - 2
    json_data = {
        "stations": [],
        "trainSchedules": []
    }

    for i in range(num_cols):
        json_data["trainSchedules"].append([])
    
    for line in lines:
        if not line.strip():  # Skip empty lines
            continue
        values = line.split(',')
        json_data["stations"].append(values[0])

        for i, value in enumerate(values[2:]):
            num_value = int(value.split(':')[0])*60 + int(value.split(':')[1])
            if num_value < 4*60:
                num_value += 24*60
            json_data["trainSchedules"][i].append(num_value)

    json_file_name = file.replace('.csv', '_schedule.json')
    with open(json_file_name, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)