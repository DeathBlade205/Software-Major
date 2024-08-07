from flask import Flask, render_template, redirect, url_for, request, session
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import json
import os

# Create the application object
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for session management

# Define the path to the team_roster text file
team_roster_file_path = 'team_roster.txt'

def load_team_roster_from_file():
    team_roster = []
    if os.path.exists(team_roster_file_path):
        with open(team_roster_file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        player_data = json.loads(line)
                        team_roster.append(player_data)
                    except json.JSONDecodeError as e:
                        print(f"Error loading line: {line}. Error: {e}")
    return team_roster

def save_team_roster_to_file(team_roster):
    with open(team_roster_file_path, 'w') as file:
        for player in team_roster:
            file.write(json.dumps(player) + '\n')

# Load the initial team_roster
team_roster = load_team_roster_from_file()

tasks = [
    {'task': 'Review strategy', 'assigned_to': 'Player1', 'due_date': '2023-05-10'},
    {'task': 'Practice session', 'assigned_to': 'Player2', 'due_date': '2023-05-11'}
]

match_results = [
    {'opponent': 'Team A', 'result': 'Win'},
    {'opponent': 'Team B', 'result': 'Loss'},
    {'opponent': 'Team C', 'result': 'Win'}
]

# Helper function to calculate win percentage
def calculate_win_percentage(matches):
    total_matches = len(matches)
    wins = sum(1 for match in matches if match['result'] == 'Win')
    return (wins / total_matches) * 100 if total_matches > 0 else 0

# Data validation functions
def validate_player(name, role, availability):
    if not name or not role or not availability:
        return False, "All fields are required."
    if len(name) < 3 or len(role) < 3:
        return False, "Name and Role must be at least 3 characters long."
    return True, ""

def validate_task(task, assigned_to, due_date):
    if not task or not assigned_to or not due_date:
        return False, "All fields are required."
    if len(task) < 3:
        return False, "Task must be at least 3 characters long."
    if assigned_to not in [player['name'] for player in team_roster]:
        return False, "Assigned player does not exist."
    return True, ""

# Routes and their handlers
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
    return render_template('login.html', error=error)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    win_percentage = calculate_win_percentage(match_results)
    return render_template('dashboard.html', team=team_roster, matches=match_results, win_percentage=win_percentage)

@app.route('/team')
def team():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('team.html', team=team_roster)

@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_id = max(player['id'] for player in team_roster) + 1 if team_roster else 1
        name = request.form['name']
        role = request.form['role']
        availability = request.form['availability']
        is_valid, error_message = validate_player(name, role, availability)
        if is_valid:
            new_player = {
                'id': new_id,
                'name': name,
                'role': role,
                'availability': availability
            }
            team_roster.append(new_player)
            save_team_roster_to_file(team_roster)  # Save updated roster
            return redirect(url_for('team'))
        else:
            return render_template('add_player.html', error=error_message)
    return render_template('add_player.html')

@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    player = next((p for p in team_roster if p['id'] == player_id), None)
    if request.method == 'POST':
        player['name'] = request.form['name']
        player['role'] = request.form['role']
        player['availability'] = request.form['availability']
        is_valid, error_message = validate_player(player['name'], player['role'], player['availability'])
        if is_valid:
            save_team_roster_to_file(team_roster)  # Save updated roster
            return redirect(url_for('team'))
        else:
            return render_template('edit_player.html', player=player, error=error_message)
    return render_template('edit_player.html', player=player)

@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    global team_roster
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    team_roster = [player for player in team_roster if player['id'] != player_id]
    save_team_roster_to_file(team_roster)  # Save updated roster
    return redirect(url_for('team'))

@app.route('/tasks')
def tasks_view():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('tasks.html', tasks=tasks)

@app.route('/analytics')
def analytics():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    win_percentage = calculate_win_percentage(match_results)

    # Data visualization using matplotlib
    fig, ax = plt.subplots()
    results_df = pd.DataFrame(match_results)
    results_df['result'].value_counts().plot(kind='bar', ax=ax)
    plt.title('Match Results')
    plt.xlabel('Result')
    plt.ylabel('Count')

    # Save plot to a string in base64 format
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    return render_template('analytics.html', matches=match_results, win_percentage=win_percentage, plot_url=img_base64)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)