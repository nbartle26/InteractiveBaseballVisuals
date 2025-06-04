import pandas as pd
import plotly.graph_objects as go
import os
from dash import Dash, dcc, html, Input, Output

FILE_NAME = 'MLBData2024.csv'

# Strike zone boundaries (approximate, feet)
LEFT, RIGHT = -0.7083, 0.7083
BOTTOM, TOP = 1.5, 3.5

def assign_zone(row):
    x, z = row['plate_x'], row['plate_z']
    if pd.isna(x) or pd.isna(z):
        return -1  # invalid zone

    if x < LEFT or x > RIGHT or z < BOTTOM or z > TOP:
        return 0  # outside zone

    x_bins = [LEFT, LEFT + (RIGHT - LEFT)/3, LEFT + 2*(RIGHT - LEFT)/3, RIGHT]
    z_bins = [BOTTOM, BOTTOM + (TOP - BOTTOM)/3, BOTTOM + 2*(TOP - BOTTOM)/3, TOP]

    if x <= x_bins[1]:
        col = 1
    elif x <= x_bins[2]:
        col = 2
    else:
        col = 3

    if z <= z_bins[1]:
        row_num = 1
    elif z <= z_bins[2]:
        row_num = 2
    else:
        row_num = 3

    zone = (row_num - 1)*3 + col
    return zone

def load_and_prepare_data(filename):
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Data file {filename} not found.")
    print("📂 Loading data...")
    df = pd.read_csv(filename)
    print(f"✅ Loaded {len(df)} rows.")

    critical_cols = ['player_name', 'plate_x', 'plate_z', 'ba', 'xba']
    df = df.dropna(subset=critical_cols)

    df['zone'] = df.apply(assign_zone, axis=1)
    df = df[df['zone'] >= 0]
    print(f"🧹 Data cleaned to {len(df)} rows with valid zones.")
    return df

def aggregate_player_stats(df):
    agg = df.groupby(['player_name', 'zone']).agg(
        avg_ba=pd.NamedAgg(column='ba', aggfunc='mean'),
        avg_xba=pd.NamedAgg(column='xba', aggfunc='mean'),
        count=pd.NamedAgg(column='ba', aggfunc='count')
    ).reset_index()
    return agg

def create_strikezone_figure(df_agg, selected_player):
    zone_centers = {
        1: (LEFT + (RIGHT - LEFT)/6, BOTTOM + (TOP - BOTTOM)/6),
        2: (LEFT + (RIGHT - LEFT)/2, BOTTOM + (TOP - BOTTOM)/6),
        3: (LEFT + 5*(RIGHT - LEFT)/6, BOTTOM + (TOP - BOTTOM)/6),
        4: (LEFT + (RIGHT - LEFT)/6, BOTTOM + (TOP - BOTTOM)/2),
        5: (LEFT + (RIGHT - LEFT)/2, BOTTOM + (TOP - BOTTOM)/2),
        6: (LEFT + 5*(RIGHT - LEFT)/6, BOTTOM + (TOP - BOTTOM)/2),
        7: (LEFT + (RIGHT - LEFT)/6, BOTTOM + 5*(TOP - BOTTOM)/6),
        8: (LEFT + (RIGHT - LEFT)/2, BOTTOM + 5*(TOP - BOTTOM)/6),
        9: (LEFT + 5*(RIGHT - LEFT)/6, BOTTOM + 5*(TOP - BOTTOM)/6),
        0: (RIGHT + 0.3, BOTTOM),  # Outside zone
    }

    fig = go.Figure()

    # Strike zone rectangle
    fig.add_shape(type="rect",
                  x0=LEFT, y0=BOTTOM, x1=RIGHT, y1=TOP,
                  line=dict(color="black", width=3))

    # Grid lines (lighter)
    for x in [LEFT + (RIGHT - LEFT)/3, LEFT + 2*(RIGHT - LEFT)/3]:
        fig.add_shape(type="line",
                      x0=x, y0=BOTTOM, x1=x, y1=TOP,
                      line=dict(color="gray", width=1, dash="dash"))
    for y in [BOTTOM + (TOP - BOTTOM)/3, BOTTOM + 2*(TOP - BOTTOM)/3]:
        fig.add_shape(type="line",
                      x0=LEFT, y0=y, x1=RIGHT, y1=y,
                      line=dict(color="gray", width=1, dash="dash"))

    player_data = df_agg[df_agg['player_name'] == selected_player]

    x_vals_avg, y_vals_avg, text_avg = [], [], []
    x_vals_xba, y_vals_xba, text_xba = [], [], []

    for zone, center in zone_centers.items():
        stats = player_data[player_data['zone'] == zone]
        if not stats.empty:
            avg_ba = stats['avg_ba'].values[0]
            avg_xba = stats['avg_xba'].values[0]
            count = stats['count'].values[0]
            text_avg.append(f"AVG: {avg_ba:.3f}<br>Pitches: {count}")
            text_xba.append(f"xAVG: {avg_xba:.3f}")
        else:
            text_avg.append("")
            text_xba.append("")

        x_vals_avg.append(center[0])
        y_vals_avg.append(center[1] + 0.05)
        x_vals_xba.append(center[0])
        y_vals_xba.append(center[1] - 0.05)

    # AVG trace
    fig.add_trace(go.Scatter(
        x=x_vals_avg, y=y_vals_avg,
        mode='text',
        text=text_avg,
        textfont=dict(color='blue', size=14),
        name="AVG",
        hoverinfo='text',
        hovertext=text_avg
    ))

    # xAVG trace
    fig.add_trace(go.Scatter(
        x=x_vals_xba, y=y_vals_xba,
        mode='text',
        text=text_xba,
        textfont=dict(color='red', size=14),
        name="xAVG",
        hoverinfo='text',
        hovertext=text_xba
    ))

    fig.update_layout(
        title="Interactive Plate Discipline: Offensive Analysis",
        xaxis=dict(range=[LEFT - 0.5, RIGHT + 1.5], zeroline=False, showgrid=False, showticklabels=False),
        yaxis=dict(range=[BOTTOM - 0.5, TOP + 0.5], zeroline=False, showgrid=False, showticklabels=False),
        height=700,
        width=600,
        margin=dict(t=80)
    )

    return fig

def main():
    df = load_and_prepare_data(FILE_NAME)
    df_agg = aggregate_player_stats(df)
    players = sorted(df_agg['player_name'].unique())

    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("Interactive Plate Discipline: Offensive Analysis", style={'textAlign': 'center'}),
        dcc.Dropdown(
            id='player-dropdown',
            options=[{'label': p, 'value': p} for p in players],
            value="Judge, Aaron",
            searchable=True,
            clearable=False,
            style={'width': '50%', 'margin': 'auto'}
        ),
        dcc.Graph(id='strikezone-graph')
    ])

    @app.callback(
        Output('strikezone-graph', 'figure'),
        Input('player-dropdown', 'value')
    )
    def update_figure(selected_player):
        return create_strikezone_figure(df_agg, selected_player)

    app.run(debug=True)

if __name__ == "__main__":
    main()
