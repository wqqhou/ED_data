import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
import plotly.express as px

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
    plt.title('Figure 1: Total First-Time, Full-Time Undergraduate Enrollment\nat Public 2-Year Colleges (2010 - 2015)', 
              fontsize=14, fontweight='bold', pad=15)
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
    plt.close()

def plot_ny_vs_vt_aid(df, output_dir):
    print("Filtering for NY and VT 2015 data...")

    # Filtering, aggregation, and calculation
    df_2015 = df[(df['year'] == 2015) & (df['stabbr'].isin(['NY', 'VT']))]
    state_totals = df_2015.groupby('stabbr')[['grant_federal', 'enroll_ftug']].sum().reset_index()
    state_totals['per_student_aid'] = state_totals['grant_federal'] / state_totals['enroll_ftug']

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
    plt.title('Figure 2: Average Federal Grant Aid per Student\nNew York vs. Vermont (2015-16)', 
              fontsize=14, fontweight='bold', pad=15)
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
    state_totals = df_2015.groupby('stabbr')[['grant_federal', 'enroll_ftug']].sum().reset_index()
    state_totals['per_student_aid'] = state_totals['grant_federal'] / state_totals['enroll_ftug']
    
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
    ratio_90_10 = stats['90th Percentile'] / stats['10th Percentile']
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
        labels={'per_student_aid': 'Average Aid ($)'},
        title="Figure 3: Average Federal Grant Aid per Student by State (2015-16)"
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

    print("\n--- Task 3: Policy Simulation (Current vs. Proposed) ---")
    
    # Filtering, aggregation, and calculation
    df_2015 = df[df['year'] == 2015].copy()
    df_2015['grant_simulated'] = (1750 * df_2015['enroll_ftug']) + (0.15 * (df_2015['enroll_ftug'] ** 2))
    state_totals = df_2015.groupby('stabbr')[['grant_federal', 'grant_simulated', 'enroll_ftug']].sum().reset_index()
    state_totals['Current System'] = state_totals['grant_federal'] / state_totals['enroll_ftug']
    state_totals['Proposed System'] = state_totals['grant_simulated'] / state_totals['enroll_ftug']

    print(f"{'Statistic':<20} | {'Current System':<15} | {'Proposed System':<15}")
    print("-" * 56)
    
    metrics = ['mean', 'std', 'min', 'max']
    for metric in metrics:
        current_val = state_totals['Current System'].agg(metric)
        proposed_val = state_totals['Proposed System'].agg(metric)
        print(f"{metric.capitalize():<20} | ${current_val:,.2f}{'':<5} | ${proposed_val:,.2f}")
    current_9010 = state_totals['Current System'].quantile(0.9) / state_totals['Current System'].quantile(0.1)
    proposed_9010 = state_totals['Proposed System'].quantile(0.9) / state_totals['Proposed System'].quantile(0.1)
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
    
    print("\nGenerating Spread Comparison Plot...")
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    
    ax = sns.boxplot(
        data=plot_data, 
        x='Allocation Model', 
        y='Per-Student Aid',
        palette=['#95a5a6', '#2ecc71'], 
        width=0.4,
        fliersize=5 
    )
    
    plt.title('Figure 4: Distribution of State Average Per-Student Aid\nCurrent Policy vs. Proposed Change (2015-16)', 
              fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Allocation Framework', fontsize=12, labelpad=10)
    plt.ylabel('State Average Aid per Student ($)', fontsize=12, labelpad=10)
    
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "${:,.0f}".format(x)))
    plt.tight_layout()
    
    # Save the output
    plot_path = os.path.join(output_dir, "figure4_policy_simulation.png")
    plt.savefig(plot_path, dpi=300)
    print(f"Plot successfully saved to: {plot_path}")
    plt.close()

    print("\nGenerating Simulated US Heat Map...")
    
    fig_sim = px.choropleth(
        state_totals,
        locations='stabbr',
        locationmode="USA-states",
        color='Proposed System', 
        scope="usa",
        color_continuous_scale="YlGnBu", 
        labels={'Proposed System': 'Simulated Aid ($)'},
        title="Figure 5: Simulated Federal Grant Aid per Student by State"
    )

    fig_sim.update_layout(
        title_font_size=18,
        title_x=0.5,
        coloraxis_colorbar=dict(title="Simulated Aid per Student")
    )
    
    # Save the output
    plot_path_sim = os.path.join(output_dir, "figure5_simulated_aid_map.png")
    fig_sim.write_image(plot_path_sim, scale=3) 
    print(f"Simulated map successfully saved to: {plot_path_sim}")
    # --- Winners & Losers Dummy Variable Map ---
    
    # 1. Create the dummy variable (1 if budget_impact > 0, 0 otherwise)
    state_totals['winner_dummy'] = (state_totals['budget_impact'] > 0).astype(int)
    
    # Create a clean string label for the map legend based on the dummy
    state_totals['outcome'] = state_totals['winner_dummy'].map({
        1: 'Winner (Net Gain)', 
        0: 'Loser (Net Loss)'
    })
    
    # 2. Generate the Discrete Heat Map
    print("\nGenerating Winners/Losers US Heat Map...")
    fig_winners = px.choropleth(
        state_totals,
        locations='stabbr',
        locationmode="USA-states",
        color='outcome', 
        scope="usa",
        # Force strict discrete colors: Green for 1, Red for 0
        color_discrete_map={
            'Winner (Net Gain)': '#0072B2', 
            'Loser (Net Loss)': '#E69F00'
        }, 
        title="Figure 6: Policy Winners and Losers"
    )
    
    # Adjust layout for the memo
    fig_winners.update_layout(
        title_font_size=18,
        title_x=0.5,
        legend_title_text="Policy Impact"
    )
    
    # 3. Save the final map
    plot_path_winners = os.path.join(output_dir, "figure6_winners_losers_map.png")
    fig_winners.write_image(plot_path_winners, scale=3) 
    print(f"Winners map successfully saved to: {plot_path_winners}")

def main():
    load_dotenv()
    base_path = os.getenv("BASE_PROJECT_PATH")
    data_file = os.path.join(base_path, "data/clean/cleaned_panel.parquet")
    df = pd.read_parquet(data_file)

    figure_folder = input("Figure directory name: ")
    figure_dir = os.path.join(base_path, figure_folder)
    os.makedirs(figure_dir, exist_ok=True)
    
    # Execute all plotting functions
    plot_2yr_public_enrollment(df, figure_dir)
    plot_ny_vs_vt_aid(df, figure_dir)
    state_spread_analysis(df, figure_dir)
    policy_simulation(df, figure_dir)
    
    print("\nAll visualizations complete!")
    #All done: )  hooray!! 

if __name__ == "__main__":
    main()