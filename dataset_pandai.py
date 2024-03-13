import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from st_aggrid import GridOptionsBuilder, AgGrid

# Configure API key
GOOGLE_API_KEY = "AIzaSyCUPTiOotHcQzOBcv6m-9aFu9WGrzBl2Y4"
genai.configure(api_key=GOOGLE_API_KEY)

# Function to generate content using GPT-3
def chat_with_csv(df, prompt):
    model = genai.GenerativeModel("gemini-pro")
    chunk_size = 500  # Adjust the chunk size as needed
    chunks = [df.iloc[i:i+chunk_size] for i in range(0, len(df), chunk_size)]
    response_parts = []
    for chunk in chunks:
        data_json = chunk.to_json(orient='records', lines=True)
        prompt_with_data = f"{prompt}\n{data_json}"
        response = model.generate_content(prompt_with_data)
        response_parts.append(response.text)
    return '\n'.join(response_parts)

# Main function
def main():
    st.set_page_config(layout='wide')
    st.title("HP2B Insights Accelerator")

    # File upload
    input_csv = st.file_uploader("Upload your CSV file", type=['csv'])

    if input_csv is not None:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.info("CSV Uploaded Successfully")
            data = pd.read_csv(input_csv)
            gb = GridOptionsBuilder.from_dataframe(data)
            gb.configure_pagination()
            gb.configure_side_bar()
            gb.configure_selection("single")
            gridOptions = gb.build()
            AgGrid(data, gridOptions=gridOptions, width='100%', height=500, theme='streamlit')

        with col2:
            st.info("Chat Below")
            input_text = st.text_area("Enter your query")

            if input_text is not None:
                if st.button("Analyse"):
                    st.info("Your Query: " + input_text)
                    result = chat_with_csv(data, input_text)
                    st.success(result)

        st.subheader("Data Visualization")

        # Display charts for selected columns
        column = st.selectbox("Select a column for visualization:", data.columns)
        if pd.api.types.is_numeric_dtype(data[column]):
            display_histogram(data, column)
        else:
            display_bar_chart(data, column)

# Function to display histogram
def display_histogram(data, column):
    fig = px.histogram(data, x=column, title=f'Histogram of {column}')
    fig.update_traces(marker_color='rgb(55, 83, 109)', marker_line_color='rgb(8,48,107)',
                      marker_line_width=1.5, opacity=0.6)
    fig.update_layout(title_font_family="Arial", title_font_size=20, title_font_color="#2b2b2b",
                      xaxis_title="Value", yaxis_title="Frequency",
                      xaxis=dict(title_font_family="Arial", title_font_size=14, title_font_color="#2b2b2b"),
                      yaxis=dict(title_font_family="Arial", title_font_size=14, title_font_color="#2b2b2b"))
    st.plotly_chart(fig)

# Function to display bar chart
def display_bar_chart(data, column):
    fig = px.bar(data[column].value_counts().reset_index(), x='index', y=column, 
                 title=f'Bar Chart of {column}', labels={'index': column, column: 'Count'})
    fig.update_traces(marker_color='#636efa', marker_line_color='#2a3f5f',
                      marker_line_width=1.5, opacity=0.6)
    fig.update_layout(title_font_family="Arial", title_font_size=20, title_font_color="#2b2b2b",
                      xaxis_title="", yaxis_title="Count",
                      xaxis=dict(title_font_family="Arial", title_font_size=14, title_font_color="#2b2b2b"),
                      yaxis=dict(title_font_family="Arial", title_font_size=14, title_font_color="#2b2b2b"))
    st.plotly_chart(fig)

if __name__ == "__main__":
    main()
