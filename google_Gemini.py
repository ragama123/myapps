import streamlit as st
from google.ads.google_ads.client import GoogleAdsClient
from google.ads.google_ads.errors import GoogleAdsException

# Set up your Google Ads API credentials
# (Assuming you have a google-ads.yaml file in your project directory)

# Authenticate to the Google Ads API
client = GoogleAdsClient.load_from_storage()

# Function to get insights from the Google Gemini API
def get_insights(data):
    try:
        # Initialize a GoogleAdsServiceClient
        google_ads_service = client.google_ads_service

        # Here, 'data' is the query provided by the user
        query = data

        # Issue a search request
        response = google_ads_service.search(client.customer_id, query)

        return response
    except GoogleAdsException as ex:
        st.error(f"Request with ID '{ex.request_id}' failed with status '{ex.error.code().name}' and includes the following errors:")
        for error in ex.error.errors:
            st.error(f"\t{error.message}")
        raise


# Streamlit UI
st.title('Google Gemini Insights and Recommendations')

# Input fields
data = st.text_area('Enter your data:', 'Paste your data here...')

# Button to trigger the API call
if st.button('Get Insights'):
    st.write('Fetching insights...')
    insights = get_insights(data)
    st.write(insights)
