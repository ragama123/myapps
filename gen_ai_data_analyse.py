import streamlit as st
import pandas as pd
import google.generativeai as genai

# Function to load and display the dataset
def load_dataset(file):
    df = pd.read_csv(file)
    return df

# Function to generate response using gemini-pro or gemini-pro-vision model
def generate_response(prompt):
    # Generate response based on the prompt
    response = model.generate_content(prompt)
    generated_response = response.text
    return generated_response

# Main function to run the Streamlit app
def main():
    st.title("Gemini Chat")

    # File upload field to upload the dataset
    uploaded_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

    # Prompt question input field
    prompt = st.text_input("Enter your prompt question:")

    # Process button to generate response
    if st.button("Process"):
        if uploaded_file is not None:
            # Load the dataset
            df = load_dataset(uploaded_file)
            st.write("Dataset loaded successfully!")

            # Display prompt question
            st.write("Prompt Question:", prompt)

            # Split the dataset into smaller chunks and generate responses
            chunk_size = 100  # Adjust the chunk size as needed
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]
                prompt_with_data = prompt + "\n\nDataset:\n" + chunk.to_string(index=False)
                response = generate_response(prompt_with_data)
                st.write("Generated Response:", response)
        else:
            st.write("Please upload a dataset first.")

if __name__ == "__main__":
    # Configure API key
    genai.configure(api_key="AIzaSyCUPTiOotHcQzOBcv6m-9aFu9WGrzBl2Y4")
    
    # Initialize GenerativeModel with gemini-pro
    model = genai.GenerativeModel("gemini-pro")

    # Run the Streamlit app
    main()
