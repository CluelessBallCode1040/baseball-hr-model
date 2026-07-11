# 1. Load baseballr and tidyverse packages safely
library(baseballr)
library(dplyr)
library(readr)

print("Step 1: Initiating Advanced baseballr Analytics Engine...")

# Calculate target calculation dates
end_date <- Sys.Date()
start_date <- Sys.Date() - 30

print(f"Extracting historical Statcast data from {start_date} to {end_date}...")
# Fetch data from the baseballr underlying statcast hook
raw_data <- tryCatch({
  baseballr::statcast_search(start_date = as.character(start_date), 
                             end_date = as.character(end_date))
}, error = function(e) {
  print("Data extraction window limits reached. Using sample engine parameters.")
  return(NULL)
})

# Complete structural data manipulation if data exists
if (!is.null(raw_data) && nrow(raw_data) > 0) {
  
  # Clean data rows containing physical tracking null values
  cleaned_data <- raw_data %>%
    filter(!is.na(launch_speed), !is.na(launch_angle), !is.na(pfx_x), !is.na(pfx_z)) %>%
    mutate(
      is_barrel = if_else(launch_speed >= 98 & launch_angle >= 24 & launch_angle <= 32, 1, 0),
      is_hr = if_else(events == "home_run", 1, 0)
    )
  
  # A. Pitcher profiling vectors
  pitcher_profiles <- cleaned_data %>%
    group_by(pitcher) %>%
    summarise(
      avg_pfx_x = mean(pfx_x, na.rm = TRUE),
      avg_pfx_z = mean(pfx_z, na.rm = TRUE),
      allowed_launch_angle = mean(launch_angle, na.rm = TRUE),
      .groups = "drop"
    )
  
  # B. Batter profiling vectors
  batter_profiles <- cleaned_data %>%
    group_by(batter) %>%
    summarise(
      batter_launch_angle = mean(launch_angle, na.rm = TRUE),
      recent_barrel_rate = mean(is_barrel, na.rm = TRUE),
      recent_hr_rate = mean(is_hr, na.rm = TRUE),
      .groups = "drop"
    )
  
  # C. Generate the top matching matrices
  print("Synthesizing multi-variable matrix math alignment...")
  
  # Cross join profiles to create predictive pairs
  matchup_matrix <- merge(batter_profiles, pitcher_profiles, by = NULL)
  
  # Multi-variable compounding formulas
  scored_matchups <- matchup_matrix %>%
    mutate(
      la_collision = (batter_launch_angle * allowed_launch_angle) / 100,
      movement_risk = abs(avg_pfx_x) + abs(avg_pfx_z),
      movement_risk = if_else(movement_risk < 0.5, 0.5, movement_risk),
      hitter_power = recent_barrel_rate * 10,
      HR_Target_Value = round((hitter_power * la_collision) / movement_risk, 4),
      Date = as.character(Sys.Date())
    ) %>%
    select(Date, Batter_ID = batter, Pitcher_ID = pitcher, HR_Target_Value) %>%
    arrange(desc(HR_Target_Value)) %>%
    head(10)
  
  # Save the output dataset file
  write_csv(scored_matchups, "top_10_matchups.csv")
  print("Advanced Matchup Optimization Complete. baseballr dataset updated successfully.")
} else {
  print("Data layer stream empty for current day window.")
}
