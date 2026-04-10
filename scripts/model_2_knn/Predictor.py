import pandas as pd
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, accuracy_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


def Prediction():
    """
    Predicts the probability that a vehicle will break down
    within the next 14 days using KNN algorithm.
    Analyzes ALL vehicles in the dataset.
    Returns: YES/NO answer with confidence level
    """

    print("VEHICLE BREAKDOWN PROBABILITY PREDICTION")
    print("Analyzing vehicles in the dataset")
    print("=" * 50)

    # Load data with preference for processed datasets
    try:
        df = pd.read_excel("../notebooks/data/SERVICE_ORDER_CLEAN.xlsx")
        print(f"Total records loaded (clean): {len(df):,}")
        data_source = "clean"
    except FileNotFoundError:
        try:
            df = pd.read_excel("../notebooks/data/SERVICE_ORDER_BASE_outliers_treated.xlsx")
            print(f"Total records loaded (outliers treated): {len(df):,}")
            data_source = "outliers_treated"
        except FileNotFoundError:
            df = pd.read_excel("../notebooks/data/SERVICE_ORDER_BASE.xlsx")
            print(f"Total records loaded (original): {len(df):,}")
            print("Note: Using original dataset - run data processing first for better results")
            data_source = "original"

    # Check available columns
    print(f"\nAvailable columns: {list(df.columns)}")

    # Handle different possible column names for dates
    date_columns = []
    if 'SERVICE_ORDER_year' in df.columns and 'SERVICE_ORDER_month' in df.columns and 'SERVICE_ORDER_day' in df.columns:
        date_columns = ['SERVICE_ORDER_year', 'SERVICE_ORDER_month', 'SERVICE_ORDER_day']
        print("Using processed date columns")
    elif 'SERVICE ORDER ORIGINAL DATE' in df.columns:
        # Convert the original date format
        print("Converting original date format...")
        # SERVICE ORDER ORIGINAL DATE -> datetime
        # Format : 20200312 (12 March 2020)
        print(f"Converting SERVICE ORDER DATE format")
        print(f"Before conversion: {df['SERVICE ORDER ORIGINAL DATE'].head(5)}")
        df['SERVICE ORDER ORIGINAL DATE'] = df['SERVICE ORDER ORIGINAL DATE'].apply(lambda x: datetime.strptime(str(x), '%Y%m%d') if pd.notnull(x) else x)
        print(f"After conversion: {df['SERVICE ORDER ORIGINAL DATE'].head(5)}")
        df['SERVICE ORDER ORIGINAL DATE'] = pd.to_datetime(df['SERVICE ORDER ORIGINAL DATE'], errors='coerce')
        df['SERVICE_ORDER_year'] = df['SERVICE ORDER ORIGINAL DATE'].dt.year
        df['SERVICE_ORDER_month'] = df['SERVICE ORDER ORIGINAL DATE'].dt.month
        df['SERVICE_ORDER_day'] = df['SERVICE ORDER ORIGINAL DATE'].dt.day
        print(f"Year : {df['SERVICE_ORDER_year'].head(5)} Month : {df['SERVICE_ORDER_month'].head(5)} Day : {df['SERVICE_ORDER_day'].head(5)}")
        date_columns = ['SERVICE_ORDER_year', 'SERVICE_ORDER_month', 'SERVICE_ORDER_day']
        # Drop the original date column to avoid confusion
        df = df.drop(columns=['SERVICE ORDER ORIGINAL DATE'])
    else:
        print("Error: No recognizable date columns found!")
        print("Available columns:", df.columns.tolist())
        return None

    # Handle different possible column names for vehicle codes
    if 'ASSET_CODE_encoded' in df.columns:
        vehicle_id_col = 'ASSET_CODE_encoded'
        print("Using encoded vehicle IDs")
    elif 'ASSET CODE' in df.columns:
        vehicle_id_col = 'ASSET CODE'
        print("Using original vehicle IDs")
    else:
        print("Error: No vehicle ID column found!")
        print("Available columns:", df.columns.tolist())
        return None

    # Use ALL vehicles instead of filtering by manufacturer
    all_vehicles_data = df.copy()
    print(f"Total vehicle records: {len(all_vehicles_data):,}")
    print(f"Unique vehicles: {all_vehicles_data[vehicle_id_col].nunique():,}")

    # Convert date columns to datetime
    try:
        # Ensure all date columns exist and have valid values
        valid_date_mask = (
            all_vehicles_data[date_columns[0]].notna() &
            all_vehicles_data[date_columns[1]].notna() &
            all_vehicles_data[date_columns[2]].notna()
        )

        print(f"All vehcles data date columns 0: {all_vehicles_data[date_columns[0]].head}")
        print(f"All vehcles data date columns 1: {all_vehicles_data[date_columns[1]].head}")
        print(f"All vehcles data date columns 2: {all_vehicles_data[date_columns[2]].head}")

        print(f"Records with valid dates: {valid_date_mask.sum():,}")
        all_vehicles_data = all_vehicles_data[valid_date_mask].copy()

        # Create datetime column
        all_vehicles_data['SERVICE_ORDER_date'] = pd.to_datetime(
            all_vehicles_data[date_columns].astype(int),
            errors='coerce'
        )

        # Remove any rows where date conversion failed
        all_vehicles_data = all_vehicles_data[all_vehicles_data['SERVICE_ORDER_date'].notna()].copy()
        print(f"Records with successfully converted dates: {len(all_vehicles_data):,}")

    except Exception as e:
        print(f"Error converting dates: {e}")
        print("Attempting alternative date conversion...")
        try:
            # Alternative method using string concatenation
            date_strings = (
                all_vehicles_data[date_columns[0]].astype(str) + '-' +
                all_vehicles_data[date_columns[1]].astype(str).str.zfill(2) + '-' +
                all_vehicles_data[date_columns[2]].astype(str).str.zfill(2)
            )
            all_vehicles_data['SERVICE_ORDER_date'] = pd.to_datetime(date_strings, errors='coerce')
            all_vehicles_data = all_vehicles_data[all_vehicles_data['SERVICE_ORDER_date'].notna()].copy()
            print(f"Successfully converted dates using alternative method: {len(all_vehicles_data):,}")
        except Exception as e2:
            print(f"Alternative date conversion also failed: {e2}")
            return None

    # Sort by vehicle and date
    all_vehicles_data = all_vehicles_data.sort_values([vehicle_id_col, 'SERVICE_ORDER_date']).reset_index(drop=True)

    # Check date range
    min_date = all_vehicles_data['SERVICE_ORDER_date'].min()
    max_date = all_vehicles_data['SERVICE_ORDER_date'].max()
    print(f"Date range: {min_date.date()} to {max_date.date()}")

    # Create features for each vehicle service record
    vehicle_features = []
    print("\nCreating features for vehicle breakdown prediction...")






    # TO MODIFY FOR MODEL 2 :

    # Process vehicles in batches to show progress
    unique_vehicles = all_vehicles_data[vehicle_id_col].unique()
    batch_size = max(1, len(unique_vehicles) // 10)  # 10% batches

    for batch_idx, vehicle_id in enumerate(unique_vehicles):
        if batch_idx % batch_size == 0:
            progress = (batch_idx / len(unique_vehicles)) * 100
            print(f"Processing vehicles... {progress:.1f}% complete")

        vehicle_data = all_vehicles_data[all_vehicles_data[vehicle_id_col] == vehicle_id].copy()
        vehicle_data = vehicle_data.sort_values('SERVICE_ORDER_date').reset_index(drop=True)

        for i in range(len(vehicle_data)):
            current_record = vehicle_data.iloc[i]
            current_date = current_record['SERVICE_ORDER_date']

            # Calculate days since last service (if any)
            if i > 0:
                days_since_last = (current_date - vehicle_data.iloc[i-1]['SERVICE_ORDER_date']).days
            else:
                days_since_last = 0

            # Count services in last 30 days
            services_last_30 = len(vehicle_data[
                (vehicle_data['SERVICE_ORDER_date'] < current_date) &
                (vehicle_data['SERVICE_ORDER_date'] >= current_date - timedelta(days=30))
            ])

            # Count services in last 90 days
            services_last_90 = len(vehicle_data[
                (vehicle_data['SERVICE_ORDER_date'] < current_date) &
                (vehicle_data['SERVICE_ORDER_date'] >= current_date - timedelta(days=90))
            ])

            # Average cost of last 3 services
            prev_services = vehicle_data[vehicle_data['SERVICE_ORDER_date'] < current_date]
            if len(prev_services) >= 3:
                avg_cost_last_3 = prev_services.tail(3)['GRAND TOTAL'].mean()
            elif len(prev_services) > 0:
                avg_cost_last_3 = prev_services['GRAND TOTAL'].mean()
            else:
                avg_cost_last_3 = 0

            # Check if there's a breakdown within next 14 days
            future_services = vehicle_data[
                (vehicle_data['SERVICE_ORDER_date'] > current_date) &
                (vehicle_data['SERVICE_ORDER_date'] <= current_date + timedelta(days=14))
            ]

            # Consider it a breakdown if there's a corrective maintenance
            breakdown_next_14_days = 0
            if len(future_services) > 0:
                # Check if any future service is corrective
                if 'PREVENTIVE_CORRECTIVE MAINTENANCE' in vehicle_data.columns:
                    breakdown_next_14_days = int(any(future_services['PREVENTIVE_CORRECTIVE MAINTENANCE'] == 0))
                else:
                    # If no maintenance type info, assume breakdown if multiple services in 14 days
                    breakdown_next_14_days = int(len(future_services) > 1)

            # Create feature vector
            features = {
                'vehicle_id': vehicle_id,
                'service_date': current_date,
                'month_of_year': current_date.month,
                'current_cost': current_record['GRAND TOTAL'],
                'is_preventive': current_record.get('PREVENTIVE_CORRECTIVE MAINTENANCE', 1),
                'days_since_last_service': days_since_last,
                'services_last_30_days': services_last_30,
                'services_last_90_days': services_last_90,
                'avg_cost_last_3_services': avg_cost_last_3,
                'breakdown_next_14_days': breakdown_next_14_days
            }

            vehicle_features.append(features)

    print("Feature creation completed!")









    # Convert to DataFrame
    feature_df = pd.DataFrame(vehicle_features)

    # Check if we have any features created
    if len(feature_df) == 0:
        print("Error: No features were created! This might be due to:")
        print("- No valid data in the dataset")
        print("- Date conversion issues")
        print("- Missing required columns")
        return None

    print(f"Feature DataFrame created with {len(feature_df)} records")
    print(f"Feature columns: {list(feature_df.columns)}")

    # Remove records where we can't determine future breakdown (last 14 days of data)
    max_date = feature_df['service_date'].max()
    cutoff_date = max_date - timedelta(days=14)
    model_data = feature_df[feature_df['service_date'] <= cutoff_date].copy()
    
    print(f"\nDataset prepared:")
    print(f"Total service records: {len(feature_df):,}")
    print(f"Training records (excluding last 14 days): {len(model_data):,}")
    
    # Check if we have breakdown data
    if 'breakdown_next_14_days' not in model_data.columns:
        print("Error: No breakdown data found!")
        return None
    
    breakdown_cases = model_data['breakdown_next_14_days'].sum()
    breakdown_rate = model_data['breakdown_next_14_days'].mean() * 100
    print(f"Breakdown cases: {breakdown_cases:,} ({breakdown_rate:.1f}%)")

    # Check if we have enough data
    if len(model_data) < 100:
        print("Error: Not enough data for reliable prediction!")
        return None

    # Prepare features for KNN
    feature_columns = ['month_of_year', 'current_cost', 'is_preventive', 'days_since_last_service',
                      'services_last_30_days', 'services_last_90_days', 'avg_cost_last_3_services']

    X = model_data[feature_columns]
    y = model_data['breakdown_next_14_days']

    # Handle missing values
    X = X.fillna(0)

    # Scale features for KNN
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train/test split (last 20% for testing)
    test_size = max(100, int(len(X) * 0.2))
    train_size = len(X) - test_size

    X_train, X_test = X_scaled[:train_size], X_scaled[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    print(f"\nModel training:")
    print(f"Training samples: {len(X_train):,}")
    print(f"Testing samples: {len(X_test):,}")
    print(f"Features used: {len(feature_columns)}")

    # Train KNN model (using optimal k)
    k_values = [3, 5, 7, 9, 11, 15, 21]
    best_k = 5
    best_score = 0

    for k in k_values:
        if k < len(X_train):  # Ensure k is not larger than training set
            knn = KNeighborsClassifier(n_neighbors=k)
            knn.fit(X_train, y_train)
            score = knn.score(X_test, y_test)
            if score > best_score:
                best_score = score
                best_k = k

    print(f"Optimal k: {best_k} (accuracy: {best_score:.3f})")

    # Train final model with best k
    model = KNeighborsClassifier(n_neighbors=best_k)
    model.fit(X_train, y_train)

    # Evaluate model
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]  # Probability of breakdown

    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    try:
        auc_score = roc_auc_score(y_test, y_pred_proba)
    except:
        auc_score = 0

    print(f"\nModel Performance:")
    print(f"  Accuracy: {accuracy:.3f}")
    print(f"  AUC Score: {auc_score:.3f}")

    # Create visualization
    plt.figure(figsize=(20, 5))

    # Confusion Matrix
    plt.subplot(1, 4, 1)
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['No Breakdown', 'Breakdown'],
                yticklabels=['No Breakdown', 'Breakdown'])
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')

    # Probability distribution
    plt.subplot(1, 4, 2)
    plt.hist(y_pred_proba[y_test == 0], alpha=0.5, label='No Breakdown', bins=20)
    plt.hist(y_pred_proba[y_test == 1], alpha=0.5, label='Breakdown', bins=20)
    plt.xlabel('Predicted Probability of Breakdown')
    plt.ylabel('Frequency')
    plt.title('Probability Distribution')
    plt.legend()

    # Predicted vs Actual Values
    plt.subplot(1, 4, 3)
    # Create scatter plot with jitter for better visibility since we have binary outcomes
    jitter_strength = 0.05
    y_test_jittered = y_test + np.random.normal(0, jitter_strength, len(y_test))
    y_pred_proba_jittered = y_pred_proba + np.random.normal(0, jitter_strength, len(y_pred_proba))

    # Scatter plot
    plt.scatter(y_test_jittered, y_pred_proba_jittered, alpha=0.6, s=20)

    # Perfect prediction line (diagonal)
    plt.plot([0, 1], [0, 1], 'r--', lw=2, label='Perfect Prediction')

    # Add trend line
    from sklearn.linear_model import LinearRegression
    lr = LinearRegression()
    lr.fit(y_test.values.reshape(-1, 1), y_pred_proba)
    trend_line = lr.predict([[0], [1]])
    plt.plot([0, 1], trend_line, 'b-', lw=2, alpha=0.8, label='Trend Line')

    plt.xlabel('Actual Values (0=No Breakdown, 1=Breakdown)')
    plt.ylabel('Predicted Probability')
    plt.title('Predicted vs Actual Values')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Add performance metrics
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    mse = mean_squared_error(y_test, y_pred_proba)
    mae = mean_absolute_error(y_test, y_pred_proba)

    plt.text(0.05, 0.95, f'MSE: {mse:.3f}\nMAE: {mae:.3f}\nR²: {auc_score:.3f}',
             transform=plt.gca().transAxes, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    # Feature importance (approximation for KNN)
    plt.subplot(1, 4, 4)
    feature_importance = []
    base_score = model.score(X_test, y_test)

    for i in range(len(feature_columns)):
        X_test_perm = X_test.copy()
        X_test_perm[:, i] = np.random.permutation(X_test_perm[:, i])
        perm_score = model.score(X_test_perm, y_test)
        importance = base_score - perm_score
        feature_importance.append(importance)

    # Create horizontal bar plot with colors
    colors = plt.cm.viridis(np.linspace(0, 1, len(feature_columns)))
    plt.barh(feature_columns, feature_importance, color=colors)
    plt.xlabel('Feature Importance (Permutation)')
    plt.title('Feature Importance')

    # Add importance values as text on bars
    for i, (importance, color) in enumerate(zip(feature_importance, colors)):
        plt.text(importance + max(feature_importance) * 0.01, i, f'{importance:.3f}',
                va='center', fontsize=9)

    plt.tight_layout()

    plt.savefig('Breakdown_Prediction.png', dpi=300, bbox_inches='tight')
    plt.show()

    print(f"\nVisualization saved as 'Breakdown_Prediction.png'")

    # Additional detailed performance analysis
    print(f"\nDetailed Model Performance Analysis:")
    print(f"=" * 50)
    print(f"Mean Squared Error (MSE): {mse:.4f}")
    print(f"Mean Absolute Error (MAE): {mae:.4f}")
    print(f"Root Mean Squared Error (RMSE): {np.sqrt(mse):.4f}")

    # Calibration analysis
    from sklearn.calibration import calibration_curve
    fraction_of_positives, mean_predicted_value = calibration_curve(y_test, y_pred_proba, n_bins=5)

    print(f"\nCalibration Analysis (how well probabilities match reality):")
    for i, (actual, predicted) in enumerate(zip(fraction_of_positives, mean_predicted_value)):
        print(f"  Bin {i+1}: Predicted {predicted:.2%} → Actual {actual:.2%}")

    # Prediction quality by probability ranges
    prob_ranges = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
    print(f"\nPrediction Quality by Probability Range:")
    for low, high in prob_ranges:
        mask = (y_pred_proba >= low) & (y_pred_proba < high)
        if mask.sum() > 0:
            actual_rate = y_test[mask].mean()
            predicted_avg = y_pred_proba[mask].mean()
            count = mask.sum()
            print(f"  {low:.1%}-{high:.1%}: {count:3d} samples, Predicted: {predicted_avg:.1%}, Actual: {actual_rate:.1%}")

    # Make final prediction and provide clear answer
    recent_data = feature_df[feature_df['service_date'] > cutoff_date]
    if len(recent_data) > 0:
        print(f"\nPredictions for recent services (last 14 days):")
        X_recent = recent_data[feature_columns].fillna(0)
        X_recent_scaled = scaler.transform(X_recent)
        recent_probabilities = model.predict_proba(X_recent_scaled)[:, 1]

        avg_probability = recent_probabilities.mean()
        max_probability = recent_probabilities.max()

        # Determine confidence level based on model performance
        confidence_score = min(accuracy * 100, 95)  # Cap at 95% to be realistic

        print(f"\n" + "=" * 60)
        print("FINAL PREDICTION RESULT")
        print("=" * 60)

        # Decision threshold (you can adjust this)
        threshold = 0.3  # 30% probability threshold

        if avg_probability > threshold:
            answer = "YES"
            risk_level = "HIGH" if avg_probability > 0.5 else "MODERATE"
        else:
            answer = "NO"
            risk_level = "LOW"

        print(f"Will a vehicle break down in the next 14 days? {answer}")
        print(f"Average breakdown probability: {avg_probability:.1%}")
        print(f"Highest risk vehicle probability: {max_probability:.1%}")
        print(f"Risk level: {risk_level}")
        print(f"Model confidence: {confidence_score:.1f}%")

        # Show top risk vehicles
        recent_data_with_prob = recent_data.copy()
        recent_data_with_prob['breakdown_probability'] = recent_probabilities
        top_risk = recent_data_with_prob.nlargest(min(5, len(recent_data_with_prob)), 'breakdown_probability')

        print(f"\nTop {len(top_risk)} vehicles at highest risk:")
        for _, row in top_risk.iterrows():
            print(f"  Vehicle {row['vehicle_id']}: {row['breakdown_probability']:.1%} probability")

        print(f"\n" + "=" * 60)

        return {
            'answer': answer,
            'probability': avg_probability,
            'confidence': confidence_score,
            'risk_level': risk_level,
            'max_risk_probability': max_probability
        }
    else:
        print(f"\nNo recent data available for prediction")
        return {
            'answer': 'UNKNOWN',
            'probability': 0.0,
            'confidence': 0.0,
            'risk_level': 'UNKNOWN',
            'max_risk_probability': 0.0
        }
