import streamlit as st
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Load your dataset
def load_data(file_path, file_type):
    if file_type == "csv":
        data = pd.read_csv(file_path)
    elif file_type == "xlsx":
        data = pd.read_excel(file_path)
    else:
        st.error("Unsupported file type. Please upload a CSV or XLSX file.")
        return None
    return data

def preprocess_data(data):
    # Perform necessary preprocessing steps
    # Example: Drop irrelevant columns, handle missing values, encode categorical variables, etc.
    data = data[['Market', 'Customer Segment', 'CustomerAssisted', 'OrderLoadDate', 
                 'Sold To Organization_Id', 'EndCustomerName', 'Total Line $ Value', 
                 'HPOrderNo', 'Total_OrderedQty']]  # Removed 'Churn' from the selection

    # Example preprocessing steps:
    data = data.dropna()
    data['OrderLoadDate'] = pd.to_datetime(data['OrderLoadDate'])

    # Encode categorical variables using one-hot encoding
    data = pd.get_dummies(data, columns=['Market', 'Customer Segment', 'CustomerAssisted'])

    # Assuming 'OrderLoadDate' is the date of the order
    last_order_date = data['OrderLoadDate'].max()
    cutoff_date = last_order_date - pd.DateOffset(months=3)

    # Create 'Churn' column based on the condition
    data['Churn'] = (data['OrderLoadDate'] <= cutoff_date).astype(int)

    return data

# Train a predictive model
def train_model(data):
    # Replace 'target_column' with the actual name of your target variable
    # In churn prediction, it could be a binary variable indicating churn or not
    # For simplicity, let's assume 'Churn' is a binary variable in the 'target_column'
    data['Churn'] = data['Total Line $ Value'] <= 0  # Example: Churn if Total Line $ Value is zero or negative
    
    # Drop unnecessary columns
    X = data.drop(['Churn', 'OrderLoadDate'], axis=1)  # Drop 'Churn' and 'OrderLoadDate'
    y = data['Churn']

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Drop the 'EndCustomerName' column as it is not needed for model training
    X_train = X_train.drop('EndCustomerName', axis=1)
    X_test = X_test.drop('EndCustomerName', axis=1)

    # Train a RandomForestClassifier (you can choose another classifier based on your needs)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    # Evaluate the model
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)

    return model, accuracy, report

# Streamlit app
def main():
    st.title("Churn Prediction App")

    # Upload Online Dataset
    st.sidebar.header("Upload Dataset")
    uploaded_file = st.sidebar.file_uploader("Upload your Excel file (CSV or XLSX)", type=["csv", "xlsx"])

    if uploaded_file is not None:
        data = load_data(uploaded_file, uploaded_file.name.split('.')[-1])

        # Display the raw data
        st.subheader("Raw Data")
        st.dataframe(data)

        # Preprocess data
        data = preprocess_data(data)

        # Train the model
        st.subheader("Train Predictive Model")
        model, accuracy, report = train_model(data)
        st.write(f"Model Accuracy: {accuracy:.2f}")
        st.write("Classification Report:")
        st.text(report)

        # Select customer and show results
        st.subheader("Customer Prediction")
        selected_customer = st.selectbox("Select Customer", data['EndCustomerName'].unique())

        # Filter data for selected customer
        selected_customer_data = data[data['EndCustomerName'] == selected_customer]

        # Display selected customer data
        st.subheader(f"Data for {selected_customer}")
        st.dataframe(selected_customer_data)

        # Make prediction for selected customer
        customer_input = selected_customer_data.drop(['Churn', 'OrderLoadDate', 'EndCustomerName'], axis=1)
        prediction = model.predict(customer_input)
        st.write(f"Churn Prediction for {selected_customer}: {'Churn' if prediction[0] else 'Not Churn'}")

        # Display a table with churned customers and reasons
        churned_customers = data[data['Churn'] == 1]
        st.subheader("Churned Customers")
        st.table(churned_customers[['EndCustomerName', 'OrderLoadDate', 'Churn']])

if __name__ == '__main__':
    main()