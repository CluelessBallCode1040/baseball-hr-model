import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from pybaseball import statcast, park_factors

def fetch_and_calculate():
    print("Step 1: Fetching past 30 days of Statcast pitch data...")
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Using small sample range for demonstration/speed on free runners
    raw_data = statcast(start_dt=start_date, end_dt=end_date)
    
    # 2. Pitcher Mix Calculation
    print("Step 2: Calculating pitcher repertoires...")
    mix = raw_data.groupby(['pitcher', 'pitch_type']).size().unstack(fill_value=0)
    pitcher_mixes = mix.div(mix.sum(axis=1), axis=0)
    
    # 3. Batter Profile vs Pitch Types
    print("Step 3: Indexing batter profiles against pitch types...")
    batted_balls = raw_data[raw_data['launch_speed'].notna() & raw_data['launch_angle'].notna()].copy()
    batted_balls['is_barrel'] = ((batted_balls['launch_speed'] >= 98) & 
                                 (batted_balls['launch_angle'].between(26, 30))).astype(int)
    batter_profiles = batted_balls.groupby(['batter', 'pitch_type'])['is_barrel'].mean().unstack(fill_value=0)
    
    # 4. Batter Recency Index (Last 14 Days)
    print("Step 4: Compiling rolling 14-day performance...")
    two_weeks_ago = (datetime.today() - timedelta(days=14)).strftime('%Y-%m-%d')
    recent_data = raw_data[raw_data['game_date'] >= two_weeks_ago].copy()
    recent_data['is_hr'] = (recent_data['events'] == 'home_run').astype(int)
    batter_hot_index = recent_data.groupby('batter')['is_hr'].mean().to_dict()
    
    # 5. Get Live Scheduled Matchups & Weather via open API
    print("Step 5: Simulating today's schedule and weather metrics...")
    # NOTE: In a production app, fetch live daily schedules from the MLB Stats API.
    # We will build a dummy matchup list using existing data IDs for validation:
    sample_pitchers = pitcher_mixes.index[:15].tolist()
    sample_batters = batter_profiles.index[:15].tolist()
    
    venues = ['COL', 'CIN', 'NYY', 'MIA', 'LA', 'CHC', 'BOS', 'TEX']
    todays_games = []
    
    for i in range(10):
        if i < len(sample_pitchers) and i < len(sample_batters):
            todays_games.append({
                'batter_id': sample_batters[i],
                'pitcher_id': sample_pitchers[i],
                'venue': np.random.choice(venues),
                'temp': 78 # Base average game-day temp
            })
            
    # 6. Apply Environmental Factors
    park_hr_map = {'COL': 1.35, 'CIN': 1.25, 'NYY': 1.15, 'MIA': 0.85, 'CHC': 1.05}
    
    # 7. Matchup Processing Core
    print("Step 6: Executing algorithm layers...")
    scored_matchups = []
    for matchup in todays_games:
        b_id = matchup['batter_id']
        p_id = matchup['pitcher_id']
        venue = matchup['venue']
        temp = matchup['temp']
        
        if p_id in pitcher_mixes.index and b_id in batter_profiles.index:
            p_mix = pitcher_mixes.loc[p_id]
            b_profile = batter_profiles.loc[b_id]
            
            # Matchup calculation via dot product
            base_score = np.dot(p_mix, b_profile.reindex(p_mix.index, fill_value=0))
            
            # Apply Hot Streak Multiplier
            hot_modifier = batter_hot_index.get(b_id, 0.02) / 0.02
            hot_modifier = np.clip(hot_modifier, 0.5, 2.0)
            
            # Environmental multipliers
            park_mod = park_hr_map.get(venue, 1.00)
            weather_mod = 1.0 + ((temp - 70) * 0.0025)
            
            final_score = base_score * hot_modifier * park_mod * weather_mod
            
            scored_matchups.append({
                'Date': datetime.today().strftime('%Y-%m-%d'),
                'Batter_ID': b_id,
                'Pitcher_ID': p_id,
                'Venue': venue,
                'HR_Likelihood_Score': round(final_score, 4)
            })
            
    # Sort and Export Top 10 Matchups
    top_10 = pd.DataFrame(scored_matchups).sort_values(by='HR_Likelihood_Score', ascending=False).head(10)
    top_10.to_csv('top_10_matchups.csv', index=False)
    print("Successfully generated and saved top_10_matchups.csv!")

if __name__ == "__main__":
    fetch_and_calculate()
