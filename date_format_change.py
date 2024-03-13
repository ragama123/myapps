import streamlit as st
from datetime import datetime

def convert_text_date_to_custom_format(text_date):
    # Convert text date to datetime object
    date_obj = datetime.strptime(text_date, "%B %d, %Y")
    # Convert datetime object to custom format
    custom_format_date = date_obj.strftime("%d-%m-%Y")
    return custom_format_date

def main():
    st.title("Text Date Converter")
    
    text_dates = st.text_area("Enter text dates (one per line)", "")
    text_dates_list = [date.strip() for date in text_dates.split("\n")]  # Strip whitespace from each date
    
    converted_dates = []
    for text_date in text_dates_list:
        if text_date:
            try:
                converted_date = convert_text_date_to_custom_format(text_date)
                converted_dates.append(converted_date)
            except ValueError:
                st.warning(f"Invalid date format: {text_date}")
    
    st.write("Converted Dates:")
    for converted_date in converted_dates:
        st.write(converted_date)

if __name__ == "__main__":
    main()
