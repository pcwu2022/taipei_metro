import json
import time
import os
import csv
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import networkx as nx
import numpy as np
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import re



# Colors for different metro lines
LINE_COLORS = {
    "BL": "#0070bd",  # Blue Line
    "R": "#e3002c",   # Red Line
    "G": "#008659",   # Green Line
    "O": "#f8b61c",   # Orange Line
    "BR": "#7e3f00",  # Brown Line
    "Y": "#ffd800",   # Yellow Line (Circle Line)
    "A": "#c48c31"    # Airport Line
}

def load_station_locations():
    """Load station locations from the CSV file."""
    locations = {}
    try:
        with open('location.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                station_code = row['station_code']
                lat = float(row['lat'])
                lon = float(row['lon'])
                line_code = row['line_code']
                station_name = row['station_name_en']
                
                locations[station_code] = {
                    'lat': lat,
                    'lon': lon,
                    'line': line_code,
                    'name': station_name
                }
    except Exception as e:
        print(f"Error loading location.csv: {e}")
    
    return locations

def extract_station_info(node_id):
    """Extract line, direction, station, and time from node ID."""
    parts = node_id.split("_")
    if len(parts) < 4:
        return None, None, None, None
    
    line = parts[0]
    direction = parts[1]
    station = parts[2]
    try:
        time = int(parts[3])
        hours = time // 60
        minutes = time % 60
        time_str = f"{hours:02d}:{minutes:02d}"
    except:
        time_str = "N/A"
    
    return line, direction, station, time_str

def get_all_stations(data):
    """Extract all unique stations from the 12345.json data."""
    stations = {}
    locations = load_station_locations()
    
    for line_dir, info in data.items():
        if 'stations' in info:
            line = line_dir.split('_')[0]
            direction = line_dir.split('_')[1]
            for station in info['stations']:
                key = f"{line}_{station}"
                if key not in stations:
                    stations[key] = {'line': line, 'station': station, 'directions': []}
                if direction not in stations[key]['directions']:
                    stations[key]['directions'].append(direction)
    
    # Add additional stations from location.csv if they exist in our data
    for station_code, loc_info in locations.items():
        line = loc_info['line']
        if line in LINE_COLORS:  # Make sure we support this line color
            key = f"{line}_{station_code}"
            if key not in stations:
                stations[key] = {'line': line, 'station': station_code, 'directions': []}
    
    return stations

def create_network_layout(stations):
    """Create a layout for the network based on geographical station locations."""
    G = nx.Graph()
    
    # Load station geographical locations
    locations = load_station_locations()
    
    # Add nodes for all stations
    for key, info in stations.items():
        G.add_node(key, line=info['line'], station=info['station'])
    
    # Add edges based on line and station order
    for line_key in LINE_COLORS.keys():
        line_stations = sorted([k for k in stations.keys() if k.startswith(line_key + "_")],
                              key=lambda x: int(re.search(r'\d+', x.split("_")[1]).group()))
        for i in range(len(line_stations) - 1):
            G.add_edge(line_stations[i], line_stations[i + 1])
    
    # Create positions based on geographical coordinates
    pos = {}
    
    # Map our stations to the location data
    for station_key, info in stations.items():
        line = info['line']
        station_code = info['station']
        
        # Look up the station in the location data
        if station_code in locations:
            # Use longitude for x and latitude for y to match geographical orientation
            lon = locations[station_code]['lon']
            lat = locations[station_code]['lat']
            pos[station_key] = np.array([lon, lat])
        else:
            # If station not found in locations, use a fallback position
            print(f"Warning: No location data for {station_key}")
            pos[station_key] = np.array([0, 0])
    
    return G, pos

def load_best_path():
    """Load the best path from the JSON file."""
    try:
        with open('working/best_path.json', 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading best_path.json: {e}")
        return []

def load_metro_data():
    """Load the metro data from the JSON file."""
    try:
        with open('working/12345.json', 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading 12345.json: {e}")
        return {}

def update_visualization(frame, ax, stations, pos, path_info):
    """Update the visualization with the current best path."""
    ax.clear()
    best_path = load_best_path()
    
    # Create NetworkX graph for visualization
    G = nx.Graph()
    
    # Add all stations as nodes
    for station_key, info in stations.items():
        G.add_node(station_key, line=info['line'], station=info['station'])
    
    # Draw the network with line colors
    for line, color in LINE_COLORS.items():
        line_nodes = [n for n in G.nodes() if G.nodes[n]['line'] == line]
        nx.draw_networkx_nodes(G, pos, nodelist=line_nodes, node_color=color, 
                              node_size=50, alpha=0.8, ax=ax)
        
    # Draw edges for each line with matching colors
    for line, color in LINE_COLORS.items():
        line_edges = []
        line_stations = sorted([n for n in G.nodes() if G.nodes[n]['line'] == line],
                              key=lambda x: int(re.search(r'\d+', x.split("_")[1]).group()))
        
        for i in range(len(line_stations) - 1):
            if (line_stations[i], line_stations[i+1]) in G.edges():
                line_edges.append((line_stations[i], line_stations[i+1]))
        
        nx.draw_networkx_edges(G, pos, edgelist=line_edges, width=1.5, alpha=0.7,
                              edge_color=color, ax=ax)
    
    # Label the stations - only show labels for transfer stations to avoid clutter
    locations = load_station_locations()
    station_counts = {}
    for node in G.nodes():
        station_code = G.nodes[node]['station']
        if station_code not in station_counts:
            station_counts[station_code] = 0
        station_counts[station_code] += 1
    
    # Only label transfer stations (stations that appear in multiple lines)
    transfer_stations = {node: G.nodes[node]['station'] for node in G.nodes() 
                         if station_counts.get(G.nodes[node]['station'], 0) > 1}
    
    nx.draw_networkx_labels(G, pos, labels=transfer_stations, font_size=6, font_color="black", 
                           font_weight='bold', ax=ax)
    
    # Process and highlight the best path
    if best_path:
        # Extract station keys from the path for highlighting
        path_stations = []
        
        for i, node_id in enumerate(best_path):
            # Skip S_source nodes (fake stations)
            if node_id.startswith("S_a_source") or node_id.startswith("S_b_source"):
                continue
                
            parts = node_id.split("_")
            if len(parts) >= 3:
                line = parts[0]
                station = parts[2]
                station_key = f"{line}_{station}"
                path_stations.append(station_key)
        
        # Draw the highlighted path nodes
        highlighted_nodes = list(set(path_stations))
        nx.draw_networkx_nodes(G, pos, nodelist=highlighted_nodes, node_color='red', 
                              node_size=80, alpha=1.0, ax=ax)
        
        # Draw path lines for direction rather than arrows (better for geographic display)
        path_edges = []
        for i in range(len(path_stations) - 1):
            # Skip if either station doesn't have a position
            if path_stations[i] not in pos or path_stations[i+1] not in pos:
                continue
            
            path_edges.append((path_stations[i], path_stations[i+1]))
        
        # Draw path edges as red lines
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, width=2.5, alpha=1.0,
                              edge_color='red', style='dashed', ax=ax)
        
        # Add path information
        path_text = []
        displayed_index = 1
        for i, node_id in enumerate(best_path):
            # Skip source nodes
            if node_id.startswith("S_a_source") or node_id.startswith("S_b_source"):
                continue
                
            line, direction, station, time = extract_station_info(node_id)
            if line and station and time:
                path_text.append(f"{displayed_index}. {line}_{station} - {time}")
                displayed_index += 1
        
        path_info.set_text("\n".join(path_text[:20]) + "\n..." if len(path_text) > 20 else "\n".join(path_text))
    
    # Add legend
    legend_elements = [Patch(facecolor=color, edgecolor='w', label=line) 
                      for line, color in LINE_COLORS.items()]
    legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='red', 
                                 markersize=10, label='Path'))
    
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    ax.set_title('Taipei Metro Network - Best Path Visualization')
    ax.axis('off')
    
    return ax,

def main():
    # Load the metro data
    metro_data = load_metro_data()
    
    if not metro_data:
        print("No metro data available. Exiting.")
        return
    
    # Get all stations
    stations = get_all_stations(metro_data)
    
    # Create layout
    G, pos = create_network_layout(stations)
    
    # Set up the plot with an appropriate aspect ratio for the map
    fig, ax = plt.subplots(figsize=(12, 14))
    
    # Text box for path information
    path_info = ax.text(1.05, 0.5, '', transform=ax.transAxes, 
                       verticalalignment='center', bbox=dict(facecolor='white', alpha=0.8))
    
    # Add a title
    plt.suptitle('Taipei Metro Network - Best Path Visualization (Geographic)', fontsize=16)
    
    # Create animation that updates every 2 seconds
    ani = animation.FuncAnimation(fig, update_visualization, fargs=(ax, stations, pos, path_info), 
                                  interval=200, cache_frame_data=False)
    
    plt.subplots_adjust(left=0.05, right=0.8, top=0.95, bottom=0.05)
    plt.show()

if __name__ == "__main__":
    main()
