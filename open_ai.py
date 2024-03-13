import streamlit as st
import openai

# Set up your OpenAI API key
openai.api_key = "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"

# Function to generate insights and recommendations using OpenAI
def generate_insights_and_recommendations(data):
    prompt = f"Given the following data:\n\n{data}\n\nGenerate insights and recommendations based on this data."
    response = openai.Completion.create(
        engine="babbage-002",  # Choose the GPT-3 engine
        prompt=prompt,
        max_tokens=150,  # Adjust as needed
        n=1,  # Number of completions to generate
        stop=None,  # Stop generation at specific token (optional)
        temperature=0.7  # Controls the randomness of the generated text
    )
    return response.choices[0].text.strip()

# Streamlit UI
def main():
    st.title('Data Insights and Recommendations')

    # Data input
    data = st.text_area('Paste your data here:', '')

    if st.button('Generate Insights and Recommendations'):
        if data:
            # Generate insights and recommendations using OpenAI
            insights_recommendations = generate_insights_and_recommendations(data)

            # Display insights and recommendations
            st.write('Insights and Recommendations:')
            st.write(insights_recommendations)
        else:
            st.warning('Please provide some data.')

if __name__ == '__main__':
    main()
