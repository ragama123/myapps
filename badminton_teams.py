import streamlit as st
import pandas as pd

# Predefined list of players with their levels
predefined_players = [
    {"name": "RK", "level": 4},
    {"name": "Pavan", "level": 4},
    {"name": "Chakri", "level": 4},
    {"name": "Rama Reddy", "level": 3},
    {"name": "Ramu", "level": 4},
    {"name": "Manu", "level": 4},
    {"name": "Suresh", "level": 4},
    {"name": "Arun", "level": 4},
    {"name": "Amit", "level": 4},
    {"name": "Dileep", "level": 4},
    {"name": "Pradeep", "level": 2},
    {"name": "Chandru", "level": 4},
    {"name": "Guru", "level": 3},
    {"name": "Ganapati", "level": 2},
    {"name": "Kundan", "level": 3},
    {"name": "Manish", "level": 4},
    {"name": "Extra_Player1", "level": 3},
    {"name": "Extra_Player2", "level": 3}
]

# Initialize an empty list to store selected players
if 'selected_players' not in st.session_state:
    st.session_state.selected_players = []

# Display the list of predefined players with checkboxes in 3 columns
st.header("Select Players for the Tournament")

cols = st.columns(3)
for i, player in enumerate(predefined_players):
    col = cols[i % 3]
    if col.checkbox(f"{player['name']} (Level {player['level']})", key=player['name']):
        if player not in st.session_state.selected_players:
            st.session_state.selected_players.append(player)
    else:
        if player in st.session_state.selected_players:
            st.session_state.selected_players.remove(player)

# Display the current list of selected players in 3 columns with serial numbers
st.header("Selected Players")
num_selected_players = len(st.session_state.selected_players)

if num_selected_players > 0:
    selected_cols = st.columns(3)
    for i, player in enumerate(st.session_state.selected_players):
        col = selected_cols[i % 3]
        col.write(f"{i + 1}. {player['name']} (Level {player['level']})")

    st.write(f"**Total Players Selected: {num_selected_players}**")
else:
    st.write("No players selected yet.")

# Logic to create teams of doubles
st.header("Generate Teams")
if num_selected_players >= 4:
    if st.button("Create Teams"):
        # Sort players by level for balanced teams
        players_sorted = sorted(st.session_state.selected_players, key=lambda x: x['level'], reverse=True)

        # Determine the number of teams (each team needs 2 players)
        num_teams = num_selected_players // 2

        # Create teams without the level information
        teams = []
        for i in range(num_teams):
            team = {
                "Team": f"Team {i+1}",
                "Player 1": players_sorted[i]['name'],
                "Player 2": players_sorted[-(i+1)]['name'],
            }
            teams.append(team)

        # Convert the list of teams to a DataFrame
        teams_df = pd.DataFrame(teams)

        # Display the teams in a table format without index
        teams_df.index = [''] * len(teams_df)  # Remove index by setting it to empty strings
        st.table(teams_df)
else:
    st.write("Select at least 4 players to generate teams.")
