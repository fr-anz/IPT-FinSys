import pandas as pd

from src.config import CLEANED_DATA_PATH, RAW_DATA_PATH


def clean_dataset(df):
    """Apply the first basic cleaning steps for the starter project."""
    cleaned_df = df.copy()

    cleaned_df.columns = cleaned_df.columns.str.strip()

    # --- Duplicate handling ---
    cleaned_df = cleaned_df.drop_duplicates()
    cleaned_df = cleaned_df.drop_duplicates(subset=["transaction_id"], keep="first")

    # --- Key Integrity Drop ---
    cleaned_df = cleaned_df.dropna(subset=["transaction_id", "date"])

    # --- Date and type conversions ---
    cleaned_df["date"] = pd.to_datetime(cleaned_df["date"], errors="coerce")
    cleaned_df = cleaned_df.dropna(
        subset=["date"]
    )  # Drop if date became NaT from coercion
    cleaned_df["month"] = cleaned_df["date"].dt.to_period("M")

    # Handle blanks before string conversion
    text_cols = [
        "category",
        "payment_method",
        "status",
        "account_type",
        "subcategory",
        "necessity_type",
        "merchant",
    ]
    for col in text_cols:
        cleaned_df[col] = cleaned_df[col].fillna("Unknown")

    # --- Columns standardization ---
    for col in text_cols:
        cleaned_df[col] = cleaned_df[col].astype(str).str.strip()

    # Category mapping
    category_map = {
        "food & dining": "Food & Dining",
        "shopping": "Shopping",
        "entertainment": "Entertainment",
        "utilities": "Utilities",
        "transportation": "Transportation",
        "transport": "Transportation",
        "healthcare": "Healthcare",
        "education": "Education",
        "savings": "Savings",
        "rent": "Rent",
        "others": "Others",
    }
    # Using .fillna('Others') handles anything that didn't match our map
    cleaned_df["category"] = (
        cleaned_df["category"].str.lower().map(category_map).fillna("Others")
    )

    # Payment method mapping
    payment_map = {
        "gcash": "GCash",
        "g-cash": "GCash",
        "maya": "Maya",
        "credit card": "Credit Card",
        "debit card": "Debit Card",
        "bank transfer": "Bank Transfer",
        "bdo online": "BDO Online",
        "cash": "Cash",
    }
    cleaned_df["payment_method"] = (
        cleaned_df["payment_method"].str.lower().map(payment_map).fillna("Cash")
    )

    # Status mapping
    status_map = {
        "paid": "Paid",
        "pending": "Pending",
        "cancelled": "Cancelled",
        "refunded": "Refunded",
    }
    cleaned_df["status"] = cleaned_df["status"].str.lower().map(status_map)

    # --- Numeric Handling & Filling ---
    cleaned_df["budget_limit_php"] = pd.to_numeric(
        cleaned_df["budget_limit_php"], errors="coerce"
    ).fillna(0.0)

    # Safely convert numeric amounts
    cleaned_df["amount_php"] = pd.to_numeric(cleaned_df["amount_php"], errors="coerce")

    # Sets 'Refunded' for entries with negative amount_php and missing status
    cleaned_df.loc[
        (cleaned_df["amount_php"] < 0) & (cleaned_df["status"].isna()), "status"
    ] = "Refunded"

    # If any status mappings resulted to NaN, fallback to 'Paid'
    cleaned_df["status"] = cleaned_df["status"].fillna("Paid")

    # Drops rows with 'Paid' status but no amount value
    cleaned_df = cleaned_df[
        ~(
            (cleaned_df["status"].astype(str).str.upper() == "PAID")
            & (cleaned_df["amount_php"].isna())
        )
    ]

    # Drop any remaining unparseable amount_php rows
    cleaned_df = cleaned_df.dropna(subset=["amount_php"])
    cleaned_df["notes"] = cleaned_df["notes"].fillna("No notes provided")

    # --- Outlier Handling ---
    cleaned_df.loc[
        (cleaned_df["status"] == "Refunded") & (cleaned_df["amount_php"] > 0),
        "amount_php",
    ] = -cleaned_df["amount_php"]

    # Cast categorized items back into strict Pandas categories
    strict_categories = [
        "account_type",
        "category",
        "subcategory",
        "payment_method",
        "necessity_type",
        "status",
    ]
    for cat_col in strict_categories:
        cleaned_df[cat_col] = cleaned_df[cat_col].astype("category")

    # --- Export cleaned dataset ---
    CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(CLEANED_DATA_PATH, index=False)

    return cleaned_df


if __name__ == "__main__":
    raw_df = pd.read_csv(RAW_DATA_PATH)
    cleaned_df = clean_dataset(raw_df)

    print(cleaned_df.head())
    print(cleaned_df.shape)
