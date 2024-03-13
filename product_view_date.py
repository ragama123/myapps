import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# Streamlit app
st.title('Product Views Analysis')

# File Upload
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

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
