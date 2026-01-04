from flask import Flask, render_template, request, redirect, jsonify
import requests

app = Flask(__name__)

# 1. SIMPLE STORAGE (In a real app, use a database or JSON file)
# Example: {'User1': {'roster': {...}, 'color': '#ff0000'}, 'User2': {'roster': {...}, 'color': '#00ff00'}}
teams = {}

# Initialize sample teams if none exist
if not teams:
    teams["Scott's Team"] = {
        'roster': {
            'QB': [{'name': 'Baker Mayfield', 'team': 'TB', 'position': 'QB', 'team_color': '#d50a0a'}],
            'RB': [
                {'name': 'Bucky Irving', 'team': 'TB', 'position': 'RB', 'team_color': '#d50a0a'},
                {'name': 'Kenneth Walker III', 'team': 'SEA', 'position': 'RB', 'team_color': '#002244'}
            ],
            'WR': [
                {'name': 'Mike Evans', 'team': 'TB', 'position': 'WR', 'team_color': '#d50a0a'},
                {'name': 'Jaxon Smith-Njigba', 'team': 'SEA', 'position': 'WR', 'team_color': '#002244'}
            ],
            'TE': [{'name': 'Cade Otton', 'team': 'TB', 'position': 'TE', 'team_color': '#d50a0a'}],
            'K': [{'name': 'Chase McLaughlin', 'team': 'TB', 'position': 'K', 'team_color': '#d50a0a'}],
            'DST': [{'name': 'TB DST', 'team': 'TB', 'position': 'DST', 'team_color': '#d50a0a'}]
        },
        'color': '#ff6b35'
    }
    
    teams["John's Team"] = {
        'roster': {
            'QB': [{'name': 'Sam Darnold', 'team': 'MIN', 'position': 'QB', 'team_color': '#4f2683'}],
            'RB': [
                {'name': 'Zach Charbonnet', 'team': 'SEA', 'position': 'RB', 'team_color': '#002244'},
                {'name': 'Christian McCaffrey', 'team': 'SF', 'position': 'RB', 'team_color': '#aa0000'}
            ],
            'WR': [
                {'name': 'Cooper Kupp', 'team': 'LAR', 'position': 'WR', 'team_color': '#003594'},
                {'name': 'George Kittle', 'team': 'SF', 'position': 'WR', 'team_color': '#aa0000'}
            ],
            'TE': [{'name': 'AJ Barner', 'team': 'SEA', 'position': 'TE', 'team_color': '#002244'}],
            'K': [{'name': 'Jason Myers', 'team': 'SEA', 'position': 'K', 'team_color': '#002244'}],
            'DST': [{'name': 'SF DST', 'team': 'SF', 'position': 'DST', 'team_color': '#aa0000'}]
        },
        'color': '#4ecdc4'
    }

# Roster structure requirements
ROSTER_POSITIONS = {
    'QB': 1,
    'RB': 2, 
    'WR': 2,
    'TE': 1,  # This will be the flex spot that can also hold RB/WR
    'K': 1,
    'DST': 1
}

# Position mapping for ESPN data
POSITION_MAPPING = {
    'QB': 'QB',
    'RB': 'RB', 
    'WR': 'WR',
    'TE': 'TE',
    'K': 'K',
    'PK': 'K',  # Some kickers are listed as PK
    'D/ST': 'DST',
    'DEF': 'DST',
    'DST': 'DST'
}

# Cache for players to avoid repeated API calls
players_cache = {
    'players': {},
    'last_updated': None
}

def get_teams_with_games():
    """Get list of teams that have games this week from the scoreboard."""
    try:
        scoreboard_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        response = requests.get(scoreboard_url)
        
        if response.status_code != 200:
            return set()
            
        data = response.json()
        teams_with_games = set()
        
        for event in data.get('events', []):
            competitors = event.get('competitions', [{}])[0].get('competitors', [])
            for competitor in competitors:
                team_info = competitor.get('team', {})
                team_abbr = team_info.get('abbreviation', '')
                team_name = team_info.get('displayName', '')
                team_short_name = team_info.get('shortDisplayName', '')
                team_location = team_info.get('location', '')
                
                # Add multiple variations of team names
                if team_abbr:
                    teams_with_games.add(team_abbr.upper())
                    teams_with_games.add(team_abbr.lower())
                if team_name:
                    teams_with_games.add(team_name)
                if team_short_name:
                    teams_with_games.add(team_short_name)
                if team_location:
                    teams_with_games.add(team_location)
                    
        print(f"Found {len(teams_with_games)} teams with games this week")
        return teams_with_games
        
    except Exception as e:
        print(f"Error getting teams with games: {e}")
        return set()

def get_available_players():
    """Fetch available players from ESPN API organized by position."""
    from datetime import datetime, timedelta
    
    # Check cache (refresh every hour)
    now = datetime.now()
    if (players_cache['last_updated'] and 
        now - players_cache['last_updated'] < timedelta(hours=1) and
        players_cache['players']):
        return players_cache['players']
    
    # Get teams that have games this week
    teams_with_games = get_teams_with_games()
    
    players_by_position = {
        'QB': [],
        'RB': [],
        'WR': [], 
        'TE': [],
        'K': [],
        'DST': []
    }
    
    try:
        # First, get all NFL teams and their roster links
        teams_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
        teams_response = requests.get(teams_url)
        
        if teams_response.status_code == 200:
            teams_data = teams_response.json()
            
            # Process each team
            for team in teams_data.get('sports', [{}])[0].get('leagues', [{}])[0].get('teams', []):
                team_info = team.get('team', {})
                team_abbr = team_info.get('abbreviation', '')
                team_name = team_info.get('displayName', '')
                
                # Only process teams that have games this week
                # Check both abbreviation and full name variations
                has_game = False
                if team_abbr and team_abbr.upper() in teams_with_games:
                    has_game = True
                if team_name and team_name in teams_with_games:
                    has_game = True
                
                if not has_game:
                    print(f"  Skipping {team_name} ({team_abbr}) - no game this week")
                    continue
                
                print(f"Processing team: {team_name} ({team_abbr})")
                
                # Add DST for this team
                dst_name = f"{team_abbr} DST"
                team_color = team_info.get('color', '000000')  # Get team color, default to black
                # Ensure color has # prefix and is valid
                if team_color and not team_color.startswith('#'):
                    team_color = f"#{team_color}"
                if not team_color or team_color == '#' or team_color == '#000000':
                    team_color = '#64748b'  # Default gray for missing colors
                    
                if dst_name != " DST":
                    players_by_position['DST'].append({
                        'name': dst_name,
                        'team': team_abbr,
                        'position': 'DST',
                        'team_color': team_color
                    })
                
                # Try to get roster from the roster API endpoint
                # Use the team abbreviation to construct roster URL
                if team_abbr:
                    roster_api_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_abbr.lower()}/roster"
                    print(f"Trying roster URL: {roster_api_url}")
                    
                    roster_response = requests.get(roster_api_url)
                    
                    if roster_response.status_code == 200:
                        roster_data = roster_response.json()
                        
                        # Process athletes in the roster - each group is a position category (offense, defense, etc)
                        athlete_groups = roster_data.get('athletes', [])
                        print(f"  Found {len(athlete_groups)} position groups for {team_name}")
                        
                        for athlete_group in athlete_groups:
                            group_name = athlete_group.get('position', '')  # "offense", "defense", etc
                            players_in_group = athlete_group.get('items', [])
                            print(f"    Processing {group_name} group with {len(players_in_group)} players")
                            
                            # Skip defensive players - we only want offensive skill players and kickers
                            if group_name.lower() in ['defense', 'defensive']:
                                print(f"      Skipping {group_name} group (defensive players)")
                                continue
                            
                            for athlete_data in players_in_group:
                                player_name = athlete_data.get('displayName', '')
                                
                                # Only include active roster players - filter out inactive statuses
                                status = athlete_data.get('status', {})
                                status_type = status.get('type', '') if status else ''
                                status_name = status.get('name', '') if status else ''
                                
                                # Skip players with inactive statuses
                                inactive_statuses = ['practice-squad', 'injured-reserve', 'suspended', 'out']
                                if status_type in inactive_statuses or status_name.lower() in ['injured reserve', 'out', 'suspended']:
                                    continue
                                
                                # Get the player's specific position
                                position_info = athlete_data.get('position', {})
                                position_abbr = position_info.get('abbreviation', '') if position_info else ''
                                
                                # Map ESPN positions to our position system
                                mapped_position = POSITION_MAPPING.get(position_abbr, None)
                                
                                # Get team color for this player
                                team_color = team_info.get('color', '000000')
                                # Ensure color has # prefix and is valid
                                if team_color and not team_color.startswith('#'):
                                    team_color = f"#{team_color}"
                                if not team_color or team_color == '#' or team_color == '#000000':
                                    team_color = '#64748b'  # Default gray for missing colors
                                
                                if mapped_position and mapped_position in players_by_position and player_name:
                                    # Only include offensive skill players and kickers (DST is handled separately above)
                                    if mapped_position in ['QB', 'RB', 'WR', 'TE', 'K']:
                                        players_by_position[mapped_position].append({
                                            'name': player_name,
                                            'team': team_abbr,
                                            'position': mapped_position,
                                            'team_color': team_color
                                        })
                                        print(f"      Added {player_name} ({position_abbr} -> {mapped_position})")
                    else:
                        print(f"  Failed to get roster for {team_name}: {roster_response.status_code}")
        
        # Remove duplicates and sort by name
        for position in players_by_position:
            # Remove duplicates based on player name
            seen_names = set()
            unique_players = []
            for player in players_by_position[position]:
                if player['name'] not in seen_names:
                    seen_names.add(player['name'])
                    unique_players.append(player)
            
            # Sort alphabetically
            unique_players.sort(key=lambda x: x['name'])
            players_by_position[position] = unique_players
        
        total_players = sum(len(pos_players) for pos_players in players_by_position.values())
        print(f"Fetched {total_players} total players from API")
        for pos, players in players_by_position.items():
            print(f"  {pos}: {len(players)} players")
        
        # Update cache
        players_cache['players'] = players_by_position
        players_cache['last_updated'] = now
        
        return players_by_position
        
    except Exception as e:
        print(f"Error fetching players from API: {e}")
        import traceback
        traceback.print_exc()
        
        # Return empty structure if API fails - no fallbacks
        print("API failed - returning empty player lists")
        return players_by_position

# 2. SCORING SETTINGS (now editable via settings page)
DEFAULT_SCORING = {
    # Offensive scoring
    'pass_td': 4,
    'rush_td': 6,
    'rec_td': 6,
    'pass_yds': 0.04,  # 1 pt per 25 yds
    'rush_yds': 0.1,   # 1 pt per 10 yds
    'rec_yds': 0.1,    # 1 pt per 10 yds
    'receptions': 1,   # PPR - 1 pt per reception
    'fumble': -2,
    'interception': -2,
    
    # Kicker scoring
    'fg_0_39': 3,      # Field goal 0-39 yards
    'fg_40_49': 4,     # Field goal 40-49 yards
    'fg_50_plus': 5,   # Field goal 50+ yards
    'fg_miss': -1,     # Missed field goal
    'extra_point': 1,  # Extra point made
    'extra_miss': -1,  # Extra point missed
    
    # D/ST scoring
    'dst_td': 6,       # Defensive/Special teams TD
    'dst_safety': 2,   # Safety
    'dst_interception': 2,  # Interception
    'dst_fumble_rec': 2,    # Fumble recovery
    'dst_sack': 1,     # Sack
    'dst_block': 2,    # Blocked kick
    'dst_pts_0': 10,   # 0 points allowed
    'dst_pts_1_6': 7,  # 1-6 points allowed
    'dst_pts_7_13': 4, # 7-13 points allowed
    'dst_pts_14_20': 1,# 14-20 points allowed
    'dst_pts_21_27': 0,# 21-27 points allowed
    'dst_pts_28_34': -1, # 28-34 points allowed
    'dst_pts_35_plus': -4  # 35+ points allowed
}

# Initialize scoring settings
SCORING = DEFAULT_SCORING.copy()

def get_team_defensive_performance():
    """Get team defensive performance (points allowed and defensive stats) from scoreboard."""
    team_performance = {}
    
    try:
        scoreboard_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        response = requests.get(scoreboard_url)
        
        if response.status_code != 200:
            return team_performance
            
        data = response.json()
        
        for event in data.get('events', []):
            competitions = event.get('competitions', [])
            for competition in competitions:
                competitors = competition.get('competitors', [])
                if len(competitors) == 2:
                    # Get both teams and their stats
                    team1 = competitors[0]
                    team2 = competitors[1]
                    
                    team1_abbr = team1.get('team', {}).get('abbreviation', '')
                    team2_abbr = team2.get('team', {}).get('abbreviation', '')
                    
                    team1_score = int(team1.get('score', 0))
                    team2_score = int(team2.get('score', 0))
                    
                    # Initialize team performance data
                    if team1_abbr:
                        team_performance[team1_abbr] = {
                            'points_allowed': team2_score,
                            'sacks': 0,
                            'interceptions': 0,
                            'fumbles_recovered': 0,
                            'defensive_tds': 0
                        }
                    
                    if team2_abbr:
                        team_performance[team2_abbr] = {
                            'points_allowed': team1_score,
                            'sacks': 0,
                            'interceptions': 0,
                            'fumbles_recovered': 0,
                            'defensive_tds': 0
                        }
                    
                    # Try to get team defensive stats from game details
                    game_id = event.get('id')
                    if game_id:
                        try:
                            game_detail_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={game_id}"
                            detail_response = requests.get(game_detail_url)
                            
                            if detail_response.status_code == 200:
                                detail_data = detail_response.json()
                                
                                # Look for team stats in boxscore
                                boxscore = detail_data.get('boxscore', {})
                                teams = boxscore.get('teams', [])
                                
                                for team_box in teams:
                                    team_abbr = team_box.get('team', {}).get('abbreviation', '')
                                    
                                    if team_abbr and team_abbr in team_performance:
                                        # Look for defensive statistics
                                        statistics = team_box.get('statistics', [])
                                        
                                        for stat_group in statistics:
                                            stat_name = stat_group.get('name', '').lower()
                                            stats = stat_group.get('stats', [])
                                            
                                            print(f"Team {team_abbr} stat group '{stat_name}': {stats}")
                                            
                                            for stat in stats:
                                                label = stat.get('label', '').lower()
                                                value = stat.get('displayValue', '0')
                                                
                                                try:
                                                    if 'sack' in label:
                                                        team_performance[team_abbr]['sacks'] = float(value)
                                                        print(f"  Found sacks for {team_abbr}: {value}")
                                                    elif 'interception' in label and 'yard' not in label:
                                                        team_performance[team_abbr]['interceptions'] = int(value)
                                                        print(f"  Found interceptions for {team_abbr}: {value}")
                                                    elif 'fumble' in label and ('recover' in label or 'lost' in label):
                                                        team_performance[team_abbr]['fumbles_recovered'] = int(value)
                                                        print(f"  Found fumbles recovered for {team_abbr}: {value}")
                                                    elif ('defensive' in label or 'def' in label) and ('touchdown' in label or 'td' in label):
                                                        team_performance[team_abbr]['defensive_tds'] = int(value)
                                                        print(f"  Found defensive TDs for {team_abbr}: {value}")
                                                except (ValueError, TypeError):
                                                    continue
                        except Exception as e:
                            print(f"Error getting game details for {game_id}: {e}")
        
        # Since team defensive stats aren't available in boxscore, extract from QB sacks allowed
        # Sacks allowed by offensive team = sacks by opposing defensive team
        for event in data.get('events', []):
            competitions = event.get('competitions', [])
            for competition in competitions:
                competitors = competition.get('competitors', [])
                if len(competitors) == 2:
                    team1 = competitors[0]
                    team2 = competitors[1]
                    
                    team1_abbr = team1.get('team', {}).get('abbreviation', '')
                    team2_abbr = team2.get('team', {}).get('abbreviation', '')
                    
                    # Look for sacks in team1's passing stats (sacks allowed = team2's defensive sacks)
                    team1_stats = team1.get('statistics', [])
                    for stat_group in team1_stats:
                        if stat_group.get('name') == 'passing':
                            athletes = stat_group.get('athletes', [])
                            for athlete in athletes:
                                stats = athlete.get('stats', [])
                                keys = athlete.get('keys', [])
                                
                                # Find sacks-sackYardsLost in keys
                                for i, key in enumerate(keys):
                                    if key == 'sacks-sackYardsLost' and i < len(stats):
                                        sacks_stat = stats[i]  # Format like "3-7"
                                        if '-' in str(sacks_stat):
                                            sacks_allowed = int(str(sacks_stat).split('-')[0])
                                            if team2_abbr and team2_abbr in team_performance:
                                                team_performance[team2_abbr]['sacks'] = sacks_allowed
                                                print(f"  Extracted sacks for {team2_abbr}: {sacks_allowed} (from {team1_abbr} QB sacks allowed)")
                    
                    # Look for sacks in team2's passing stats (sacks allowed = team1's defensive sacks)
                    team2_stats = team2.get('statistics', [])
                    for stat_group in team2_stats:
                        if stat_group.get('name') == 'passing':
                            athletes = stat_group.get('athletes', [])
                            for athlete in athletes:
                                stats = athlete.get('stats', [])
                                keys = athlete.get('keys', [])
                                
                                # Find sacks-sackYardsLost in keys
                                for i, key in enumerate(keys):
                                    if key == 'sacks-sackYardsLost' and i < len(stats):
                                        sacks_stat = stats[i]  # Format like "3-7"
                                        if '-' in str(sacks_stat):
                                            sacks_allowed = int(str(sacks_stat).split('-')[0])
                                            if team1_abbr and team1_abbr in team_performance:
                                                team_performance[team1_abbr]['sacks'] = sacks_allowed
                                                print(f"  Extracted sacks for {team1_abbr}: {sacks_allowed} (from {team2_abbr} QB sacks allowed)")
                    
                    # Look for interceptions in passing stats
                    for stat_group in team1_stats:
                        if stat_group.get('name') == 'passing':
                            athletes = stat_group.get('athletes', [])
                            for athlete in athletes:
                                stats = athlete.get('stats', [])
                                keys = athlete.get('keys', [])
                                
                                # Find interceptions in keys
                                for i, key in enumerate(keys):
                                    if key == 'interceptions' and i < len(stats):
                                        ints_thrown = int(stats[i])
                                        if team2_abbr and team2_abbr in team_performance:
                                            team_performance[team2_abbr]['interceptions'] = ints_thrown
                                            print(f"  Extracted interceptions for {team2_abbr}: {ints_thrown} (from {team1_abbr} QB interceptions thrown)")
                    
                    for stat_group in team2_stats:
                        if stat_group.get('name') == 'passing':
                            athletes = stat_group.get('athletes', [])
                            for athlete in athletes:
                                stats = athlete.get('stats', [])
                                keys = athlete.get('keys', [])
                                
                                # Find interceptions in keys
                                for i, key in enumerate(keys):
                                    if key == 'interceptions' and i < len(stats):
                                        ints_thrown = int(stats[i])
                                        if team1_abbr and team1_abbr in team_performance:
                                            team_performance[team1_abbr]['interceptions'] = ints_thrown
                                            print(f"  Extracted interceptions for {team1_abbr}: {ints_thrown} (from {team2_abbr} QB interceptions thrown)")
        
        
        print(f"Team defensive performance: {team_performance}")
        return team_performance
        
    except Exception as e:
        print(f"Error getting team defensive performance: {e}")
        return team_performance

def calculate_dst_points_allowed_score(points_allowed):
    """Calculate D/ST scoring based on points allowed."""
    if points_allowed == 0:
        return SCORING['dst_pts_0']
    elif 1 <= points_allowed <= 6:
        return SCORING['dst_pts_1_6']
    elif 7 <= points_allowed <= 13:
        return SCORING['dst_pts_7_13']
    elif 14 <= points_allowed <= 20:
        return SCORING['dst_pts_14_20']
    elif 21 <= points_allowed <= 27:
        return SCORING['dst_pts_21_27']
    elif 28 <= points_allowed <= 34:
        return SCORING['dst_pts_28_34']
    else:  # 35+ points
        return SCORING['dst_pts_35_plus']

def get_live_stats():
    """Fetches live NFL stats from ESPN's public scoreboard API."""
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    try:
        response = requests.get(url)
        data = response.json()
        player_stats = {}
        player_detailed_stats = {}
        dst_stats = {}  # Track D/ST stats by team
        team_defensive_performance = {}  # Track team defensive stats (sacks, ints, points allowed)
        games_processed = 0

        for event in data.get('events', []):
            # Check if game has started/finished (only completed games have detailed stats)
            status = event.get('status', {}).get('type', {}).get('name', '')
            if status not in ['STATUS_FINAL', 'STATUS_IN_PROGRESS']:
                continue
                
            game_id = event['id']
            games_processed += 1
            print(f"Processing game {game_id} (status: {status})")
            
            summary_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event={game_id}"
            summary_response = requests.get(summary_url)
            
            if summary_response.status_code != 200:
                print(f"Failed to get summary for game {game_id}")
                continue
                
            summary = summary_response.json()
            
            # Check if boxscore and players exist
            boxscore = summary.get('boxscore', {})
            if 'players' not in boxscore:
                print(f"No player stats available for game {game_id}")
                continue
            
            # Process each team's player statistics
            competitors = event.get('competitions', [{}])[0].get('competitors', [])
            
            # Initialize team defensive performance for both teams
            for team_idx, competitor in enumerate(competitors):
                if team_idx < 2:  # Only process the two competing teams
                    team_info = competitor.get('team', {})
                    team_abbr = team_info.get('abbreviation', '')
                    team_score = int(competitor.get('score', 0))
                    opponent_score = int(competitors[1 - team_idx].get('score', 0)) if len(competitors) > 1 else 0
                    
                    if team_abbr:
                        team_defensive_performance[team_abbr] = {
                            'points_allowed': opponent_score,
                            'sacks': 0,
                            'interceptions': 0,
                            'fumbles_recovered': 0,
                            'defensive_tds': 0
                        }
                        print(f"Initialized {team_abbr} defensive performance: points_allowed={opponent_score}")
            
            for team_idx, team_players in enumerate(boxscore['players']):
                # Get team info for this team
                team_info = competitors[team_idx].get('team', {}) if team_idx < len(competitors) else {}
                team_abbr = team_info.get('abbreviation', f'TEAM_{team_idx}')
                team_name = team_info.get('displayName', f'Team {team_idx}')
                
                print(f"=== TEAM STATS DEBUG ({team_name} - {team_abbr}) ===")
                print(f"Available stat groups: {[group.get('name', 'UNKNOWN') for group in team_players.get('statistics', [])]}")
                
                # Extract team defensive stats from QB passing stats
                for stat_group in team_players.get('statistics', []):
                    if stat_group.get('name') == 'passing':
                        # Get opponent team abbreviation
                        opponent_idx = 1 - team_idx if team_idx < 2 else None
                        opponent_abbr = None
                        if opponent_idx is not None and opponent_idx < len(competitors):
                            opponent_abbr = competitors[opponent_idx].get('team', {}).get('abbreviation', '')
                        
                        athletes = stat_group.get('athletes', [])
                        keys = stat_group.get('keys', [])
                        
                        for athlete in athletes:
                            stats = athlete.get('stats', [])
                            
                            # Extract sacks allowed (opponent gets credit for sacks)
                            if 'sacks-sackYardsLost' in keys:
                                sack_idx = keys.index('sacks-sackYardsLost')
                                if sack_idx < len(stats):
                                    sacks_stat = stats[sack_idx]  # Format like "3-7"
                                    if '-' in str(sacks_stat):
                                        sacks_allowed = int(str(sacks_stat).split('-')[0])
                                        if opponent_abbr and opponent_abbr in team_defensive_performance:
                                            team_defensive_performance[opponent_abbr]['sacks'] = sacks_allowed
                                            print(f"🛡️ TEAM DEFENSIVE EXTRACTION: {opponent_abbr} gets {sacks_allowed} sacks (from {team_abbr} QB sacks allowed)")
                            
                            # Extract interceptions thrown (opponent gets credit for interceptions)
                            if 'interceptions' in keys:
                                int_idx = keys.index('interceptions')
                                if int_idx < len(stats):
                                    ints_thrown = int(stats[int_idx])
                                    if opponent_abbr and opponent_abbr in team_defensive_performance:
                                        team_defensive_performance[opponent_abbr]['interceptions'] = ints_thrown
                                        print(f"🛡️ TEAM DEFENSIVE EXTRACTION: {opponent_abbr} gets {ints_thrown} interceptions (from {team_abbr} QB interceptions thrown)")
                
                for stat_group in team_players.get('statistics', []):
                    stat_name = stat_group.get('name', '')
                    keys = stat_group.get('keys', [])
                    athletes = stat_group.get('athletes', [])
                    
                    print(f"📊 STAT GROUP: '{stat_name}' with {len(athletes)} athletes")
                    print(f"   Keys available: {keys}")
                    
                    # Special debug for passing stats
                    if stat_name == 'passing':
                        print(f"   🔍 PASSING GROUP DETAILS:")
                        for idx, athlete in enumerate(athletes):
                            athlete_name = athlete['athlete']['displayName']
                            athlete_stats = athlete.get('stats', [])
                            print(f"     Athlete {idx}: {athlete_name}")
                            print(f"     Stats: {athlete_stats}")
                    
                    for athlete in athletes:
                        name = athlete['athlete']['displayName']
                        stats = athlete.get('stats', [])
                        
                        # Skip individual defensive players - aggregate their stats for D/ST instead
                        if stat_name in ['defensive', 'interceptions'] and not name.endswith(' DST'):
                            print(f"  🛡️ Aggregating defensive stats for {name} ({team_abbr})")
                            
                            # Initialize team defensive stats if needed
                            if team_abbr not in dst_stats:
                                dst_stats[team_abbr] = {}
                            if name not in dst_stats[team_abbr]:
                                dst_stats[team_abbr][name] = {}
                            
                            # Extract defensive stats for aggregation
                            detailed_stats = extract_key_stats(stat_name, keys, stats)
                            if detailed_stats:
                                dst_stats[team_abbr][name].update(detailed_stats)
                                print(f"    Added stats: {detailed_stats}")
                            
                            continue
                        
                        print(f"  🏈 Processing {name} for {stat_name}")
                        
                        if name not in player_stats:
                            player_stats[name] = 0
                            player_detailed_stats[name] = {}
                        
                        # Special handling for D/ST defensive stats
                        if stat_name in ['defensive', 'interceptions'] and name.endswith(' DST'):
                            print(f"  🛡️ Processing D/ST unit: {name}")
                        
                        # Calculate fantasy points based on stat category
                        points = calculate_fantasy_points(stat_name, keys, stats)
                        player_stats[name] += points
                        
                        # Store detailed stats for display
                        detailed_stats = extract_key_stats(stat_name, keys, stats)
                        if detailed_stats:
                            player_detailed_stats[name].update(detailed_stats)
                        
                        print(f"  📊 {name}: +{points} points from {stat_name} (total: {player_stats[name]})")
                        if points == 0:
                            print(f"  ⚠️  Zero points calculated for {name} in {stat_name}")
                            print(f"      Stats array: {stats}")
                            print(f"      Keys array: {keys}")
        
        if games_processed == 0:
            print("No live games available for scoring")
        
        # Process D/ST aggregation - assign team defensive stats to D/ST units
        print(f"\n🛡️ AGGREGATING D/ST STATS:")
        print(f"Available teams with defensive stats: {list(dst_stats.keys())}")
        
        # Use team defensive performance that was extracted during game processing
        print(f"Team defensive performance: {team_defensive_performance}")
        
        for dst_team, team_defensive_stats in dst_stats.items():
            dst_name = f"{dst_team} DST"
            print(f"Creating D/ST player: '{dst_name}'")
            if dst_name not in player_stats:
                player_stats[dst_name] = 0
                player_detailed_stats[dst_name] = {}
            
            # Calculate total D/ST points for this team
            dst_points = 0
            dst_details = {}
            
            # Use team-level defensive stats if available, otherwise fall back to aggregated player stats
            if dst_team in team_defensive_performance:
                team_def_data = team_defensive_performance[dst_team]
                
                # Use team-level stats
                total_sacks = team_def_data.get('sacks', 0)
                total_ints = team_def_data.get('interceptions', 0) 
                total_fum_rec = team_def_data.get('fumbles_recovered', 0)
                total_tds = team_def_data.get('defensive_tds', 0)
                
                print(f"  Using team-level stats for {dst_name}: sacks={total_sacks}, ints={total_ints}, fum_rec={total_fum_rec}, tds={total_tds}")
            else:
                # No team-level stats available
                total_sacks = 0
                total_ints = 0
                total_fum_rec = 0
                total_tds = 0
                
                print(f"  No team-level defensive stats available for {dst_name}")
            
            # Calculate D/ST points
            if total_sacks > 0:
                sack_points = total_sacks * SCORING['dst_sack']
                dst_points += sack_points
                dst_details['sacks'] = total_sacks
                print(f"  {dst_name}: {total_sacks} sacks = {sack_points} points")
                
            if total_ints > 0:
                int_points = total_ints * SCORING['dst_interception']
                dst_points += int_points
                dst_details['ints'] = total_ints
                print(f"  {dst_name}: {total_ints} interceptions = {int_points} points")
                
            if total_fum_rec > 0:
                fum_points = total_fum_rec * SCORING['dst_fumble_rec']
                dst_points += fum_points
                dst_details['fum_rec'] = total_fum_rec
                print(f"  {dst_name}: {total_fum_rec} fumble recoveries = {fum_points} points")
                
            if total_tds > 0:
                td_points = total_tds * SCORING['dst_td']
                dst_points += td_points
                dst_details['tds'] = total_tds
                print(f"  {dst_name}: {total_tds} defensive TDs = {td_points} points")
            
            # Add points allowed scoring
            if dst_team in team_defensive_performance:
                points_allowed = team_defensive_performance[dst_team]['points_allowed']
                points_allowed_score = calculate_dst_points_allowed_score(points_allowed)
                dst_points += points_allowed_score
                dst_details['points_allowed'] = points_allowed
                print(f"  {dst_name}: {points_allowed} points allowed = {points_allowed_score} points")
            else:
                print(f"  {dst_name}: No points allowed data available")
            
            # Add points to the D/ST unit
            player_stats[dst_name] += dst_points
            player_detailed_stats[dst_name].update(dst_details)
            
            if dst_points > 0:
                print(f"  ✅ {dst_name}: Total defensive points = {dst_points}")
            else:
                print(f"  ⚪ {dst_name}: No defensive points scored")
        
        return player_stats, player_detailed_stats
        
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {}, {}

def extract_key_stats(stat_name, keys, stats):
    """Extract key stats for display next to player names."""
    if len(keys) != len(stats):
        print(f"    ⚠️  Key stats extraction - Keys/Stats length mismatch: {len(keys)} keys vs {len(stats)} stats")
        # Don't return empty, continue with processing using available stats
    
    key_stats = {}
    
    try:
        if stat_name == 'passing':
            print(f"  EXTRACTING PASSING KEY STATS:")
            print(f"    Keys: {keys}")
            print(f"    Stats: {stats}")
            for i, key in enumerate(keys):
                if i >= len(stats):
                    print(f"    Index {i} out of range")
                    break
                print(f"    Index {i}: key='{key}', value='{stats[i]}'")
                if key == 'passingYards':
                    key_stats['pass_yds'] = stats[i]
                    print(f"    ✅ Set pass_yds = {stats[i]}")
                elif key == 'passingTouchdowns':
                    key_stats['pass_tds'] = stats[i]
                    print(f"    ✅ Set pass_tds = {stats[i]}")
                elif key == 'interceptions':
                    key_stats['ints'] = stats[i]
                    print(f"    ✅ Set ints = {stats[i]}")
            print(f"    Final key_stats for passing: {key_stats}")
                    
        elif stat_name == 'rushing':
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                if key == 'rushingYards':
                    key_stats['rush_yds'] = stats[i]
                elif key == 'rushingTouchdowns':
                    key_stats['rush_tds'] = stats[i]
                elif key == 'rushingAttempts':
                    key_stats['rush_att'] = stats[i]
                    
        elif stat_name == 'receiving':
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                if key == 'receivingYards':
                    key_stats['rec_yds'] = stats[i]
                elif key == 'receivingTouchdowns':
                    key_stats['rec_tds'] = stats[i]
                elif key == 'receptions':
                    key_stats['rec'] = stats[i]
                elif key == 'receivingTargets':
                    key_stats['targets'] = stats[i]
                    
        elif stat_name == 'kicking':
            fg_made = 0
            ep_made = 0
            print(f"  🦵 EXTRACTING KICKING KEY STATS:")
            print(f"    Keys: {keys}")
            print(f"    Stats: {stats}")
            
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                
                print(f"    Processing key '{key}': {stats[i]}")
                
                if 'fieldGoalsMade' in key:
                    try:
                        # Handle both integer and fraction formats like '3/3'
                        stat_value = stats[i]
                        if '/' in str(stat_value):
                            # Extract the first number from fraction format
                            fg_made += int(str(stat_value).split('/')[0])
                        else:
                            fg_made += int(stat_value)
                    except (ValueError, IndexError):
                        pass
                elif key == 'extraPointsMade' or 'extraPoint' in key:
                    try:
                        stat_value = stats[i]
                        if '/' in str(stat_value):
                            ep_made = int(str(stat_value).split('/')[0])
                        else:
                            ep_made = int(stat_value)
                    except (ValueError, IndexError):
                        pass
                        
            if fg_made > 0:
                key_stats['fg'] = fg_made
                print(f"    ✅ Set fg = {fg_made}")
            if ep_made > 0:
                key_stats['xp'] = ep_made
                print(f"    ✅ Set xp = {ep_made}")
            print(f"    Final kicking key_stats: {key_stats}")
                
        elif stat_name == 'defensive' or stat_name == 'defense':
            print(f"  🛡️ EXTRACTING DEFENSIVE KEY STATS:")
            print(f"    Keys: {keys}")
            print(f"    Stats: {stats}")
            
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                
                print(f"    Processing key '{key}': {stats[i]}")
                
                if key == 'sacks':
                    key_stats['sacks'] = stats[i]
                    print(f"    ✅ Set sacks = {stats[i]}")
                elif key == 'interceptions':
                    key_stats['ints'] = stats[i]
                    print(f"    ✅ Set ints = {stats[i]}")
                elif key == 'fumblesRecovered':
                    key_stats['fum_rec'] = stats[i]
                    print(f"    ✅ Set fum_rec = {stats[i]}")
                elif key == 'defensiveTouchdowns':
                    key_stats['tds'] = stats[i]
                    print(f"    ✅ Set tds = {stats[i]}")
                elif key == 'pointsAllowed':
                    key_stats['pts_allow'] = stats[i]
                    print(f"    ✅ Set pts_allow = {stats[i]}")
                else:
                    print(f"    ➡️  Unknown defensive key: '{key}' = {stats[i]}")
                    
            print(f"    Final defensive key_stats: {key_stats}")
            
        elif stat_name == 'interceptions':
            print(f"  🛡️ EXTRACTING INTERCEPTION KEY STATS:")
            print(f"    Keys: {keys}")
            print(f"    Stats: {stats}")
            
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                
                print(f"    Processing key '{key}': {stats[i]}")
                
                if key == 'interceptions':
                    key_stats['ints'] = stats[i]
                    print(f"    ✅ Set ints = {stats[i]}")
                elif key == 'interceptionTouchdowns':
                    key_stats['tds'] = stats[i]
                    print(f"    ✅ Set tds = {stats[i]}")
                else:
                    print(f"    ➡️  Unknown interception key: '{key}' = {stats[i]}")
                    
            print(f"    Final interception key_stats: {key_stats}")
                    
    except (ValueError, IndexError) as e:
        print(f"Error extracting key stats for {stat_name}: {e}")
        
    return key_stats

def calculate_fantasy_points(stat_name, keys, stats):
    """Calculate fantasy points for a player's stat line."""
    if len(keys) != len(stats):
        print(f"    ⚠️  Keys/Stats length mismatch: {len(keys)} keys vs {len(stats)} stats")
        print(f"    Keys: {keys}")
        print(f"    Stats: {stats}")
        # Don't return 0, continue with processing using the minimum length
    
    points = 0
    
    try:
        if stat_name == 'passing':
            # Keys: ['completions/passingAttempts', 'passingYards', 'yardsPerPassAttempt', 'passingTouchdowns', 'interceptions', ...]
            print(f"  DETAILED PASSING STATS DEBUG:")
            print(f"    Keys array: {keys}")
            print(f"    Stats array: {stats}")
            print(f"    Keys count: {len(keys)}, Stats count: {len(stats)}")
            
            for i, key in enumerate(keys):
                if i >= len(stats):
                    print(f"    Index {i} out of range for stats array")
                    break
                
                print(f"    Processing index {i}: key='{key}', value='{stats[i]}', type={type(stats[i])}")
                    
                if key == 'passingYards':
                    try:
                        yards = float(stats[i])
                        yard_points = yards * SCORING['pass_yds']
                        points += yard_points
                        print(f"    ✅ Passing yards: {yards} * {SCORING['pass_yds']} = {yard_points} points")
                    except (ValueError, TypeError) as e:
                        print(f"    ❌ Error parsing passing yards '{stats[i]}': {e}")
                elif key == 'passingTouchdowns':
                    try:
                        tds = int(stats[i])
                        td_points = tds * SCORING['pass_td']
                        points += td_points
                        print(f"    ✅ Passing TDs: {tds} * {SCORING['pass_td']} = {td_points} points")
                    except (ValueError, TypeError) as e:
                        print(f"    ❌ Error parsing passing TDs '{stats[i]}': {e}")
                elif key == 'interceptions':
                    try:
                        ints = int(stats[i])
                        int_points = ints * SCORING['interception']
                        points += int_points
                        print(f"    ✅ Interceptions: {ints} * {SCORING['interception']} = {int_points} points")
                    except (ValueError, TypeError) as e:
                        print(f"    ❌ Error parsing interceptions '{stats[i]}': {e}")
                elif 'completions' in key.lower() or 'attempts' in key.lower():
                    print(f"    📊 Completions/Attempts field '{key}': {stats[i]}")
                else:
                    print(f"    ➡️  Other field '{key}': {stats[i]}")
                    
            print(f"    Total points from passing: {points}")
                    
        elif stat_name == 'rushing':
            # Keys: ['rushingAttempts', 'rushingYards', 'yardsPerRushAttempt', 'rushingTouchdowns', 'longRushing']
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                    
                if key == 'rushingYards':
                    yards = float(stats[i])
                    points += yards * SCORING['rush_yds']
                elif key == 'rushingTouchdowns':
                    tds = int(stats[i])
                    points += tds * SCORING['rush_td']
                    
        elif stat_name == 'receiving':
            # Keys: ['receptions', 'receivingYards', 'yardsPerReception', 'receivingTouchdowns', 'longReception', 'receivingTargets']
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                    
                if key == 'receptions':
                    receptions = int(stats[i])
                    points += receptions * SCORING['receptions']
                elif key == 'receivingYards':
                    yards = float(stats[i])
                    points += yards * SCORING['rec_yds']
                elif key == 'receivingTouchdowns':
                    tds = int(stats[i])
                    points += tds * SCORING['rec_td']
                    
        elif stat_name == 'fumbles':
            # Keys: ['fumbles', 'fumblesLost', 'fumblesRecovered']
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                    
                if key == 'fumblesLost':
                    fumbles = int(stats[i])
                    points += fumbles * SCORING['fumble']
                    
        elif stat_name == 'kicking':
            # Keys typically include field goals by distance and extra points
            print(f"  🦵 KICKING STATS DEBUG:")
            print(f"    Keys: {keys}")
            print(f"    Stats: {stats}")
            
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                
                print(f"    Processing kicking key '{key}': {stats[i]}")
                    
                if 'fieldGoalsMade' in key:
                    try:
                        stat_value = stats[i]
                        if '/' in str(stat_value):
                            # Extract the first number from fraction format like '3/3'
                            made = int(str(stat_value).split('/')[0])
                        else:
                            made = int(stat_value)
                        
                        print(f"    ✅ Field goals made: {made}")
                    except (ValueError, IndexError):
                        print(f"    ❌ Error parsing field goals: {stats[i]}")
                        continue
                        
                    # Determine distance based on key name
                    if '0-39' in key or 'under40' in key.lower():
                        fg_points = made * SCORING['fg_0_39']
                        points += fg_points
                        print(f"    ✅ FG 0-39 yards: {made} * {SCORING['fg_0_39']} = {fg_points}")
                    elif '40-49' in key:
                        fg_points = made * SCORING['fg_40_49']
                        points += fg_points
                        print(f"    ✅ FG 40-49 yards: {made} * {SCORING['fg_40_49']} = {fg_points}")
                    elif '50' in key or 'over50' in key.lower():
                        fg_points = made * SCORING['fg_50_plus']
                        points += fg_points
                        print(f"    ✅ FG 50+ yards: {made} * {SCORING['fg_50_plus']} = {fg_points}")
                    else:
                        # Default field goal scoring if distance unknown
                        fg_points = made * SCORING['fg_0_39']
                        points += fg_points
                        print(f"    ✅ FG (default): {made} * {SCORING['fg_0_39']} = {fg_points}")
                elif key == 'extraPointsMade' or 'extraPoint' in key:
                    try:
                        stat_value = stats[i]
                        if '/' in str(stat_value):
                            made = int(str(stat_value).split('/')[0])
                        else:
                            made = int(stat_value)
                        
                        ep_points = made * SCORING['extra_point']
                        points += ep_points
                        print(f"    ✅ Extra points made: {made} * {SCORING['extra_point']} = {ep_points}")
                    except (ValueError, IndexError):
                        print(f"    ❌ Error parsing extra points: {stats[i]}")
                        continue
                elif key == 'extraPointsMissed':
                    try:
                        stat_value = stats[i]
                        if '/' in str(stat_value):
                            missed = int(str(stat_value).split('/')[1]) - int(str(stat_value).split('/')[0])
                        else:
                            missed = int(stat_value)
                        
                        ep_miss_points = missed * SCORING['extra_miss']
                        points += ep_miss_points
                        print(f"    ✅ Extra points missed: {missed} * {SCORING['extra_miss']} = {ep_miss_points}")
                    except (ValueError, IndexError):
                        print(f"    ❌ Error parsing extra points missed: {stats[i]}")
                        continue
                else:
                    print(f"    ➡️  Unknown kicking key: '{key}' = {stats[i]}")
            
            print(f"    Total kicking points: {points}")
                    
        elif stat_name == 'defensive' or stat_name == 'defense':
            # D/ST scoring
            print(f"  🛡️ DEFENSIVE STATS DEBUG:")
            print(f"    Keys: {keys}")
            print(f"    Stats: {stats}")
            
            for i, key in enumerate(keys):
                if i >= len(stats):
                    break
                
                print(f"    Processing defensive key '{key}': {stats[i]}")
                    
                if key == 'defensiveTouchdowns':
                    tds = int(stats[i])
                    td_points = tds * SCORING['dst_td']
                    points += td_points
                    print(f"    ✅ Defensive TDs: {tds} * {SCORING['dst_td']} = {td_points}")
                elif key == 'safeties':
                    safeties = int(stats[i])
                    safety_points = safeties * SCORING['dst_safety']
                    points += safety_points
                    print(f"    ✅ Safeties: {safeties} * {SCORING['dst_safety']} = {safety_points}")
                elif key == 'interceptions':
                    ints = int(stats[i])
                    int_points = ints * SCORING['dst_interception']
                    points += int_points
                    print(f"    ✅ Interceptions: {ints} * {SCORING['dst_interception']} = {int_points}")
                elif key == 'fumblesRecovered':
                    fumbles = int(stats[i])
                    fum_points = fumbles * SCORING['dst_fumble_rec']
                    points += fum_points
                    print(f"    ✅ Fumbles recovered: {fumbles} * {SCORING['dst_fumble_rec']} = {fum_points}")
                elif key == 'sacks':
                    sacks = float(stats[i])
                    sack_points = sacks * SCORING['dst_sack']
                    points += sack_points
                    print(f"    ✅ Sacks: {sacks} * {SCORING['dst_sack']} = {sack_points}")
                elif key == 'blockedKicks':
                    blocks = int(stats[i])
                    block_points = blocks * SCORING['dst_block']
                    points += block_points
                    print(f"    ✅ Blocked kicks: {blocks} * {SCORING['dst_block']} = {block_points}")
                elif key == 'pointsAllowed':
                    pts_allowed = int(stats[i])
                    # Points allowed scoring tiers
                    if pts_allowed == 0:
                        pa_points = SCORING['dst_pts_0']
                        points += pa_points
                        print(f"    ✅ Points allowed (0): {SCORING['dst_pts_0']} points")
                    elif pts_allowed <= 6:
                        pa_points = SCORING['dst_pts_1_6']
                        points += pa_points
                        print(f"    ✅ Points allowed (1-6): {pts_allowed} -> {SCORING['dst_pts_1_6']} points")
                    elif pts_allowed <= 13:
                        pa_points = SCORING['dst_pts_7_13']
                        points += pa_points
                        print(f"    ✅ Points allowed (7-13): {pts_allowed} -> {SCORING['dst_pts_7_13']} points")
                    elif pts_allowed <= 20:
                        pa_points = SCORING['dst_pts_14_20']
                        points += pa_points
                        print(f"    ✅ Points allowed (14-20): {pts_allowed} -> {SCORING['dst_pts_14_20']} points")
                    elif pts_allowed <= 27:
                        pa_points = SCORING['dst_pts_21_27']
                        points += pa_points
                        print(f"    ✅ Points allowed (21-27): {pts_allowed} -> {SCORING['dst_pts_21_27']} points")
                    elif pts_allowed <= 34:
                        pa_points = SCORING['dst_pts_28_34']
                        points += pa_points
                        print(f"    ✅ Points allowed (28-34): {pts_allowed} -> {SCORING['dst_pts_28_34']} points")
                    else:
                        pa_points = SCORING['dst_pts_35_plus']
                        points += pa_points
                        print(f"    ✅ Points allowed (35+): {pts_allowed} -> {SCORING['dst_pts_35_plus']} points")
                else:
                    print(f"    ➡️  Unknown defensive key: '{key}' = {stats[i]}")
            
            print(f"    Total defensive points: {points}")
                    
    except (ValueError, IndexError) as e:
        print(f"Error calculating points for {stat_name}: {e}")
        
    return points

@app.route('/')
def index():
    edit_mode = request.args.get('edit', '').lower() == 'true'
    live_data, detailed_stats = get_live_stats()
    
    final_scores = {}
    for user, team_data in teams.items():
        # Handle both old and new team data structures
        if isinstance(team_data, dict) and 'roster' in team_data:
            roster = team_data['roster']
            team_color = team_data.get('color', '#3b82f6')
        else:
            # Old format - convert to new format
            roster = team_data if isinstance(team_data, dict) else {}
            team_color = '#3b82f6'  # Default blue
            teams[user] = {'roster': roster, 'color': team_color}
        
        player_scores = {}
        player_details = {}
        user_total = 0
        
        # Initialize roster structure if not exists
        if not isinstance(roster, dict):
            # Convert old list format to new position-based format
            old_roster = roster if isinstance(roster, list) else []
            roster = {pos: [] for pos in ROSTER_POSITIONS.keys()}
            # Try to place old players in appropriate positions (simplified)
            for i, player in enumerate(old_roster[:sum(ROSTER_POSITIONS.values())]):
                if i == 0: roster['QB'].append(player)
                elif i <= 2: roster['RB'].append(player) 
                elif i <= 4: roster['WR'].append(player)
                elif i == 5: roster['TE'].append(player)
                elif i == 6: roster['DST'].append(player)
                elif i == 7: roster['K'].append(player)
            teams[user]['roster'] = roster
        
        # Calculate scores for all players
        for position, players in roster.items():
            for player in players:
                if isinstance(player, dict):
                    player_name = player['name']
                else:
                    player_name = player
                    
                score = live_data.get(player_name, 0)
                player_scores[player_name] = score
                player_details[player_name] = detailed_stats.get(player_name, {})
                user_total += score
                
        final_scores[user] = {
            "roster": roster,
            "player_scores": player_scores,
            "player_details": player_details,
            "total": user_total,
            "team_color": team_color
        }
    
    # Sort teams by total score (highest first)
    final_scores = dict(sorted(final_scores.items(), key=lambda x: x[1]['total'], reverse=True))
    
    # Get available players organized by position
    all_available_players = get_available_players()
    used_player_names = set()
    for team_data in teams.values():
        roster = team_data.get('roster', {}) if isinstance(team_data, dict) else team_data
        if isinstance(roster, dict):
            for pos_players in roster.values():
                for player in pos_players:
                    player_name = player['name'] if isinstance(player, dict) else player
                    used_player_names.add(player_name)
    
    available_players = {}
    for position, players in all_available_players.items():
        available_players[position] = [
            player for player in players 
            if player['name'] not in used_player_names
        ]
    
    return render_template('index.html', 
                         scores=final_scores, 
                         edit_mode=edit_mode,
                         available_players=available_players,
                         roster_positions=ROSTER_POSITIONS,
                         all_teams=list(teams.keys()))

@app.route('/add_team', methods=['POST'])
def add_team():
    team_name = request.form.get('team_name', '').strip()
    team_color = request.form.get('team_color', '#3b82f6').strip()
    if team_name and team_name not in teams:
        teams[team_name] = {
            'roster': {pos: [] for pos in ROSTER_POSITIONS.keys()},
            'color': team_color
        }
    return redirect('/?edit=true')

@app.route('/settings')
def settings():
    return render_template('settings.html', scoring=SCORING, default_scoring=DEFAULT_SCORING)

@app.route('/update_scoring', methods=['POST'])
def update_scoring():
    global SCORING
    
    try:
        # Update offensive scoring settings from form
        SCORING['pass_td'] = float(request.form.get('pass_td', DEFAULT_SCORING['pass_td']))
        SCORING['rush_td'] = float(request.form.get('rush_td', DEFAULT_SCORING['rush_td']))
        SCORING['rec_td'] = float(request.form.get('rec_td', DEFAULT_SCORING['rec_td']))
        SCORING['pass_yds'] = float(request.form.get('pass_yds', DEFAULT_SCORING['pass_yds']))
        SCORING['rush_yds'] = float(request.form.get('rush_yds', DEFAULT_SCORING['rush_yds']))
        SCORING['rec_yds'] = float(request.form.get('rec_yds', DEFAULT_SCORING['rec_yds']))
        SCORING['receptions'] = float(request.form.get('receptions', DEFAULT_SCORING['receptions']))
        SCORING['fumble'] = float(request.form.get('fumble', DEFAULT_SCORING['fumble']))
        SCORING['interception'] = float(request.form.get('interception', DEFAULT_SCORING['interception']))
        
        # Update kicker scoring settings
        SCORING['fg_0_39'] = float(request.form.get('fg_0_39', DEFAULT_SCORING['fg_0_39']))
        SCORING['fg_40_49'] = float(request.form.get('fg_40_49', DEFAULT_SCORING['fg_40_49']))
        SCORING['fg_50_plus'] = float(request.form.get('fg_50_plus', DEFAULT_SCORING['fg_50_plus']))
        SCORING['fg_miss'] = float(request.form.get('fg_miss', DEFAULT_SCORING['fg_miss']))
        SCORING['extra_point'] = float(request.form.get('extra_point', DEFAULT_SCORING['extra_point']))
        SCORING['extra_miss'] = float(request.form.get('extra_miss', DEFAULT_SCORING['extra_miss']))
        
        # Update D/ST scoring settings
        SCORING['dst_td'] = float(request.form.get('dst_td', DEFAULT_SCORING['dst_td']))
        SCORING['dst_safety'] = float(request.form.get('dst_safety', DEFAULT_SCORING['dst_safety']))
        SCORING['dst_interception'] = float(request.form.get('dst_interception', DEFAULT_SCORING['dst_interception']))
        SCORING['dst_fumble_rec'] = float(request.form.get('dst_fumble_rec', DEFAULT_SCORING['dst_fumble_rec']))
        SCORING['dst_sack'] = float(request.form.get('dst_sack', DEFAULT_SCORING['dst_sack']))
        SCORING['dst_block'] = float(request.form.get('dst_block', DEFAULT_SCORING['dst_block']))
        SCORING['dst_pts_0'] = float(request.form.get('dst_pts_0', DEFAULT_SCORING['dst_pts_0']))
        SCORING['dst_pts_1_6'] = float(request.form.get('dst_pts_1_6', DEFAULT_SCORING['dst_pts_1_6']))
        SCORING['dst_pts_7_13'] = float(request.form.get('dst_pts_7_13', DEFAULT_SCORING['dst_pts_7_13']))
        SCORING['dst_pts_14_20'] = float(request.form.get('dst_pts_14_20', DEFAULT_SCORING['dst_pts_14_20']))
        SCORING['dst_pts_21_27'] = float(request.form.get('dst_pts_21_27', DEFAULT_SCORING['dst_pts_21_27']))
        SCORING['dst_pts_28_34'] = float(request.form.get('dst_pts_28_34', DEFAULT_SCORING['dst_pts_28_34']))
        SCORING['dst_pts_35_plus'] = float(request.form.get('dst_pts_35_plus', DEFAULT_SCORING['dst_pts_35_plus']))
        
        print(f"Updated scoring settings: {SCORING}")
        return redirect('/settings?success=true')
        
    except ValueError as e:
        print(f"Error updating scoring: {e}")
        return redirect('/settings?error=true')

@app.route('/reset_scoring', methods=['POST'])
def reset_scoring():
    global SCORING
    SCORING = DEFAULT_SCORING.copy()
    print("Reset scoring to defaults")
    return redirect('/settings?reset=true')

@app.route('/remove_team', methods=['POST'])
def remove_team():
    team_name = request.form.get('team_name', '').strip()
    if team_name in teams:
        del teams[team_name]
    return redirect('/?edit=true')

@app.route('/add_player', methods=['POST'])
def add_player():
    data = request.get_json()
    team_name = data.get('team_name')
    player_data = data.get('player_data')  # Now expects full player object
    position = data.get('position')
    
    if team_name not in teams:
        return jsonify({'success': False, 'error': 'Team not found'})
    
    # Handle both old and new team data structures
    if isinstance(teams[team_name], dict) and 'roster' in teams[team_name]:
        roster = teams[team_name]['roster']
    else:
        # Convert old format
        roster = {pos: [] for pos in ROSTER_POSITIONS.keys()}
        teams[team_name] = {'roster': roster, 'color': '#3b82f6'}
    
    # Check position limits
    if len(roster.get(position, [])) >= ROSTER_POSITIONS.get(position, 0):
        return jsonify({'success': False, 'error': f'Position {position} is full'})
    
    # Check if player is already on any team
    player_name = player_data['name']
    for existing_team, existing_data in teams.items():
        existing_roster = existing_data.get('roster', {}) if isinstance(existing_data, dict) else existing_data
        if isinstance(existing_roster, dict):
            for pos_players in existing_roster.values():
                for player in pos_players:
                    existing_name = player['name'] if isinstance(player, dict) else player
                    if existing_name == player_name:
                        return jsonify({'success': False, 'error': 'Player already on another team'})
    
    # Add player to roster
    roster[position].append(player_data)
    return jsonify({'success': True})

@app.route('/remove_player_form', methods=['POST'])
def remove_player_form():
    team_name = request.form.get('team_name', '').strip()
    player_name = request.form.get('player_name', '').strip()
    position = request.form.get('position', '').strip()
    
    print(f"Form-based remove player: team={team_name}, player={player_name}, position={position}")
    
    if team_name not in teams:
        print(f"Team '{team_name}' not found")
        return redirect('/?edit=true&error=team_not_found')
    
    # Handle both old and new team data structures
    if isinstance(teams[team_name], dict) and 'roster' in teams[team_name]:
        roster = teams[team_name]['roster']
    else:
        roster = teams[team_name] if isinstance(teams[team_name], dict) else {}
    
    if isinstance(roster, dict) and position in roster:
        # Find and remove the player
        for i, player in enumerate(roster[position]):
            player_check_name = player['name'] if isinstance(player, dict) else player
            if player_check_name == player_name:
                removed_player = roster[position].pop(i)
                print(f"Successfully removed player: {removed_player}")
                return redirect('/?edit=true&success=player_removed')
    
    print(f"Player '{player_name}' not found")
    return redirect('/?edit=true&error=player_not_found')

@app.route('/remove_player', methods=['POST'])
def remove_player():
    data = request.get_json()
    team_name = data.get('team_name')
    player_name = data.get('player_name')
    position = data.get('position')
    
    print(f"Remove player request: team={team_name}, player={player_name}, position={position}")
    print(f"Current teams structure: {teams}")
    
    if team_name not in teams:
        print(f"Team '{team_name}' not found in teams")
        return jsonify({'success': False, 'error': 'Team not found'})
    
    # Handle both old and new team data structures
    if isinstance(teams[team_name], dict) and 'roster' in teams[team_name]:
        roster = teams[team_name]['roster']
    else:
        roster = teams[team_name] if isinstance(teams[team_name], dict) else {}
    
    print(f"Team roster for {team_name}: {roster}")
    
    if isinstance(roster, dict) and position in roster:
        print(f"Position {position} players: {roster[position]}")
        # Find and remove the player
        for i, player in enumerate(roster[position]):
            player_check_name = player['name'] if isinstance(player, dict) else player
            print(f"Checking player {i}: {player_check_name} vs {player_name}")
            if player_check_name == player_name:
                removed_player = roster[position].pop(i)
                print(f"Successfully removed player: {removed_player}")
                return jsonify({'success': True})
    
    print(f"Player '{player_name}' not found in position '{position}' for team '{team_name}'")
    return jsonify({'success': False, 'error': 'Player not found on team'})


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    
    if os.environ.get('RENDER'):
        # Production mode on Render
        print("Starting Fantasy Playoff Scoring App on Render...")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Local development mode
        print("Starting Fantasy Playoff Scoring App...")
        print("Visit http://localhost:5000 to view scores")
        print("Visit http://localhost:5000/?edit=true to edit teams")
        app.run(debug=True, port=port)
