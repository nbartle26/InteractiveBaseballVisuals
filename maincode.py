import os
import pandas as pd
import matplotlib.pyplot as plt

FILE_NAME = 'MLBData2024.csv'

def load_and_clean_data(file_path):
    print("📂 Attempting to load data...")

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return pd.DataFrame()

    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            print(f"❌ Unsupported file format: {file_path}")
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error reading the file: {e}")
        return pd.DataFrame()

    print(f"✅ Successfully loaded {len(df)} rows.")

    df.columns = df.columns.str.strip()

    # Check critical columns, drop rows with NaNs in those
    critical_cols = ['plate_x', 'plate_z', 'player_name', 'events']
    existing_critical_cols = [col for col in critical_cols if col in df.columns]

    if existing_critical_cols:
        df = df.dropna(subset=existing_critical_cols)
    else:
        print("⚠️ None of the critical columns for filtering found. Skipping dropna step.")

    useful_cols = [
        'player_name', 'plate_x', 'plate_z', 'zone', 'events',
        'estimated_ba_using_speedangle', 'game_date', 'launch_speed',
        'launch_angle', 'description'
    ]
    df = df[[col for col in useful_cols if col in df.columns]]

    print(f"🧹 Cleaned data has {len(df)} rows and {len(df.columns)} columns.")
    return df

def build_strike_zone_grid(ax):
    # strikezone boundaries
    left, right = -0.7083, 0.7083  # horizontal limits (feet)
    bottom, top = 1.5, 3.5          # vertical limits (feet)
    
    # Draw outer big strike zone rectangle (bold black)
    ax.plot([left, right, right, left, left],
            [bottom, bottom, top, top, bottom],
            color='black', linewidth=2)

    # Draw 3x3 grid inside strike zone (lighter lines)
    x_ticks = [left, (left+right)/3, (left+right)*2/3, right]
    y_ticks = [bottom, (bottom+top)/3, (bottom+top)*2/3, top]

    for x in x_ticks:
        ax.plot([x, x], [bottom, top], color='gray', linestyle='--', linewidth=0.8)
    for y in y_ticks:
        ax.plot([left, right], [y, y], color='gray', linestyle='--', linewidth=0.8)

    # Draw outer 9 "outside" zones (lighter grid around the strike zone)
    # Extend grid by same width/height beyond main strike zone edges
    width = right - left
    height = top - bottom

    # Horizontal grid lines above and below
    for y in [bottom - height/3, bottom - 2*height/3, top + height/3, top + 2*height/3]:
        ax.plot([left - width, right + width], [y, y], color='lightgray', linestyle=':', linewidth=0.6)

    # Vertical grid lines left and right
    for x in [left - width/3, left - 2*width/3, right + width/3, right + 2*width/3]:
        ax.plot([x, x], [bottom - height, top + height], color='lightgray', linestyle=':', linewidth=0.6)

    # Outer big square boundary for outside zones (lighter)
    ax.plot([left - width, right + width, right + width, left - width, left - width],
            [bottom - height, bottom - height, top + height, top + height, bottom - height],
            color='lightgray', linewidth=1)

    # Set equal aspect ratio and limits to fit all zones
    ax.set_aspect('equal', 'box')
    ax.set_xlim(left - width, right + width)
    ax.set_ylim(bottom - height, top + height)

    ax.set_xlabel("Horizontal Location (feet)")
    ax.set_ylabel("Vertical Location (feet)")
    ax.set_title("2024 MLB Plate Discipline: Aaron Judge")

    # Remove axis ticks (optional)
    ax.set_xticks([])
    ax.set_yticks([])

def calculate_zone_stats(df, player_name):
    # Filter for this player and valid hits/events
    player_df = df[df['player_name'] == player_name].copy()

    if player_df.empty:
        print(f"⚠️ No data for player {player_name}")
        return {}

    # Zones are integers from 1 to 9 inside the strike zone
    # Outside zones can be 10 to 18 (if 'zone' column follows Baseball Savant convention)
    # We'll calculate AVG and xAVG for each zone from 1 to 18

    zone_stats = {}

    # Check if 'zone' and 'estimated_ba_using_speedangle' exist
    if 'zone' not in player_df.columns or 'estimated_ba_using_speedangle' not in player_df.columns:
        print("⚠️ Missing 'zone' or 'estimated_ba_using_speedangle' columns for calculation")
        return {}

    for zone_num in range(1, 19):
        zone_data = player_df[player_df['zone'] == zone_num]

        if zone_data.empty:
            zone_stats[zone_num] = {'AVG': None, 'xAVG': None, 'count': 0}
            continue

        # Calculate batting average: hits / at-bats (approximate with events)
        # We'll approximate hits by counting rows where events is a hit event

        # Define hit events for simplicity
        hits_events = ['single', 'double', 'triple', 'home_run']

        hits = zone_data['events'].str.lower().isin(hits_events).sum()
        at_bats = len(zone_data)

        avg = hits / at_bats if at_bats > 0 else None
        xavg = zone_data['estimated_ba_using_speedangle'].mean() if 'estimated_ba_using_speedangle' in zone_data else None

        zone_stats[zone_num] = {'AVG': avg, 'xAVG': xavg, 'count': at_bats}

    return zone_stats

def plot_zone_stats(zone_stats):
    fig, ax = plt.subplots(figsize=(8, 10))
    build_strike_zone_grid(ax)

    # Mapping zones 1-9 inside strike zone, 10-18 outside zones
    # Position zo
