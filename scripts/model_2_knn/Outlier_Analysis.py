import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

def analyze_outliers():
    """Analyze outliers in the maintenance cost dataset"""
    print("Outlier Analysis for Maintenance Cost Dataset")
    print("=" * 50)
    
    # Load data
    df = pd.read_excel("../notebooks/data/SERVICE_ORDER_CLEAN.xlsx")
    print(f"Total records: {len(df):,}")
    
    # Focus on key numerical columns
    numerical_columns = ['GRAND TOTAL', 'PRODUCT QUANTITY', 'UNIT VALUE', 'ODOMETER']
    
    outlier_summary = {}
    
    for column in numerical_columns:
        if column in df.columns:
            print(f"\n{column} Analysis:")
            print("-" * 30)
            
            data = df[column].dropna()
            
            # Basic statistics
            print(f"Count: {len(data):,}")
            print(f"Mean: ${data.mean():,.2f}" if 'VALUE' in column or 'TOTAL' in column else f"Mean: {data.mean():,.2f}")
            print(f"Median: ${data.median():,.2f}" if 'VALUE' in column or 'TOTAL' in column else f"Median: {data.median():,.2f}")
            print(f"Std Dev: ${data.std():,.2f}" if 'VALUE' in column or 'TOTAL' in column else f"Std Dev: {data.std():,.2f}")
            
            # IQR method for outliers
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers_iqr = data[(data < lower_bound) | (data > upper_bound)]
            outlier_percentage_iqr = len(outliers_iqr) / len(data) * 100
            
            print(f"IQR Outliers: {len(outliers_iqr):,} ({outlier_percentage_iqr:.2f}%)")
            print(f"IQR Bounds: {lower_bound:.2f} - {upper_bound:.2f}")
            
            # Z-score method (for normal distributions)
            z_scores = np.abs(stats.zscore(data))
            outliers_z = data[z_scores > 3]
            outlier_percentage_z = len(outliers_z) / len(data) * 100
            
            print(f"Z-score Outliers (>3): {len(outliers_z):,} ({outlier_percentage_z:.2f}%)")
            
            # Extreme values
            print(f"Min value: {data.min():.2f}")
            print(f"Max value: {data.max():,.2f}")
            print(f"99th percentile: {data.quantile(0.99):,.2f}")
            print(f"95th percentile: {data.quantile(0.95):,.2f}")
            
            outlier_summary[column] = {
                'iqr_outliers': len(outliers_iqr),
                'iqr_percentage': outlier_percentage_iqr,
                'z_outliers': len(outliers_z),
                'z_percentage': outlier_percentage_z,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound
            }
    
    return outlier_summary

def treat_outliers_iqr(df, columns, method='cap'):
    """
    Treat outliers using IQR method
    
    Methods:
    - 'cap': Cap outliers to the IQR bounds
    - 'remove': Remove outlier records
    - 'winsorize': Replace with percentile values
    """
    df_treated = df.copy()
    treatment_summary = {}
    
    print(f"\nTreating outliers using method: {method}")
    print("-" * 40)
    
    for column in columns:
        if column in df.columns:
            original_count = len(df_treated)
            data = df_treated[column]
            
            # Calculate IQR bounds
            Q1 = data.quantile(0.25)
            Q3 = data.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # Count outliers before treatment
            outliers_before = len(data[(data < lower_bound) | (data > upper_bound)])
            
            if method == 'cap':
                # Cap outliers to bounds
                df_treated[column] = df_treated[column].clip(lower=lower_bound, upper=upper_bound)
                outliers_after = 0
                records_removed = 0
                
            elif method == 'remove':
                # Remove outlier records
                mask = (df_treated[column] >= lower_bound) & (df_treated[column] <= upper_bound)
                df_treated = df_treated[mask]
                records_removed = original_count - len(df_treated)
                outliers_after = 0
                
            elif method == 'winsorize':
                # Replace with 5th and 95th percentiles
                p5 = data.quantile(0.05)
                p95 = data.quantile(0.95)
                df_treated[column] = df_treated[column].clip(lower=p5, upper=p95)
                outliers_after = 0
                records_removed = 0
            
            treatment_summary[column] = {
                'outliers_before': outliers_before,
                'outliers_after': outliers_after,
                'records_removed': records_removed if method == 'remove' else 0,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound
            }
            
            print(f"{column}:")
            print(f"  Outliers before: {outliers_before}")
            print(f"  Outliers after: {outliers_after}")
            if method == 'remove':
                print(f"  Records removed: {records_removed}")
    
    print(f"\nFinal dataset: {len(df_treated):,} records")
    return df_treated, treatment_summary

def outlier_analysis():
    """Main function to analyze and treat outliers"""
    
    # Analyze outliers
    outlier_summary = analyze_outliers()
    print(outlier_summary)
    
    # Load data for treatment
    df = pd.read_excel("../notebooks/data/SERVICE_ORDER_CLEAN.xlsx")
    
    # Define columns to treat
    cost_columns = ['GRAND TOTAL', 'UNIT VALUE', 'PRODUCT QUANTITY']
    
    # Show treatment options
    print(f"\n" + "=" * 50)
    print("Outlier Treatment Options:")
    print("1. Cap outliers (replace with IQR bounds)")
    print("2. Remove outlier records") 
    print("3. Winsorize (replace with 5th/95th percentiles)")
    print("=" * 50)
    
    # For demonstration, use capping method
    df_treated, treatment_summary = treat_outliers_iqr(df, cost_columns, method='cap')
    
    # Save treated dataset
    output_file = "../notebooks/data/SERVICE_ORDER_BASE_outliers_treated.xlsx"
    df_treated.to_excel(output_file, index=False)
    print(f"\nTreated dataset saved to: {output_file}")
    
    return df_treated, treatment_summary
