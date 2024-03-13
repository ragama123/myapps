import streamlit as st
import pandas as pd

def find_matching_values(input_file, data_file):
    try:
        # Read input and data files
        input_df = read_file(input_file)
        data_df = read_file(data_file)

        # Check if both files are successfully loaded
        if input_df is None or data_df is None:
            st.error("One or both of the files are empty or incorrectly formatted. Please upload files with data.")
            return None, None

        # Debugging information
        st.write("Input DataFrame Columns:")
        st.write(input_df.columns)

        st.write("Data DataFrame Columns:")
        st.write(data_df.columns)

        # Check if necessary columns are present in data file
        required_columns_data = ['Order ID (v95) (evar95)']
        st.write("Required Columns in Data File:")
        st.write(required_columns_data)

        missing_columns_data = set(required_columns_data) - set(data_df.columns)

        if missing_columns_data:
            st.error(f"Data file is missing columns: {missing_columns_data}. Please check your file.")
            return None, None

        # Merge data frames based on 'B2B_Quote_Identifier' using a left join
        merged_df = pd.merge(input_df, data_df, how='left', left_on='B2B_Quote_Identifier', right_on='Order ID (v95) (evar95)')

        # Save the result to a new file
        output_file = 'matching_values_with_non_matching.xlsx'
        merged_df.to_excel(output_file, index=False)

        return output_file, merged_df

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None, None

def read_file(file):
    try:
        if file.name.endswith('.xlsx'):
            return pd.read_excel(file, engine='openpyxl')
        elif file.name.endswith('.csv'):
            return pd.read_csv(file)
        else:
            st.error(f"Unsupported file format. Please upload a CSV or Excel file.")
            return None
    except pd.errors.EmptyDataError:
        st.error("The file is empty.")
        return None
    except Exception as e:
        st.error(f"An error occurred while reading the file: {e}")
        return None

def main():
    st.title("Matching Values Finder")

    # Upload input and data files
    input_file = st.file_uploader("Upload Input File (CSV or Excel)", type=["csv", "xlsx"])
    data_file = st.file_uploader("Upload Data File (CSV or Excel)", type=["csv", "xlsx"])

    if input_file and data_file:
        st.success("Files successfully uploaded!")

        # Display the uploaded files
        st.subheader("Uploaded Input File:")
        try:
            st.write(read_file(input_file))
        except pd.errors.EmptyDataError:
            st.error("The input file is empty or incorrectly formatted.")

        st.subheader("Uploaded Data File:")
        try:
            st.write(read_file(data_file))
        except pd.errors.EmptyDataError:
            st.error("The data file is empty or incorrectly formatted.")

        # Button to perform matching and create a new file
        if st.button("Find Matching Values"):
            output_file, matching_df = find_matching_values(input_file, data_file)

            if matching_df is not None:
                # Display matched values
                st.subheader("Matching Values (Including Non-Matching):")
                st.write(matching_df)

                # Provide download link for the new file
                st.markdown(f"### [Download Matching Values File]({output_file})")

if __name__ == "__main__":
    main()
