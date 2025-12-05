import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="TCPL Ticket Dashboard", layout="wide")

st.title("📊 TCPL Ticket Management Dashboard")
st.write("Upload the latest Excel file to refresh the ticket dashboard.")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.success("File uploaded successfully!")

    # Convert dates if present
    if 'Created Time' in df.columns:
        df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
    if 'Closed Time' in df.columns:
        df['Closed Time'] = pd.to_datetime(df['Closed Time'], errors='coerce')

    # Sidebar filters
    st.sidebar.header("🔍 Filters")

    priority_filter = st.sidebar.multiselect("Select Priority", df['Priority'].dropna().unique())
    ticket_type_filter = st.sidebar.multiselect("Select Ticket Type", df['TicketType'].dropna().unique())
    sla_filter = st.sidebar.multiselect("SLA Status", df['Resolution Status'].dropna().unique())

    # Date filter
    if 'Created Time' in df.columns:
        min_date = df['Created Time'].min()
        max_date = df['Created Time'].max()
        date_range = st.sidebar.date_input("Created Date Range", [min_date, max_date])

    filtered_df = df.copy()

    # Apply filters
    if priority_filter:
        filtered_df = filtered_df[filtered_df['Priority'].isin(priority_filter)]
    if ticket_type_filter:
        filtered_df = filtered_df[filtered_df['TicketType'].isin(ticket_type_filter)]
    if sla_filter:
        filtered_df = filtered_df[filtered_df['Resolution Status'].isin(sla_filter)]

    if 'Created Time' in df.columns:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['Created Time'] >= pd.to_datetime(start_date)) &
            (filtered_df['Created Time'] <= pd.to_datetime(end_date))
        ]

    # KPIs
    total_tickets = len(filtered_df)
    within_sla = len(filtered_df[filtered_df['Resolution Status'] == "Within SLA"])
    sla_percentage = (within_sla / total_tickets * 100) if total_tickets > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tickets", total_tickets)
    col2.metric("Within SLA", f"{sla_percentage:.1f}%")
    col3.metric("Bug Tickets", len(filtered_df[filtered_df["TicketType"] == "Bug"]))

    # Charts
    if 'Priority' in filtered_df.columns:
        fig1 = px.bar(filtered_df.groupby('Priority').size().reset_index(name='Count'), 
                      x="Priority", y="Count", title="Tickets by Priority")
        st.plotly_chart(fig1, use_container_width=True)

    if 'TicketType' in filtered_df.columns:
        fig2 = px.pie(filtered_df, names="TicketType", title="Ticket Distribution by Type")
        st.plotly_chart(fig2, use_container_width=True)

    # Table
    st.subheader("📄 Filtered Data")
    st.dataframe(filtered_df)

    # Download
    excel_data = filtered_df.to_excel(index=False)
    st.download_button("Download Filtered Data", data=excel_data, file_name="filtered_tickets.xlsx")

else:
    st.warning("Please upload an Excel file to view the dashboard.")
