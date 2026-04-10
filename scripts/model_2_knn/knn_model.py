import pandas as pd
import numpy as np
import time
import warnings
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import RandomizedSearchCV
from imblearn.over_sampling import SMOTE

warnings.filterwarnings('ignore')

# ==============================================================================
# ETAPA 1: PROCESSAMENTO E LIMPEZA DOS DADOS
# ==============================================================================
print("="*20)
print("ETAPA 1: PROCESSAMENTO E LIMPEZA DOS DADOS")
print("="*20)

input_file = "../../notebooks/data/SERVICE_ORDER_BASE.xlsx"
output_file = "../../notebooks/data/SERVICE_ORDER_CLEAN.xlsx"
print("Iniciando o processamento de dados...")
start_time = time.time()

try:
    df = pd.read_excel(input_file)
    to_remove = [
        "MODEL TYPE DESCRIPTION", "ASSET PURCHASE DATE", "ITEM OF LEDGER ACCOUNT",
        "LEDGER ACCOUNT DESCRIPTION", "MAINTENANCE TYPE", "SERVICE ORDER", "INVOICE",
        "SUPPLIER'S CODE", "SUPPLIER'S STORE", "NAME OR COMPANY NAME"
    ]
    df = df.drop(columns=[c for c in to_remove if c in df.columns], errors="ignore")

    if "COUNTER  OF SERVICE ORDER" in df:
        df = df.rename(columns={"COUNTER  OF SERVICE ORDER": "ODOMETER"})
    if "SERVICE ORDER ORIGINAL DATE" in df:
        df["SERVICE ORDER ORIGINAL DATE"] = (
            df["SERVICE ORDER ORIGINAL DATE"].astype(str)
            .str.strip(" '\"\t")
            .str.replace(r"[^\d/]", "", regex=True)
        )
        def format_date(d):
            if d.isdigit() and len(d) == 8: return f"{d[6:]}/{d[4:6]}/{d[:4]}"
            return d
        df["SERVICE ORDER ORIGINAL DATE"] = df["SERVICE ORDER ORIGINAL DATE"].apply(format_date)

    if "TIER" in df:
        df["TIER"] = df["TIER"].replace({"TIER 1": 1, "T1": 1, "TIER 2": 2, "T2": 2})
    if "ASSET STATUS" in df:
        df["ASSET STATUS"] = df["ASSET STATUS"].map({"ACTIVE": 1, "INACTIVE": 0}).fillna(df["ASSET STATUS"])
    if "PREVENTIVE_CORRECTIVE MAINTENANCE" in df:
        df["PREVENTIVE_CORRECTIVE MAINTENANCE"] = df["PREVENTIVE_CORRECTIVE MAINTENANCE"].map({"PREVENTIVE": 1, "CORRECTIVE": 0}).fillna(df["PREVENTIVE_CORRECTIVE MAINTENANCE"])

    req = ["PRODUCT QUANTITY", "UNIT VALUE", "GRAND TOTAL"]
    if all(c in df for c in req):
        df = df.dropna(subset=req)

    if "SERVICE ORDER ORIGINAL DATE" in df:
        df["SERVICE ORDER ORIGINAL DATE"] = pd.to_datetime(df["SERVICE ORDER ORIGINAL DATE"], dayfirst=True, errors="coerce")
        df["SERVICE_ORDER_year"] = df["SERVICE ORDER ORIGINAL DATE"].dt.year
        df["SERVICE_ORDER_month"] = df["SERVICE ORDER ORIGINAL DATE"].dt.month
        df["SERVICE_ORDER_day"] = df["SERVICE ORDER ORIGINAL DATE"].dt.day
        df = df.drop(columns=["SERVICE ORDER ORIGINAL DATE"])

    le = LabelEncoder()
    for col in ["MODEL TYPE CODE", "PRODUCT CODE", "ASSET CODE"]:
        if col in df:
            df[col + "_enc"] = le.fit_transform(df[col].astype(str))
            df = df.drop(columns=[col])

    df.to_excel(output_file, index=False)
    print("Dados processados em", round(time.time() - start_time, 2), "s")

    # ==============================================================================
    # ETAPA 2: ANÁLISE E TRATAMENTO DE OUTLIERS
    # ==============================================================================
    print("\n" + "="*20)
    print("ETAPA 2: ANÁLISE E TRATAMENTO DE OUTLIERS")
    print("="*20)

    cols = ["GRAND TOTAL", "PRODUCT QUANTITY", "UNIT VALUE", "ODOMETER"]
    for c in cols:
        if c in df:
            data = df[c].dropna()
            Q1, Q3 = data.quantile([0.25, 0.75])
            IQR = Q3 - Q1
            low, high = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
            print(f"{c}: média={data.mean():.2f}, outliers={((data<low)|(data>high)).sum()}")
            df[c] = df[c].clip(low, high)
    out_file = "../../notebooks/data/SERVICE_ORDER_BASE_outliers_treated.xlsx"
    df.to_excel(out_file, index=False)
    print("Outliers tratados e salvos.")

    # ==============================================================================
    # ETAPA 3: PREPARAÇÃO DO DATASET PARA MODELAGEM
    # ==============================================================================
    print("\n" + "="*20)
    print("ETAPA 3: PREPARAÇÃO DO DATASET PARA MODELAGEM")
    print("="*20)

    if all(c in df.columns for c in ["SERVICE_ORDER_year", "SERVICE_ORDER_month", "SERVICE_ORDER_day"]):
        df["SERVICE_ORDER_date"] = pd.to_datetime(
            dict(year=df["SERVICE_ORDER_year"], month=df["SERVICE_ORDER_month"], day=df["SERVICE_ORDER_day"]),
            errors="coerce"
        )
    else:
        raise ValueError("Colunas de data válidas não encontradas!")

    vid = "ASSET CODE_enc" if "ASSET CODE_enc" in df.columns else "ASSET CODE"
    if vid not in df.columns or "ODOMETER" not in df.columns:
        raise ValueError("Coluna de identificação do veículo ou odômetro não encontrada!")

    df = df.dropna(subset=["GRAND TOTAL", "SERVICE_ORDER_date", "ODOMETER"])
    df = df.sort_values([vid, "SERVICE_ORDER_date"])

    feats = []
    for v in df[vid].unique():
        vdf = df[df[vid] == v]
        for _, row in vdf.iterrows():
            date = row["SERVICE_ORDER_date"]
            prev = vdf[vdf["SERVICE_ORDER_date"] < date]
            days = (date - prev["SERVICE_ORDER_date"].max()).days if len(prev) else 0
            feats.append({
                "vehicle_id": v, "date": date, "cost": row["GRAND TOTAL"],
                "days_since_last": days, "odometer": row["ODOMETER"]
            })
    featdf = pd.DataFrame(feats)

    threshold_cost = featdf["cost"].quantile(0.75)
    threshold_days = 180
    featdf["is_high_cost"] = (featdf["cost"] > threshold_cost).astype(int)
    featdf["is_long_interval"] = (featdf["days_since_last"] > threshold_days).astype(int)
    featdf = featdf.sort_values(["vehicle_id", "date"])
    featdf["breakdown"] = featdf.groupby("vehicle_id")[["is_high_cost", "is_long_interval"]].shift(-1).any(axis=1)
    featdf = featdf.dropna(subset=["breakdown"])
    featdf["breakdown"] = featdf["breakdown"].astype(int)

    if featdf["breakdown"].nunique() < 2:
        raise ValueError("A variável alvo não tem variação (apenas uma classe presente).")

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

    featdf = featdf.sort_values("date")
    split = int(len(featdf) * 0.8)
    train, test = featdf.iloc[:split], featdf.iloc[split:]

    feature_names = [
        "cost", "days_since_last", "rolling_cost_mean", "service_count",
        "km_since_last", "km_per_day", "avg_cost_so_far",
        "std_dev_cost_so_far", "avg_days_between_services", "days_overdue"
    ]
    Xtr, ytr = train[feature_names], train["breakdown"]
    Xte, yte = test[feature_names], test["breakdown"]

    print("\nAplicando SMOTE nos dados de treino...")
    smote = SMOTE(random_state=42)
    Xtr_resampled, ytr_resampled = smote.fit_resample(Xtr, ytr)

    print("\nEscalonando features...")
    scaler = StandardScaler()
    Xtr_scaled_resampled = scaler.fit_transform(Xtr_resampled)
    Xte_scaled = scaler.transform(Xte)

    # ==============================================================================
    # ETAPA 4: AVALIAÇÃO DO MODELO KNN DE BASE
    # ==============================================================================
    print("\n" + "="*20)
    print("ETAPA 4: AVALIAÇÃO DO MODELO KNN DE BASE")
    print("="*20)

    knn_base = KNeighborsClassifier(n_neighbors=5)
    knn_base.fit(Xtr_scaled_resampled, ytr_resampled)
    ypred_knn_base = knn_base.predict(Xte_scaled)

    print("\n[Avaliação do K-Nearest Neighbors (KNN) de Base]")
    print(classification_report(yte, ypred_knn_base))

    # ==============================================================================
    # ETAPA 4.1: MATRIZ DE CONFUSÃO DO MODELO KNN DE BASE
    # ==============================================================================
    print("\n" + "="*20)
    print("ETAPA 4.1: MATRIZ DE CONFUSÃO DO MODELO KNN DE BASE")
    print("="*20)
    
    # Gerar matriz de confusão
    cm_base = confusion_matrix(yte, ypred_knn_base)
    
    # Configurar o plot da matriz de confusão
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_base, 
                annot=True, 
                fmt='d', 
                cmap='Blues', 
                cbar=True,
                xticklabels=['Não Quebra', 'Quebra'],
                yticklabels=['Não Quebra', 'Quebra'])
    
    plt.title('Matriz de Confusão - KNN Base (k=5)', fontsize=14, fontweight='bold')
    plt.xlabel('Predição', fontsize=12)
    plt.ylabel('Real', fontsize=12)
    plt.tight_layout()
    
    # Salvar a matriz de confusão
    plt.savefig('../../assets/matriz_confusao_knn_base.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Calcular e exibir métricas adicionais da matriz de confusão
    tn, fp, fn, tp = cm_base.ravel()
    
    print("\nMétricas da Matriz de Confusão (KNN Base):")
    print(f"True Negatives (TN): {tn}")
    print(f"False Positives (FP): {fp}")
    print(f"False Negatives (FN): {fn}")
    print(f"True Positives (TP): {tp}")
    
    # Calcular métricas derivadas
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\nMétricas Calculadas:")
    print(f"Acurácia: {accuracy:.4f}")
    print(f"Precisão: {precision:.4f}")
    print(f"Recall (Sensibilidade): {recall:.4f}")
    print(f"Especificidade: {specificity:.4f}")
    print(f"F1-Score: {f1_score:.4f}")

    # ==============================================================================
    # ETAPA 5: OTIMIZAÇÃO DE HIPERPARÂMETROS PARA KNN
    # ==============================================================================
    print("\n" + "="*20)
    print("ETAPA 5: OTIMIZAÇÃO DE HIPERPARÂMETROS PARA KNN")
    print("="*20)

    param_grid = {
        'n_neighbors': list(range(3, 31, 2)),
        'weights': ['uniform', 'distance'],
        'metric': ['euclidean', 'manhattan', 'minkowski']
    }

    knn_opt = KNeighborsClassifier()
    knn_random = RandomizedSearchCV(estimator=knn_opt, param_distributions=param_grid,
                                    n_iter=50, cv=3, verbose=2, random_state=42,
                                    n_jobs=-1, scoring='f1')

    print("\nAjustando o modelo... (Isso pode levar vários minutos)")
    knn_random.fit(Xtr_scaled_resampled, ytr_resampled)

    print("\nMelhores parâmetros encontrados:")
    print(knn_random.best_params_)

    best_model = knn_random.best_estimator_
    ypred_best = best_model.predict(Xte_scaled)

    print("\n[Avaliação do K-Nearest Neighbors (KNN) Otimizado]")
    print(classification_report(yte, ypred_best))

    # ==============================================================================
    # ETAPA 5.1: MATRIZ DE CONFUSÃO DO MODELO KNN OTIMIZADO
    # ==============================================================================
    print("\n" + "="*20)
    print("ETAPA 5.1: MATRIZ DE CONFUSÃO DO MODELO KNN OTIMIZADO")
    print("="*20)
    
    # Gerar matriz de confusão para o modelo otimizado
    cm_optimized = confusion_matrix(yte, ypred_best)
    
    # Configurar o plot da matriz de confusão otimizada
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm_optimized, 
                annot=True, 
                fmt='d', 
                cmap='Greens', 
                cbar=True,
                xticklabels=['Não Quebra', 'Quebra'],
                yticklabels=['Não Quebra', 'Quebra'])
    
    plt.title(f'Matriz de Confusão - KNN Otimizado\nParâmetros: {knn_random.best_params_}', 
              fontsize=14, fontweight='bold')
    plt.xlabel('Predição', fontsize=12)
    plt.ylabel('Real', fontsize=12)
    plt.tight_layout()
    
    # Salvar a matriz de confusão otimizada
    plt.savefig('../../assets/matriz_confusao_knn_otimizado.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Calcular e exibir métricas adicionais da matriz de confusão otimizada
    tn_opt, fp_opt, fn_opt, tp_opt = cm_optimized.ravel()
    
    print("\nMétricas da Matriz de Confusão (KNN Otimizado):")
    print(f"True Negatives (TN): {tn_opt}")
    print(f"False Positives (FP): {fp_opt}")
    print(f"False Negatives (FN): {fn_opt}")
    print(f"True Positives (TP): {tp_opt}")
    
    # Calcular métricas derivadas para o modelo otimizado
    accuracy_opt = (tp_opt + tn_opt) / (tp_opt + tn_opt + fp_opt + fn_opt)
    precision_opt = tp_opt / (tp_opt + fp_opt) if (tp_opt + fp_opt) > 0 else 0
    recall_opt = tp_opt / (tp_opt + fn_opt) if (tp_opt + fn_opt) > 0 else 0
    specificity_opt = tn_opt / (tn_opt + fp_opt) if (tn_opt + fp_opt) > 0 else 0
    f1_score_opt = 2 * (precision_opt * recall_opt) / (precision_opt + recall_opt) if (precision_opt + recall_opt) > 0 else 0
    
    print(f"\nMétricas Calculadas (Otimizado):")
    print(f"Acurácia: {accuracy_opt:.4f}")
    print(f"Precisão: {precision_opt:.4f}")
    print(f"Recall (Sensibilidade): {recall_opt:.4f}")
    print(f"Especificidade: {specificity_opt:.4f}")
    print(f"F1-Score: {f1_score_opt:.4f}")
    
    # Comparação entre os modelos
    print("\n" + "="*50)
    print("COMPARAÇÃO ENTRE MODELOS")
    print("="*50)
    print(f"{'Métrica':<20} {'KNN Base':<15} {'KNN Otimizado':<15} {'Melhoria':<15}")
    print("-" * 65)
    print(f"{'Acurácia':<20} {accuracy:.4f:<15} {accuracy_opt:.4f:<15} {accuracy_opt-accuracy:+.4f}")
    print(f"{'Precisão':<20} {precision:.4f:<15} {precision_opt:.4f:<15} {precision_opt-precision:+.4f}")
    print(f"{'Recall':<20} {recall:.4f:<15} {recall_opt:.4f:<15} {recall_opt-recall:+.4f}")
    print(f"{'Especificidade':<20} {specificity:.4f:<15} {specificity_opt:.4f:<15} {specificity_opt-specificity:+.4f}")
    print(f"{'F1-Score':<20} {f1_score:.4f:<15} {f1_score_opt:.4f:<15} {f1_score_opt-f1_score:+.4f}")

except FileNotFoundError:
    print(f"ERRO: Arquivo '{input_file}' não encontrado. Verifique se o arquivo está no diretório correto.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")
