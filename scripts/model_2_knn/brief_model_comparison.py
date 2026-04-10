import pandas as pd
import numpy as np
import json, time, warnings
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import RandomizedSearchCV
from imblearn.over_sampling import SMOTE
try:
    from xgboost import XGBClassifier
except ImportError:
    print("XGBoost não encontrado. Instale com: pip install xgboost")
    XGBClassifier = None

warnings.filterwarnings('ignore')

# ===================== DATA PROCESSING =====================
def process_dataset():
    # ... (código existente, sem alterações)
    input_file = "../notebooks/data/SERVICE_ORDER_BASE.xlsx"
    output_file = "../notebooks/data/SERVICE_ORDER_CLEAN.xlsx"
    mappings_file = "../notebooks/data/code_name_mappings.json"
    print("Starting data processing...")
    start = time.time()

    try:
        df = pd.read_excel(input_file)

        # remover colunas desnecessárias
        to_remove = [
            "MODEL TYPE DESCRIPTION","ASSET PURCHASE DATE","ITEM OF LEDGER ACCOUNT",
            "LEDGER ACCOUNT DESCRIPTION","MAINTENANCE TYPE","SERVICE ORDER","INVOICE",
            "SUPPLIER'S CODE","SUPPLIER'S STORE","NAME OR COMPANY NAME"
        ]
        df = df.drop(columns=[c for c in to_remove if c in df.columns], errors="ignore")

        # renomear coluna e formatar datas
        if "COUNTER  OF SERVICE ORDER" in df:
            df = df.rename(columns={"COUNTER  OF SERVICE ORDER":"ODOMETER"})
        if "SERVICE ORDER ORIGINAL DATE" in df:
            df["SERVICE ORDER ORIGINAL DATE"] = (
                df["SERVICE ORDER ORIGINAL DATE"].astype(str)
                .str.strip(" '\"\t")
                .str.replace(r"[^\d/]", "", regex=True)
            )
            def format_date(d):
                if d.isdigit() and len(d)==8: return f"{d[6:]}/{d[4:6]}/{d[:4]}"
                return d
            df["SERVICE ORDER ORIGINAL DATE"] = df["SERVICE ORDER ORIGINAL DATE"].apply(format_date)

        # criar mapeamentos básicos
        mappings = {}
        if {"MODEL TYPE CODE","ASSET NAME"} <= set(df.columns):
            mp = dict(zip(df["MODEL TYPE CODE"], df["ASSET NAME"]))
            mappings["MODEL_TYPE_CODE"] = mp
            df = df.drop(columns=["ASSET NAME"])

        # simplificar TIER
        if "TIER" in df:
            df["TIER"] = df["TIER"].replace({"TIER 1":1,"T1":1,"TIER 2":2,"T2":2})

        # converter binário
        if "ASSET STATUS" in df:
            df["ASSET STATUS"] = df["ASSET STATUS"].map({"ACTIVE":1,"INACTIVE":0}).fillna(df["ASSET STATUS"])
        if "PREVENTIVE_CORRECTIVE MAINTENANCE" in df:
            df["PREVENTIVE_CORRECTIVE MAINTENANCE"] = df["PREVENTIVE_CORRECTIVE MAINTENANCE"].map({"PREVENTIVE":1,"CORRECTIVE":0}).fillna(df["PREVENTIVE_CORRECTIVE MAINTENANCE"])

        # remover linhas incompletas
        req = ["PRODUCT QUANTITY","UNIT VALUE","GRAND TOTAL"]
        if all(c in df for c in req):
            df = df.dropna(subset=req)

        # features temporais
        if "SERVICE ORDER ORIGINAL DATE" in df:
            df["SERVICE ORDER ORIGINAL DATE"] = pd.to_datetime(df["SERVICE ORDER ORIGINAL DATE"],dayfirst=True,errors="coerce")
            df["SERVICE_ORDER_year"] = df["SERVICE ORDER ORIGINAL DATE"].dt.year
            df["SERVICE_ORDER_month"] = df["SERVICE ORDER ORIGINAL DATE"].dt.month
            df["SERVICE_ORDER_day"] = df["SERVICE ORDER ORIGINAL DATE"].dt.day
            df = df.drop(columns=["SERVICE ORDER ORIGINAL DATE"])

        # label encode colunas pesadas
        le = LabelEncoder()
        for col in ["MODEL TYPE CODE","PRODUCT CODE","ASSET CODE"]:
            if col in df:
                df[col+"_enc"] = le.fit_transform(df[col].astype(str))
                df = df.drop(columns=[col])

        # salvar
        df.to_excel(output_file,index=False)
        with open(mappings_file,"w") as f: json.dump(mappings,f,indent=2)

        print("Data processed in",round(time.time()-start,2),"s")
        return df
    except Exception as e:
        print("Processing error:",e)
        return None

# ===================== OUTLIER ANALYSIS =====================
def outlier_analysis():
    # ... (código existente, sem alterações)
    print("\nOutlier Analysis")
    df = pd.read_excel("../notebooks/data/SERVICE_ORDER_CLEAN.xlsx")
    cols = ["GRAND TOTAL","PRODUCT QUANTITY","UNIT VALUE","ODOMETER"]
    for c in cols:
        if c in df:
            data = df[c].dropna()
            Q1,Q3 = data.quantile([0.25,0.75]); IQR=Q3-Q1
            low,high = Q1-1.5*IQR, Q3+1.5*IQR
            print(f"{c}: mean={data.mean():.2f}, outliers={((data<low)|(data>high)).sum()}")
            df[c] = df[c].clip(low,high)
    out_file = "../notebooks/data/SERVICE_ORDER_BASE_outliers_treated.xlsx"
    df.to_excel(out_file,index=False)
    print("Outliers treated and saved.")
    return df

# ===================== PREDICTOR =====================
def Prediction():
    print("\nBreakdown Prediction")
    try:
        df = pd.read_excel("../notebooks/data/SERVICE_ORDER_BASE_outliers_treated.xlsx")
    except:
        df = pd.read_excel("../notebooks/data/SERVICE_ORDER_CLEAN.xlsx")

    # preparar datas
    if all(c in df.columns for c in ["SERVICE_ORDER_year","SERVICE_ORDER_month","SERVICE_ORDER_day"]):
        df["SERVICE_ORDER_date"] = pd.to_datetime(
            dict(year=df["SERVICE_ORDER_year"], month=df["SERVICE_ORDER_month"], day=df["SERVICE_ORDER_day"]),
            errors="coerce"
        )
    elif "SERVICE ORDER ORIGINAL DATE" in df.columns:
        df["SERVICE_ORDER_date"] = pd.to_datetime(df["SERVICE ORDER ORIGINAL DATE"], errors="coerce")
    else:
        print("Nenhuma coluna de data válida encontrada!")
        return

    # identificar veículo
    if "ASSET CODE_enc" in df.columns:
        vid = "ASSET CODE_enc"
    elif "ASSET CODE" in df.columns:
        vid = "ASSET CODE"
    else:
        print("Nenhuma coluna de veículo encontrada!")
        return

    # Garantir que ODOMETER está presente
    if "ODOMETER" not in df.columns:
        print("Coluna ODOMETER não encontrada! Não será possível criar features de quilometragem.")
        return

    df = df.dropna(subset=["GRAND TOTAL","SERVICE_ORDER_date", "ODOMETER"])
    df = df.sort_values([vid,"SERVICE_ORDER_date"])

    # construir dataset de features
    feats=[]
    for v in df[vid].unique():
        vdf = df[df[vid]==v]
        for _,row in vdf.iterrows():
            date=row["SERVICE_ORDER_date"]
            prev=vdf[vdf["SERVICE_ORDER_date"]<date]
            days=(date-prev["SERVICE_ORDER_date"].max()).days if len(prev) else 0
            feats.append({
                "vehicle_id":v,"date":date,"cost":row["GRAND TOTAL"],
                "days_since_last":days,
                "odometer": row["ODOMETER"]
            })
    featdf=pd.DataFrame(feats)

    # Corrigido para evitar data leakage
    threshold_cost = featdf["cost"].quantile(0.75)
    threshold_days = 180
    featdf["is_high_cost"] = (featdf["cost"] > threshold_cost).astype(int)
    featdf["is_long_interval"] = (featdf["days_since_last"] > threshold_days).astype(int)

    featdf = featdf.sort_values(["vehicle_id", "date"])
    featdf["breakdown"] = featdf.groupby("vehicle_id")[["is_high_cost", "is_long_interval"]].shift(-1).any(axis=1)

    featdf = featdf.dropna(subset=["breakdown"])
    featdf["breakdown"] = featdf["breakdown"].astype(int)

    if featdf["breakdown"].nunique() < 2:
        print("Não há variação na variável alvo (breakdown) após o ajuste.")
        return

    # Engenharia de features avançada
    print("Criando features avançadas...")
    featdf["rolling_cost_mean"] = featdf.groupby("vehicle_id")["cost"].transform(lambda x: x.rolling(3, min_periods=1).mean())
    featdf['service_count'] = featdf.groupby('vehicle_id').cumcount()
    featdf['km_since_last'] = featdf.groupby('vehicle_id')['odometer'].diff().clip(lower=0)
    featdf['km_per_day'] = (featdf['km_since_last'] / featdf['days_since_last']).replace([np.inf, -np.inf], 0)
    featdf['avg_cost_so_far'] = featdf.groupby('vehicle_id')['cost'].transform(lambda x: x.shift(1).expanding().mean())
    featdf['std_dev_cost_so_far'] = featdf.groupby('vehicle_id')['cost'].transform(lambda x: x.shift(1).expanding().std())
    featdf['avg_days_between_services'] = featdf.groupby('vehicle_id')['days_since_last'].transform(lambda x: x.shift(1).expanding().mean())
    featdf['days_overdue'] = featdf['days_since_last'] - featdf['avg_days_between_services']
    featdf = featdf.fillna(0)
    print("Features criadas.")

    # treino/teste temporal
    featdf = featdf.sort_values("date")
    split = int(len(featdf)*0.8)
    train, test = featdf.iloc[:split], featdf.iloc[split:]

    feature_names = [
        "cost", "days_since_last", "rolling_cost_mean", "service_count",
        "km_since_last", "km_per_day", "avg_cost_so_far",
        "std_dev_cost_so_far", "avg_days_between_services", "days_overdue"
    ]
    Xtr, ytr = train[feature_names], train["breakdown"]
    Xte, yte = test[feature_names], test["breakdown"]

    print("\nFeatures usadas para o treinamento:", feature_names)

    # ==================== MUDANÇA 2: APLICAR SMOTE ====================
    print("\nAplicando SMOTE nos dados de treino para balancear as classes...")
    smote = SMOTE(random_state=42)
    Xtr_resampled, ytr_resampled = smote.fit_resample(Xtr, ytr)
    print("SMOTE aplicado. Novas dimensões do treino:", Xtr_resampled.shape)
    # =================================================================

    # Escalonamento dos dados (após SMOTE para os dados de treino)
    scaler=StandardScaler()
    Xtr_scaled_resampled = scaler.fit_transform(Xtr_resampled)
    Xte_scaled = scaler.transform(Xte) # Teste continua o mesmo

    # ==================== MUDANÇA 3: TREINAR MODELOS COM DADOS BALANCEADOS ====================

    # ===== Modelo 1: Regressão Logística =====
    # Removido class_weight
    logreg = LogisticRegression(max_iter=1000).fit(Xtr_scaled_resampled, ytr_resampled)
    ypred_lr = logreg.predict(Xte_scaled)

    print("\n[Logistic Regression] Evaluation:")
    print(classification_report(yte,ypred_lr))

    # ===== Modelo 2: Random Forest =====
    # Removido class_weight
    rf = RandomForestClassifier(n_estimators=100, random_state=42).fit(Xtr_resampled, ytr_resampled)
    ypred_rf = rf.predict(Xte)

    print("\n[Random Forest] Evaluation:")
    print(classification_report(yte,ypred_rf))

    # ===== Modelo 3: XGBoost =====
    if XGBClassifier:
        print("\n[XGBoost] Evaluation:")
        # Removido scale_pos_weight
        xgb = XGBClassifier(random_state=42).fit(Xtr_resampled, ytr_resampled)
        ypred_xgb = xgb.predict(Xte)
        print(classification_report(yte, ypred_xgb))

    # ===== Modelo 4: K-Nearest Neighbors (KNN) =====
    print("\n[K-Nearest Neighbors (KNN)] Evaluation:")
    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(Xtr_scaled_resampled, ytr_resampled)
    ypred_knn = knn.predict(Xte_scaled)
    print(classification_report(yte, ypred_knn))

    return Xtr_resampled, ytr_resampled, Xte, yte

def optimize_hyperparameters(Xtr_resampled, ytr_resampled, Xte, yte):
    """
Otimiza os hiperparâmetros do modelo Random Forest usando RandomizedSearchCV.
    """
    print("\n" + "="*20)
    print("INICIANDO OTIMIZAÇÃO DE HIPERPARÂMETROS")
    print("="*20)

    # Definindo o grid de parâmetros para o Random Forest
    param_grid = {
        'n_estimators': [100, 200, 300, 500],
        'max_depth': [10, 20, 30, None],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['sqrt', 'log2']
    }

    # Criando o modelo base
    rf = RandomForestClassifier(random_state=42)

    # Criando o objeto de busca aleatória
    # n_iter: número de combinações a testar
    # cv: número de folds da validação cruzada
    # n_jobs=-1: usa todos os processadores disponíveis
    rf_random = RandomizedSearchCV(estimator=rf, param_distributions=param_grid,
                                   n_iter=50, cv=3, verbose=2, random_state=42,
                                   n_jobs=-1, scoring='f1')

    print("\nAjustando o modelo... (Isso pode levar vários minutos)")
    # Ajustando o modelo aos dados rebalanceados
    rf_random.fit(Xtr_resampled, ytr_resampled)

    print("\nMelhores parâmetros encontrados:")
    print(rf_random.best_params_)

    # Usando o melhor modelo para fazer previsões
    best_model = rf_random.best_estimator_
    ypred_best = best_model.predict(Xte)

    print("\n[Random Forest Otimizado] Evaluation:")
    print(classification_report(yte, ypred_best))

    return best_model

# ===================== MAIN =====================
def main():
    process_dataset()
    outlier_analysis()

    # MUDANÇA: O fluxo agora inclui a otimização
    # A função Prediction agora retorna os dados necessários
    training_data = Prediction()

    if training_data:
        Xtr_resampled, ytr_resampled, Xte, yte = training_data
        # A nova função de otimização é chamada
        optimize_hyperparameters(Xtr_resampled, ytr_resampled, Xte, yte)

if __name__=="__main__":
    main()