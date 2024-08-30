import streamlit as st
import pandas as pd
import random
from io import BytesIO

# Predefined list of players with their levels
predefined_players = [
    {"name": "RK", "level": 4},
    {"name": "Pavan", "level": 4},
    {"name": "Chakri", "level": 4},
    {"name": "Rama Reddy", "level": 4},
    {"name": "Ramu", "level": 4},
    {"name": "Manu", "level": 4},
    {"name": "Suresh", "level": 4},
    {"name": "Arun", "level": 4},
    {"name": "Amit", "level": 4},
    {"name": "Dileep", "level": 4},
    {"name": "Pradeep", "level": 4},
    {"name": "Chandru", "level": 4},
    {"name": "Guru", "level": 4},
    {"name": "Ganapati", "level": 4},
    {"name": "Kundan", "level": 4},
    {"name": "Manish", "level": 4},
    {"name": "Extra_Player1", "level": 4},
    {"name": "Extra_Player2", "level": 4}
]

# Initialize session state variables
if 'selected_players' not in st.session_state:
    st.session_state.selected_players = []
if 'teams_a' not in st.session_state:
    st.session_state.teams_a = []
if 'teams_b' not in st.session_state:
    st.session_state.teams_b = []

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

# Display the current list of selected players
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

# Logic to create equal pairs of players and divide them into two groups
def create_teams():
    players_sorted = sorted(st.session_state.selected_players, key=lambda x: x['level'], reverse=True)
    random.shuffle(players_sorted)  # Shuffle players to avoid the same teams

    # Create equal pairs of players with combined names
    num_pairs = len(players_sorted) // 2
    teams = [f"{players_sorted[i]['name']}-{players_sorted[num_pairs + i]['name']}" for i in range(num_pairs)]
    
    # Divide the teams equally into Group A and Group B
    teams_a = teams[:len(teams)//2]
    teams_b = teams[len(teams)//2:]

    # If odd number of teams, balance by adding an empty string to the smaller group
    if len(teams_a) > len(teams_b):
        teams_b.append('')
    elif len(teams_b) > len(teams_a):
        teams_a.append('')

    return teams_a, teams_b

# Generate fixtures ensuring each team plays at least 3 matches
def generate_fixtures(teams):
    fixtures = []
    num_teams = len(teams)

    # Each team should play against every other team in a round-robin format
    for i in range(num_teams):
        for j in range(i + 1, num_teams):
            if teams[i] and teams[j]:  # Ensure no empty strings are included
                fixtures.append({"Team 1": teams[i], "Team 2": teams[j]})

    return fixtures

# Generate the Excel file
def generate_excel(teams_a, teams_b, fixtures_a, fixtures_b):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # Teams
    teams_df = pd.DataFrame({
        "Group A Teams": teams_a,
        "Group B Teams": teams_b
    })
    teams_df.to_excel(writer, sheet_name='Teams', index=False)

    # Fixtures
    fixtures_a_df = pd.DataFrame(fixtures_a)
    fixtures_b_df = pd.DataFrame(fixtures_b)

    fixtures_df = pd.concat([fixtures_a_df, fixtures_b_df], keys=['Group A', 'Group B']).reset_index(level=0).rename(columns={'level_0': 'Group'})
    fixtures_df.to_excel(writer, sheet_name='Fixtures', index=False)

    writer.save()
    output.seek(0)
    return output

# Generate teams and fixtures
st.header("Generate Teams")
col1, col2 = st.columns(2)

if num_selected_players >= 4 and num_selected_players % 2 == 0:
    if col1.button("Create Teams"):
        st.session_state.teams_a, st.session_state.teams_b = create_teams()

    if st.session_state.teams_a and st.session_state.teams_b:
        # Display Group A and Group B teams in one table
        st.write("### Teams")
        teams_df = pd.DataFrame({
            "Group A Teams": st.session_state.teams_a,
            "Group B Teams": st.session_state.teams_b
        })
        st.table(teams_df)

        # Generate fixtures
        fixtures_a = generate_fixtures(st.session_state.teams_a)
        fixtures_b = generate_fixtures(st.session_state.teams_b)

        # Display Fixtures
        st.write("### Group A Fixtures")
        fixtures_a_df = pd.DataFrame(fixtures_a)
        st.table(fixtures_a_df)

        st.write("### Group B Fixtures")
        fixtures_b_df = pd.DataFrame(fixtures_b)
        st.table(fixtures_b_df)

        # Provide download link for Excel
        excel_data = generate_excel(st.session_state.teams_a, st.session_state.teams_b, fixtures_a, fixtures_b)
        st.download_button(label="Download Excel", data=excel_data, file_name='tournament_fixtures.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
else:
    st.write("Select an even number of players to generate teams.")
