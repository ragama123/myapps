import streamlit as st
import pandas as pd
import os

def merge_files(folder_path, file_type):
    files = [f for f in os.listdir(folder_path) if f.endswith(file_type)]
    if len(files) == 0:
        st.error(f"No {file_type.upper()} files found in the selected folder.")
        return None
    
    st.write(f"Found {len(files)} {file_type.upper()} file(s) in the folder.")
    
    # Initialize an empty DataFrame to store the merged data
    merged_data = pd.DataFrame()
    
    for file in files:
        file_path = os.path.join(folder_path, file)
        if file_type == '.csv':
            data = pd.read_csv(file_path)
        elif file_type == '.xlsx':
            data = pd.read_excel(file_path)
        
        # Merge the current file's data with the existing data
        merged_data = pd.concat([merged_data, data], ignore_index=True)
    
    st.success("Files merged successfully!")
    return merged_data

def main():
    st.title("Merge Multiple CSV/Excel Files")
    
    # Select folder
    folder_path = st.sidebar.text_input("Enter folder path:", "")
    
    # Select file type
    file_type = st.sidebar.selectbox("Select file type:", [".csv", ".xlsx"])
    
    if st.sidebar.button("Merge Files"):
        merged_data = merge_files(folder_path, file_type)
        if merged_data is not None:
            st.write("Merged Data:")
            st.write(merged_data)

if __name__ == "__main__":
    main()
