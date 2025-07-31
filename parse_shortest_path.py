import json

with open('working/best_path.json', 'r') as file:
    data = json.load(file)

log = "Shortest Path:\n"
for stop in data:
    station = stop.split('_')[2]
    time = int(stop.split('_')[3]) 
    hours = time // 60
    minutes = time % 60
    log += f"{station}, {hours:02d}:{minutes:02d}\n"

print(log)
with open('output/shortest_path.txt', 'w') as file:
    file.write(log)