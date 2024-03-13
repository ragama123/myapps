import streamlit as st
import pandas as pd
import altair as alt
import matplotlib.pyplot as plt
import seaborn as sns

# Load Data Function
def load_data(file_path, file_type):
    try:
        if file_type == "csv":
            data = pd.read_csv(file_path)
        elif file_type == "xlsx":
            data = pd.read_excel(file_path)
        else:
            st.error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None
        return data
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Create Online Summary Table by User and Account
def create_online_summary(online_data):
    necessary_columns = ['User: mdm_mdcp_id (v150) (evar150)', 'User: Account Name (v182) (evar182)', 'Orders', 'Order Value']
    if online_data is not None and all(column in online_data.columns for column in necessary_columns):
        online_summary = online_data.groupby(['User: mdm_mdcp_id (v150) (evar150)', 'User: Account Name (v182) (evar182)']).agg({
            'Orders': 'sum',
            'Order Value': 'sum'
        }).reset_index()
        return online_summary
    else:
        st.warning("Necessary columns are missing in the online dataset. Please check the file.")
        return None

# Create Online Monthly Summary Table
def create_monthly_summary(online_data):
    necessary_columns = ['User: mdm_mdcp_id (v150) (evar150)', 'Orders', 'Order Value', 'Date']
    if online_data is not None and all(column in online_data.columns for column in necessary_columns):
        online_data['Date'] = pd.to_datetime(online_data['Date'])
        monthly_summary = online_data.groupby([online_data['Date'].dt.to_period("M")]).agg({
            'Orders': 'sum',
            'Order Value': 'sum'
        }).reset_index()

        # Format the period index to display month names
        monthly_summary['Date'] = monthly_summary['Date'].dt.to_timestamp()
        monthly_summary['Month'] = monthly_summary['Date'].dt.strftime('%B %Y')
        monthly_summary.drop('Date', axis=1, inplace=True)

        return monthly_summary
    else:
        st.warning("Necessary columns are missing in the online dataset for monthly summary. Please check the file.")
        return None

# Create Offline Summary Table by User and Account
def create_offline_summary(offline_data):
    necessary_columns_offline = ['Sold To Organization_Id', 'EndCustomerName', 'HPOrderNo', 'TotalLineValue']
    if offline_data is not None and all(column in offline_data.columns for column in necessary_columns_offline):
        offline_summary = offline_data.groupby(['Sold To Organization_Id', 'EndCustomerName']).agg({
            'HPOrderNo': 'nunique',  # unique count of 'HPOrderNo'
            'TotalLineValue': 'sum'
        }).reset_index()
        return offline_summary
    else:
        st.warning("Necessary columns are missing in the offline dataset. Please check the file.")
        return None

# Create Online Summary Table by User and Account for Offline Data
def create_online_summary_offline(offline_data):
    necessary_columns_offline = ['User: mdm_mdcp_id (v150) (evar150)', 'User: Account Name (v182) (evar182)', 'Orders', 'Order Value']
    if offline_data is not None and all(column in offline_data.columns for column in necessary_columns_offline):
        online_summary_offline = offline_data.groupby(['User: mdm_mdcp_id (v150) (evar150)', 'User: Account Name (v182) (evar182)']).agg({
            'Orders': 'sum',
            'Order Value': 'sum'
        }).reset_index()
        return online_summary_offline
    else:
        st.warning("Necessary columns are missing in the offline dataset for online summary. Please check the file.")
        return None

# Create Another Offline Summary Table by User and Account
def create_offline_summary_user_account(offline_data):
    necessary_columns_offline = ['Sold To Organization_Id', 'EndCustomerName', 'HPOrderNo', 'Total Line $ Value']
    if offline_data is not None and all(column in offline_data.columns for column in necessary_columns_offline):
        offline_summary_user_account = offline_data.groupby(['Sold To Organization_Id', 'EndCustomerName']).agg({
            'HPOrderNo': 'nunique',  # unique count of 'HPOrderNo'
            'Total Line $ Value': 'sum'
        }).reset_index()
        return offline_summary_user_account
    else:
        st.warning("Necessary columns are missing in the offline dataset for another summary. Please check the file.")
        return None

# Create Monthly Summary Table for Offline Data
def create_monthly_summary_offline(offline_data):
    necessary_columns_offline = ['OrderLoadDate', 'HPOrderNo', 'Total Line $ Value']
    if offline_data is not None and all(column in offline_data.columns for column in necessary_columns_offline):
        offline_data['OrderLoadDate'] = pd.to_datetime(offline_data['OrderLoadDate'])
        monthly_summary_offline = offline_data.groupby([offline_data['OrderLoadDate'].dt.to_period("M")]).agg({
            'HPOrderNo': 'nunique',  # unique count of 'HPOrderNo'
            'Total Line $ Value': 'sum'
        }).reset_index()

        # Format the period index to display month names
        monthly_summary_offline['OrderLoadDate'] = monthly_summary_offline['OrderLoadDate'].dt.to_timestamp()
        monthly_summary_offline['Month'] = monthly_summary_offline['OrderLoadDate'].dt.strftime('%B %Y')
        monthly_summary_offline.drop('OrderLoadDate', axis=1, inplace=True)

        return monthly_summary_offline
    else:
        st.warning("Necessary columns are missing in the offline dataset for monthly summary. Please check the file.")
        return None

# Streamlit App
def main():
    st.title("Data Summary App")

    # Upload Online Dataset
    st.sidebar.header("Online Dataset")
    online_file = st.sidebar.file_uploader("Upload Online Dataset (CSV or XLSX)", type=["csv", "xlsx"])
    online_file_type = "csv" if online_file is not None and online_file.name.endswith('.csv') else "xlsx"
    if online_file is not None:
        online_data = load_data(online_file, online_file_type)

        # Display Online Data
        st.subheader("Online Data")
        st.dataframe(online_data)

        # Create Online Summary Table by User and Account
        online_summary = create_online_summary(online_data)
        if online_summary is not None:
            st.subheader("Online Summary Table by User and Account")
            st.dataframe(online_summary)

        # Create Monthly Summary Table for Online Data
        monthly_summary = create_monthly_summary(online_data)
        if monthly_summary is not None:
            st.subheader("Monthly Summary Table for Online Data")
            st.dataframe(monthly_summary)

    # Upload Offline Dataset
    st.sidebar.header("Offline Dataset")
    offline_file = st.sidebar.file_uploader("Upload Offline Dataset (CSV or XLSX)", type=["csv", "xlsx"])
    offline_file_type = "csv" if offline_file is not None and offline_file.name.endswith('.csv') else "xlsx"
    if offline_file is not None:
        offline_data = load_data(offline_file, offline_file_type)

        # Display Offline Data
        st.subheader("Offline Data")
        st.dataframe(offline_data)

        # Create Offline Summary Table by User and Account
        offline_summary = create_offline_summary(offline_data)
        if offline_summary is not None:
            st.subheader("Offline Summary Table by User and Account")
            st.dataframe(offline_summary)

        # Create Online Summary Table by User and Account for Offline Data
        online_summary_offline = create_online_summary_offline(offline_data)
        if online_summary_offline is not None:
            st.subheader("Online Summary Table by User and Account for Offline Data")
            st.dataframe(online_summary_offline)

        # Create Another Offline Summary Table by User and Account
        offline_summary_user_account = create_offline_summary_user_account(offline_data)
        if offline_summary_user_account is not None:
            st.subheader("Another Offline Summary Table by User and Account")
            st.dataframe(offline_summary_user_account)

        # Create Monthly Summary Table for Offline Data
        monthly_summary_offline = create_monthly_summary_offline(offline_data)
        if monthly_summary_offline is not None:
            st.subheader("Monthly Summary Table for Offline Data")
            st.dataframe(monthly_summary_offline)

        # Bar Chart: Online Total Orders vs Offline Unique Count of HPOrderNo by Month
        st.subheader("Comparison of Online Total Orders vs Offline Unique Count of HPOrderNo by Month")
        plot_comparison_bar_chart(monthly_summary, monthly_summary_offline, 'Orders', 'HPOrderNo')

        # Bar Chart: Online Total Order Value vs Offline Total Line $ Value by Month
        st.subheader("Comparison of Online Total Order Value vs Offline Total Line $ Value by Month")
        plot_comparison_bar_chart(monthly_summary, monthly_summary_offline, 'Order Value', 'Total Line $ Value')


def plot_comparison_bar_chart(online_data, offline_data, online_column, offline_column):
    # Combine Online and Offline Monthly Summaries for Visualization
    combined_summary = pd.merge(online_data, offline_data, how='outer', on='Month', suffixes=('_online', '_offline'))

    # Plot the Bar Chart
    plt.figure(figsize=(12, 6))
    sns.barplot(x='Month', y=online_column, data=combined_summary, label=f'Online {online_column}', color='blue')
    sns.barplot(x='Month', y=offline_column, data=combined_summary, label=f'Offline {offline_column}', color='orange')
    plt.title(f"Comparison of Online {online_column} vs Offline {offline_column} by Month")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    st.pyplot(plt)

def plot_vertical_bar_chart(data, column, top_n=20):
    # Sort data by the specified column in descending order and select top N records
    data_sorted = data.sort_values(by=column, ascending=False).head(top_n)

    # Plot the Vertical Bar Chart
    plt.figure(figsize=(10, 6))
    sns.barplot(x=data_sorted[column], y=data_sorted.index, data=data_sorted, palette='viridis')
    plt.title(f"Top {top_n} Customers by {column}")
    plt.xlabel(column)
    plt.ylabel("Customer")
    plt.tight_layout()

    # Display the Bar Chart
    st.subheader(f"Top {top_n} Customers by {column}")
    st.pyplot(plt)

# Streamlit App (Continued)
if __name__ == "__main__":
    main()