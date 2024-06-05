from flask import Flask, render_template, redirect, url_for, request, session, jsonify

# Create the application object
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for session management

# In-memory data storage for simplicity
team_roster = [
    {'id': 1, 'name': 'Player1', 'role': 'DPS', 'availability': '10am - 12pm'},
    {'id': 2, 'name': 'Player2', 'role': 'Support', 'availability': '1pm - 3pm'}
]

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

# Use decorators to link the function to a URL
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
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
        new_player = {
            'id': new_id,
            'name': request.form['name'],
            'role': request.form['role'],
            'availability': request.form['availability']
        }
        team_roster.append(new_player)
        return redirect(url_for('team'))
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
        return redirect(url_for('team'))
    return render_template('edit_player.html', player=player)

@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    global team_roster
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    team_roster = [player for player in team_roster if player['id'] != player_id]
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
    return render_template('analytics.html', matches=match_results, win_percentage=win_percentage)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

# Start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)
