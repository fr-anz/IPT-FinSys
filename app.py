import streamlit as st

from src.analysis import get_basic_summary
from src.config import BASE_DATASET_NAME
from src.data_cleaning import clean_dataset
from src.data_loader import dataset_exists, load_raw_dataset, save_cleaned_dataset
from src.insights import generate_placeholder_insights
from src.visualizations import create_sample_chart


st.set_page_config(page_title="Financial Expense Monitoring Dashboard", layout="wide")

st.title("Financial Expense Monitoring Dashboard")

st.write(
    "A minimal Python Streamlit starter dashboard for loading, cleaning, "
    "analyzing, visualizing, and summarizing a financial expenses dataset."
)

st.subheader("Dataset")
st.write(f"Main dataset filename: `{BASE_DATASET_NAME}`")
st.write("Expected location: `data/raw/financial_expenses_dataset_raw.csv`")

raw_df = None
cleaned_df = None

if dataset_exists():
    st.success("Dataset file found.")
    raw_df = load_raw_dataset()
else:
    st.error("Place financial_expenses_dataset_raw.csv inside data/raw/")

st.subheader("Raw Dataset Preview")
if raw_df is None:
    st.info("Raw dataset preview will appear after the CSV file is added.")
else:
    st.dataframe(raw_df.head(), use_container_width=True)
    st.write(f"Rows: `{raw_df.shape[0]}`")
    st.write(f"Columns: `{raw_df.shape[1]}`")

st.subheader("Data Cleaning")
if raw_df is None:
    st.info("Data cleaning will run after the raw dataset is available.")
else:
    cleaned_df = clean_dataset(raw_df)
    st.write("Basic cleaning applied: column names stripped and duplicate rows removed.")
    st.write(f"Rows after basic cleaning: `{cleaned_df.shape[0]}`")
    st.dataframe(cleaned_df.head(), use_container_width=True)

    if st.button("Save Basic Cleaned Dataset"):
        saved_path = save_cleaned_dataset(cleaned_df)
        st.success(f"Cleaned dataset saved to `{saved_path}`")

st.subheader("Data Analysis")
if cleaned_df is None:
    st.info("Analysis results will appear after the dataset is loaded.")
else:
    summary = get_basic_summary(cleaned_df)
    st.write(summary)

st.subheader("Visualizations")
if cleaned_df is None:
    st.info("Visualizations will appear after the dataset is loaded.")
else:
    sample_chart = create_sample_chart(cleaned_df)
    if sample_chart is None:
        st.info("Sample chart requires `category` and `amount_php` columns.")
    else:
        st.pyplot(sample_chart)

st.subheader("Insights and Recommendations")
for insight in generate_placeholder_insights(cleaned_df):
    st.write(f"- {insight}")
