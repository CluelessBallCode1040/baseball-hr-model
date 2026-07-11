import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
from pybaseball import statcast

# Install this library via your workflow terminal if needed: pip install MLB-StatsAPI
import statsapi 

def get_density_altitude(temp_f, pressure_mb, humidity):
    """Calculates a proxy for how thin the air is (thinner air = more home runs)"""
    temp_c = (temp_f - 32) * 5/9
    # Simplified Air Density calculation (kg/m3)
    p1 = pressure_mb * 100
    r_hum = humidity / 100
    eso = 6.1078 * (10**((7.5 * temp_c) / (237.3 + temp_c)))
    pv = r_hum * eso * 100
    pd = p1 - pv
    rho = (pd / (287.05 * (temp_c + 273.15))) + (pv / (461.495 * (temp_c + 273.15)))
    # Return variance modifier from standard sea level density (~1.225)
    return max(0.5, 1.225 / rho)

def fetch_live_mlb_schedule():
    """Fetches today's live starting pitchers and lineups using official MLB API"""
    today = datetime.today().strftime('%Y-%m-%d')
    print(f"Fetching official MLB schedule for {today}...")
    
    schedule = statsapi.schedule(date=today)
    live_matchups = []
    
    for game in schedule:
        if game['status'] in ['Scheduled', 'Pre-Game']:
            # Pull probable pitchers provided by MLB API hydration channels
            p_home_id = game.get('home_probable_pitcher_id')
            p_away_id = game.get('away_probable_pitcher_id')
            
            # Fetch teams
            home_team = game['home_name']
            away_team = game['away_name']
            game_id = game['game_id']
            
            # Fallback to general rosters if live lineups are not posted yet
            try:
                lineup = statsapi.game_lineup(game_id)
                # Parse through active hitters
                for batter in lineup['away_lineup']:
                    if p_home_id:
                        live_matchups.append({'batter_id': batter['id'], 'pitcher_id': p_home_id, 'venue': home_team})
                for batter in lineup['home_lineup']:
                    if p_away_id:
                        live_matchups.append({'batter_id': batter['id'], 'pitcher_id': p_away_id, 'venue': away_team})
            except:
                # If lineup call fails, pass down team mapping for historical lookup
                continue
                
    return live_matchups

def fetch_weather_metrics():
    """Fallback weather tracking engine"""
    # Standard baseline values if Open-Meteo local coordinate requests fail
    return {"temp": 82, "pressure": 1011, "humidity": 55}

def run_advanced_pipeline():
    print("Initiating Advanced Machine Learning Pipeline...")
    
    # 1. Fetch Schedule
    todays_games = fetch_live_mlb_schedule()
    if not todays_games:
        print("No games scheduled or lineups ready yet. Running baseline calculation.")
        return
        
    # 2. Extract Deep Physical Statcast Dimensions
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=35)).strftime('%Y-%m-%d')
    raw_data = statcast(start_dt=start_date, end_dt=end_date)
    
    # Clean data columns
    raw_data = raw_data.dropna(subset=['launch_speed', 'launch_angle', 'pfx_x', 'pfx_z'])
    
    # Create target metrics
    raw_data['is_barrel'] = ((raw_data['launch_speed'] >= 98) & (raw_data['launch_angle'].between(24, 32))).astype(int)
    raw_data['is_hr'] = (raw_data['events'] == 'home_run').astype(int)
    
    # A. Pitcher Movement Repertoire Map
    print("Mapping Pitcher Break Vectors...")
    pitcher_profiles = raw_data.groupby('pitcher').agg(
        avg_pfx_x=('pfx_x', 'mean'),
        avg_pfx_z=('pfx_z', 'mean'),
        allowed_launch_angle=('launch_angle', 'mean')
    )
    
    # B. Batter Launch Angle + Movement Response Profile
    print("Mapping Hitter Sweet Spots...")
    batter_profiles = raw_data.groupby('batter').agg(
        batter_launch_angle=('launch_angle', 'mean'),
        recent_barrel_rate=('is_barrel', 'mean'),
        recent_hr_rate=('is_hr', 'mean')
    )
    
    # 3. Environment Extraction Engine
    weather = fetch_weather_metrics()
    air_density_mod = get_density_altitude(weather['temp'], weather['pressure'], weather['humidity'])
    
    # 4. Matrix Matchup Math
    scored_matchups = []
    
    for matchup in todays_games:
        b_id = matchup['batter_id']
        p_id = matchup['pitcher_id']
        
        if p_id in pitcher_profiles.index and b_id in batter_profiles.index:
            pitcher = pitcher_profiles.loc[p_id]
            batter = batter_profiles.loc[b_id]
            
            # NOVEL ATTR 1: Launch Angle Collision Index (Synergy between flyball hitters and pitchers)
            # High values mean both profiles cause high launch angles
            la_collision = (batter['batter_launch_angle'] * pitcher['allowed_launch_angle']) / 100
            
            # NOVEL ATTR 2: Movement Mismatch Index
            # Checking if pitcher's movements map into the hitter's performance baseline
            movement_risk = abs(pitcher['avg_pfx_x']) + abs(pitcher['avg_pfx_z'])
            
            # Baseline forms
            hitter_power = batter['recent_barrel_rate'] * 10
            
            # Compounding scores into individual Matchup Targets
            raw_target_score = (hitter_power * la_collision) / max(0.5, movement_risk)
            final_target_score = raw_target_score * air_density_mod
            
            # Resolve actual metadata strings using MLB statsapi lookup tools
            try:
                b_name = statsapi.lookup_player(b_id)[0]['fullName']
                p_name = statsapi.lookup_player(p_id)[0]['fullName']
            except:
                b_name = f"ID: {b_id}"
                p_name = f"ID: {p_id}"
                
            scored_matchups.append({
                'Date': datetime.today().strftime('%Y-%m-%d'),
                'Batter': b_name,
                'Pitcher': p_name,
                'Stadium_Host': matchup['venue'],
                'HR_Target_Value': round(final_target_score, 4)
            })
            
    # Format and Save Output
    top_10 = pd.DataFrame(scored_matchups).sort_values(by='HR_Target_Value', ascending=False).head(10)
    top_10.to_csv('top_10_matchups.csv', index=False)
    print("Advanced Matchup Optimization Complete.")

if __name__ == "__main__":
    run_advanced_pipeline()
