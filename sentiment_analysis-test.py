import streamlit as st
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import seaborn as sns
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import plotly.express as px
import plotly.graph_objects as go

st.set_option('deprecation.showPyplotGlobalUse', False)

# Download NLTK resources
nltk.download('vader_lexicon')

# Define categories for sentiment classification
categories = [
    'Page Load Slowness', 'IT errors', 'Ops quality', 'Customer service',
    'Marketing content', 'HP2B Search', 'Features/ UX', 'Delivery/ Order Mgmt',
    'Products quality', 'Customer service', 'UX', 'Products', 'Generic'
]

# Define colors for sentiment split chart
sentiment_colors = {
    'positive': 'green',
    'negative': 'red',
    'neutral': 'orange'
}

def upload_file():
    uploaded_file = st.file_uploader("Upload CSV or Excel file", type=['csv', 'xlsx'])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('csv') else pd.read_excel(uploaded_file)
        return df

def analyze_sentiment(df):
    sia = SentimentIntensityAnalyzer()
    df['Sentiment Score'] = df['comments'].apply(lambda x: sia.polarity_scores(str(x))['compound'])
    # Classify sentiments based on scores
    df['Sentiment'] = pd.cut(df['Sentiment Score'], bins=3, labels=['negative', 'neutral', 'positive'])
    return df

def generate_wordcloud(df, sentiment):
    if 'Sentiment' in df:
        comments = df[df['Sentiment'] == sentiment]['comments']
        comments = comments.dropna()  # Drop missing values
        if not comments.empty:
            comments_text = ' '.join(comments.astype(str))  # Convert to string before joining
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(comments_text)
            st.subheader(f"{sentiment.capitalize()} Comments Word Cloud")
            st.image(wordcloud.to_array())
        else:
            st.write(f"No comments available for {sentiment} sentiment.")
    else:
        st.write("Please perform sentiment analysis first.")

def plot_sentiment_distribution(df):
    if 'Sentiment' in df:
        sentiment_counts = df['Sentiment'].value_counts()
        colors = [sentiment_colors[sent] for sent in sentiment_counts.index]
        plt.figure(figsize=(8, 6))
        plt.pie(sentiment_counts, labels=sentiment_counts.index, colors=colors, autopct='%1.1f%%', startangle=140)
        plt.title("Sentiment Distribution")
        st.pyplot()
    else:
        st.write("Please perform sentiment analysis first.")

def classify_comments(df):
    # Initialize classification columns with zeros
    for category in categories:
        df[category] = 0

    # Classify comments based on categories
    for category in categories:
        df[category] = df['comments'].str.count(category)

def main():
    st.title("Survey Analysis App")
    st.sidebar.title("Options")
    option = st.sidebar.selectbox("Choose an option", ["Upload File", "Sentiment Analysis"])

    if option == "Upload File":
        df = upload_file()
        st.session_state.df = df
    elif option == "Sentiment Analysis":
        if 'df' not in st.session_state:
            st.error("Please upload a file first.")
        else:
            df = st.session_state.df
            df = analyze_sentiment(df)
            classify_comments(df)

            st.subheader("Preview Table")
            st.write(df.drop(columns=categories, errors='ignore'))

            st.subheader("Word Clouds")
            generate_wordcloud(df, sentiment='positive')
            generate_wordcloud(df, sentiment='negative')
            generate_wordcloud(df, sentiment='neutral')

            st.subheader("Sentiment Distribution")
            plot_sentiment_distribution(df)

            sentiment_df = pd.DataFrame(columns=['Category', 'Positive', 'Neutral', 'Negative'])

            for category in categories:
                positive_count = ((df[category] > 0) & (df['Sentiment'] == 'positive')).sum()
                neutral_count = ((df[category] > 0) & (df['Sentiment'] == 'neutral')).sum()
                negative_count = ((df[category] > 0) & (df['Sentiment'] == 'negative')).sum()
                sentiment_df.loc[len(sentiment_df)] = [category, positive_count, neutral_count, negative_count]


            st.table(sentiment_df)

            st.subheader("Sentiment Heatmap")
            fig = go.Figure(data=go.Heatmap(
                            z=[sentiment_df['Positive'], sentiment_df['Neutral'], sentiment_df['Negative']],
                            x=sentiment_df['Category'],
                            y=['Positive', 'Neutral', 'Negative'],
                            colorscale=[[0, 'green'], [0.5, 'orange'], [1.0, 'red']],
                            colorbar=dict(title='Number of Mentions')))
            fig.update_layout(title='Sentiment Heatmap for Categories',
                              xaxis_title='Category',
                              yaxis_title='Sentiment')
            st.plotly_chart(fig)

if __name__ == "__main__":
    main()
