import streamlit as st
import pandas as pd

def process_file(file, primary_key_column):
    if file:
        df = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file)

        # Ensure primary key column is in numeric format
        df[primary_key_column] = pd.to_numeric(df[primary_key_column], errors='coerce')

        return df.dropna(subset=[primary_key_column])
    else:
        return None

def map_columns(df, mapping):
    # Map columns in the DataFrame based on the provided mapping
    return df.rename(columns=mapping)

def main():
    st.title("Data Matching App")

    st.sidebar.header("Upload Files")
    online_file = st.sidebar.file_uploader("Upload Online File (CSV or Excel)", type=["csv", "xlsx"])
    offline_file = st.sidebar.file_uploader("Upload Offline File (CSV or Excel)", type=["csv", "xlsx"])

    online_primary_key_column = st.sidebar.text_input("Enter Primary Key Column for Online File")
    offline_primary_key_column = st.sidebar.text_input("Enter Primary Key Column for Offline File")

    # Default values for date columns
    online_date_column = "Date"
    offline_date_column = "OrderLoadDate"

    # Add 'Market' column to the offline data
    offline_market_column = "Market"
    if offline_file:
        offline_df = process_file(offline_file, offline_primary_key_column)
        if offline_df is not None and offline_market_column not in offline_df.columns:
            offline_df[offline_market_column] = ""

    if st.sidebar.button("Process Files"):
        if online_file and offline_file and online_primary_key_column and offline_primary_key_column:
            st.success("Files uploaded successfully!")

            online_df = process_file(online_file, online_primary_key_column)
            offline_df = process_file(offline_file, offline_primary_key_column)

            if offline_df is not None and offline_market_column not in offline_df.columns:
                offline_df[offline_market_column] = ""

            if online_df is not None and offline_df is not None:
                try:
                    # Convert date columns to datetime format
                    online_df[online_date_column] = pd.to_datetime(online_df[online_date_column])
                    offline_df[offline_date_column] = pd.to_datetime(offline_df[offline_date_column])

                    # Identify the primary key values that are present in both online and offline files
                    matching_primary_keys = set(online_df[online_primary_key_column]).intersection(offline_df[offline_primary_key_column])

                    # Filter out non-matching primary key values from both online and offline DataFrames
                    online_df = online_df[online_df[online_primary_key_column].isin(matching_primary_keys)]
                    offline_df = offline_df[offline_df[offline_primary_key_column].isin(matching_primary_keys)]

                    # Aggregated data for online table by 'User: mdm_mdcp_id (v150) (evar150)'
                    online_aggregated_data = online_df.groupby('User: mdm_mdcp_id (v150) (evar150)').agg({
                        'Orders': 'sum',
                        'Order Value': 'sum',
                        'User: Account Name (v182) (evar182)': 'first'
                    }).reset_index()

                    # Aggregated data for offline table by 'Sold To Organization_Id'
                    offline_aggregated_data = offline_df.groupby([offline_primary_key_column, offline_market_column]).agg({
                        'Total Line $ Value': 'sum',
                        'HPOrderNo': pd.Series.nunique,  # Unique count of HPOrderNo for total offline orders
                        'Customer Segment': 'first'  # Customer Segment based on offline data
                    }).reset_index()

                    # Monthly orders and order values for online and offline
                    online_monthly_data = online_df.resample('M', on=online_date_column).agg({
                        'Orders': 'sum',
                        'Order Value': 'sum'
                    }).reset_index()

                    offline_monthly_data = offline_df.resample('M', on=offline_date_column).agg({
                        'Total Line $ Value': 'sum',
                        'HPOrderNo': pd.Series.nunique
                    }).reset_index()

                    # Merge tables on the primary key column
                    merged_table = pd.merge(online_aggregated_data, offline_aggregated_data, how='outer',
                                           left_on='User: mdm_mdcp_id (v150) (evar150)', right_on=offline_primary_key_column,
                                           suffixes=('_online', '_offline'))

                    # Summary table
                    total_data_matches = len(matching_primary_keys)
                    total_online_orders = online_aggregated_data['Orders'].sum()
                    total_offline_orders = offline_aggregated_data['HPOrderNo'].sum()  # Unique count of HPOrderNo for total offline orders
                    total_online_order_value = online_aggregated_data['Order Value'].sum()
                    total_offline_order_value = offline_aggregated_data['Total Line $ Value'].sum()

                    summary_table = pd.DataFrame({
                        'Metric': ['Total Data Matches', 'Total Online Orders', 'Total Offline Orders',
                                   'Total Online Order Value', 'Total Offline Order Value'],
                        'Count': [total_data_matches, total_online_orders, total_offline_orders,
                                  total_online_order_value, total_offline_order_value]
                    })

                    # New table for Customer Segment based on offline orders
                    customer_segment_table = offline_aggregated_data.groupby('Customer Segment').agg({
                        'HPOrderNo': 'sum',  # Total offline orders for each Customer Segment
                        'Total Line $ Value': 'sum'  # Total order value for each Customer Segment
                    }).reset_index()

                    # New table for Market based on offline orders
                    market_table = offline_aggregated_data.groupby('Market').agg({
                        'HPOrderNo': 'sum',  # Total offline orders for each Market
                        'Total Line $ Value': 'sum'  # Total order value for each Market
                    }).reset_index()

                    # Monthly tables
                    online_monthly_table = online_monthly_data.rename(columns={'Orders': 'Monthly Online Orders', 'Order Value': 'Monthly Online Order Value'})
                    offline_monthly_table = offline_monthly_data.rename(columns={'HPOrderNo': 'Monthly Offline HPOrderNo', 'Total Line $ Value': 'Monthly Offline Total Line $ Value'})

                    st.write("Merged Table:")
                    st.write(merged_table)

                    st.write("Summary Table:")
                    st.write(summary_table)

                    st.write("Customer Segment Table:")
                    st.write(customer_segment_table)

                    st.write("Market Table:")
                    st.write(market_table)

                    st.write("Monthly Online Orders & Order Value:")
                    st.write(online_monthly_table)

                    st.write("Monthly Offline Total Line $ Value & HPOrderNo:")
                    st.write(offline_monthly_table)

                except KeyError as e:
                    st.error(f"Error: {e}. Please ensure the specified columns exist in the DataFrames.")

            else:
                st.error("Please upload both online and offline files, and provide primary key columns for each.")

if __name__ == "__main__":
    main()
