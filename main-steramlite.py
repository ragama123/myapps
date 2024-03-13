import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import altair as alt
import streamlit_shadcn_ui as ui
from offline_online_data_merg import main as  Offline_Online_Analysis
from Offline_Online_Analysis import main as Offline_Online_Analysis_1
from ai_model_churn_predictive_analysis import main as Churn_Prediction

# Custom CSS for a better-looking UI
st.markdown(
    """
    <style>
    .sidebar .sidebar-content {
        background: linear-gradient(to bottom, #5b86e5, #36d1dc);
        color: white;
    }
    .css-1aumxhk {
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
        padding: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Your logo file path
#logo_path = 'C:/Users/sinmanis/OneDrive - HP Inc/Python/Streamlit/HP Analysis/logo.png'

def welcome_screen():
    st.title("Welcome to HP2B Data Analysis Models")
    # Display your logo
    #st.image(logo_path, width=200)
    st.write("This application provides comprehensive data analytics capabilities. Begin your analysis by selecting an app from the sidebar.")

def last_order_analysis():
    st.title('Last Transaction Analysis')
    #st.markdown("<h1 style='text-align: center; color: black;'>Last Transaction Analysis</h1>", unsafe_allow_html=True)

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], key="Last_Transaction_Analysis")

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

        else:
            st.warning("Please upload a file with the required columns: Date, User: Account Name (v182) (evar182), Last Touch Channel Detail, Orders, Order Value")


def productView_Analysis():
    # Streamlit app
    st.title('Product Views Analysis')

    # File Upload
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], key="Product_Views_Analysis")

    if uploaded_file is not None:
        # Load the data
        df = pd.read_csv(uploaded_file)
        df['Date'] = pd.to_datetime(df['Date'])

        # Filter rows where Product Views is 1
        df_filtered = df[df['Product Views'] == 1]

        # Process the data to identify the last product viewed and calculate total product views
        last_product_views = df_filtered.groupby('User: Account Name (v182) (evar182)').agg({
            'Date': 'max',
            'Product Name (v52) (evar52)': 'last',
            'Product Views': 'sum',
            'catalog_name': 'last',
            'Products': 'last',
            'User: custom_group_id (v145) (evar145)': 'last'
        }).reset_index()

        # Rename the 'Date' column to 'Last Product Viewed Date'
        last_product_views.rename(columns={'Date': 'Last Product Viewed Date'}, inplace=True)

        # Calculate days difference from today
        last_product_views['Days Difference'] = (datetime.now() - last_product_views['Last Product Viewed Date']).dt.days

        # Display the slider for selecting the maximum days difference
        max_days_difference = st.slider('Select Max Days Difference for Product Views:', min_value=0, max_value=365, value=30)

        # Filter the results based on the selected maximum days difference
        filtered_results = last_product_views[last_product_views['Days Difference'] <= max_days_difference]

        # Display the processed data including days difference in the table
        st.write(filtered_results[['User: Account Name (v182) (evar182)',
                                'User: custom_group_id (v145) (evar145)',
                                'Product Name (v52) (evar52)',
                                'catalog_name',
                                'Products',
                                'Last Product Viewed Date',
                                'Days Difference',
                                'Product Views']])

        # Additional information (last product viewed date, total product views, and days difference from today)
        st.subheader('Search for an Account')

        # Search box for Account Name, Group ID, or Catalog Name
        search_term = st.text_input('Enter Account Name, Group ID, or Catalog Name:')
        filtered_accounts = filtered_results[
            (filtered_results['User: Account Name (v182) (evar182)'].str.contains(search_term, case=False)) |
            (filtered_results['User: custom_group_id (v145) (evar145)'].astype(str).str.contains(search_term, case=False)) |
            (filtered_results['catalog_name'].str.contains(search_term, case=False))
        ]

        # Select Account Name from filtered results
        if not filtered_accounts.empty:
            selected_account = st.selectbox('Select Account Name:', filtered_accounts['User: Account Name (v182) (evar182)'])
            # Display Last Product Viewed and Date for the selected Account Name
            account_info = filtered_results[filtered_results['User: Account Name (v182) (evar182)'] == selected_account]
            last_product_date = account_info.iloc[0]["Last Product Viewed Date"]
            days_difference = (datetime.now() - last_product_date).days

            st.write(f'<b>Last Product Viewed:</b> {account_info.iloc[0]["Product Name (v52) (evar52)"]}', unsafe_allow_html=True)
            st.write(f'<b>Last Product:</b> {account_info.iloc[0]["catalog_name"]}', unsafe_allow_html=True)
            st.write(f'<b>Last Product Category:</b> {account_info.iloc[0]["Products"]}', unsafe_allow_html=True)
            st.write(f'<b>Last Product Viewed Date:</b> {last_product_date}', unsafe_allow_html=True)
            st.write(f'<b>Days Difference from Today:</b> {days_difference} days', unsafe_allow_html=True)
            st.write(f'<b>Total Product Views:</b> {account_info.iloc[0]["Product Views"]}', unsafe_allow_html=True)
            st.write(f'<b>User Custom Group ID:</b> {account_info.iloc[0]["User: custom_group_id (v145) (evar145)"]}', unsafe_allow_html=True)

            # Bar chart for days difference ranges
            st.subheader('Days Difference Ranges for Total Product Views')
            days_diff_ranges = [1, 8, 15, 22, max_days_difference + 1]
            labels = [f'{i}-{i+6}' for i in days_diff_ranges[:-1]]
            labels[-1] = f'{days_diff_ranges[-2]}+'

            # Create a new column for days difference ranges in the filtered_results DataFrame
            filtered_results['Days Difference Range'] = pd.cut(filtered_results['Days Difference'], bins=days_diff_ranges, labels=labels)

            # Bar chart
            chart_data = filtered_results.groupby('Days Difference Range')['Product Views'].sum().reset_index()

            # Use Altair for charting
            chart = alt.Chart(chart_data).mark_bar().encode(
                x='Days Difference Range',
                y='Product Views'
            )
            st.altair_chart(chart, use_container_width=True)

            # Additional chart for total product views by account name, sorted by total product views
            st.subheader('Top 20 Accounts by Total Product Views')

            # Get top 20 accounts by total product views and sort by product views
            top_accounts_chart_data = filtered_results.sort_values(by='Product Views', ascending=False).head(20)

            # Use Altair for charting as horizontal bar chart (side bar) and sort account names by product views
            chart_top_accounts = alt.Chart(top_accounts_chart_data).mark_bar().encode(
                y=alt.Y('User\: Account Name \(v182\) \(evar182)', sort='-x'),
                x='Product Views'
            )
            st.altair_chart(chart_top_accounts, use_container_width=True)
        else:
            st.warning('No matching accounts found.')

def checkout_analysis():
    st.title("Checkout Flow Analysis")

    # Upload CSV file
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], key="Checkout_Flow _anlysis")

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

def Assites_manual_Analysis():
    st.title("Assisted & Manual Data Analysis")

    # Upload file
    uploaded_file = st.file_uploader("Upload a file", type=["xlsx", "csv"], key="Assites_Manual_Data_Analysis")

    if uploaded_file is not None:
        # Determine file type
        file_ext = uploaded_file.name.split('.')[-1]

        # Load the data
        if file_ext == 'xlsx':
            df = pd.read_excel(uploaded_file)
        elif file_ext == 'csv':
            df = pd.read_csv(uploaded_file)

        # Convert 'OrderLoadDate' column to datetime format
        if 'OrderLoadDate' in df.columns:
            df['OrderLoadDate'] = pd.to_datetime(df['OrderLoadDate'])

        # Extract Month-Year and create a new column
        if 'OrderLoadDate' in df.columns:
            df['Month-Year'] = df['OrderLoadDate'].dt.strftime('%b %Y')

        # Group by EndCustomerName and calculate the line values
        end_customer_values = df.groupby(['EndCustomerName', 'Market']).agg({
            'Total Line $ Value': 'sum',
            'Customer Segment': 'first',
            'HPOrderNo': 'count'
        }).sort_values(by='Total Line $ Value', ascending=False)

        # Calculate percentage of total orders
        total_orders = df['HPOrderNo'].count()
        end_customer_values['% of Total Orders'] = (end_customer_values['HPOrderNo'] / total_orders) * 100

        # Display all end customers with customer segment, total orders, and % of total orders
        st.write("End Customers by Total Line $ Value:")

        # Allow user to filter by Customer Segment
        selected_customer_segment = st.selectbox('Select Customer Segment', ['All'] + end_customer_values['Customer Segment'].unique().tolist())

        # Apply filter to the entire table
        if selected_customer_segment == 'All':
            filtered_end_customer_values = end_customer_values
        else:
            filtered_end_customer_values = end_customer_values[end_customer_values['Customer Segment'] == selected_customer_segment]

        st.dataframe(filtered_end_customer_values)

        # Group by Market and calculate the line values
        if 'Market' in df.columns:
            market_values = df.groupby('Market').agg({
                'Total Line $ Value': 'sum',
                'HPOrderNo': 'count'
            }).sort_values(by='Total Line $ Value', ascending=False)

            # Display all markets with Total Orders and Total Line $ Value
            st.write("Markets by Total Line $ Value:")
            st.write(market_values)

        # Group by CustomerAssisted and calculate the line values
        if 'CustomerAssisted' in df.columns:
            customer_assisted_values = df.groupby('CustomerAssisted').agg({
                'Total Line $ Value': 'sum',
                'HPOrderNo': 'count'
            })

            # Display all customer assisted values with Total Orders and Total Line $ Value
            st.write("Total Line $ Value by Customer Assisted:")
            st.write(customer_assisted_values)

        # Group by Customer Segment and calculate the line values
        if 'Customer Segment' in df.columns:
            customer_segment_values = df.groupby('Customer Segment').agg({
                'Total Line $ Value': 'sum',
                'HPOrderNo': 'count'
            }).sort_values(by='Total Line $ Value', ascending=False)

            # Calculate percentage of total orders
            customer_segment_values['% of Total Orders'] = (customer_segment_values['HPOrderNo'] / total_orders) * 100

            # Display all customer segments with Total Orders, Total Line $ Value, and % of total orders
            st.write("Customer Segments by Total Line $ Value:")
            st.write(customer_segment_values.rename(columns={'Total Line $ Value': 'Total Line $ Value', 'HPOrderNo': 'Total Orders', 'Total Line $ Value': 'Total Line $ Value', '% of Total Orders': '% of Total Orders'}))

        # Group by Month-Year and calculate the total HPOrderNo
        if 'Month-Year' in df.columns and 'HPOrderNo' in df.columns:
            total_hp_order_by_month = df.groupby('Month-Year').agg({
                'Total Line $ Value': 'sum',
                'HPOrderNo': 'count'
            })

            # Calculate percentage of total orders
            total_hp_order_by_month['% of Total Orders'] = (total_hp_order_by_month['HPOrderNo'] / total_orders) * 100

            # Allow user to select multiple months
            selected_months = st.multiselect('Select Months', total_hp_order_by_month.index.unique().tolist(), default=total_hp_order_by_month.index.unique().tolist())

            # Apply filter to the table based on selected months
            if 'All' in selected_months:
                filtered_total_orders_by_month = total_hp_order_by_month
            else:
                filtered_total_orders_by_month = total_hp_order_by_month.loc[selected_months]

            # Display total orders by month
            st.write("Total Orders by Month:")
            st.write(filtered_total_orders_by_month.rename(columns={'Total Line $ Value': 'Total Line $ Value', 'HPOrderNo': 'Total Orders', '% of Total Orders': '% of Total Orders'}))

            # Group by Quarter and calculate the line values
            total_hp_order_by_month['Quarter'] = pd.to_datetime(total_hp_order_by_month.index).to_period("Q")
            total_orders_by_quarter = total_hp_order_by_month.groupby('Quarter').agg({
                'Total Line $ Value': 'sum',
                'HPOrderNo': 'sum',
                '% of Total Orders': 'mean'
            })

            # Display bar charts for Month by Total Orders and Month by Total Line $ Value
            st.write("Month by Total Orders:")
            chart_total_orders = alt.Chart(filtered_total_orders_by_month.reset_index()).mark_bar().encode(
                x=alt.X('Month-Year:N', sort=list(selected_months)),  # Use list of selected months for sorting
                y='HPOrderNo',
                color='Month-Year'
            ).properties(
                width=600,
                height=300
            )
            st.altair_chart(chart_total_orders, use_container_width=True)

            st.write("Month by Total Line $ Value:")
            chart_total_line_value = alt.Chart(filtered_total_orders_by_month.reset_index()).mark_bar().encode(
                x=alt.X('Month-Year:N', sort=list(selected_months)),  # Use list of selected months for sorting
                y='Total Line $ Value',
                color='Month-Year'
            ).properties(
                width=600,
                height=300
            )
            st.altair_chart(chart_total_line_value, use_container_width=True)

def main():
    # Sidebar navigation
    st.sidebar.title("Analytics Models")
    app_selection = st.sidebar.radio(" ", ["Home", "Last Transaction Analysis", "Product View Analysis", "Checkout Flow Analysis", "Assisted & Manual Data Analysis", "Offline_online_data_merg", "Offline_online_data_analysis", "Churn_Prediction"])

    if app_selection == "Home":
        welcome_screen()
    elif app_selection == "Last Transaction Analysis":
        last_order_analysis()
    elif app_selection == "Product View Analysis":
        productView_Analysis()
    elif app_selection == "Checkout Flow Analysis":
        checkout_analysis()
    elif app_selection == "Assisted & Manual Data Analysis":
        Assites_manual_Analysis()
    elif app_selection == "Offline_online_data_merg":
        Offline_Online_Analysis()
    elif app_selection == "Offline_online_data_analysis":
        Offline_Online_Analysis_1()
    elif app_selection == "Churn_Prediction":
       Churn_Prediction()
if __name__ == "__main__":
    main()
