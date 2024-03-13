import streamlit as st
import pandas as pd
import base64

# Function to unhash email using Base64 decoding
def unhash_email(hashed_email):
    return base64.b64decode(hashed_email).decode()

# Function to unhash email IDs from CSV or Excel file
def unhash_emails(input_file):
    if input_file is not None:
        if input_file.name.endswith('.csv'):
            df = pd.read_csv(input_file)
        elif input_file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(input_file)
        else:
            st.error('Unsupported file format. Please upload a CSV or Excel file.')
            return None
        
        # Check if the 'Hashed Email' column exists
        if 'Hashed Email' not in df.columns:
            st.error("The file doesn't contain a 'Hashed Email' column.")
            return None
        
        # Unhash email IDs
        df['Original Email'] = df['Hashed Email'].apply(unhash_email)
        return df

# Streamlit app
def main():
    st.title('Email Unhashing')

    # Option to upload file or manually enter hashed email IDs
    option = st.radio('Select an option:', ('Upload CSV or Excel file', 'Manually enter hashed email IDs'))

    if option == 'Upload CSV or Excel file':
        # Upload file
        uploaded_file = st.file_uploader('Upload CSV or Excel file', type=['csv', 'xlsx', 'xls'])

        if uploaded_file is not None:
            # Unhash emails and display result
            unhashed_df = unhash_emails(uploaded_file)
            if unhashed_df is not None:
                st.write('**Original Data:**')
                st.write(unhashed_df.drop(columns='Original Email', errors='ignore'))
                st.write('**Unhashed Data:**')
                st.write(unhashed_df)
    else:
        # Manually enter hashed email IDs
        st.subheader('Manually Enter Hashed Email IDs')
        hashed_email_ids = st.text_area('Enter hashed email IDs (one per line)', '')
        if st.button('Unhash Email IDs'):
            if hashed_email_ids:
                hashed_emails = hashed_email_ids.split('\n')
                original_emails = [unhash_email(email) for email in hashed_emails]
                result_df = pd.DataFrame({'Hashed Email': hashed_emails, 'Original Email': original_emails})
                st.write('**Unhashed Data:**')
                st.write(result_df)

# Run the app
if __name__ == '__main__':
    main()
