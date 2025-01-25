import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pytz  # For time zone handling
import requests  # For API integration (if needed)

# Define the Kampala time zone
KAMPALA = pytz.timezone('Africa/Kampala')  # Kampala, Uganda (EAT, UTC+3)

# Custom CSS for styling
st.markdown(
    """
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .sidebar .sidebar-content {
        background-color: #ffffff;
    }
    h1 {
        color: #2e86c1;
    }
    h2 {
        color: #1a5276;
    }
    .stButton button {
        background-color: #1a5276;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
    }
    .stButton button:hover {
        background-color: #2e86c1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Connect to the SQLite database
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
    return conn

# Add a customer
def add_customer(conn, name, email, phone):
    sql = '''INSERT INTO customers(name, email, phone) VALUES(?, ?, ?)'''
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (name, email, phone))
        conn.commit()
        st.success(f"Customer {name} added successfully!")
    except sqlite3.IntegrityError:
        st.warning(f"Customer with email {email} or phone {phone} already exists.")
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

# Add a WiFi plan
def add_wifi_plan(conn, name, price, duration_days):
    price_ugx = int(price)  # Price in UGX
    sql = '''INSERT INTO wifi_plans(name, price, duration_days) VALUES(?, ?, ?)'''
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (name, price_ugx, duration_days))
        conn.commit()
        st.success(f"WiFi plan {name} added successfully!")
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

# Subscribe a customer to a plan
def subscribe_customer(conn, customer_id, plan_id):
    cursor = conn.cursor()
    try:
        conn.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT duration_days FROM wifi_plans WHERE plan_id = ?", (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            st.warning("Plan not found.")
            return

        duration_days = plan[0]
        start_date = datetime.now(KAMPALA).strftime('%Y-%m-%d %H:%M:%S')  # Kampala timestamp
        end_date = (datetime.now(KAMPALA) + timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S')  # Kampala timestamp

        sql = '''INSERT INTO subscriptions(customer_id, plan_id, start_date, end_date)
                 VALUES(?, ?, ?, ?)'''
        cursor.execute(sql, (customer_id, plan_id, start_date, end_date))
        conn.commit()
        st.success(f"Customer {customer_id} subscribed to plan {plan_id}!")
    except sqlite3.IntegrityError:
        conn.rollback()
        st.warning(f"Customer {customer_id} is already subscribed to plan {plan_id}.")
    except Exception as e:
        conn.rollback()
        st.error(f"An error occurred: {e}")

# Log data usage
def log_usage(conn, customer_id, data_used_mb):
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM customers WHERE customer_id = ?", (customer_id,))
    if not cursor.fetchone():
        st.warning(f"Customer {customer_id} does not exist.")
        return
    sql = '''INSERT INTO usage_logs(customer_id, data_used_mb) VALUES(?, ?)'''
    try:
        cursor.execute(sql, (customer_id, data_used_mb))
        conn.commit()
        st.success(f"Usage logged for customer {customer_id}!")
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

# Generate an invoice
def generate_invoice(conn, customer_id):
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT wifi_plans.price
            FROM subscriptions
            JOIN wifi_plans ON subscriptions.plan_id = wifi_plans.plan_id
            WHERE subscriptions.customer_id = ? AND subscriptions.end_date >= ?
        ''', (customer_id, datetime.now(KAMPALA).strftime('%Y-%m-%d %H:%M:%S')))  # Kampala timestamp
        plan = cursor.fetchone()
        if not plan:
            st.warning("No active subscription found for the customer.")
            return

        total_amount = plan[0]
        sql = '''INSERT INTO invoices(customer_id, total_amount) VALUES(?, ?)'''
        cursor.execute(sql, (customer_id, total_amount))
        conn.commit()
        st.success(f"Invoice generated for customer {customer_id}!")
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

# Fetch all invoices for a customer
def fetch_invoices(conn, customer_id):
    sql = '''SELECT invoice_id, total_amount, invoice_date FROM invoices WHERE customer_id = ?'''
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (customer_id,))
        invoices = cursor.fetchall()
        if not invoices:
            st.warning(f"No invoices found for customer {customer_id}.")
        return invoices
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return []

# Format currency as UGX
def format_currency(amount):
    return f"{amount:,} UGX"  # Format with commas as thousand separators

# Mock API for mobile money payment
def make_payment(phone_number, amount, reference):
    """
    Simulate a mobile money payment using a mock API.
    Replace this with a real API call to your payment gateway.
    """
    st.write(f"Simulating payment of {format_currency(amount)} to {phone_number} with reference {reference}...")
    return True, "Payment successful!"

# Streamlit UI
def main():
    # Add a logo using a relative path
    st.image("logo.png", width=100)  # Ensure the logo file is in the same folder as the script

    # App title
    st.title("WiFi Hotspot Billing System")
    st.markdown("---")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Choose an action", ["Add Customer", "Add WiFi Plan", "Subscribe Customer", "Log Usage", "Generate Invoice", "View Invoices", "Make Payment"])

    conn = create_connection("wifi_billing.db")

    if choice == "Add Customer":
        st.header("Add a New Customer")
        name = st.text_input("Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone")
        if st.button("Add Customer"):
            if name and email and phone:
                add_customer(conn, name, email, phone)
            else:
                st.warning("Please fill in all fields.")

    elif choice == "Add WiFi Plan":
        st.header("Add a New WiFi Plan")
        name = st.text_input("Plan Name")
        price = st.number_input("Price (UGX)", min_value=0)
        duration_days = st.number_input("Duration (Days)", min_value=1)
        if st.button("Add WiFi Plan"):
            if name and price and duration_days:
                add_wifi_plan(conn, name, price, duration_days)
            else:
                st.warning("Please fill in all fields.")

    elif choice == "Subscribe Customer":
        st.header("Subscribe a Customer to a Plan")
        customer_id = st.number_input("Customer ID", min_value=1)
        plan_id = st.number_input("Plan ID", min_value=1)
        if st.button("Subscribe Customer"):
            if customer_id and plan_id:
                subscribe_customer(conn, customer_id, plan_id)
            else:
                st.warning("Please fill in all fields.")

    elif choice == "Log Usage":
        st.header("Log Data Usage for a Customer")
        customer_id = st.number_input("Customer ID", min_value=1)
        data_used_mb = st.number_input("Data Used (MB)", min_value=0)
        if st.button("Log Usage"):
            if customer_id and data_used_mb:
                log_usage(conn, customer_id, data_used_mb)
            else:
                st.warning("Please fill in all fields.")

    elif choice == "Generate Invoice":
        st.header("Generate an Invoice for a Customer")
        customer_id = st.number_input("Customer ID", min_value=1)
        if st.button("Generate Invoice"):
            if customer_id:
                generate_invoice(conn, customer_id)
            else:
                st.warning("Please fill in all fields.")

    elif choice == "View Invoices":
        st.header("View Invoices for a Customer")
        customer_id = st.number_input("Customer ID", min_value=1)
        if st.button("View Invoices"):
            if customer_id:
                invoices = fetch_invoices(conn, customer_id)
                for invoice in invoices:
                    st.write(f"Invoice ID: {invoice[0]}, Amount: {format_currency(invoice[1])}, Date: {invoice[2]}")
            else:
                st.warning("Please fill in all fields.")

    elif choice == "Make Payment":
        st.header("Make a Payment")
        customer_id = st.number_input("Customer ID", min_value=1)
        phone_number = st.text_input("Phone Number (for payment)")
        amount = st.number_input("Amount (UGX)", min_value=0)
        reference = st.text_input("Payment Reference")
        if st.button("Make Payment"):
            if customer_id and phone_number and amount and reference:
                success, message = make_payment(phone_number, amount, reference)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
