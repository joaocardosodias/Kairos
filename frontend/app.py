# ======================================================================================
# PART 0: GENERAL IMPORTS
# ======================================================================================
# All libraries required for the model and Streamlit
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, accuracy_score, precision_recall_curve
from sklearn.preprocessing import LabelEncoder

# ======================================================================================
# PART 1: MODEL LOGIC
# ======================================================================================
# This section contains all functions to load raw data,
# process it, train the model, and save the results.

def model_create_breakdown_target(df):
    """Creates the target variable for the model."""
    print("MODEL: Creating target variable...")
    df_clean = df.dropna(subset=['SERVICE_ORDER_year', 'SERVICE_ORDER_month', 'SERVICE_ORDER_day']).copy()
    date_column_map = {'SERVICE_ORDER_year': 'year', 'SERVICE_ORDER_month': 'month', 'SERVICE_ORDER_day': 'day'}
    
    df_clean['service_date'] = pd.to_datetime(
        df_clean[['SERVICE_ORDER_year', 'SERVICE_ORDER_month', 'SERVICE_ORDER_day']].rename(columns=date_column_map),
        errors='coerce'
    )
    
    df_clean = df_clean.dropna(subset=['service_date']).sort_values(['ASSET_CODE_encoded', 'service_date'])
    results = []

    for vehicle_id in df_clean['ASSET_CODE_encoded'].unique():
        vehicle_data = df_clean[df_clean['ASSET_CODE_encoded'] == vehicle_id]

        for idx, record in vehicle_data.iterrows():
            current_date = record['service_date']
            
            future_date = current_date + timedelta(days=30)
            future_records = vehicle_data[
                (vehicle_data['service_date'] > current_date) &
                (vehicle_data['service_date'] <= future_date)
            ]

            will_breakdown = (future_records['PREVENTIVE_CORRECTIVE MAINTENANCE'] == 0).any()
            
            base_record = record.to_dict()
            base_record['target'] = int(will_breakdown)
            base_record['vehicle_id'] = record['ASSET_CODE_encoded']
            base_record['model_type'] = record['MODEL_TYPE_CODE_encoded']
            base_record['tier'] = record['TIER']
            base_record['asset_status'] = record['ASSET STATUS']
            base_record['maintenance_type'] = record['PREVENTIVE_CORRECTIVE MAINTENANCE']
            base_record['cost'] = record['GRAND TOTAL']
            base_record['product_code'] = record['PRODUCT_CODE_encoded']

            results.append(base_record)
            
    target_df = pd.DataFrame(results)
    print(f"MODEL: Target variable created. Breakdown rate: {target_df['target'].mean():.1%}")
    return target_df

def model_create_features(df):
    """Performs feature engineering for the model."""
    print("MODEL: Starting feature engineering...")
    df_features = df.copy().sort_values(['vehicle_id', 'service_date'])
    
    first_service = df_features.groupby('vehicle_id')['service_date'].transform('min')
    df_features['vehicle_age_days'] = (df_features['service_date'] - first_service).dt.days

    df_features['days_since_last'] = df_features.groupby('vehicle_id')['service_date'].diff().dt.days.fillna(999)

    results = []

    for vehicle_id in df_features['vehicle_id'].unique():
        vehicle_data = df_features[df_features['vehicle_id'] == vehicle_id].copy()
        
        for idx, row in vehicle_data.iterrows():
            current_date = row['service_date']
            
            past_90_days = current_date - timedelta(days=90)
            past_30_days = current_date - timedelta(days=30)
            
            hist_90 = vehicle_data[(vehicle_data['service_date'] >= past_90_days) & (vehicle_data['service_date'] < current_date)]
            hist_30 = vehicle_data[(vehicle_data['service_date'] >= past_30_days) & (vehicle_data['service_date'] < current_date)]
            all_previous = vehicle_data[vehicle_data['service_date'] < current_date]
            
            recent_breakdowns_30d = (hist_30['maintenance_type'] == 0).sum()
            recent_breakdowns_90d = (hist_90['maintenance_type'] == 0).sum()
            total_breakdowns = (all_previous['maintenance_type'] == 0).sum()
            
            recent_services = len(hist_90)
            
            avg_cost_30d = hist_30['cost'].mean() if len(hist_30) > 0 else 0
            avg_cost_90d = hist_90['cost'].mean() if len(hist_90) > 0 else 0
            cost_trend = avg_cost_30d - avg_cost_90d if avg_cost_90d > 0 else 0
            
            last_breakdown = all_previous[all_previous['maintenance_type'] == 0]
            if len(last_breakdown) > 0:
                days_since_breakdown = (current_date - last_breakdown['service_date'].max()).days
            else:
                days_since_breakdown = 999
            
            vehicle_age_months = max(row['vehicle_age_days'] / 30, 1)
            service_intensity = len(all_previous) / vehicle_age_months
            
            row_dict = row.to_dict()
            row_dict.update({
                'recent_breakdowns_30d': recent_breakdowns_30d,
                'recent_breakdowns_90d': recent_breakdowns_90d,
                'total_breakdowns': total_breakdowns,
                'recent_services': recent_services,
                'avg_cost_30d': avg_cost_30d,
                'cost_trend': cost_trend,
                'days_since_breakdown': days_since_breakdown,
                'service_intensity': service_intensity
            })
            results.append(row_dict)
    
    df_final = pd.DataFrame(results)
    print("MODEL: Feature engineering completed.")
    return df_final.fillna(0)

def preprocess_raw_data(df_raw):
    """
    Transforms a raw DataFrame into the semi-processed format
    expected by the model pipeline.
    """
    print("PREPROCESSING: Starting raw data transformation...")
    df = df_raw.copy()
    df.columns = df.columns.str.strip()

    if 'PREVENTIVE_CORRECTIVE MAINTENANCE' in df.columns:
        maintenance_map = {'PREVENTIVE': 1, 'CORRECTIVE': 0}
        df['PREVENTIVE_CORRECTIVE MAINTENANCE'] = df['PREVENTIVE_CORRECTIVE MAINTENANCE'].map(maintenance_map)

    if 'ASSET STATUS' in df.columns:
        status_map = {'ACTIVE': 1, 'INACTIVE': 0}
        df['ASSET STATUS'] = df['ASSET STATUS'].map(status_map)

    if 'TIER' in df.columns:
        tier_map = {'TIER 1 - T1': 1, 'TIER 1': 1, 'T1': 1, 'TIER 2 - T2': 2, 'TIER 2': 2, 'T2': 2}
        df['TIER'] = df['TIER'].map(tier_map)

    le = LabelEncoder()
    for col in ['ASSET CODE', 'MODEL TYPE CODE', 'PRODUCT CODE']:
        if col in df.columns:
            new_col_name = col.replace(' ', '_') + '_encoded'
            df[new_col_name] = le.fit_transform(df[col].astype(str))

    if 'SERVICE ORDER ORIGINAL DATE' in df.columns:
        s_date = pd.to_datetime(df['SERVICE ORDER ORIGINAL DATE'], format='%Y%m%d', errors='coerce')
        df['SERVICE_ORDER_year'] = s_date.dt.year
        df['SERVICE_ORDER_month'] = s_date.dt.month
        df['SERVICE_ORDER_day'] = s_date.dt.day

    df.dropna(subset=['SERVICE_ORDER_year'], inplace=True)
    print("PREPROCESSING: Raw data transformation completed.")
    return df

@st.cache_data
def run_model_pipeline_and_generate_outputs(df_raw_input):
    """
    Orchestrates the model pipeline: processing, training, and results generation.
    """
    # This function is now only called once. The spinner is moved to the upload section.
    df_processed = preprocess_raw_data(df_raw_input)

    df_target = model_create_breakdown_target(df_processed)
    df_model_input = model_create_features(df_target)

    feature_columns = [
        'model_type', 'tier', 'asset_status', 'maintenance_type', 'cost', 'product_code',
        'vehicle_age_days', 'days_since_last', 'days_since_breakdown',
        'recent_breakdowns_30d', 'recent_breakdowns_90d', 'total_breakdowns', 
        'recent_services', 'avg_cost_30d', 'cost_trend', 'service_intensity'
    ]
    
    final_feature_columns = [col for col in feature_columns if col in df_model_input.columns]
    
    df_sorted = df_model_input.sort_values('service_date')
    if df_sorted['service_date'].dt.tz is not None:
        df_sorted['service_date'] = df_sorted['service_date'].dt.tz_localize(None)

    recent_cutoff = df_sorted['service_date'].max() - timedelta(days=730)
    df_recent = df_sorted[df_sorted['service_date'] >= recent_cutoff]
    
    split_point = int(len(df_recent) * 0.8)
    train_data = df_recent.iloc[:split_point]
    test_data = df_recent.iloc[split_point:].copy()
    
    X_train, y_train = train_data[final_feature_columns], train_data['target']
    X_test, y_test = test_data[final_feature_columns], test_data['target']
    
    rf_model = RandomForestClassifier(
        n_estimators=300, max_depth=None, min_samples_split=2, min_samples_leaf=1,
        max_features='sqrt', class_weight={0: 1, 1: 6}, bootstrap=True,
        random_state=42, n_jobs=-1
    )
    rf_model.fit(X_train, y_train)

    y_prob = rf_model.predict_proba(X_test)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_prob)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
    
    if np.all(np.isnan(f1_scores)):
        optimal_threshold = 0.5
    else:
        optimal_threshold = thresholds[np.nanargmax(f1_scores)]

    y_pred = (y_prob >= optimal_threshold).astype(int)

    # Prepare results for the application
    predictions_output = test_data[['ASSET NAME', 'MANUFACTURER NAME', 'MODEL TYPE DESCRIPTION', 'days_since_breakdown', 'total_breakdowns', 'vehicle_age_days', 'days_since_last']].copy()
    predictions_output.rename(columns={'ASSET NAME': 'License Plate', 'MANUFACTURER NAME': 'Manufacturer', 'MODEL TYPE DESCRIPTION': 'Model', 'days_since_breakdown': 'Days Since Last Breakdown', 'total_breakdowns': 'Total Breakdowns', 'vehicle_age_days': 'Age (days)', 'days_since_last': 'Days Since Last Maintenance'}, inplace=True)
    
    predictions_output['Breakdown Prediction (30 days)'] = ['Yes' if p == 1 else 'No' for p in y_pred]
    predictions_output['Breakdown Probability'] = y_prob
    
    def suggest_action(prob):
        if prob > 0.90: return "Immediate Inspection"
        elif prob > 0.70: return "Schedule Inspection"
        elif prob > 0.50: return "Monitor Closely"
        else: return "No Immediate Action"
    predictions_output['Suggested Action'] = predictions_output['Breakdown Probability'].apply(suggest_action)
    predictions_output['Age (years)'] = (predictions_output['Age (days)'] / 365).round(1)
    predictions_output.drop(columns=['Age (days)'], inplace=True)
    
    return predictions_output.sort_values(by='Breakdown Probability', ascending=False).reset_index(drop=True)


# ======================================================================================
# PART 2: STREAMLIT APPLICATION LOGIC
# ======================================================================================
st.set_page_config(page_title="Predictive Maintenance Dashboard", page_icon="🚛", layout="wide")

# Initialize session state variables
if 'data_loaded' not in st.session_state:
    st.session_state['data_loaded'] = False
if 'predictions_df' not in st.session_state:
    st.session_state['predictions_df'] = None
if 'raw_df' not in st.session_state:
    st.session_state['raw_df'] = None

# --- Page 0: File Upload ---
if not st.session_state.data_loaded:
    st.title("🚛 Predictive Maintenance Dashboard - Data Upload")
    st.markdown("To get started, please upload the fleet data file in Excel (`.xlsx`) or CSV (`.csv`) format.")

    uploaded_file = st.file_uploader("Select the fleet data file", type=['xlsx', 'csv'])

    if uploaded_file is not None:
        try:
            with st.spinner("Loading and validating file..."):
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, low_memory=False)
                else:
                    df = pd.read_excel(uploaded_file)

            required_cols_raw = [
                'ASSET CODE', 'ASSET NAME', 'MANUFACTURER NAME', 'MODEL TYPE DESCRIPTION', 
                'SERVICE ORDER ORIGINAL DATE', 'PREVENTIVE_CORRECTIVE MAINTENANCE', 'GRAND TOTAL',
                'MANUFACTURE YEAR', 'MANUFACTURER CODE'
            ]
            df.columns = df.columns.str.strip()
            missing_cols = [col for col in required_cols_raw if col not in df.columns]

            if not missing_cols:
                st.session_state['raw_df'] = df
                
                # --- OPTIMIZATION: Run the model pipeline ONLY ONCE here ---
                with st.spinner("Running model pipeline... This may take a few minutes."):
                    predictions = run_model_pipeline_and_generate_outputs(df)
                    st.session_state['predictions_df'] = predictions

                st.session_state['data_loaded'] = True
                st.success("File loaded and processed! The dashboard will start.")
                st.rerun()
            else:
                st.error(f"Validation Error: The uploaded file is missing columns: **{', '.join(missing_cols)}**")

        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")

# --- Main Dashboard (displayed after data is loaded and processed) ---
else:
    # Retrieve pre-computed data from session state
    fleet_df_raw = st.session_state['raw_df']
    predictions_df = st.session_state['predictions_df']

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select a page", ["Fleet Dashboard", "Risk Predictions"])
    st.sidebar.markdown("---")
    st.sidebar.info("This panel presents fleet analytics and results from the predictive maintenance model.")

    if page == "Fleet Dashboard":
        st.title("🚛 General Fleet Dashboard")
        st.markdown("An overview of the main characteristics and maintenance metrics of the vehicle fleet.")

        st.header("General Metrics")
        total_vehicles = fleet_df_raw['ASSET CODE'].nunique()
        avg_age = (pd.Timestamp.now().year - fleet_df_raw['MANUFACTURE YEAR'].dropna()).mean()
        total_cost = fleet_df_raw['GRAND TOTAL'].sum()
        at_risk_unique_vehicles = predictions_df[predictions_df['Breakdown Prediction (30 days)'] == 'Yes']['License Plate'].nunique()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Unique Vehicles", f"{total_vehicles}")
        col2.metric("Average Fleet Age", f"{avg_age:.1f} years")
        col3.metric("Total Maintenance Cost", f"R$ {total_cost/1e6:.2f} M")
        col4.metric(
            "Fleet at Immediate Risk",
            f"{(at_risk_unique_vehicles / total_vehicles) * 100:.1f}%" if total_vehicles > 0 else "0.0%",
            help="Percentage of unique vehicles with a predicted breakdown in the next 30 days."
        )

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Top 10 Manufacturers by Maintenance Cost")
            if 'MANUFACTURER CODE' in fleet_df_raw.columns:
                top_brands = fleet_df_raw.groupby('MANUFACTURER CODE')['GRAND TOTAL'].sum().nlargest(10).sort_values()
                fig, ax = plt.subplots(figsize=(8, 6))
                top_brands.plot(kind='barh', ax=ax, color=sns.color_palette("viridis", len(top_brands)))
                ax.set_title("Accumulated Cost by Manufacturer Code")
                ax.set_xlabel("Total Cost (R$)")
                ax.set_ylabel("Manufacturer Code")
                ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x/1e6:.1f}M'))
                st.pyplot(fig)
        with col2:
            st.subheader("Maintenance Type Analysis")
            maintenance_counts = fleet_df_raw['PREVENTIVE_CORRECTIVE MAINTENANCE'].value_counts()
            corrective_count = maintenance_counts.get('CORRECTIVE', 0)
            preventive_count = maintenance_counts.get('PREVENTIVE', 0)
            pie_counts = [corrective_count, preventive_count]
            pie_labels = [f"Corrective ({corrective_count:,})", f"Preventive ({preventive_count:,})"]

            fig, ax = plt.subplots(figsize=(8, 6))
            ax.pie(pie_counts, labels=pie_labels, autopct='%1.1f%%', startangle=90, colors=['#FF6B6B', '#4ECDC4'], explode=(0.05, 0))
            ax.axis('equal')
            ax.set_title("Proportion of Corrective vs. Preventive Maintenance")
            st.pyplot(fig)

    elif page == "Risk Predictions":
        st.title("📋 Action and Risk Panel")
        st.markdown("Breakdown predictions for the next 30 days and the main risk factors for each vehicle.")
        
        st.sidebar.header("Filters")
        show_risk_only = st.sidebar.checkbox("Show only vehicles at risk of breakdown", value=False)
        search_plate = st.sidebar.text_input("Search by Vehicle License Plate")

        filtered_df = predictions_df.copy()
        if show_risk_only:
            filtered_df = filtered_df[filtered_df['Breakdown Prediction (30 days)'] == 'Yes']
        if search_plate:
            filtered_df['License Plate'] = filtered_df['License Plate'].astype(str)
            filtered_df = filtered_df[filtered_df['License Plate'].str.contains(search_plate.upper(), na=False)]

        st.subheader(f"Vehicle List ({'High Risk Only' if show_risk_only else 'Entire Fleet'})")
        display_columns = ['License Plate', 'Manufacturer', 'Model', 'Breakdown Probability', 'Total Breakdowns', 'Age (years)', 'Days Since Last Maintenance', 'Breakdown Prediction (30 days)']
        
        def color_risk(val):
            if val == 'Yes': return 'background-color: #F005; color: white; font-weight: bold;'
            return ''
        
        styled_df = filtered_df[display_columns].style.applymap(color_risk, subset=['Breakdown Prediction (30 days)'])

        st.dataframe(styled_df, use_container_width=True, height=600)
        st.caption("The table is sorted from highest to lowest breakdown probability.")