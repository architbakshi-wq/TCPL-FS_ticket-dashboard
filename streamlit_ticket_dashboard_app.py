import streamlit as st
import pandas as pd
import plotly.express as px
import os
from io import BytesIO

st.set_page_config(page_title="TCPL Ticket Dashboard", layout="wide")
st.title("📊 TCPL Ticket Management Dashboard")
st.write("Upload the latest Excel file to refresh the ticket dashboard.")

# --- File upload / default file -------------------------------------------
uploaded_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"]) 

# If no upload, try to use data.xlsx placed in the repository (optional)
DEFAULT_DATAFILE = "data.xlsx"
if uploaded_file is None and os.path.exists(DEFAULT_DATAFILE):
    uploaded_file = DEFAULT_DATAFILE

# If still no file, show friendly message and stop
if not uploaded_file:
    st.warning(
        "No data file found. Please either:

"
        "• Upload the Excel file using the 'Upload Excel File' control, or
"
        "• Add a file named 'data.xlsx' into the repository so the app can use it by default."
    )
    st.stop()

# --- Read the spreadsheet -------------------------------------------------
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

# --- Sidebar filters -----------------------------------------------------
st.sidebar.header("Filters")
priority_filter = st.sidebar.multiselect("Select Priority", options=df.get('Priority', pd.Series()).dropna().unique())
ticket_type_filter = st.sidebar.multiselect("Select Ticket Type", options=df.get('TicketType', pd.Series()).dropna().unique())
sla_filter = st.sidebar.multiselect("SLA Status", options=df.get('Resolution Status', pd.Series()).dropna().unique())

# --- Robust date-range input ---------------------------------------------
start_date = None
end_date = None
if 'Created Time' in df.columns:
    min_date = df['Created Time'].min().date()
    max_date = df['Created Time'].max().date()
    # Provide a date_input that returns either a single date or a list of two dates
    date_input_value = st.sidebar.date_input("Choose a date range", [min_date, max_date])

    # Normalize date_input_value to start_date and end_date
    if isinstance(date_input_value, (list, tuple)):
        if len(date_input_value) == 2:
            start_date, end_date = date_input_value
n        elif len(date_input_value) == 1:
            # single selection returned as list with one element
            start_date = end_date = date_input_value[0]
    else:
        # single date returned
        start_date = end_date = date_input_value

# convert to pandas timestamps if set
if start_date is not None:
    start_date = pd.to_datetime(start_date)
if end_date is not None:
    end_date = pd.to_datetime(end_date)

# --- Apply filters and produce filtered_df --------------------------------
filtered_df = df.copy()
if priority_filter:
    filtered_df = filtered_df[filtered_df['Priority'].isin(priority_filter)]
if ticket_type_filter:
    filtered_df = filtered_df[filtered_df['TicketType'].isin(ticket_type_filter)]
if sla_filter:
    filtered_df = filtered_df[filtered_df['Resolution Status'].isin(sla_filter)]

if start_date is not None and 'Created Time' in filtered_df.columns:
    if end_date is None:
        end_date = start_date
    # include full day for end_date
    filtered_df = filtered_df[(filtered_df['Created Time'] >= start_date) & (filtered_df['Created Time'] <= end_date)]

# --- KPIs ----------------------------------------------------------------
total_tickets = len(filtered_df)
within_sla = 0
if 'Resolution Status' in filtered_df.columns:
    within_sla = filtered_df['Resolution Status'].str.contains('Within', case=False, na=False).sum()
sla_percentage = (within_sla / total_tickets * 100) if total_tickets > 0 else 0

col1, col2, col3, col4 = st.columns([1.5,1,1,1])
col1.metric("Total Tickets", total_tickets)
col2.metric("Within SLA", f"{sla_percentage:.1f}%")
col3.metric("Avg Resolution (hrs)", round(((filtered_df['Closed Time'] - filtered_df['Created Time']).dt.total_seconds()/3600).mean(),2) if ('Closed Time' in filtered_df.columns and 'Created Time' in filtered_df.columns and not filtered_df.empty) else '—')
col4.metric("P4 Tickets", int(filtered_df[filtered_df.get('Priority') == 'P4'].shape[0]) if 'Priority' in filtered_df.columns else 0)

st.markdown("---")

# --- Charts ---------------------------------------------------------------
if 'Priority' in filtered_df.columns and not filtered_df.empty:
    prio_counts = filtered_df['Priority'].value_counts().reset_index()
    prio_counts.columns = ['Priority','Count']
    fig_prio = px.bar(prio_counts, x='Priority', y='Count', title='Tickets by Priority', text='Count')
    st.plotly_chart(fig_prio, use_container_width=True)

if 'TicketType' in filtered_df.columns and not filtered_df.empty:
    fig_type = px.pie(filtered_df, names='TicketType', title='Ticket Type Distribution')
    st.plotly_chart(fig_type, use_container_width=True)

if 'Created Time' in filtered_df.columns and not filtered_df.empty:
    trend = filtered_df.groupby(filtered_df['Created Time'].dt.date).size().reset_index(name='Count')
    trend.columns = ['Date','Count']
    fig_trend = px.line(trend, x='Date', y='Count', title='Tickets Over Time', markers=True)
    st.plotly_chart(fig_trend, use_container_width=True)

st.markdown("---")

# --- Data table ----------------------------------------------------------
st.subheader("Filtered Tickets")
st.dataframe(filtered_df.sort_values(by='Created Time', ascending=False).reset_index(drop=True), height=420)

# --- Excel download (BytesIO) --------------------------------------------
def to_excel_bytes(df_to_export):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_export.to_excel(writer, index=False, sheet_name='Filtered')
    return output.getvalue()

if not filtered_df.empty:
    excel_bytes = to_excel_bytes(filtered_df)
    st.download_button(label='Download filtered data as Excel', data=excel_bytes, file_name='filtered_tickets.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

st.caption("Built with Streamlit — Upload your Excel file to refresh the dashboard. For persistent uploads, consider saving files to a secure storage (S3/GitHub) or implementing authenticated upload." )
