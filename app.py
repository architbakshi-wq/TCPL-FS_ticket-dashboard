# app.py - corrected minimal Streamlit dashboard
import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO

st.set_page_config(page_title="TCPL Ticket Dashboard", layout="wide")
st.title("📊 TCPL Ticket Management Dashboard")
st.write("Upload the latest Excel file to refresh the ticket dashboard.")

# File uploader
uploaded_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"])

# If no upload, try to use data.xlsx in repo (optional)
DEFAULT_DATAFILE = "data.xlsx"
if uploaded_file is None and os.path.exists(DEFAULT_DATAFILE):
    uploaded_file = DEFAULT_DATAFILE

# If still no file, show message and stop further execution
if not uploaded_file:
    st.warning("No data file found. Please either:\n\n"
               "• Upload the Excel file using the 'Upload Excel File' control, or\n"
               "• Add a file named 'data.xlsx' into the repository so the app can use it by default.")
    st.stop()

# Read the file (uploaded_file is either a file-like object or a path)
try:
    df = pd.read_excel(uploaded_file)
except Exception as e:
    st.error(f"Failed to read uploaded file: {e}")
    st.stop()

# Normalize / parse dates safely
if 'Created Time' in df.columns:
    df['Created Time'] = pd.to_datetime(df['Created Time'], errors='coerce')
if 'Closed Time' in df.columns:
    df['Closed Time'] = pd.to_datetime(df['Closed Time'], errors='coerce')

# Basic filters in sidebar
st.sidebar.header("Filters")
priority_filter = st.sidebar.multiselect("Select Priority", options=df.get('Priority', pd.Series()).dropna().unique())
ticket_type_filter = st.sidebar.multiselect("Select Ticket Type", options=df.get('TicketType', pd.Series()).dropna().unique())
sla_filter = st.sidebar.multiselect("SLA Status", options=df.get('Resolution Status', pd.Series()).dropna().unique())

# Date range filter (if present)
if 'Created Time' in df.columns:
    min_date = df['Created Time'].min().date()
    max_date = df['Created Time'].max().date()
    date_range = st.sidebar.date_input("Created Date Range", [min_date, max_date])
else:
    date_range = None

# Apply filters to create filtered_df (always define it)
filtered_df = df.copy()
if priority_filter:
    filtered_df = filtered_df[filtered_df['Priority'].isin(priority_filter)]
if ticket_type_filter:
    filtered_df = filtered_df[filtered_df['TicketType'].isin(ticket_type_filter)]
if sla_filter:
    filtered_df = filtered_df[filtered_df['Resolution Status'].isin(sla_filter)]
if date_range and 'Created Time' in filtered_df.columns:
    start_date, end_date = date_range
    filtered_df = filtered_df[(filtered_df['Created Time'] >= pd.to_datetime(start_date)) & (filtered_df['Created Time'] <= pd.to_datetime(end_date))]

# KPIs
total_tickets = len(filtered_df)
within_sla = len(filtered_df[filtered_df.get('Resolution Status') == "Within SLA"]) if 'Resolution Status' in filtered_df.columns else 0
sla_percentage = (within_sla / total_tickets * 100) if total_tickets > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Tickets", total_tickets)
col2.metric("Within SLA", f"{sla_percentage:.1f}%")
col3.metric("Bug Tickets", len(filtered_df[filtered_df.get("TicketType") == "Bug"]) if 'TicketType' in filtered_df.columns else 0)

# Simple charts
if 'Priority' in filtered_df.columns and not filtered_df.empty:
    fig1 = px.bar(filtered_df.groupby('Priority').size().reset_index(name='Count'), x="Priority", y="Count", title="Tickets by Priority")
    st.plotly_chart(fig1, use_container_width=True)

if 'TicketType' in filtered_df.columns and not filtered_df.empty:
    fig2 = px.pie(filtered_df, names="TicketType", title="Ticket Distribution by Type")
    st.plotly_chart(fig2, use_container_width=True)

# Table
st.subheader("📄 Filtered Data")
st.dataframe(filtered_df, height=400)

# Prepare Excel download correctly (BytesIO)
def to_excel_bytes(df_to_export):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_to_export.to_excel(writer, index=False, sheet_name="Filtered")
    return output.getvalue()

if not filtered_df.empty:
    excel_bytes = to_excel_bytes(filtered_df)
    st.download_button(
        label="Download Filtered Data",
        data=excel_bytes,
        file_name="filtered_tickets.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
