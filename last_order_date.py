import streamlit as st
import pandas as pd
import numpy as np

st.title('Last Transaction Analysis')
#st.markdown("<h1 style='text-align: center; color: black;'>Last Transaction Analysis</h1>", unsafe_allow_html=True)

def assign_cohort(date):
    # Replace with your cohort assignment logic (e.g., monthly cohorts)
    return date.dt.to_period("M").start_time.strftime("%Y-%m")

def analyze_top_channels(data):
    channels_data = data.groupby('Last Touch Channel Detail').agg(
        Total_Order_Value=('Order Value', 'sum'),
        Total_Transactions=('Orders', 'sum'),
        Conversion_Rate=('Orders', 'mean')
    )

    # Sort by total order value (descending)
    top_channels = channels_data.sort_values(by='Total_Order_Value', ascending=False)

    # Display using st.table or st.bar_chart
    st.markdown(f"<h5 style='background-color: #d3d3d3; padding: 4px; color: #808080; font-weight: bold;'>Top-Performing Last Touch Channels (by Total Order Value)</h5>", unsafe_allow_html=True)
    st.table(top_channels)

    # Or, create a bar chart
    # st.bar_chart(top_channels['Total_Order_Value'])

# Upload CSV file
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)

    # Check if all required columns are present
    required_columns = ['Date', 'User: Account Name (v182) (evar182)', 'Last Touch Channel Detail', 'Orders', 'Order Value']
    if all(col in data.columns for col in required_columns):
        # Convert 'Date' column to datetime format
        data['Date'] = pd.to_datetime(data['Date'])

        # Group by account name and calculate last order date, total order value, and total number of transactions
        grouped_data = data.groupby('User: Account Name (v182) (evar182)')
        last_order_date = grouped_data['Date'].max()
        order_value = grouped_data['Order Value'].sum()
        total_transactions = grouped_data.size()

        # Calculate days between last two transactions and previous transaction date
        def calculate_days(row):
            if len(row) >= 2:
                # Sort transactions by date in descending order and remove duplicate dates
                unique_dates = row['Date'].sort_values(ascending=False).dt.date.unique()[:2]
                if len(unique_dates) == 2:
                    return (unique_dates[0] - unique_dates[1]).days, unique_dates[1]
                else:
                    return None, None
            else:
                return None, None

        days_between_transactions, previous_order_date = zip(*grouped_data.apply(calculate_days))

        # Combine the results into a single DataFrame
        result = pd.DataFrame({
            'Last Order Date': last_order_date,
            'Days Between Last Two Transactions': days_between_transactions,
            'Previous Order Date': previous_order_date,
            'Total Order Value': order_value.round().astype(int),  # Rounds to nearest integer without decimals
            'Total Number of Transactions': total_transactions
        }).reset_index()

        # Display the main table without rows where 'Days Between Last Two Transactions' is None
        st.markdown(
            f"<h5 style='background-color: #d3d3d3; padding: 4px; color: #808080; font-weight: bold;'>Days Between Last Two Transactions</h5>",
            unsafe_allow_html=True
        )

        result_without_none = result.dropna(subset=['Days Between Last Two Transactions'])
       

        # Add a range slider for filtering 'Days Between Last Two Transactions'
        min_value = int(result_without_none['Days Between Last Two Transactions'].min())
        max_value = int(result_without_none['Days Between Last Two Transactions'].max())
        slider_value = st.slider("Select a range of days:", min_value, max_value, (0, max_value))
        filtered_result = result_without_none[(result_without_none['Days Between Last Two Transactions'] >= slider_value[0]) & (result_without_none['Days Between Last Two Transactions'] <= slider_value[1])]

        if len(filtered_result) > 0:
            st.write(filtered_result)
            
            # Create a histogram based on the filtered 'Days Between Last Two Transactions'
            st.markdown(
                f"<h5 style='background-color: #d3d3d3; padding: 4px; color: #808080; font-weight: bold;'>Histogram of Days Between Last Two Transactions</h5>",
                unsafe_allow_html=True
            )
            
            bins = [0, 30, 60, 90, float('inf')]
            hist_values, _ = np.histogram(filtered_result['Days Between Last Two Transactions'], bins=bins)

            none_count = len(result[result['Days Between Last Two Transactions'].isnull()])
            hist_values[-1] += none_count

            hist_df = pd.DataFrame({
                'Labels': ['1-30 days', '31-60 days', '61-90 days', '90+ days'],
                'Values': hist_values
            })

            st.bar_chart(hist_df.set_index('Labels'))

        else:
            st.warning("No data in the selected range.")

        # Display accounts with only a single order date
        single_date_accounts = result[result['Days Between Last Two Transactions'].isnull()].groupby('User: Account Name (v182) (evar182)').filter(lambda x: len(x) == 1)['User: Account Name (v182) (evar182)'].unique()
        single_date_rows = result[result['User: Account Name (v182) (evar182)'].isin(single_date_accounts)]
        
        st.markdown(
            f"<h5 style='background-color: #d3d3d3; padding: 4px; color: #808080; font-weight: bold;'>Accounts with Only a Single Order Date</h5>",
            unsafe_allow_html=True
        )
        st.write(single_date_rows.style.set_table_styles(
            [{'selector': 'th', 'props': [('background-color', 'black'), ('color', 'white'), ('font-weight', 'bold')]}]
        ))

        analyze_top_channels(data)

    else:
        st.warning("Please upload a file with the required columns: Date, User: Account Name (v182) (evar182), Last Touch Channel Detail, Orders, Order Value")
