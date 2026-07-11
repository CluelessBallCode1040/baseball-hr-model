name: Daily HR Model Refresh (baseballr)

on:
  schedule:
    - cron: '0 13 * * *' # Runs daily at 9:00 AM Eastern Time
  workflow_dispatch: # Allows manual button executions

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Repository Code
      uses: actions/checkout@v4

    - name: Set up R Environment
      uses: r-lib/actions/setup-r@v2
      with:
        r-version: 'release'

    - name: Install System Dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y libcurl4-openssl-dev libssl-dev libxml2-dev

    - name: Install baseballr and pak Package Manager
      run: |
        Rscript -e "if (!requireNamespace('pak', quietly = TRUE)){ install.packages('pak') }"
        Rscript -e "pak::pak(c('BillPetti/baseballr', 'tidyverse/dplyr', 'tidyverse/readr'))"

    - name: Execute baseballr Model Script
      run: Rscript daily_top_10.R

    - name: Commit and Save Daily Results
      run: |
        git config --global user.name 'GitHub Actions Bot'
        git config --global user.email 'actions@github.com'
        git add top_10_matchups.csv
        git commit -m "Automated Daily baseballr Update: $(date +'%Y-%m-%d')" || exit 0
        git push
