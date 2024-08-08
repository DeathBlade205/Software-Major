from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import json
import os
from datetime import datetime, timedelta

# Create the Flask application object
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management

# Define the file paths for data persistence
team_roster_file_path = 'team_roster.txt'
tasks_file_path = 'tasks.txt'
match_results_file_path = 'match_results.txt'


# Function to load data from a text file
def load_data_from_file(file_path, add_id=False):
    """Load data from a text file and return it as a list of dictionaries."""
    data = []
    if os.path.exists(file_path):  # Check if the file exists
        with open(file_path, 'r') as file:
            for i, line in enumerate(file):
                line = line.strip()
                if line:
                    try:
                        item = json.loads(line)  # Parse JSON data
                        if add_id and 'id' not in item:
                            item['id'] = i  # Add an ID if it's missing
                        data.append(item)
                    except json.JSONDecodeError as e:
                        print(f"Error loading line: {line}. Error: {e}")
    return data


# Function to save data to a text file
def save_data_to_file(data, file_path):
    """Save data (list of dictionaries) to a text file."""
    with open(file_path, 'w') as file:
        for item in data:
            file.write(json.dumps(item) + '\n')


# Load the initial data from text files
team_roster = load_data_from_file(team_roster_file_path, add_id=True)
tasks = load_data_from_file(tasks_file_path, add_id=True)
match_results = load_data_from_file(match_results_file_path, add_id=True)


# Function to calculate win percentage from match results
def calculate_win_percentage(matches):
    """Calculate the win percentage based on match results."""
    total_matches = len(matches)
    wins = sum(1 for match in matches if match['result'].lower() == 'win')
    return (wins / total_matches) * 100 if total_matches > 0 else 0


# Function to get the dates for the current week (Monday to Sunday)
def get_current_week_dates():
    """Return a list of dates for the current week (Monday to Sunday)."""
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())  # Get the start of the week (Monday)
    return [(start_of_week + timedelta(days=i)).date() for i in range(7)]


# Utility function to parse dates
def parse_date(date_str):
    """Try to parse a date string in multiple formats."""
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


# Function to validate player data
def validate_player(name, role, availabilities):
    """Validate player data to ensure all fields are correct."""
    for availability in availabilities:
        if not parse_date(availability['start']) or not parse_date(availability['end']):
            return False, "Each availability must be a valid datetime in YYYY-MM-DD or YYYY-MM-DD HH:MM format."

    if not name or not role or not availabilities:
        return False, "All fields are required."
    if len(name) < 3 or len(role) < 3:
        return False, "Name and Role must be at least 3 characters long."
    return True, ""


# Function to validate task data
def validate_task(task, assigned_to, due_date):
    """Validate task data to ensure all fields are correct."""
    if not parse_date(due_date):
        return False, "Due date must be a valid datetime in YYYY-MM-DD or YYYY-MM-DD HH:MM format."

    if not task or not assigned_to or not due_date:
        return False, "All fields are required."
    if len(task) < 3:
        return False, "Task must be at least 3 characters long."
    if assigned_to not in [player['name'] for player in team_roster]:
        return False, "Assigned player does not exist."
    return True, ""


# Function to check if a given date string is valid
def is_valid_date(date_str):
    """Check if the given string is a valid datetime in YYYY-MM-DD or YYYY-MM-DD HH:MM format."""
    return parse_date(date_str) is not None


# Route to render the home page
@app.route('/')
def home():
    """Render the home page."""
    return render_template('index.html')


# Route to render the about page
@app.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')


# Route to render the welcome page
@app.route('/welcome')
def welcome():
    """Render the welcome page."""
    return render_template('welcome.html')


# Route to handle user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    error = None
    if request.method == 'POST':
        # Check if the username and password are correct
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
    return render_template('login.html', error=error)


# Decorator function to check if user is logged in
def login_required(f):
    """Decorator function to check if user is logged in."""
    def wrap(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap


# Route to render the dashboard page with current week's schedule and win percentage
@app.route('/dashboard')
@login_required
def dashboard():
    """Render the dashboard page with current week's schedule and win percentage."""
    current_week_dates = get_current_week_dates()

    # Filter player availability for the current week
    weekly_availability = [
        availability for player in team_roster for availability in player.get('availabilities', [])
        if isinstance(availability, dict) and is_valid_date(availability['start']) and is_valid_date(
            availability['end']) and
           parse_date(availability['start']).date() in current_week_dates
    ]

    # Filter tasks for the current week
    weekly_tasks = [
        task for task in tasks if parse_date(task['due_date']).date() in current_week_dates
    ]

    win_percentage = calculate_win_percentage(match_results)
    return render_template('dashboard.html', availabilities=weekly_availability, tasks=weekly_tasks,
                           win_percentage=win_percentage, week_dates=current_week_dates)


# Route to render the team roster page
@app.route('/team')
@login_required
def team():
    """Render the team roster page."""
    return render_template('team.html', team=team_roster)


# Route to add a new player to the team roster
@app.route('/add_player', methods=['GET', 'POST'])
@login_required
def add_player():
    """Add a new player to the team roster."""
    if request.method == 'POST':
        # Generate a new ID for the player
        new_id = max(player['id'] for player in team_roster) + 1 if team_roster else 1
        name = request.form['name']
        role = request.form['role']
        availabilities = []
        for date, start_time, end_time in zip(request.form.getlist('date'), request.form.getlist('start_time'),
                                              request.form.getlist('end_time')):
            availabilities.append({'start': f"{date} {start_time}", 'end': f"{date} {end_time}"})
        is_valid, error_message = validate_player(name, role, availabilities)
        if is_valid:
            new_player = {
                'id': new_id,
                'name': name,
                'role': role,
                'availabilities': availabilities
            }
            team_roster.append(new_player)
            save_data_to_file(team_roster, team_roster_file_path)  # Save updated roster
            return redirect(url_for('team'))
        else:
            return render_template('add_player.html', error=error_message)
    return render_template('add_player.html')


# Route to edit an existing player's details
@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
@login_required
def edit_player(player_id):
    """Edit an existing player's details."""
    player = next((p for p in team_roster if p['id'] == player_id), None)
    if request.method == 'POST':
        player['name'] = request.form['name']
        player['role'] = request.form['role']
        player['availabilities'] = []
        for date, start_time, end_time in zip(request.form.getlist('date'), request.form.getlist('start_time'),
                                              request.form.getlist('end_time')):
            player['availabilities'].append({'start': f"{date} {start_time}", 'end': f"{date} {end_time}"})
        is_valid, error_message = validate_player(player['name'], player['role'], player['availabilities'])
        if is_valid:
            save_data_to_file(team_roster, team_roster_file_path)  # Save updated roster
            return redirect(url_for('team'))
        else:
            return render_template('edit_player.html', player=player, error=error_message)
    return render_template('edit_player.html', player=player)


# Route to delete a player from the team roster
@app.route('/delete_player/<int:player_id>', methods=['POST'])
@login_required
def delete_player(player_id):
    """Delete a player from the team roster."""
    global team_roster
    team_roster = [player for player in team_roster if player['id'] != player_id]
    save_data_to_file(team_roster, team_roster_file_path)  # Save updated roster
    return redirect(url_for('team'))


# Route to render the tasks page
@app.route('/tasks')
@login_required
def tasks_view():
    """Render the tasks page."""
    return render_template('tasks.html', tasks=tasks)


# Route to add a new task to the task list
@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    """Add a new task to the task list."""
    if request.method == 'POST':
        # Generate a new ID for the task
        new_id = max(task['id'] for task in tasks) + 1 if tasks else 1
        task = request.form['task']
        assigned_to = request.form['assigned_to']
        due_date = request.form['due_date']
        is_valid, error_message = validate_task(task, assigned_to, due_date)
        if is_valid:
            new_task = {
                'id': new_id,
                'task': task,
                'assigned_to': assigned_to,
                'due_date': due_date
            }
            tasks.append(new_task)
            save_data_to_file(tasks, tasks_file_path)  # Save updated tasks
            return redirect(url_for('tasks_view'))
        else:
            return render_template('add_task.html', error=error_message)
    return render_template('add_task.html', players=team_roster)


# Route to edit an existing task's details
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    """Edit an existing task's details."""
    task = next((t for t in tasks if t['id'] == task_id), None)
    if request.method == 'POST':
        task['task'] = request.form['task']
        task['assigned_to'] = request.form['assigned_to']
        task['due_date'] = request.form['due_date']
        is_valid, error_message = validate_task(task['task'], task['assigned_to'], task['due_date'])
        if is_valid:
            save_data_to_file(tasks, tasks_file_path)  # Save updated tasks
            return redirect(url_for('tasks_view'))
        else:
            return render_template('edit_task.html', task=task, players=team_roster, error=error_message)
    return render_template('edit_task.html', task=task, players=team_roster)


# Route to delete a task from the task list
@app.route('/delete_task/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    """Delete a task from the task list."""
    global tasks
    tasks = [task for task in tasks if task['id'] != task_id]
    save_data_to_file(tasks, tasks_file_path)  # Save updated tasks
    return redirect(url_for('tasks_view'))


# Route to render the analytics page with match results and win percentage
@app.route('/analytics')
@login_required
def analytics():
    """Render the analytics page with match results and win percentage."""
    win_percentage = calculate_win_percentage(match_results)

    # Create a bar chart of match results using matplotlib
    fig, ax = plt.subplots()
    results_df = pd.DataFrame(match_results)
    results_df['result'].value_counts().plot(kind='bar', ax=ax)
    plt.title('Match Results')
    plt.xlabel('Result')
    plt.ylabel('Count')

    # Save the plot to a string in base64 format
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    return render_template('analytics.html', matches=match_results, win_percentage=win_percentage, plot_url=img_base64)


# Route to add a new match result
@app.route('/add_match', methods=['POST'])
@login_required
def add_match():
    """Add a new match result."""
    opponent = request.form['opponent']
    result = request.form['result']
    stats = request.form.get('stats', '')
    description = request.form.get('description', '')
    new_match = {
        'id': max(match['id'] for match in match_results) + 1 if match_results else 1,
        'opponent': opponent,
        'result': result,
        'stats': stats,
        'description': description
    }
    match_results.append(new_match)
    save_data_to_file(match_results, match_results_file_path)  # Save updated match results
    return redirect(url_for('analytics'))


# Route to edit an existing match result
@app.route('/edit_match/<int:match_id>', methods=['GET', 'POST'])
@login_required
def edit_match(match_id):
    """Edit an existing match result."""
    match = next((m for m in match_results if m['id'] == match_id), None)
    if request.method == 'POST':
        match['opponent'] = request.form['opponent']
        match['result'] = request.form['result']
        match['stats'] = request.form['stats']
        match['description'] = request.form['description']
        save_data_to_file(match_results, match_results_file_path)  # Save updated match results
        return redirect(url_for('analytics'))
    return render_template('edit_match.html', match=match)


# Route to delete a match result from the match results list
@app.route('/delete_match/<int:match_id>', methods=['POST'])
@login_required
def delete_match(match_id):
    """Delete a match result from the match results list."""
    global match_results
    match_results = [match for match in match_results if match['id'] != match_id]
    save_data_to_file(match_results, match_results_file_path)  # Save updated match results
    return redirect(url_for('analytics'))


# API endpoint to get events for FullCalendar
@app.route('/api/events')
@login_required
def get_events():
    """API endpoint to get events for FullCalendar."""
    events = []
    for player in team_roster:
        for availability in player.get('availabilities', []):
            if isinstance(availability, dict) and is_valid_date(availability['start']) and is_valid_date(
                    availability['end']):
                events.append({
                    'title': f"{player['name']} - {player['role']}",
                    'start': availability['start'],
                    'end': availability['end']
                })

    for task in tasks:
        if is_valid_date(task['due_date']):
            events.append({
                'title': task['task'],
                'start': task['due_date'],
                'end': task['due_date']
            })

    return jsonify(events)


# Route to handle user logout
@app.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('logged_in', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
