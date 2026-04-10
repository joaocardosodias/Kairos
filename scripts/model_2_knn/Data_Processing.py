import pandas as pd
import numpy as np
import json
import time
import os
import sklearn


def loading_dataset(input_file):
    print("\nStep 1: Loading dataset...")
    df = pd.read_excel(input_file)
    print(f"Dataset loaded: {df.shape}")
    print(f"Original columns: {len(df.columns)}")
    return df


def remove_unnecessary_columns(df):
    print("\nStep 2: Removing unnecessary columns...")
    columns_to_remove = [
        "MODEL TYPE DESCRIPTION",
        "ASSET PURCHASE DATE",
        "ITEM OF LEDGER ACCOUNT",
        "LEDGER ACCOUNT DESCRIPTION",
        "MAINTENANCE TYPE",
        "SERVICE ORDER",
        "INVOICE",
        "SUPPLIER'S CODE",
        "SUPPLIER'S STORE",
        "NAME OR COMPANY NAME"
    ]

    existing_columns_to_remove = [col for col in columns_to_remove if col in df.columns]
    if existing_columns_to_remove:
        df = df.drop(columns=existing_columns_to_remove)
        print(f"Removed {len(existing_columns_to_remove)} columns")
    else:
        print("No specified columns found to remove")


def formatting_column(df):
    print("\nStep 3: Formatting columns and dates...")

    # Rename column
    if "COUNTER  OF SERVICE ORDER" in df.columns:
        df = df.rename(columns={"COUNTER  OF SERVICE ORDER": "ODOMETER"})
        print("Renamed 'COUNTER  OF SERVICE ORDER' to 'ODOMETER'")

    # Format dates
    if "SERVICE ORDER ORIGINAL DATE" in df.columns:
        def format_date(date_str):
            try:
                date_str = str(date_str).strip("'\"")
                if pd.isna(date_str) or date_str == 'nan' or date_str == '':
                    return date_str
                if len(date_str) == 8 and date_str.isdigit():
                    year = date_str[:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    return f"{day}/{month}/{year}"
                return date_str
            except Exception:
                return date_str

        print(df["SERVICE ORDER ORIGINAL DATE"].head(10))
        df["SERVICE ORDER ORIGINAL DATE"] = (
            df["SERVICE ORDER ORIGINAL DATE"]
            .astype(str)
            .str.strip(" '\"\t")
            .str.replace(r"[^\d/]", "", regex=True)
        )
        mask_valid = df["SERVICE ORDER ORIGINAL DATE"].str.match(r"\d{2}/\d{2}/\d{4}")
        print(df.loc[~mask_valid, "SERVICE ORDER ORIGINAL DATE"].head(10))

        df["SERVICE ORDER ORIGINAL DATE"] = df["SERVICE ORDER ORIGINAL DATE"].apply(format_date)
        print("Formatted dates from YYYYMMDD to DD/MM/YYYY")


def create_code_name_mappings(df):
    print("\nStep 4: Creating code-name mappings...")

    code_name_pairs = [
        ("MODEL TYPE CODE", "ASSET NAME"),
        ("ASSET FAMILY CODE", "FAMILY NAME"),
        ("MANUFACTURER CODE", "MANUFACTURER NAME")
    ]

    all_mappings = {}
    columns_to_drop = []

    for code_col, name_col in code_name_pairs:
        if code_col in df.columns and name_col in df.columns:
            mapping_df = df[[code_col, name_col]].dropna().drop_duplicates()
            mapping_dict = dict(zip(mapping_df[code_col], mapping_df[name_col]))
            mapping_key = f"{code_col}_to_{name_col.replace(' ', '_')}"
            all_mappings[mapping_key] = mapping_dict
            columns_to_drop.append(name_col)
            print(f"Created {mapping_key} with {len(mapping_dict)} mappings")

    # Add product mapping if columns exist
    if "PRODUCT CODE" in df.columns and "PRODUCT DESCRIPTION" in df.columns:
        mapping_df = df[["PRODUCT CODE", "PRODUCT DESCRIPTION"]].dropna().drop_duplicates()
        product_mapping = dict(zip(mapping_df["PRODUCT CODE"], mapping_df["PRODUCT DESCRIPTION"]))
        all_mappings["PRODUCT_CODE_to_PRODUCT_DESCRIPTION"] = product_mapping
        columns_to_drop.append("PRODUCT DESCRIPTION")
        print(f"Created PRODUCT_CODE_to_PRODUCT_DESCRIPTION with {len(product_mapping)} mappings")

    # Add additional mappings for converted values
    additional_mappings = {
        "ASSET_STATUS_to_CODE": {
            "0": "INACTIVE",
            "1": "ACTIVE"
        },
        "TIER_to_CODE": {
            "1": "TIER 1",
            "2": "TIER 2"
        },
        "PREVENTIVE_CORRECTIVE_MAINTENANCE_to_CODE": {
            "0": "CORRECTIVE",
            "1": "PREVENTIVE"
        }
    }
    all_mappings.update(additional_mappings)

    # Remove name columns
    if columns_to_drop:
        df = df.drop(columns=columns_to_drop)
        print(f"Removed {len(columns_to_drop)} name columns (kept codes)")

    return all_mappings


def simplify_tier_column(df):
    print("\nStep 5: Simplifying TIER column...")
    if "TIER" in df.columns:
        def simplify_tier_value(tier_value):
            if pd.isna(tier_value):
                return tier_value
            tier_str = str(tier_value).strip()
            if "TIER 1" in tier_str or "T1" in tier_str:
                return 1
            elif "TIER 2" in tier_str or "T2" in tier_str:
                return 2
            else:
                return tier_value

        df["TIER"] = df["TIER"].apply(simplify_tier_value)
        tier_counts = df["TIER"].value_counts()
        print(f"TIER simplified: {dict(tier_counts)}")


def convert_columns_to_binary(df):
    print("\nStep 6: Converting ASSET STATUS to binary...")
    if "ASSET STATUS" in df.columns:
        def convert_status_value(status_value):
            if pd.isna(status_value):
                return status_value
            status_str = str(status_value).strip().upper()
            if status_str == "ACTIVE":
                return 1
            elif status_str == "INACTIVE":
                return 0
            else:
                return status_value

        df["ASSET STATUS"] = df["ASSET STATUS"].apply(convert_status_value)
        status_counts = df["ASSET STATUS"].value_counts()
        print(f"ASSET STATUS converted: {dict(status_counts)}")

        print("\nStep 7: Converting PREVENTIVE_CORRECTIVE MAINTENANCE to binary...")
        if "PREVENTIVE_CORRECTIVE MAINTENANCE" in df.columns:
            def convert_maintenance_value(maintenance_value):
                if pd.isna(maintenance_value):
                    return maintenance_value
                maintenance_str = str(maintenance_value).strip().upper()
                if maintenance_str == "PREVENTIVE":
                    return 1
                elif maintenance_str == "CORRECTIVE":
                    return 0
                else:
                    return maintenance_value

            df["PREVENTIVE_CORRECTIVE MAINTENANCE"] = df["PREVENTIVE_CORRECTIVE MAINTENANCE"].apply(
                convert_maintenance_value)
            maintenance_counts = df["PREVENTIVE_CORRECTIVE MAINTENANCE"].value_counts()
            print(f"MAINTENANCE converted: {dict(maintenance_counts)}")


def remove_incomplete_rows(df):
    print("\nStep 8: Removing incomplete rows...")
    required_columns = ["PRODUCT QUANTITY", "UNIT VALUE", "GRAND TOTAL"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"Missing required columns: {missing_columns}")
    else:
        original_rows = len(df)
        df = df.dropna(subset=required_columns)
        removed_rows = original_rows - len(df)
        retention_rate = (len(df) / original_rows) * 100
        print(f"Removed {removed_rows} incomplete rows")
        print(f"Data retention: {retention_rate:.2f}%")


def extract_temporal_features(df, all_mappings):
    print("\nStep 9: Extracting temporal features from SERVICE ORDER ORIGINAL DATE...")
    if "SERVICE ORDER ORIGINAL DATE" in df.columns:
        # Convert to datetime first
        df["SERVICE ORDER ORIGINAL DATE"] = pd.to_datetime(df["SERVICE ORDER ORIGINAL DATE"], format='%d/%m/%Y',
                                                           errors='coerce')

        # Check for any failed conversions
        failed_conversions = df["SERVICE ORDER ORIGINAL DATE"].isna().sum()
        if failed_conversions > 0:
            print(f"{failed_conversions} dates could not be parsed")

        # Store date range before processing
        min_date = df["SERVICE ORDER ORIGINAL DATE"].min()
        max_date = df["SERVICE ORDER ORIGINAL DATE"].max()

        # Extract basic temporal features
        df["SERVICE_ORDER_year"] = df["SERVICE ORDER ORIGINAL DATE"].dt.year
        df["SERVICE_ORDER_month"] = df["SERVICE ORDER ORIGINAL DATE"].dt.month
        df["SERVICE_ORDER_day"] = df["SERVICE ORDER ORIGINAL DATE"].dt.day

        # Remove original date column (keep only features)
        df = df.drop(columns=["SERVICE ORDER ORIGINAL DATE"])

        temporal_features = [
            "SERVICE_ORDER_year", "SERVICE_ORDER_month", "SERVICE_ORDER_day"
        ]

        # Store temporal feature information in mappings
        temporal_mapping = {
            "SERVICE_ORDER_temporal_features": {
                "type": "temporal_extraction",
                "original_column": "SERVICE ORDER ORIGINAL DATE",
                "extracted_features": temporal_features,
                "feature_descriptions": {
                    "SERVICE_ORDER_year": "Year (e.g., 2020, 2021)",
                    "SERVICE_ORDER_month": "Month (1-12)",
                    "SERVICE_ORDER_day": "Day of month (1-31)"
                },
                "date_range": {
                    "earliest": str(min_date.date()) if not pd.isna(min_date) else "Unknown",
                    "latest": str(max_date.date()) if not pd.isna(max_date) else "Unknown"
                }
            }
        }
        all_mappings.update(temporal_mapping)

        print(f"Extracted {len(temporal_features)} temporal features")
        print(f"Features: year, month, day")
        print(
            f"Date range: {min_date.date() if not pd.isna(min_date) else 'Unknown'} to {max_date.date() if not pd.isna(max_date) else 'Unknown'}")
        print(f"New dataset shape: {df.shape}")
    else:
        print("SERVICE ORDER ORIGINAL DATE column not found")


def label_encode_column(df, all_mappings):
    print("\nStep 10: Label encoding MODEL TYPE CODE...")
    original_model_types = []  # Initialize for scope
    if "MODEL TYPE CODE" in df.columns:
        from sklearn.preprocessing import LabelEncoder

        unique_model_types = df["MODEL TYPE CODE"].nunique()
        print(f"MODEL TYPE CODE has {unique_model_types} unique values")
        print(f"Using label encoding (much more efficient than {unique_model_types} one-hot columns)")

        # Store the original values before processing
        original_model_types = sorted(df["MODEL TYPE CODE"].unique())

        # Create label encoder and fit
        le = LabelEncoder()
        df["MODEL_TYPE_CODE_encoded"] = le.fit_transform(df["MODEL TYPE CODE"].astype(str))

        # Remove original MODEL TYPE CODE column
        df = df.drop(columns=["MODEL TYPE CODE"])

        # Update mappings with MODEL TYPE CODE information
        model_type_mapping = {
            "MODEL_TYPE_CODE_label": {
                "type": "label_encoding",
                "original_column": "MODEL TYPE CODE",
                "encoded_column": "MODEL_TYPE_CODE_encoded",
                "unique_values": unique_model_types,
                "classes": le.classes_.tolist(),
                "original_values": original_model_types
            }
        }
        all_mappings.update(model_type_mapping)

        print(f"Created 1 label-encoded column (MODEL_TYPE_CODE_encoded)")
        print(f"Removed original MODEL TYPE CODE column")
        print(f"Mapped {unique_model_types} values to integers 0-{unique_model_types - 1}")
        print(f"New dataset shape: {df.shape}")
    else:
        print("MODEL TYPE CODE column not found")

    # Label encode PRODUCT CODE
    print("\nStep 11: Label encoding PRODUCT CODE...")
    original_product_codes = []  # Initialize for scope
    if "PRODUCT CODE" in df.columns:
        unique_product_codes = df["PRODUCT CODE"].nunique()
        print(f"PRODUCT CODE has {unique_product_codes} unique values")
        print(f"Using label encoding (much more efficient than {unique_product_codes} one-hot columns)")

        # Store the original values before processing (sample only due to large size)
        original_product_codes = sorted(df["PRODUCT CODE"].unique())

        # Create label encoder and fit
        le_product = LabelEncoder()
        df["PRODUCT_CODE_encoded"] = le_product.fit_transform(df["PRODUCT CODE"].astype(str))

        # Remove original PRODUCT CODE column
        df = df.drop(columns=["PRODUCT CODE"])

        # Update mappings with PRODUCT CODE information (store sample due to large size)
        product_code_mapping = {
            "PRODUCT_CODE_label": {
                "type": "label_encoding",
                "original_column": "PRODUCT CODE",
                "encoded_column": "PRODUCT_CODE_encoded",
                "unique_values": unique_product_codes,
                "sample_classes": le_product.classes_[:100].tolist(),  # Store first 100 for reference
                "total_classes": len(le_product.classes_),
                "encoding_range": f"0-{len(le_product.classes_) - 1}"
            }
        }
        all_mappings.update(product_code_mapping)

        print(f"Created 1 label-encoded column (PRODUCT_CODE_encoded)")
        print(f"Removed original PRODUCT CODE column")
        print(f"Mapped {unique_product_codes} values to integers 0-{unique_product_codes - 1}")
        print(f"New dataset shape: {df.shape}")
    else:
        print("PRODUCT CODE column not found")

    # Label encode ASSET CODE (vehicle plates)
    print("\nStep 12: Label encoding ASSET CODE (vehicle plates)...")
    original_asset_codes = []  # Initialize for scope
    if "ASSET CODE" in df.columns:
        unique_asset_codes = df["ASSET CODE"].nunique()
        print(f"ASSET CODE has {unique_asset_codes} unique vehicle plates")
        print(f"Using label encoding (much more efficient than {unique_asset_codes} one-hot columns)")

        # Store the original values before processing (sample only due to potentially large size)
        original_asset_codes = sorted(df["ASSET CODE"].unique())

        # Create label encoder and fit
        le_asset = LabelEncoder()
        df["ASSET_CODE_encoded"] = le_asset.fit_transform(df["ASSET CODE"].astype(str))

        # Remove original ASSET CODE column
        df = df.drop(columns=["ASSET CODE"])

        # Update mappings with ASSET CODE information (store sample due to potentially large size)
        asset_code_mapping = {
            "ASSET_CODE_label": {
                "type": "label_encoding",
                "original_column": "ASSET CODE",
                "encoded_column": "ASSET_CODE_encoded",
                "unique_values": unique_asset_codes,
                "sample_classes": le_asset.classes_[:50].tolist(),  # Store first 50 vehicle plates for reference
                "total_classes": len(le_asset.classes_),
                "encoding_range": f"0-{len(le_asset.classes_) - 1}",
                "description": "Vehicle plate identifiers encoded as integers"
            }
        }
        all_mappings.update(asset_code_mapping)

        print(f"Created 1 label-encoded column (ASSET_CODE_encoded)")
        print(f"Removed original ASSET CODE column")
        print(f"Mapped {unique_asset_codes} vehicle plates to integers 0-{unique_asset_codes - 1}")
        print(f"New dataset shape: {df.shape}")
    else:
        print("ASSET CODE column not found")

    return original_model_types, original_product_codes, original_asset_codes


def reorder_columns(df):
    print("\nStep 13: Reordering columns to match original structure...")

    # Define the desired column order (similar to original dataset)
    desired_order = []

    # Vehicle/Asset identification
    if "ASSET_CODE_encoded" in df.columns:
        desired_order.append("ASSET_CODE_encoded")

    # Model and classification
    if "MODEL_TYPE_CODE_encoded" in df.columns:
        desired_order.append("MODEL_TYPE_CODE_encoded")
    if "ASSET_FAMILY_CODE_encoded" in df.columns:
        desired_order.append("ASSET_FAMILY_CODE_encoded")
    if "MANUFACTURER_CODE_encoded" in df.columns:
        desired_order.append("MANUFACTURER_CODE_encoded")
    if "MANUFACTURE_YEAR_encoded" in df.columns:
        desired_order.append("MANUFACTURE_YEAR_encoded")
    if "ASSET STATUS" in df.columns:
        desired_order.append("ASSET STATUS")
    if "TIER" in df.columns:
        desired_order.append("TIER")

    # Service/maintenance information
    if "ODOMETER" in df.columns:
        desired_order.append("ODOMETER")

    # Date information
    if "SERVICE_ORDER_year" in df.columns:
        desired_order.append("SERVICE_ORDER_year")
    if "SERVICE_ORDER_month" in df.columns:
        desired_order.append("SERVICE_ORDER_month")
    if "SERVICE_ORDER_day" in df.columns:
        desired_order.append("SERVICE_ORDER_day")

    # Product and service details
    if "PRODUCT_CODE_encoded" in df.columns:
        desired_order.append("PRODUCT_CODE_encoded")
    if "PRODUCT QUANTITY" in df.columns:
        desired_order.append("PRODUCT QUANTITY")
    if "UNIT VALUE" in df.columns:
        desired_order.append("UNIT VALUE")
    if "GRAND TOTAL" in df.columns:
        desired_order.append("GRAND TOTAL")
    if "PREVENTIVE_CORRECTIVE MAINTENANCE" in df.columns:
        desired_order.append("PREVENTIVE_CORRECTIVE MAINTENANCE")

    # Add any remaining columns that weren't explicitly ordered
    remaining_columns = [col for col in df.columns if col not in desired_order]
    desired_order.extend(remaining_columns)

    # Reorder the dataframe
    df = df[desired_order]

    print(f"Reordered {len(df.columns)} columns to match original structure")
    print(f"Order: Vehicle -> Model -> Service -> Date -> Product -> Financial")


def process_dataset():
    # File paths
    input_file = "../notebooks/data/SERVICE_ORDER_BASE.xlsx"
    output_file = "../notebooks/data/SERVICE_ORDER_CLEAN.xlsx"
    mappings_file = "../notebooks/data/code_name_mappings.json"

    print("Starting complete data processing pipeline")

    start_time = time.time()

    try:
        df = loading_dataset(input_file)

        remove_unnecessary_columns(df)

        formatting_column(df)

        all_mappings = create_code_name_mappings(df)

        simplify_tier_column(df)

        convert_columns_to_binary(df)

        remove_incomplete_rows(df)

        extract_temporal_features(df, all_mappings)

        original_model_types, original_product_codes, original_asset_codes = label_encode_column(df, all_mappings)

        reorder_columns(df)

        print(f"Final dataset shape: {df.shape}")

        # Save mappings with numpy type conversion
        print("\nSaving code-name mappings...")

        def convert_numpy_types(obj):
            if hasattr(obj, 'tolist'):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif isinstance(obj, tuple):
                return tuple(convert_numpy_types(item) for item in obj)
            else:
                return obj

        all_mappings_serializable = convert_numpy_types(all_mappings)

        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(all_mappings_serializable, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(all_mappings)} mapping dictionaries to {mappings_file}")

        # Save final dataset
        print("\nSaving final processed dataset...")
        df.to_excel(output_file, index=False)

        # Final summary
        total_time = time.time() - start_time
        print("\n" + "=" * 50)
        print("Processing complete!")
        print("=" * 50)
        print(f"Processing time: {total_time:.2f} seconds")
        print(f"Final dataset shape: {df.shape}")
        print(f"Output file: {output_file}")
        print(f"Mappings file: {mappings_file}")
        print(f"Total mappings created: {len(all_mappings)}")
        print(f"Final columns: {len(df.columns)}")

        print("\nFinal columns:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i:2d}. {col}")

        # Feature engineering summary
        print(f"\nFeature engineering summary:")

        # Temporal features
        temporal_columns = [col for col in df.columns if col.startswith("SERVICE_ORDER_")]
        if temporal_columns:
            print(f"Temporal features: {len(temporal_columns)} features from SERVICE ORDER ORIGINAL DATE")
            print(f"  Basic: year, month, day")

        # Label encoding
        if "MODEL_TYPE_CODE_encoded" in df.columns and original_model_types:
            print(
                f"MODEL TYPE CODE: {len(original_model_types)} values -> 1 encoded column (0-{len(original_model_types) - 1})")
        if "PRODUCT_CODE_encoded" in df.columns and original_product_codes:
            print(
                f"PRODUCT CODE: {len(original_product_codes)} values -> 1 encoded column (0-{len(original_product_codes) - 1})")
        if "ASSET_CODE_encoded" in df.columns and original_asset_codes:
            print(
                f"ASSET CODE (vehicles): {len(original_asset_codes)} plates -> 1 encoded column (0-{len(original_asset_codes) - 1})")

        # Memory efficiency
        encoded_columns = [col for col in df.columns if col.endswith("_encoded")]
        if encoded_columns and (original_model_types or original_product_codes or original_asset_codes):
            potential_ohe_columns = (
                    (len(original_model_types) if original_model_types else 0) +
                    (len(original_product_codes) if original_product_codes else 0) +
                    (len(original_asset_codes) if original_asset_codes else 0)
            )
            print(
                f"Efficiency: {len(encoded_columns)} label-encoded vs {potential_ohe_columns} potential one-hot columns")
            print(f"Memory savings: ~{potential_ohe_columns - len(encoded_columns)} fewer columns")

        print(f"\nDataset is ready for analysis and model training!")

    except FileNotFoundError:
        print(f"Error: File {input_file} not found.")
    except Exception as e:
        print(f"Error during processing: {e}")
        raise
