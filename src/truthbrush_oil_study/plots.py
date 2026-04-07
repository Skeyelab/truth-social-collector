from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


sns.set_theme(style="whitegrid")


def plot_abnormal_returns(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=df, x="topic", y="abnormal_return", ax=ax)
    ax.set_title("Abnormal returns by post topic")
    ax.set_xlabel("Topic")
    ax.set_ylabel("Abnormal return")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path
