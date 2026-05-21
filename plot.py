import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

def plot_2yr_public_enrollment(data_path, output_dir):
    print("Loading clean dataset...")
    
    # 1. Load the pristine Parquet file (lightning fast, preserves data types)
    if not os.path.exists(data_path):
        print(f"Error: Could not find {data_path}. Run data_clean.py first.")
        return
        
    df = pd.read_parquet(data_path)

    # 2. Isolate the 2-Year Public Colleges
    print("Filtering for public 2-year institutions...")
    two_year_publics = df[
        (df['public'] == 1) & 
        (df['degree_bach'] == 0)
    ].copy()

    # 3. Set up the visual style
    print("Generating plot...")
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))

    # 4. Create the Line Plot (Summing up total enrollment)
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

    # 5. Format Titles and Axes for professional reporting
    plt.title('Figure 1: Total First-Time, Full-Time Undergraduate Enrollment\nat Public 2-Year Colleges (2010 - 2015)', 
              fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Academic Year', fontsize=12, labelpad=10)
    plt.ylabel('Total Enrolled Students', fontsize=12, labelpad=10)

    # Clean up the ticks and numbers
    plt.xticks(range(2010, 2016))
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    
    plt.tight_layout()

    # 6. Save the output
    os.makedirs(output_dir, exist_ok=True)
    plot_path = os.path.join(output_dir, "figure1_2yr_enrollment.png")
    plt.savefig(plot_path, dpi=300)
    
    print(f"Success! High-resolution plot saved to: {plot_path}")
    plt.show()

def main():
    load_dotenv()
    base_path = os.getenv("BASE_PROJECT_PATH")
    # Define your paths based on the repo structure
    data_file = "./data/clean/cleaned_panel.parquet"

    figure_folder = input("Figure directory name: ")
    figure_dir = os.path.join(base_path, figure_folder)
    os.makedirs(figure_dir, exist_ok=True)
    
    # Execute the plotting function
    plot_2yr_public_enrollment(data_file, figure_dir)

if __name__ == "__main__":
    main()