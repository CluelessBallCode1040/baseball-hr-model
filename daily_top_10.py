import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import statsapi 
from pybaseball import statcast

def fetch_live_mlb_schedule():
    """Fetches today's live schedule using official MLB API"""
    today = datetime.today().strftime('%Y-%m-%d')
    print(f"Fetching official MLB schedule for {today}...")
    
    try:
        schedule = statsapi.schedule(date=today)
    except Exception as e:
        print(f"Schedule API error: {e}. Defaulting to sample data.")
        return []
        
    live_matchups = []
    for game in schedule:
        if game.get('status') in ['Scheduled', 'Pre-Game']:
            p_home_id = game.get('home_probable_pitcher_id')
            p_away_id = game.get('away_probable_pitcher_id')
            home_team = game.get('home_name', 'Home')
            away_team = game.get('away_name', 'Away')
            game_id = game.get('game_id')
            
            try:
                lineup = statsapi.game_lineup(game_id)
                for batter in lineup.get('away_lineup', []):
                    if p_home_id:
                        live_matchups.append({'batter_id': batter['id'], 'pitcher_id': p_home_id, 'venue': home_team})
                for batter in lineup.get('home_lineup', []):
                    if p_away_id:
                        live_matchups.append({'batter_id': batter['id'], 'pitcher_id': p_away_id, 'venue': away_team})
            except:
                continue
    return live_matchups

def run_advanced_pipeline():
    print("Initiating Advanced Machine Learning Pipeline...")
    
    # 1. Grab Today's Matchups
    todays_games = fetch_live_mlb_schedule()
    
    # 2. Extract Deep Physical Statcast Dimensions (Past 30 Days)
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    print(f"Extracting Statcast dimensions from {start_date} to {end_date}...")
    raw_data = statcast(start_dt=start_date, end_dt=end_date)
    
    # Clean data structure safely
    req_cols = ['launch_speed', 'launch_angle', 'pfx_x', 'pfx_z', 'pitcher', 'batter', 'events']
    raw_data = raw_data.dropna(subset=[c for c in req_cols if c in raw_data.columns])
    
    # Target Metric Construction
    raw_data['is_barrel'] = ((raw_data['launch_speed'] >= 98) & (raw_data['launch_angle'].between(24, 32))).astype(int)
    raw_data['is_hr'] = (raw_data['events'] == 'home_run').astype(int)
    
    # A. Pitcher Movement Profiling
    print("Mapping Pitcher Break Vectors...")
    pitcher_profiles = raw_data.groupby('pitcher').agg(
        avg_pfx_x=('pfx_x', 'mean'),
        avg_pfx_z=('pfx_z', 'mean'),
        allowed_launch_angle=('launch_angle', 'mean')
    )
    
    # B. Batter Launch Angle Profiling
    print("Mapping Hitter Sweet Spots...")
    batter_profiles = raw_data.groupby('batter').agg(
        batter_launch_angle=('launch_angle', 'mean'),
        recent_barrel_rate=('is_barrel', 'mean'),
        recent_hr_rate=('is_hr', 'mean')
    )
    
    # C. Fallback Matrix if live game lineups aren't posted yet
    if not todays_games:
        print("Live game lineups are not published yet today. Generating test matrix...")
        sample_pitchers = pitcher_profiles.index[:10].tolist()
        sample_batters = batter_profiles.index[:10].tolist()
        for i in range(min(len(sample_pitchers), len(sample_batters))):
            todays_games.append({
                'batter_id': sample_batters[i],
                'pitcher_id': sample_pitchers[i],
                'venue': 'Simulated Stadium'
            })

    # 3. Processing Core Loop
    scored_matchups = []
    park_hr_map = {'Coors Field': 1.35, 'Great American Ball Park': 1.25, 'Yankee Stadium': 1.15}
    
    for matchup in todays_games:
        b_id = matchup['batter_id']
        p_id = matchup['pitcher_id']
        venue = matchup['venue']
        
        if p_id in pitcher_profiles.index and b_id in batter_profiles.index:
            pitcher = pitcher_profiles.loc[p_id]
            batter = batter_profiles.loc[b_id]
            
            la_collision = (batter['batter_launch_angle'] * pitcher['allowed_launch_angle']) / 100
            movement_risk = abs(pitcher['avg_pfx_x']) + abs(pitcher['avg_pfx_z'])
            hitter_power = batter['recent_barrel_rate'] * 10
            park_mod = park_hr_map.get(venue, 1.00)
            
            final_score = (hitter_power * la_collision * park_mod) / max(0.5, movement_risk)
            
            try:
                b_name = statsapi.lookup_player(b_id)['fullName']
                p_name = statsapi.lookup_player(p_id)['fullName']
            except:
                b_name = f"Batter ID: {b_id}"
                p_name = f"Pitcher ID: {p_id}"
                
            scored_matchups.append({
                'Date': datetime.today().strftime('%Y-%m-%d'),
                'Batter': b_name,
                'Pitcher': p_name,
                'Stadium': venue,
                'HR_Target_Value': round(final_score, 4)
            })
            
    if scored_matchups:
        top_10 = pd.DataFrame(scored_matchups).sort_values(by='HR_Target_Value', ascending=False).head(10)
        top_10.to_csv('top_10_matchups.csv', index=False)
        print("Advanced Matchup Optimization Complete. csv saved.")
    else:
        print("No active overlapping matches found today.")

if __name__ == "__main__":
    run_advanced_pipeline()
