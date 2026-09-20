import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from dotenv import load_dotenv
import argparse  
from pathlib import Path
import numpy as np
from analysis_validation import checked_divide

def parse_args():  # Define the command-line options and defaults.
    parser = argparse.ArgumentParser(  
        description="Generate figures and statistics for the original assignment."  
    )  

    parser.add_argument(  # Allow users to override the folder for downloaded ZIP files.
        "--output-dir", default="figure",  
        help="Directory for generated figures (default: figure)"  
    )  

    parser.add_argument(  # Allow users to override the folder for extracted CSV files.
        "--cleaned-dir", default="data/cleaned",  
        help="Directory containing cleaned data (default: data/cleaned)"  
    )  
    args = parser.parse_args()  
    return args  

def plot_2yr_public_enrollment(df, output_dir):

    print("Filtering for public 2-year institutions...")
    two_year_publics = df[
        (df['public'] == 1) & 
        (df['degree_bach'] == 0)
    ].copy()

    print("Generating plot...")
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=two_year_publics, 
        x='year', 
        y='enroll_ftug', 
        estimator='sum',
        errorbar=None,
        marker='o',
        linewidth=2.5,
        color='#2c3e50'
    )
    # Formating
    plt.xlabel('Academic Year', fontsize=12, labelpad=10)
    plt.ylabel('Total Enrolled Students', fontsize=12, labelpad=10)

    # Clean up the ticks and numbers
    plt.xticks(range(2010, 2016)) # Ensure represents discrete nature of data
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x)))) #use comma to make it easier to read
    plt.tight_layout() # just in case

    # Save the output
    os.makedirs(output_dir, exist_ok=True)
    plot_path = os.path.join(output_dir, "figure1_2yr_enrollment.png")
    plt.savefig(plot_path, dpi=300)
    print(f"Success! High-resolution plot saved to: {plot_path}")

    two_year_publics = df[(df['public'] == 1) & (df['degree_bach'] == 0)]
    yearly_totals = two_year_publics.groupby('year')['enroll_ftug'].sum(min_count=1)
    enrollment_2010 = yearly_totals.loc[2010]
    enrollment_2015 = yearly_totals.loc[2015]
    
    percent_change = checked_divide((enrollment_2015 - enrollment_2010), enrollment_2010, label="percent change") * 100

    print("\n--- 2-Year Public Enrollment Decline ---")
    print(f"2010 Total: {enrollment_2010:,.0f} students")
    print(f"2015 Total: {enrollment_2015:,.0f} students")
    print(f"Percentage Change: {percent_change:.2f}%")
    plt.close()

def plot_ny_vs_vt_aid(df, output_dir):
    print("Filtering for NY and VT 2015 data...")

    # Filtering, aggregation, and calculation
    df_2015 = df[(df['year'] == 2015) & (df['stabbr'].isin(['NY', 'VT']))]
    state_totals = df_2015.groupby('stabbr')[['grant_federal', 'enroll_ftug']].sum(min_count=1).reset_index()
    
    state_totals['per_student_aid'] = checked_divide(state_totals['grant_federal'], state_totals['enroll_ftug'], label="per student aid")

    print("Generating plot...")

    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(8, 6))
    ax = sns.barplot(
        data=state_totals, 
        x='stabbr', 
        y='per_student_aid', 
        palette=['#3498db', '#e74c3c'],
        hue='stabbr',
        legend=False
    )
    #Formating
    plt.xlabel('State', fontsize=12, labelpad=10)
    plt.ylabel('Average Aid per Student ($)', fontsize=12, labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "${:,.0f}".format(x)))
    for container in ax.containers:
        ax.bar_label(container, fmt='$%.0f', padding=3, fontsize=11, fontweight='bold')
    plt.tight_layout()
    
    # Save the output
    plot_path = os.path.join(output_dir, "figure2_ny_vt_aid.png")
    plt.savefig(plot_path, dpi=300)
    print(f"Saved: {plot_path}")
    plt.close() 

def state_spread_analysis(df, output_dir):
    print("Filtering for state level data...")
    # Filtering, aggregation, and calculation
    df_2015 = df[df['year'] == 2015].copy()

    state_totals = df_2015.groupby("stabbr")[["grant_federal", "enroll_ftug"]].sum(min_count=1)
    state_totals["per_student_aid"] = checked_divide(state_totals["grant_federal"], state_totals["enroll_ftug"], label="State aid per student")
    state_totals = state_totals.reset_index()

    # Descriptive Statistics
    stats = {
        'Mean': state_totals['per_student_aid'].mean(),
        'Median': state_totals['per_student_aid'].median(),
        'Std Deviation': state_totals['per_student_aid'].std(),
        'Min': state_totals['per_student_aid'].min(),
        'Max': state_totals['per_student_aid'].max(),
        '25th Percentile': state_totals['per_student_aid'].quantile(0.25),
        '75th Percentile': state_totals['per_student_aid'].quantile(0.75),
        '10th Percentile': state_totals['per_student_aid'].quantile(0.10),
        '90th Percentile': state_totals['per_student_aid'].quantile(0.90)
    }
    
    print("\nSummary Statistics for Average Per-Student Aid (2015):")
    for key, value in stats.items():
        print(f"{key}: ${value:,.2f}")
    ratio_90_10 = checked_divide(stats['90th Percentile'], stats['10th Percentile'], label="90/10 aid ratio",)
    print(f"\n90/10 Ratio: {ratio_90_10:.2f}")

    # Heat Map 
    print("\nGenerating US Heat Map...")
    fig = px.choropleth(
        state_totals,
        locations='stabbr',
        locationmode="USA-states",
        color='per_student_aid',
        scope="usa",
        color_continuous_scale="YlGnBu", #colorblind-friendly
        labels={'per_student_aid': 'Average Aid ($)'}
    )
    
    # formating
    fig.update_layout(
        title_font_size=18,
        title_x=0.5, 
        coloraxis_colorbar=dict(title="Aid per Student")
    )
    
    # Save the output
    plot_path = os.path.join(output_dir, "figure3_state_aid_map.png")
    fig.write_image(plot_path, scale=3) 
    print(f"Map successfully saved to: {plot_path}")

def policy_simulation(df, output_dir):

    # Filtering, aggregation, and calculation
    df_2015 = df[df['year'] == 2015].copy()
    df_2015['grant_simulated'] = (1750 * df_2015['enroll_ftug']) + (0.15 * (df_2015['enroll_ftug'] ** 2))
    state_totals = df_2015.groupby('stabbr')[['grant_federal', 'grant_simulated', 'enroll_ftug']].sum(min_count=1).reset_index()
    
    state_totals['Current System'] = checked_divide(state_totals['grant_federal'], state_totals['enroll_ftug'], label="current system state total")
    state_totals['Proposed System'] = checked_divide(state_totals['grant_simulated'],state_totals['enroll_ftug'], label="proposed system state total")

    print(f"{'Statistic':<20} | {'Current System':<15} | {'Proposed System':<15}")
    print("-" * 56)
    
    metrics = ['mean', 'std', 'min', 'max']
    for metric in metrics:
        current_val = state_totals['Current System'].agg(metric)
        proposed_val = state_totals['Proposed System'].agg(metric)
        print(f"{metric.capitalize():<20} | ${current_val:,.2f}{'':<5} | ${proposed_val:,.2f}")
    current_9010 = checked_divide(state_totals['Current System'].quantile(0.9), state_totals['Current System'].quantile(0.1), label="current_9010")
    proposed_9010 = checked_divide(state_totals['Proposed System'].quantile(0.9), state_totals['Proposed System'].quantile(0.1), label="proposed_9010")
    print("-" * 56)
    print(f"{'90/10 Ratio':<20} | {current_9010:.2f}{'':<12} | {proposed_9010:.2f}")
    
    # Calculate the extra spending (budget impact) per state
    state_totals['budget_impact'] = state_totals['grant_simulated'] - state_totals['grant_federal']
    national_extra_cost = state_totals['budget_impact'].sum()
    print("\n--- Policy Budget Impact ---")
    print(f"Total Additional Federal Spending Required: ${national_extra_cost:,.2f}")


    plot_data = pd.melt(
        state_totals, 
        id_vars=['stabbr'], 
        value_vars=['Current System', 'Proposed System'],
        var_name='Allocation Model', 
        value_name='Per-Student Aid'
    )
    print("\nGenerating Simulated US Heat Map...")
    
    fig_sim = px.choropleth(
        state_totals,
        locations='stabbr',
        locationmode="USA-states",
        color='Proposed System', 
        scope="usa",
        color_continuous_scale="YlGnBu", 
        labels={'Proposed System': 'Simulated Aid ($)'}
    )

    fig_sim.update_layout(
        title_font_size=18,
        title_x=0.5,
        coloraxis_colorbar=dict(title="Simulated Aid per Student")
    )
    
    # Save the output
    plot_path_sim = os.path.join(output_dir, "figure4_simulated_aid_map.png")
    fig_sim.write_image(plot_path_sim, scale=3) 
    print(f"Simulated map successfully saved to: {plot_path_sim}")

    print("\nGenerating Spread Comparison Plot...")
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    
    ax = sns.boxplot(
        data=plot_data, 
        x='Allocation Model', 
        y='Per-Student Aid',
        palette=['#95a5a6', '#2ecc71'], 
        width=0.4,
        fliersize=5, 
        hue="Allocation Model",
        legend=False
    )

    plt.xlabel('Allocation Framework', fontsize=12, labelpad=10)
    plt.ylabel('State Average Aid per Student ($)', fontsize=12, labelpad=10)
    
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "${:,.0f}".format(x)))
    plt.tight_layout()
    
    # Save the output
    plot_path = os.path.join(output_dir, "figure5_policy_simulation.png")
    plt.savefig(plot_path, dpi=300)
    print(f"Plot successfully saved to: {plot_path}")
    plt.close()

    #Calculating net gainers and losers
    state_totals["outcome"] = np.select([state_totals["budget_impact"] > 0, state_totals["budget_impact"] < 0], ["Winner (Net Gain)", "Loser (Net Loss)"], default="No Change")
    print("\nGenerating Winners/Losers US Heat Map...")
    fig_winners = px.choropleth(
        state_totals,
        locations='stabbr',
        locationmode="USA-states",
        color='outcome', 
        scope="usa",
        color_discrete_map={ 
            'Winner (Net Gain)': '#0072B2', #Color blind friendly 
            'Loser (Net Loss)': '#E69F00',
            'No Change': '#FFFFFF'
        } 
    )
    
    fig_winners.update_layout(
        title_font_size=18,
        title_x=0.5,
        legend_title_text="Policy Impact"
    )
    #save the output
    plot_path_winners = os.path.join(output_dir, "figure6_winners_losers_map.png")
    fig_winners.write_image(plot_path_winners, scale=3) 
    print(f"Winners map successfully saved to: {plot_path_winners}")

def generate_figures(clean_dir, output_dir):
    data_file = os.path.join(clean_dir, "cleaned_panel.parquet")
    df = pd.read_parquet(data_file)

    os.makedirs(output_dir, exist_ok=True)
    
    plot_2yr_public_enrollment(df, output_dir)
    plot_ny_vs_vt_aid(df, output_dir)
    state_spread_analysis(df, output_dir)
    policy_simulation(df, output_dir)
    
    print("\nAll visualizations complete!")
    #All done: )  hooray!! 

def main():
    load_dotenv()
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    base_path = Path(os.getenv("BASE_PROJECT_PATH", repo_root)).expanduser().resolve()
    clean_dir = base_path / args.cleaned_dir
    output_dir = base_path / args.output_dir
    generate_figures(clean_dir, output_dir)

if __name__ == "__main__":
    main()
