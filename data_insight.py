import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
from reportlab.pdfgen import canvas
import base64  # Add this import
from io import BytesIO
from st_aggrid import AgGrid
from fpdf import FPDF
from streamlit_lottie import st_lottie
from IPython.display import JSON
import json
import requests

st.set_page_config(layout='wide')

def load_lottiefile(url: str):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to load Lottie file from URL: {url}. Status code: {response.status_code}")
# Configure API key
GOOGLE_API_KEY = "AIzaSyCUPTiOotHcQzOBcv6m-9aFu9WGrzBl2Y4"
genai.configure(api_key=GOOGLE_API_KEY)

# Expanded list of personas
persona_mapping = {
    'Marketing Manager': 'marketing_manager',
    'Chief Marketing Officer (CMO)': 'cmo',
    'Sales Executive': 'sales_executive',
    'Data Analyst': 'data_analyst',
    'Software Developer': 'software_developer',
    'Human Resources Manager': 'hr_manager',
    'Financial Analyst': 'financial_analyst',
    'Customer Support Representative': 'customer_support_rep',
    'Product Manager': 'product_manager',
    'Graphic Designer': 'graphic_designer'
}

# Placeholder for industry selection
industry_mapping = {
    'Technology': 'technology',
    'Healthcare': 'healthcare',
    'Finance': 'finance',
    'Retail': 'retail',
    'Education': 'education'
}

def chat_with_csv(df, prompt, user_persona, industry):
    model = genai.GenerativeModel("gemini-pro", generation_config={'temperature': 0.2, 'max_output_tokens': 5000})
    chunk_size = 500  # Adjust the chunk size as needed
    chunks = [df.iloc[i:i + chunk_size] for i in range(0, len(df), chunk_size)]
    response_parts = []

    # Modify the prompt to include user_persona and industry
    prompt_with_data = f"{prompt}\nUser Persona: {user_persona}\nIndustry: {industry}\n"

    for chunk in chunks:
        data_json = chunk.to_json(orient='records', lines=True)
        prompt_with_data += f"{data_json}\n"

    response = model.generate_content(prompt_with_data)
    response_parts.append(response.text)

    return '\n'.join(response_parts)

def generate_chart(data, x_var, y_var):
    # Generate a beautiful bar chart with different color options
    fig = px.bar(data, x=x_var, y=y_var, color=y_var,
                 title=f'Beautiful Bar Chart of {x_var} vs {y_var}',
                 labels={'index': x_var, y_var: 'Count'},
                 template='plotly_dark')  # You can customize the template as needed
    return fig

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Generated Output', 0, 1, 'C')

    def chapter_title(self, num, label):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, label, 0, 1, 'L')
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)

def save_to_pdf(output_text, user_persona, industry):
    # Create a PDF buffer
    buffer = BytesIO()

    # Generate the PDF content using reportlab
    pdf = canvas.Canvas(buffer)

    # Set the width and height for the PDF page
    width, height = 600, 800

    pdf.setFont("Helvetica", 12)

    # Split the output_text into lines
    lines = output_text.split('\n')

    # Add each line to the PDF
    for line in lines:
        pdf.drawString(72, height, line)
        height -= 12  # Adjust the vertical position for the next line

    pdf.save()

    # Get the value of the BytesIO buffer
    pdf_data = buffer.getvalue()

    # Create a download link for the PDF
    st.markdown(
        f"**[Download PDF]({get_binary_file_downloader_html(pdf_data, 'output.pdf')})**",
        unsafe_allow_html=True
    )

def get_binary_file_downloader_html(bin_data, file_label='File'):
    # Function to create a download link for binary data
    bin_str = base64.b64encode(bin_data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{file_label}">Download {file_label}</a>'
    return href

def main():
    st.title("HP2B Data Accelerator")
    col1, col2 = st.columns(2)
    with col1:
            st.markdown("<h5 class='instruction_heading'> </h5>", unsafe_allow_html=True)
            lottie_creator = load_lottiefile("https://hpinclookac.github.io/data.json")
            st_lottie(lottie_creator, speed=1, reverse=False, loop=True, height=450)
            # Video Section
            # st.subheader("Introduction Video:")
            # video_url = "1.mp4"  # Replace with your actual video URL
            # st.video(video_url)
    with col2:
            st.markdown(
                """
                <div style="">
                        <div style="
                            position: absolute;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 50%;
                        "></div>   
                            <style>
                    ul.custom-list {
                        list-style-type: none;
                        padding-left: 20px;
                        color: #1b3461;
                        font-size:14px;
                    }

                    ul.custom-list li::before {
                        content: '◼'; /* Unicode character for an em dash */
                        color: #ff555f; /* Line color */
                        display: inline-block;
                        width: 2em;
                        font-size:9px;
                        margin-left: -1em;
                    }
                </style>

                <h5 style="color: #ffffff; background: #0096D6; padding: 10px; padding-left:20px;  font-size:16px;">Business purpose</h5>
                <p style="padding-top:10px; font-size:14px; color: #1b3461">Use the tool to analyze customer data and gain deeper insights into customer behavior, preferences, and needs. This can help businesses better understand their target audience and tailor products or services to meet their demands more effectively.</p>
                <ul class="custom-list">
                    <!--<li style="font-size:14px;">&nbsp; Test content will go here</li></br> -->
                </ul>
                <h5 style="color: #ffffff; background: #0096D6; padding: 10px; padding-left:20px; font-size:16px;">Value proposition</h5>
                <p style="padding-top:10px;  font-size:14px; color: #1b3461">Our GenAI Data Accelerator/Explorer empowers businesses to harness the power of data for strategic decision-making and competitive advantage.</p>
                <ul class="custom-list">
                    <!--<li style="font-size:14px;">&nbsp; test content will go here</li> -->
                </ul>
                </div>
                """,
                unsafe_allow_html=True
            )
    input_csv = st.sidebar.file_uploader("Upload your CSV file", type=['csv'])

    if input_csv is not None:
        # Read CSV file into a pandas DataFrame
        data = pd.read_csv(input_csv)

        # Display table using st_aggrid
        AgGrid(data)
        with st.expander("Check your Data"):
            # Allow user to select variables for chart
            x_variable = st.selectbox("Select X Variable for Chart", data.columns)
            y_variable = st.selectbox("Select Y Variable for Chart", data.columns)

            # User persona and industry selection
            user_persona = st.sidebar.selectbox("Select User Persona", list(persona_mapping.keys()))
            industry = st.sidebar.selectbox("Select Industry", list(industry_mapping.keys()))

            # Generate and display the selected chart
            chart = generate_chart(data, x_variable, y_variable)
            st.plotly_chart(chart, use_container_width=True, height=500)

        # Chat and summary
        #st.sidebar.info("Chat Below")
        input_text = st.sidebar.text_area("Enter your question")
        
        if input_text is not None:
            if st.sidebar.button("Ask and Analyze"):
                st.sidebar.info("Your Question: " + input_text)
                result = chat_with_csv(data, input_text, user_persona, industry)
                st.success(result)
                # Save to PDF
                save_to_pdf(result, user_persona, industry)

if __name__ == '__main__':
    main()
