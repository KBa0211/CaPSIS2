import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "output.db"
FIGURES_DIR = BASE_DIR / "figures"

def run_eda(db_path: Path = DB_PATH) -> Dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found at {db_path}. Run loader.py first.")

    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * FROM earthquakes;", conn)
    finally:
        conn.close()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    logging.info("--- Exploratory Data Analysis (EDA) ---")
    logging.info("Dataset shape: %s", df.shape)
    logging.info("Column data types:\n%s", df.dtypes.to_string())

    num_stats = df[["magnitude", "depth", "latitude", "longitude", "update_delay_minutes", "log10_energy"]].describe().round(3)
    logging.info("Numerical descriptive statistics:\n%s", num_stats.to_string())

    cat_summary = {
        "review_status": df["review_status"].value_counts().to_dict(),
        "severity_class": df["severity_class"].value_counts().to_dict(),
        "depth_zone": df["depth_zone"].value_counts().to_dict(),
        "top_5_networks": df["source_network"].value_counts().head(5).to_dict(),
    }
    logging.info("Categorical summaries: %s", cat_summary)

    grouped_stats = (
        df.groupby("severity_class", as_index=False)
        .agg(
            count=("event_id", "count"),
            avg_magnitude=("magnitude", "mean"),
            avg_depth_km=("depth", "mean"),
            max_magnitude=("magnitude", "max"),
        )
        .round(3)
    )
    logging.info("Grouped analysis by severity_class:\n%s", grouped_stats.to_string(index=False))

    generated_figures = []

    fig1_path = FIGURES_DIR / "magnitude_distribution.png"
    plt.figure(figsize=(9, 5))
    sns.histplot(df["magnitude"], bins=25, kde=True, color="#2b7bba", edgecolor="black", alpha=0.75)
    mean_mag = df["magnitude"].mean()
    median_mag = df["magnitude"].median()
    plt.axvline(mean_mag, color="red", linestyle="--", linewidth=1.8, label=f"Mean ({mean_mag:.2f})")
    plt.axvline(median_mag, color="green", linestyle="-.", linewidth=1.8, label=f"Median ({median_mag:.2f})")
    plt.title("Distribution of Earthquake Magnitudes (USGS Catalog)", fontsize=13, fontweight="bold")
    plt.xlabel("Magnitude", fontsize=11)
    plt.ylabel("Frequency (Number of Events)", fontsize=11)
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig1_path, dpi=150)
    plt.close()
    generated_figures.append(str(fig1_path))

    fig2_path = FIGURES_DIR / "depth_vs_magnitude.png"
    plt.figure(figsize=(9, 5))
    sns.scatterplot(
        data=df,
        x="depth",
        y="magnitude",
        hue="review_status",
        style="depth_zone",
        alpha=0.8,
        s=65,
    )
    plt.title("Earthquake Depth vs. Magnitude by Review Status & Depth Zone", fontsize=13, fontweight="bold")
    plt.xlabel("Depth (km)", fontsize=11)
    plt.ylabel("Magnitude", fontsize=11)
    plt.legend(title="Category", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(fig2_path, dpi=150)
    plt.close()
    generated_figures.append(str(fig2_path))

    fig3_path = FIGURES_DIR / "events_by_network.png"
    top_networks = df["source_network"].value_counts().head(10).reset_index()
    top_networks.columns = ["source_network", "event_count"]
    plt.figure(figsize=(9, 5))
    sns.barplot(data=top_networks, x="event_count", y="source_network", hue="source_network", palette="viridis", legend=False)
    plt.title("Top 10 Seismic Source Networks by Reported Earthquake Count", fontsize=13, fontweight="bold")
    plt.xlabel("Number of Earthquakes", fontsize=11)
    plt.ylabel("Source Network Code", fontsize=11)
    for idx, row in top_networks.iterrows():
        plt.text(row["event_count"] + 0.5, idx, str(row["event_count"]), va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(fig3_path, dpi=150)
    plt.close()
    generated_figures.append(str(fig3_path))

    fig4_path = FIGURES_DIR / "global_seismic_map.png"
    plt.figure(figsize=(10, 5))
    scatter = plt.scatter(
        df["longitude"],
        df["latitude"],
        c=df["magnitude"],
        cmap="YlOrRd",
        s=df["magnitude"].clip(lower=0.5) * 18,
        alpha=0.75,
        edgecolors="black",
        linewidth=0.4,
    )
    cbar = plt.colorbar(scatter)
    cbar.set_label("Magnitude")
    plt.title("Geographic Distribution of Recorded Earthquakes", fontsize=13, fontweight="bold")
    plt.xlabel("Longitude (°)", fontsize=11)
    plt.ylabel("Latitude (°)", fontsize=11)
    plt.xlim(-185, 185)
    plt.ylim(-90, 90)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(fig4_path, dpi=150)
    plt.close()
    generated_figures.append(str(fig4_path))

    logging.info("Generated %d figures in %s", len(generated_figures), FIGURES_DIR)

    return {
        "rows_analyzed": len(df),
        "figures": generated_figures,
        "num_stats": num_stats,
        "cat_summary": cat_summary,
    }

if __name__ == "__main__":
    res = run_eda()
    print(f"EDA complete on {res['rows_analyzed']} rows. Saved figures: {len(res['figures'])}")