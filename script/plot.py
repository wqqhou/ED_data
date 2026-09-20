"""Generate the assignment figures and reusable, directly linked report results."""

import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import seaborn as sns
from dotenv import load_dotenv

from results_output import calculate_results, save_results


def parse_args():
    parser = argparse.ArgumentParser(description="Generate figures, saved results, and LaTeX macros.")
    parser.add_argument("--output-dir", default="figure", help="Figure directory (default: figure)")
    parser.add_argument("--cleaned-dir", default="data/cleaned", help="Cleaned data directory")
    parser.add_argument("--results-dir", default="results", help="JSON/CSV directory (default: results)")
    parser.add_argument("--tex-results", default="memo/results.tex", help="Generated LaTeX macros (default: memo/results.tex)")
    return parser.parse_args()


def plot_2yr_public_enrollment(yearly_totals, summary, output_dir):
    """Plot the exact annual totals exported in enrollment_by_year.csv."""
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=yearly_totals, x="year", y="enroll_ftug", errorbar=None,
                 marker="o", linewidth=2.5, color="#2c3e50")
    plt.xlabel("Academic Year", fontsize=12, labelpad=10)
    plt.ylabel("Total Enrolled Students", fontsize=12, labelpad=10)
    plt.xticks(yearly_totals["year"])
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"{x:,.0f}"))
    plt.tight_layout()
    plt.savefig(Path(output_dir) / "figure1_2yr_enrollment.png", dpi=300)
    plt.close()
    enrollment = summary["enrollment"]
    print("\n--- Public two-year enrollment ---")
    print(f'2010 total: {enrollment["start"]:,.0f}')
    print(f'2015 total: {enrollment["end"]:,.0f}')
    print(f'Change: {enrollment["change_percent"]:.2f}%')


def plot_ny_vs_vt_aid(state_results, output_dir):
    """Plot the NY/VT rows of the common state-results table."""
    state_totals = state_results.loc[state_results["stabbr"].isin(["NY", "VT"])].copy()
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(8, 6))
    ax = sns.barplot(data=state_totals, x="stabbr", y="per_student_aid",
                     palette=["#3498db", "#e74c3c"], hue="stabbr", legend=False)
    plt.xlabel("State", fontsize=12, labelpad=10)
    plt.ylabel("Average Aid per Student ($)", fontsize=12, labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"${x:,.0f}"))
    for bar_container in ax.containers:
        ax.bar_label(bar_container, fmt="$%.0f", padding=3, fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(Path(output_dir) / "figure2_ny_vt_aid.png", dpi=300)
    plt.close()


def state_spread_analysis(state_results, summary, output_dir):
    """Use the same precomputed statistics as the JSON and memo macros."""
    print("\n--- Current state aid: unweighted cross-state statistics ---")
    for metric, value in summary["current"].items():
        unit = "" if metric == "ratio_90_10" else "$"
        print(f"{metric}: {unit}{value:,.2f}")
    fig = px.choropleth(
        state_results, locations="stabbr", locationmode="USA-states",
        color="per_student_aid", scope="usa", color_continuous_scale="YlGnBu",
        labels={"per_student_aid": "Average Aid ($)"},
    )
    fig.update_layout(title_font_size=18, title_x=0.5,
                      coloraxis_colorbar=dict(title="Aid per Student"))
    fig.write_image(Path(output_dir) / "figure3_state_aid_map.png", scale=3)


def policy_simulation(state_results, summary, output_dir):
    """Visualize the already-computed institutional simulation and state totals."""
    print(f"\n{'Statistic':<20} | {'Current System':<15} | {'Proposed System':<15}")
    for metric in ("mean", "std", "min", "max", "range", "ratio_90_10"):
        unit = "" if metric == "ratio_90_10" else "$"
        print(f'{metric:<20} | {unit}{summary["current"][metric]:,.2f} | '
              f'{unit}{summary["simulated"][metric]:,.2f}')
    print(f'Budget change in retained sample: ${summary["budget"]["change"]:,.2f}')

    fig_sim = px.choropleth(
        state_results, locations="stabbr", locationmode="USA-states",
        color="simulated_aid_per_student", scope="usa", color_continuous_scale="YlGnBu",
        labels={"simulated_aid_per_student": "Simulated Aid ($)"},
    )
    fig_sim.update_layout(title_font_size=18, title_x=0.5,
                          coloraxis_colorbar=dict(title="Simulated Aid per Student"))
    fig_sim.write_image(Path(output_dir) / "figure4_simulated_aid_map.png", scale=3)

    plot_data = state_results.rename(columns={
        "per_student_aid": "Current System",
        "simulated_aid_per_student": "Proposed System",
    }).melt(id_vars="stabbr", value_vars=["Current System", "Proposed System"],
            var_name="Allocation Model", value_name="Per-Student Aid")
    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    ax = sns.boxplot(data=plot_data, x="Allocation Model", y="Per-Student Aid",
                     palette=["#95a5a6", "#2ecc71"], width=0.4, fliersize=5,
                     hue="Allocation Model", legend=False)
    plt.xlabel("Allocation Framework", fontsize=12, labelpad=10)
    plt.ylabel("State Average Aid per Student ($)", fontsize=12, labelpad=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: f"${x:,.0f}"))
    plt.tight_layout()
    plt.savefig(Path(output_dir) / "figure5_policy_simulation.png", dpi=300)
    plt.close()

    fig_change = px.choropleth(
        state_results, locations="stabbr", locationmode="USA-states", color="outcome",
        scope="usa", color_discrete_map={
            "Net increase": "#0072B2", "Net decrease": "#E69F00", "No change": "#FFFFFF",
        },
    )
    fig_change.update_layout(title_font_size=18, title_x=0.5,
                             legend_title_text="Change in grant totals")
    # Keep the original filename so existing figure references do not break.
    fig_change.write_image(Path(output_dir) / "figure6_winners_losers_map.png", scale=3)


def generate_figures(clean_dir, output_dir, results_dir, tex_path):
    data_file = Path(clean_dir) / "cleaned_panel.parquet"
    df = pd.read_parquet(data_file)
    results = calculate_results(df)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Every plot consumes the exact objects that will be exported below.
    plot_2yr_public_enrollment(results["enrollment_by_year"], results["summary"], output_dir)
    plot_ny_vs_vt_aid(results["state_results"], output_dir)
    state_spread_analysis(results["state_results"], results["summary"], output_dir)
    policy_simulation(results["state_results"], results["summary"], output_dir)

    # Do not publish new memo values when a figure-generation step fails.
    save_results(results, results_dir, tex_path, input_file=data_file)
    print("\nAll figures and numerical results complete.")
    return results


def main():
    load_dotenv()
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    base_path = Path(os.getenv("BASE_PROJECT_PATH", repo_root)).expanduser().resolve()
    generate_figures(
        base_path / args.cleaned_dir, base_path / args.output_dir,
        base_path / args.results_dir, base_path / args.tex_results,
    )


if __name__ == "__main__":
    main()
