def clean_dataset(df):
    """Apply the first basic cleaning steps for the starter project."""
    cleaned_df = df.copy()

    cleaned_df.columns = cleaned_df.columns.str.strip()
    cleaned_df = cleaned_df.drop_duplicates()

    # TODO Dev 3: Add missing value handling.
    # TODO Dev 3: Standardize inconsistent entries.
    # TODO Dev 3: Convert columns to correct data types.
    # TODO Dev 3: Add outlier handling.
    # TODO Dev 3: Expand cleaned dataset export rules.

    return cleaned_df
