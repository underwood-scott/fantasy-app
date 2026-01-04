#!/usr/bin/env python3

import requests

# Test the roster API endpoint for Detroit Lions
roster_url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/det/roster"
print(f"Testing roster API: {roster_url}")

response = requests.get(roster_url)
print(f"Status code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    
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
    
    players_by_position = {
        'QB': [],
        'RB': [],
        'WR': [], 
        'TE': [],
        'K': [],
        'DST': []
    }
    
    # Process athletes - each group is a position category
    athlete_groups = data.get('athletes', [])
    print(f"\nFound {len(athlete_groups)} position groups")
    
    for athlete_group in athlete_groups:
        group_name = athlete_group.get('position', '')
        players_in_group = athlete_group.get('items', [])
        print(f"\n{group_name.upper()} GROUP ({len(players_in_group)} players):")
        
        for athlete_data in players_in_group:
            player_name = athlete_data.get('displayName', '')
            
            # Get the player's specific position
            position_info = athlete_data.get('position', {})
            position_abbr = position_info.get('abbreviation', '') if position_info else ''
            position_name = position_info.get('name', '') if position_info else ''
            
            # Map ESPN positions to our position system
            mapped_position = POSITION_MAPPING.get(position_abbr, None)
            
            print(f"  {player_name} - {position_name} ({position_abbr}) -> {mapped_position}")
            
            if mapped_position and mapped_position in players_by_position and player_name:
                if mapped_position != 'DST':
                    players_by_position[mapped_position].append({
                        'name': player_name,
                        'team': 'DET',
                        'position': mapped_position
                    })
    
    print(f"\n=== FINAL RESULTS ===")
    for pos, players in players_by_position.items():
        print(f"{pos}: {len(players)} players")
        for player in players[:3]:  # Show first 3 players
            print(f"  - {player['name']}")
        if len(players) > 3:
            print(f"  ... and {len(players) - 3} more")

else:
    print(f"Failed to get roster: {response.status_code}")
    print(response.text[:500])