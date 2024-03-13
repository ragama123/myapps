import streamlit as st
import pandas as pd
import altair as alt

def checkout_analysis():
    st.title("Checkout Flow Analysis")

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is not None:
        # Load the data
        df = pd.read_csv(uploaded_file)

        # Convert 'Month' column to datetime format
        df['Month'] = pd.to_datetime(df['Month'])

        # Extract Month-Year and create a new column
        df['Month-Year'] = df['Month'].dt.strftime('%b %Y')

        # Group by Month-Year
        grouped_data = df.groupby('Month-Year')

        # Calculate aggregated metrics
        agg_data = grouped_data.agg({
            'Product Views': 'sum',
            'Cart Additions': 'sum',
            'Cart Views': 'sum',
            'Cart Removals': 'sum',
            'Checkout Start': 'sum',
            'Orders': 'sum'
        }).reset_index()

        # Calculate Checkout to Order Rate and add a new column (in %)
        agg_data['Checkout to Order Rate (%)'] = (agg_data['Orders'] / agg_data['Checkout Start']) * 100

        # Replace NaN values with 0 in 'Checkout to Order Rate (%)' column
        agg_data['Checkout to Order Rate (%)'].fillna(0, inplace=True)

        # Melt the DataFrame to long format for better Altair usage
        melted_data = pd.melt(agg_data, id_vars=['Month-Year'], var_name='Metric', value_name='Count')

        # Display the Checkout Flow Metrics Over Time chart with legend below the chart
        st.write("Checkout Flow Metrics Over Time:")
        line_chart = alt.Chart(melted_data).mark_line().encode(
            x='Month-Year:T',
            y=alt.Y('Count:Q', title='Count'),
            color='Metric:N',
            tooltip=['Month-Year', 'Metric', 'Count']
        ).properties(
            width=800,
            height=500
        ).configure_legend(
            orient='bottom',    # Change the legend orientation to 'bottom'
            titleOrient='left',  # Change the title orientation to 'left'
        )
        st.altair_chart(line_chart, use_container_width=True)

        # Display the Aggregated Checkout Flow Data table with 'Checkout to Order Rate (%)'
        st.write("Aggregated Checkout Flow Data:")
        st.write(agg_data)

        # Display all accounts data with filter by Month-Year
        st.write("All Accounts Data:")
        all_month_years = ['All'] + df['Month-Year'].unique().tolist()
        selected_month_year = st.selectbox("Select Month-Year", all_month_years)
        
        # Filter data based on selected month
        if selected_month_year != 'All':
            all_accounts_data = df[df['Month-Year'] == selected_month_year]
        else:
            all_accounts_data = df
        
        # Display aggregated data for all accounts including 'User: Account Name' with 'Checkout to Order Rate (%)'
        agg_all_accounts_data = all_accounts_data.groupby('User: Account Name (v182) (evar182)').agg({
            'Product Views': 'sum',
            'Cart Additions': 'sum',
            'Cart Views': 'sum',
            'Cart Removals': 'sum',
            'Checkout Start': 'sum',
            'Orders': 'sum'
        }).reset_index()

        # Calculate Checkout to Order Rate for All Accounts and add a new column (in %)
        agg_all_accounts_data['Checkout to Order Rate (%)'] = (agg_all_accounts_data['Orders'] / agg_all_accounts_data['Checkout Start']) * 100

        # Replace NaN values with 0 in 'Checkout to Order Rate (%)' column
        agg_all_accounts_data['Checkout to Order Rate (%)'].fillna(0, inplace=True)

        # Group 'Checkout to Order Rate (%)' into specified ranges
        bins = [0, 20, 40, 60, 80, 100, float('inf')]
        labels = ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%', '100+%']
        agg_all_accounts_data['Checkout to Order Rate Range'] = pd.cut(agg_all_accounts_data['Checkout to Order Rate (%)'], bins=bins, labels=labels)

        # Display the aggregated data for all accounts with 'Checkout to Order Rate (%)' column
        st.write(agg_all_accounts_data[['User: Account Name (v182) (evar182)', 'Product Views', 'Cart Additions', 'Cart Views', 'Cart Removals', 'Checkout Start', 'Orders', 'Checkout to Order Rate (%)']])

        # Display individual user details
        st.write("Individual User Checkout Flow Details:")
        selected_user = st.selectbox("Select User: Account Name", df['User: Account Name (v182) (evar182)'].unique())

        # Filter the DataFrame for the selected user and aggregate by 'Month-Year'
        user_details_agg = df[df['User: Account Name (v182) (evar182)'] == selected_user].groupby('Month-Year').agg({
            'Product Views': 'sum',
            'Cart Additions': 'sum',
            'Cart Views': 'sum',
            'Cart Removals': 'sum',
            'Checkout Start': 'sum',
            'Orders': 'sum'
        }).reset_index()

        # Calculate Checkout to Order Rate for Individual User and add a new column (in %)
        user_details_agg['Checkout to Order Rate (%)'] = (user_details_agg['Orders'] / user_details_agg['Checkout Start']) * 100

        # Replace NaN values with 0 in 'Checkout to Order Rate (%)' column
        user_details_agg['Checkout to Order Rate (%)'].fillna(0, inplace=True)

        # Display the aggregated individual user details with 'Checkout to Order Rate (%)' column
        st.write(user_details_agg[['Month-Year', 'Product Views', 'Cart Additions', 'Cart Views', 'Cart Removals', 'Checkout Start', 'Orders', 'Checkout to Order Rate (%)']])

        # Display bar chart for 'Checkout to Order Rate (%)' grouped by ranges for all accounts using Account Name count
        st.write("Checkout to Order Rate (%) Grouped by Ranges for All Accounts:")
        bar_chart_all_accounts = alt.Chart(agg_all_accounts_data.dropna(subset=['Checkout to Order Rate Range'])).mark_bar().encode(
            x=alt.X('Checkout to Order Rate Range:N', title='Checkout to Order Rate Range', sort=labels),
            y=alt.Y('count():Q', title='Account Name Count'),
            tooltip=['Checkout to Order Rate Range', 'count()']
        ).properties(
            width=600,
            height=400
        )
        st.altair_chart(bar_chart_all_accounts, use_container_width=True)

if __name__ == "__main__":
    checkout_analysis()
