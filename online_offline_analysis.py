import streamlit as st
import pandas as pd
import altair as alt

def top_line_values_analysis():
    st.title("Assisted & Manual Data Analysis")

    # Upload file
    uploaded_file = st.file_uploader("Upload a file", type=["xlsx", "csv"])

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

if __name__ == "__main__":
    top_line_values_analysis()
