import pandas as pd

from src.config import CLEANED_DATA_PATH, RAW_DATA_PATH


def dataset_exists():
    """Check if the expected raw dataset file exists."""
    return RAW_DATA_PATH.exists()


def load_raw_dataset():
    """Load the raw dataset, or return None if the file is missing."""
    if not dataset_exists():
        return None

    return pd.read_csv(RAW_DATA_PATH)


def save_cleaned_dataset(df):
    """Save the cleaned dataset to the expected cleaned data folder."""
    CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEANED_DATA_PATH, index=False)
    return CLEANED_DATA_PATH
