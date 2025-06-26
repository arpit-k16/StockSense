import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO

# --- Download Helper Functions (must be defined before use) ---
# def fig_to_image_download(fig, filename):
#     buf = BytesIO()
#     fig.write_image(buf, format='png')
#     st.download_button('Download Chart', buf.getvalue(), file_name=filename, mime='image/png')

def df_to_csv_download(df, filename):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button('Download Data', csv, file_name=filename, mime='text/csv')

# --- Caching for performance ---
@st.cache_data

def load_csv(filename, **kwargs):
    try:
        return pd.read_csv(filename, **kwargs)
    except Exception as e:
        st.error(f"Error loading {filename}: {e}")
        return pd.DataFrame()

low_inventory_df = load_csv('dashboard/Low Inventory.csv')
overstock_df = load_csv('dashboard/Overstock.csv')
turnover_df = load_csv('dashboard/Inventory Turnover Rate.csv')
forecast_deviation_df = load_csv('dashboard/Forecast Deviation.csv')
snapshot_df = load_csv('dashboard/Inventory Snapshot.csv')

# Forecast.csv is large, so read only needed columns
try:
    forecast_sample = pd.read_csv('dashboard/Forecast.csv', nrows=5000, header=None)
    forecast_header = [
        'date', 'store_id', 'product_id', 'actual', 'forecast', 'error', 'accuracy_class',
        'price', 'discount', 'holiday_promotion', 'weather_condition', 'seasonality'
    ]
    forecast_sample.columns = forecast_header[:len(forecast_sample.columns)]
except Exception as e:
    st.error(f"Error loading Forecast.csv: {e}")
    forecast_sample = pd.DataFrame()

# --- Sidebar Filters ---
st.sidebar.title('Filters')

# Date range filter (for snapshot_df and forecast_sample)
min_date = None
max_date = None
if not snapshot_df.empty and 'date' in snapshot_df.columns:
    snapshot_df['date'] = pd.to_datetime(snapshot_df['date'], errors='coerce', dayfirst=True)
    min_date = snapshot_df['date'].min()
    max_date = snapshot_df['date'].max()
    date_range = st.sidebar.date_input('Select Date Range', [min_date, max_date], min_value=min_date, max_value=max_date)
else:
    date_range = None

# Store filter
def get_unique_stores():
    stores = set()
    for df in [snapshot_df, turnover_df, low_inventory_df, overstock_df]:
        if not df.empty and 'store_id' in df.columns:
            stores.update(df['store_id'].dropna().unique())
    return sorted(list(stores))

store_options = get_unique_stores()
selected_stores = st.sidebar.multiselect('Select Store(s)', store_options, default=store_options)

# Product filter
def get_unique_products():
    products = set()
    for df in [snapshot_df, turnover_df, low_inventory_df, overstock_df]:
        if not df.empty and 'product_id' in df.columns:
            products.update(df['product_id'].dropna().unique())
    return sorted(list(products))

product_options = get_unique_products()
selected_products = st.sidebar.multiselect('Select Product(s)', product_options, default=product_options)

# Theme toggle
theme = st.sidebar.radio('Theme', ['Light', 'Dark'], index=0)
if theme == 'Dark':
    st.markdown('<style>body { background-color: #222; color: #eee; } .stApp { background-color: #222; } </style>', unsafe_allow_html=True)
    kpi_css = """
    <style>
    .kpi {
        background: #333;
        border-radius: 8px;
        padding: 1em 0.5em 0.8em 0.5em;
        margin-bottom: 0.5em;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        width: 100%;
        box-sizing: border-box;
        min-width: 0;
        max-width: 100%;
    }
    .kpi-title { font-size: 1.1em; color: #eee; }
    .kpi-value { font-size: 2em; font-weight: bold; color: #fff; }
    [data-testid="column"] { padding-right: 0.5em; }
    </style>
    """
else:
    kpi_css = """
    <style>
    .kpi {
        background: #f5f5f5;
        border-radius: 8px;
        padding: 1em 0.5em 0.8em 0.5em;
        margin-bottom: 0.5em;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        width: 100%;
        box-sizing: border-box;
        min-width: 0;
        max-width: 100%;
    }
    .kpi-title { font-size: 1.1em; color: #888; }
    .kpi-value { font-size: 2em; font-weight: bold; color: #222; }
    [data-testid="column"] { padding-right: 0.5em; }
    </style>
    """
st.markdown(kpi_css, unsafe_allow_html=True)

# --- Data Filtering ---
def filter_df(df, date_col='date'):
    if df.empty:
        return df
    if 'store_id' in df.columns:
        df = df[df['store_id'].isin(selected_stores)]
    if 'product_id' in df.columns:
        df = df[df['product_id'].isin(selected_products)]
    if date_range and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
        df = df[(df[date_col] >= pd.to_datetime(date_range[0])) & (df[date_col] <= pd.to_datetime(date_range[1]))]
    return df

snapshot_df_f = filter_df(snapshot_df, 'date')
turnover_df_f = filter_df(turnover_df)
low_inventory_df_f = filter_df(low_inventory_df)
overstock_df_f = filter_df(overstock_df)
forecast_deviation_df_f = filter_df(forecast_deviation_df)
forecast_sample_f = filter_df(forecast_sample, 'date')

# Calculate Total_Inventory for snapshot_df_f
inventory_cols = [col for col in snapshot_df_f.columns if 'inventory' in col.lower()]
if len(inventory_cols) > 1:
    snapshot_df_f['Total_Inventory'] = snapshot_df_f[inventory_cols].sum(axis=1)
elif inventory_cols:
    snapshot_df_f['Total_Inventory'] = snapshot_df_f[inventory_cols[0]]
else:
    snapshot_df_f['Total_Inventory'] = 0

# Clean and check inventory_health_flag for overstock_df_f
if not overstock_df_f.empty and 'inventory_health_flag' in overstock_df_f.columns:
    overstock_df_f['inventory_health_flag'] = overstock_df_f['inventory_health_flag'].str.strip().str.lower()
    percent_overstocked = 100 * (overstock_df_f['inventory_health_flag'] == 'overstocked').mean()
else:
    percent_overstocked = 0

# Calculate % Low Inventory
if not low_inventory_df_f.empty and 'Inventory_Level' in low_inventory_df_f.columns and 'Threshold_Level' in low_inventory_df_f.columns:
    percent_low_inventory = 100 * (low_inventory_df_f['Inventory_Level'] < low_inventory_df_f['Threshold_Level']).mean()
else:
    percent_low_inventory = 0

# Calculate Total Units Sold
if not turnover_df_f.empty and 'units_sold' in turnover_df_f.columns:
    total_units_sold = int(turnover_df_f['units_sold'].sum())
else:
    total_units_sold = 0

# Calculate % High Turnover SKUs
if not turnover_df_f.empty and 'inventory_turnover' in turnover_df_f.columns:
    percent_high_turnover = 100 * (turnover_df_f['inventory_turnover'] > 10).mean()
else:
    percent_high_turnover = 0

# --- KPIs ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown('<div class="kpi"><div class="kpi-title">Total Inventory</div><div class="kpi-value">{:,}</div></div>'.format(int(snapshot_df_f['Total_Inventory'].sum()) if not snapshot_df_f.empty else 0), unsafe_allow_html=True)
with col2:
    st.markdown('<div class="kpi"><div class="kpi-title"># Unique SKUs</div><div class="kpi-value">{:,}</div></div>'.format(len(snapshot_df_f['product_id'].unique()) if not snapshot_df_f.empty and 'product_id' in snapshot_df_f.columns else 0), unsafe_allow_html=True)
with col3:
    st.markdown('<div class="kpi"><div class="kpi-title">Avg Turnover</div><div class="kpi-value">{:.2f}</div></div>'.format(turnover_df_f['inventory_turnover'].mean() if not turnover_df_f.empty and 'inventory_turnover' in turnover_df_f.columns else 0), unsafe_allow_html=True)
with col4:
    st.markdown('<div class="kpi"><div class="kpi-title">% High Turnover SKUs</div><div class="kpi-value">{:.1f}%</div></div>'.format(percent_high_turnover), unsafe_allow_html=True)

# --- Main Layout ---
st.title("Inventory Analytics Dashboard")

# --- Tabs for Graph Organization ---
tab_names = [
    "Turnover Analysis",
    "Inventory & Overstock",
    "Forecast Accuracy",
    "ML Model Insights"
]
tabs = st.tabs(tab_names)

# --- Turnover Analysis Tab ---
with tabs[0]:
    if not turnover_df_f.empty:
        st.info("Top 10 SKUs by Inventory Turnover: Identify the fastest-moving products across all stores.")
        top10 = turnover_df_f.sort_values('inventory_turnover', ascending=False).head(10)
        fig3 = px.bar(top10, x='product_id', y='inventory_turnover', color='store_id',
                     title='Top 10 SKUs by Inventory Turnover', text='inventory_turnover')
        fig3.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig3.update_layout(legend=dict(x=1.02, y=1, xanchor='left', yanchor='top'), xaxis_tickangle=45)
        st.plotly_chart(fig3, use_container_width=True, key='fig3')
        # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
        # fig_to_image_download(fig3, 'top_10_turnover.png')
        df_to_csv_download(top10, 'top_10_turnover.csv')
    if not turnover_df_f.empty:
        st.info("Bottom 10 SKUs by Inventory Turnover: Spot slow-moving or stagnant products that may need attention.")
        bottom10 = turnover_df_f.sort_values('inventory_turnover', ascending=True).head(10)
        fig5 = px.bar(bottom10, x='product_id', y='inventory_turnover', color='store_id',
                     title='Bottom 10 SKUs by Inventory Turnover', text='inventory_turnover')
        fig5.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig5.update_layout(legend=dict(x=1.02, y=1, xanchor='left', yanchor='top'), xaxis_tickangle=45)
        st.plotly_chart(fig5, use_container_width=True, key='fig5')
        # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
        # fig_to_image_download(fig5, 'bottom_10_turnover.png')
        df_to_csv_download(bottom10, 'bottom_10_turnover.csv')
    if not turnover_df_f.empty:
        st.info("Heatmap of Inventory Turnover by Store and Product: Alternative color scheme for turnover heatmap.")
        heatmap_data = turnover_df_f.pivot(index='store_id', columns='product_id', values='inventory_turnover')
        fig8 = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='YlGnBu',
            text=np.round(heatmap_data.values, 1),
            texttemplate="%{text}",
            showscale=True,
            colorbar=dict(title='Turnover Ratio')
        ))
        fig8.update_layout(title='Heatmap of Inventory Turnover by Store and Product',
                          xaxis_title='Product ID', yaxis_title='Store ID')
        st.plotly_chart(fig8, use_container_width=True, key='fig8')
        # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
        # fig_to_image_download(fig8, 'heatmap_turnover_store_product.png')
        df_to_csv_download(heatmap_data.reset_index(), 'heatmap_turnover_store_product.csv')
    if not turnover_df_f.empty:
        st.info("Top 10 SKUs by Inventory Turnover – Store S003: Fastest-moving products in Store S003.")
        s003 = turnover_df_f[turnover_df_f['store_id'].str.strip() == 'S003']
        top10_s003 = s003.sort_values('inventory_turnover', ascending=False).head(10)
        fig6b = px.bar(top10_s003, x='product_id', y='inventory_turnover',
                      title='Top 10 SKUs by Inventory Turnover – Store S003',
                      labels={'product_id': 'Product ID', 'inventory_turnover': 'Turnover Ratio'})
        fig6b.update_traces(texttemplate='%{y:.1f}', textposition='outside')
        fig6b.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig6b, use_container_width=True, key='fig6b')
        # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
        # fig_to_image_download(fig6b, 'top_10_turnover_s003.png')
        df_to_csv_download(top10_s003, 'top_10_turnover_s003.csv')
    if not turnover_df_f.empty:
        st.info("Bottom 10 SKUs by Inventory Turnover – Store S003: Slowest-moving products in Store S003.")
        s003 = turnover_df_f[turnover_df_f['store_id'].str.strip() == 'S003']
        bottom10_s003 = s003.sort_values('inventory_turnover', ascending=True).head(10)
        fig7b = px.bar(bottom10_s003, x='product_id', y='inventory_turnover',
                      title='Bottom 10 SKUs by Inventory Turnover – Store S003',
                      labels={'product_id': 'Product ID', 'inventory_turnover': 'Turnover Ratio'})
        fig7b.update_traces(texttemplate='%{y:.1f}', textposition='outside')
        fig7b.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig7b, use_container_width=True, key='fig7b')
        # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
        # fig_to_image_download(fig7b, 'bottom_10_turnover_s003.png')
        df_to_csv_download(bottom10_s003, 'bottom_10_turnover_s003.csv')

# --- Inventory & Overstock Tab ---
with tabs[1]:
    if not snapshot_df_f.empty:
        st.info("Total Inventory Over Time by Product: Track inventory trends and spot stockouts or surpluses.")
        st.image('dashboard/graphs/plot_total_inventory_by_product.png', caption='Total Inventory Over Time by Product', use_container_width=True)

    if not low_inventory_df_f.empty:
        st.info("Low Inventory Analysis: Identify products at risk of stockout.")
        inventory_cols = [col for col in low_inventory_df_f.columns if 'inventory' in col.lower()]
        if len(inventory_cols) > 1:
            low_inventory_df_f['Inventory_Level'] = low_inventory_df_f[inventory_cols].sum(axis=1)
        else:
            low_inventory_df_f['Inventory_Level'] = low_inventory_df_f[inventory_cols[0]]
        avg_inventory = low_inventory_df_f.groupby('product_id')['Inventory_Level'].mean().sort_values(ascending=False).reset_index()
        fig2 = px.bar(avg_inventory, x='product_id', y='Inventory_Level',
                      title='Average Inventory Level by Product',
                      labels={'product_id': 'Product ID', 'Inventory_Level': 'Average Inventory Level'},
                      text='Inventory_Level', color='product_id', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig2.update_layout(showlegend=False, xaxis_tickangle=45, yaxis_showgrid=True)
        st.plotly_chart(fig2, use_container_width=True, key='fig2')
        # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
        # fig_to_image_download(fig2, 'low_inventory_analysis.png')
        df_to_csv_download(avg_inventory, 'low_inventory_analysis.csv')

    if not overstock_df_f.empty:
        st.info("Stock Units vs Avg Daily Demand (Overstock Highlighted): Visualize overstocked items and their demand.")
        color_map = {'Normal': '#A9DFBF', 'Overstocked': '#F1948A'}
        overstock_df_f['inventory_health_flag'] = overstock_df_f['inventory_health_flag'].str.strip().str.capitalize()
        fig9 = px.scatter(overstock_df_f, x='avg_inventory_7d', y='total_units_sold_7d', color='inventory_health_flag',
                         title='Stock Units vs Average Daily Demand',
                         labels={'avg_inventory_7d': 'Stock Units', 'total_units_sold_7d': 'Avg Daily Demand'},
                         color_discrete_map=color_map, symbol='inventory_health_flag')
        fig9.update_layout(legend=dict(x=1.02, y=1, xanchor='left', yanchor='top'), yaxis_showgrid=True)
        st.plotly_chart(fig9, use_container_width=True, key='fig9')
        # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
        # fig_to_image_download(fig9, 'overstock_scatter.png')
        df_to_csv_download(overstock_df_f, 'overstock_scatter.csv')

# --- Forecast Accuracy Tab ---
with tabs[2]:
    st.info("Forecast Accuracy Classification: See the distribution of accurate, underforecasted, and overforecasted cases.")
    st.image('dashboard/graphs/forecast_accuracy_classification_final.png', caption='Forecast Accuracy Classification', use_container_width=True)

    if not forecast_sample_f.empty:
        st.info("Forecast Error % Over Time by Product: Track forecast error trends and spot persistent bias.")
        forecast_sample_f['date'] = pd.to_datetime(forecast_sample_f['date'], errors='coerce', dayfirst=True)
        if 'error' in forecast_sample_f.columns and 'product_id' in forecast_sample_f.columns:
            fig11 = px.scatter(forecast_sample_f, x='date', y='error', color='product_id',
                              title='Forecast Error % Over Time by Product',
                              labels={'error': 'Forecast Error %'})
            fig11.add_hline(y=10, line_dash='dash', line_color='green', annotation_text='+10% Threshold', annotation_position='top left')
            fig11.add_hline(y=-10, line_dash='dash', line_color='red', annotation_text='-10% Threshold', annotation_position='bottom left')
            fig11.update_layout(legend=dict(x=1.02, y=1, xanchor='left', yanchor='top'), xaxis_tickangle=45)
            st.plotly_chart(fig11, use_container_width=True)
            # Image download disabled on Streamlit Cloud (Kaleido/Chrome not supported)
            # fig_to_image_download(fig11, 'forecast_error_trend_by_product_final.png')
            df_to_csv_download(forecast_sample_f, 'forecast_error_trend_by_product_final.csv')

# --- ML Model Insights Tab ---
with tabs[3]:
    st.header("ML Model Insights")
    st.subheader("Model Performance")
    st.image("ML MODEL/train_test_accuracy.png", caption="Train/Test Accuracy", use_container_width=True)
    st.image("ML MODEL/confusion_matrix.png", caption="Confusion Matrix", use_container_width=True)

    st.subheader("Recent Model Predictions")
    try:
        ml_pred_df = pd.read_csv("ML MODEL/Forecast_Deviation_with_predictions.csv")
        # Show only key columns if present
        display_cols = [col for col in ["date", "product_id", "actual", "forecast", "error", "predicted_class", "store_id"] if col in ml_pred_df.columns]
        if display_cols:
            st.dataframe(ml_pred_df[display_cols].head(50))
        else:
            st.dataframe(ml_pred_df.head(50))
        # Highlight high-risk predictions if possible
        if "predicted_class" in ml_pred_df.columns:
            st.info("High-risk predictions (Underforecasted/Overforecasted):")
            st.dataframe(ml_pred_df[ml_pred_df["predicted_class"].str.lower().isin(["underforecasted", "overforecasted"])]
                         [display_cols].head(20))
    except Exception as e:
        st.warning(f"Could not load ML predictions: {e}")

# --- User Notes/Comments ---
st.markdown("---")
st.subheader("User Notes & Comments")
user_notes = st.text_area("Add your notes or comments here:", "")
if user_notes:
    st.success("Your note has been saved (locally in this session).")

# --- Footer ---
st.markdown("""
<div style='text-align:center; color: #888; font-size: 0.9em; margin-top: 2em;'>
  &copy; 2024 Inventory Analytics Dashboard | Powered by Streamlit & Plotly
</div>
""", unsafe_allow_html=True)

# --- (END) ---
# (The plotting code for each graph should be updated to use the filtered dataframes and include download buttons and enhanced tooltips/annotations as described above.)
