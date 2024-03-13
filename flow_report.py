import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Function to load and preprocess data from CSV
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        # Dropping rows with missing values
        df.dropna(inplace=True)
        return df
    except pd.errors.ParserError as e:
        st.error(f"Error parsing CSV file: {e}")
        st.stop()

# Function to create a visitor flow report
def create_visitor_flow_report(df):
    try:
        # Grouping data by the flow path and counting occurrences
        flow_counts = df.groupby(['Backstep 1', 'Backstep 2', 'Backstep 3', 'Backstep 4']).size().reset_index(name='Path views')
        return flow_counts
    except KeyError as e:
        st.error(f"KeyError: {e}. Please ensure the CSV file contains the necessary columns.")
        st.stop()

# Streamlit UI
def main():
    st.title('Visitor Flow Report')

    # File upload
    uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])

    if uploaded_file is not None:
        df = load_data(uploaded_file)

        st.write('**Data Preview:**')
        st.write(df.head())

        st.write('---')

        # Creating visitor flow report
        st.write('**Visitor Flow Report:**')
        visitor_flow_report = create_visitor_flow_report(df)
        st.write(visitor_flow_report)

        st.write('---')

        # Plotting visitor flow
        st.write('**Visitor Flow Visualization:**')
        flow_chart = visitor_flow_report.plot(kind='bar', x='Backstep 1', y='Path views', legend=False)
        plt.xticks(rotation=45)
        plt.xlabel('Flow Path')
        plt.ylabel('Path Views')
        plt.title('Visitor Flow')
        st.pyplot()

if __name__ == '__main__':
    main()
