import streamlit as st
import google.generativeai as genai

# Configure API key
GOOGLE_API_KEY = "AIzaSyCUPTiOotHcQzOBcv6m-9aFu9WGrzBl2Y4"
genai.configure(api_key=GOOGLE_API_KEY)

# Function to generate response
def generate_response(prompt):
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text

# Streamlit app
st.title("Type Your Query to get a Reponse using Generative AI")

# Input prompt with shift+enter support
prompt = st.text_area("Enter your message:", height=100, key="input")

# Generate response
if st.button("Send"):
    if prompt:
        response = generate_response(prompt)
        st.text("GenAI:")
        st.write(response)
    else:
        st.warning("Please enter a message.")


