#!/usr/bin/env python3
"""
COMPLETE SCALING ANALYSIS OF QUANTITATIVE VARIABLES
==================================================

This code implements a complete scaling analysis including:
- Min-Max Normalization for non-normal variables
- Z-Score Standardization for approximately normal variables
- Generation of the 3 most important graphs
- Detailed statistical analyses
- Validation of preserved correlations
- Detection and analysis of outliers

Author: Data Analysis
Date: 2025
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Style configuration
plt.style.use('default')
plt.rcParams['figure.figsize'] = (15, 10)
plt.rcParams['font.size'] = 11
sns.set_palette("husl")

class AnalisadorEscalonamentoCompleto:
    """
    Class for complete scaling analysis of quantitative variables
    Includes generation of the 3 most important graphs and all analyses
    """
    
    def __init__(self):
        self.dados_originais = None
        self.dados_escalonados = None
        self.estatisticas = {}
        self.escaladores = {}
        
    def gerar_dados_exemplo(self):
        """
        Generates example data based on the analyzed real dataset
        """
        print("Generating example data based on real analysis...")
        
        np.random.seed(42)
        n_samples = 1000
        
        # Counter (mileage) - approximately normal distribution
        # Based on analysis: mean=174.145, std=72.873, min=3.880, max=396.312
        contador = np.random.normal(174145, 72873, n_samples)
        contador = np.clip(contador, 3880, 396312)
        
        # Quantity - positive asymmetric distribution (1-14)
        # Based on analysis: concentration in low values
        probs = [0.30, 0.25, 0.15, 0.10, 0.08, 0.05, 0.03, 0.02, 0.01, 0.005, 0.003, 0.002, 0.001, 0.001]
        probs = np.array(probs) / np.sum(probs)  # Normalizar
        quantidade = np.random.choice(range(1, 15), n_samples, p=probs)
        
        # Total cost - log-normal distribution
        # Based on analysis: mean=774, std=1174, min=2.61, max=37.890
        custo_base = np.random.lognormal(6.2, 1.2, n_samples)
        custo_total = np.clip(custo_base, 2.61, 37890)
        
        return pd.DataFrame({
            'contador': contador,
            'quantidade': quantidade,
            'custo_total': custo_total
        })
    
    def carregar_dados(self, caminho_arquivo=None):
        """
        Loads real data or generates simulated data
        """
        if caminho_arquivo:
            try:
                if caminho_arquivo.endswith('.xlsx'):
                    df = pd.read_excel(caminho_arquivo)
                elif caminho_arquivo.endswith('.csv'):
                    df = pd.read_csv(caminho_arquivo)
                else:
                    raise ValueError("Unsupported format")
                
                print(f"✓ Dados carregados de: {caminho_arquivo}")
                return df
            except Exception as e:
                print(f"✗ Erro ao carregar dados: {e}")
                print("Generating simulated data...")
        
        return self.gerar_dados_exemplo()
    
    def preparar_dados(self, df):
        """
        Prepares and cleans data for analysis
        """
        print("\\n" + "="*60)
        print("DATA PREPARATION")
        print("="*60)
        
        # Selecionar colunas relevantes
        colunas_necessarias = ['contador', 'quantidade', 'custo_total']
        
        # Verificar se as colunas existem
        colunas_existentes = []
        for col in colunas_necessarias:
            if col in df.columns:
                colunas_existentes.append(col)
            else:
                # Tentar encontrar colunas similares
                colunas_similares = [c for c in df.columns if col.lower() in c.lower()]
                if colunas_similares:
                    print(f"Usando '{colunas_similares[0]}' para '{col}'")
                    df = df.rename(columns={colunas_similares[0]: col})
                    colunas_existentes.append(col)
        
        if len(colunas_existentes) < 3:
            print("Columns not found, using simulated data")
            df = self.gerar_dados_exemplo()
            colunas_existentes = ['contador', 'quantidade', 'custo_total']
        
        # Filtrar dados
        self.dados_originais = df[colunas_existentes].copy()
        
        # Remover valores nulos
        antes = len(self.dados_originais)
        self.dados_originais = self.dados_originais.dropna()
        depois = len(self.dados_originais)
        
        print(f"Registros antes da limpeza: {antes:,}")
        print(f"Records after cleaning: {depois:,}")
        print(f"Registros removidos: {antes-depois:,}")
        
        # Basic information
        print(f"\\nVariables analyzed:")
        for col in self.dados_originais.columns:
            print(f"  • {col}: {self.dados_originais[col].dtype}")
        
        return self.dados_originais
    
    def calcular_estatisticas(self):
        """
        Calculates detailed descriptive statistics
        """
        print("\\n" + "="*60)
        print("DESCRIPTIVE STATISTICS CALCULATION")
        print("="*60)
        
        for coluna in self.dados_originais.columns:
            dados = self.dados_originais[coluna]
            
            # Basic statistics
            stats_basicas = {
                'n': len(dados),
                'minimo': dados.min(),
                'maximo': dados.max(),
                'media': dados.mean(),
                'desvio_padrao': dados.std(),
                'mediana': dados.median(),
                'q1': dados.quantile(0.25),
                'q3': dados.quantile(0.75),
                'iqr': dados.quantile(0.75) - dados.quantile(0.25),
                'mad': np.median(np.abs(dados - dados.median())),
                'assimetria': dados.skew(),
                'curtose': dados.kurtosis()
            }
            
            self.estatisticas[coluna] = stats_basicas
            
            print(f"\\n{coluna.upper()}:")
            print(f"  N: {stats_basicas['n']:,}")
            print(f"  Minimum: {stats_basicas['minimo']:,.2f}")
            print(f"  Maximum: {stats_basicas['maximo']:,.2f}")
            print(f"  Mean: {stats_basicas['media']:,.2f}")
            print(f"  Standard Deviation: {stats_basicas['desvio_padrao']:,.2f}")
            print(f"  Mediana: {stats_basicas['mediana']:,.2f}")
            print(f"  IQR: {stats_basicas['iqr']:,.2f}")
            print(f"  Assimetria: {stats_basicas['assimetria']:.3f}")
            print(f"  Curtose: {stats_basicas['curtose']:.3f}")
    
    def aplicar_escalonamento(self):
        """
        Applies scaling to variables using appropriate methods
        """
        print("\\n" + "="*60)
        print("SCALING APPLICATION")
        print("="*60)
        
        self.dados_escalonados = self.dados_originais.copy()
        
        # 1. COUNTER - Min-Max Normalization
        print("\\n1. COUNTER - Min-Max Normalization")
        print("-" * 40)
        
        contador_vals = self.dados_originais['contador'].values.reshape(-1, 1)
        scaler_contador = MinMaxScaler()
        contador_norm = scaler_contador.fit_transform(contador_vals).flatten()
        
        self.escaladores['contador'] = scaler_contador
        self.dados_escalonados['contador_norm'] = contador_norm
        
        print(f"   Formula: X_norm = (X - {scaler_contador.data_min_[0]:,.0f}) / {scaler_contador.data_max_[0] - scaler_contador.data_min_[0]:,.0f}")
        print(f"   Resultado: Valores entre {np.min(contador_norm):.4f} e {np.max(contador_norm):.4f}")
        
        # 2. QUANTITY - Min-Max Normalization
        print("\\n2. QUANTITY - Min-Max Normalization")
        print("-" * 40)
        
        quantidade_vals = self.dados_originais['quantidade'].values.reshape(-1, 1)
        scaler_quantidade = MinMaxScaler()
        quantidade_norm = scaler_quantidade.fit_transform(quantidade_vals).flatten()
        
        self.escaladores['quantidade'] = scaler_quantidade
        self.dados_escalonados['quantidade_norm'] = quantidade_norm
        
        print(f"   Formula: X_norm = (X - {scaler_quantidade.data_min_[0]:.0f}) / {scaler_quantidade.data_max_[0] - scaler_quantidade.data_min_[0]:.0f}")
        print(f"   Resultado: Valores entre {np.min(quantidade_norm):.4f} e {np.max(quantidade_norm):.4f}")
        
        # 3. TOTAL COST - Z-Score Standardization
        print("\\n3. TOTAL COST - Z-Score Standardization")
        print("-" * 40)
        
        custo_vals = self.dados_originais['custo_total'].values.reshape(-1, 1)
        scaler_custo = StandardScaler()
        custo_z = scaler_custo.fit_transform(custo_vals).flatten()
        
        self.escaladores['custo_total'] = scaler_custo
        self.dados_escalonados['custo_total_z'] = custo_z
        
        print(f"   Formula: Z = (X - {scaler_custo.mean_[0]:.2f}) / {scaler_custo.scale_[0]:.2f}")
        print(f"   Resultado: Valores entre {np.min(custo_z):.4f} e {np.max(custo_z):.4f}")
        
        print(f"\\n✓ Scaling completed for all variables")
    
    def grafico_1_histogramas_comparativos(self):
        """
        GRAPH 1: Comparative Histograms - Distributions before and after
        """
        print("\\n" + "="*60)
        print("CREATING GRAPH 1: COMPARATIVE HISTOGRAMS")
        print("="*60)
        
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle('GRAPH 1: Comparative Histograms - Before vs After Scaling', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        # 1. CONTADOR
        axes[0, 0].hist(self.dados_originais['contador'], bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        axes[0, 0].set_title('Original Counter (km)', fontsize=14, fontweight='bold')
        axes[0, 0].set_xlabel('Mileage (km)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Statistics in the graph
        stats_text = f'Min: {self.estatisticas["contador"]["minimo"]:,.0f}\\nMax: {self.estatisticas["contador"]["maximo"]:,.0f}\\nMean: {self.estatisticas["contador"]["media"]:,.0f}'
        axes[0, 0].text(0.02, 0.98, stats_text, transform=axes[0, 0].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        axes[0, 1].hist(self.dados_escalonados['contador_norm'], bins=50, alpha=0.7, color='lightcoral', edgecolor='black')
        axes[0, 1].set_title('Normalized Counter [0,1]', fontsize=14, fontweight='bold')
        axes[0, 1].set_xlabel('Normalized Value')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].grid(True, alpha=0.3)
        
        stats_text_norm = f'Min: {np.min(self.dados_escalonados["contador_norm"]):.4f}\\nMax: {np.max(self.dados_escalonados["contador_norm"]):.4f}\\nMean: {np.mean(self.dados_escalonados["contador_norm"]):.4f}'
        axes[0, 1].text(0.02, 0.98, stats_text_norm, transform=axes[0, 1].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # 2. QUANTIDADE
        axes[1, 0].hist(self.dados_originais['quantidade'], bins=range(1, int(self.dados_originais['quantidade'].max())+2), 
                       alpha=0.7, color='lightgreen', edgecolor='black')
        axes[1, 0].set_title('Original Quantity', fontsize=14, fontweight='bold')
        axes[1, 0].set_xlabel('Quantity (units)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].grid(True, alpha=0.3)
        
        stats_text = f'Min: {self.estatisticas["quantidade"]["minimo"]:.0f}\\nMax: {self.estatisticas["quantidade"]["maximo"]:.0f}\\nMean: {self.estatisticas["quantidade"]["media"]:.2f}'
        axes[1, 0].text(0.02, 0.98, stats_text, transform=axes[1, 0].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        axes[1, 1].hist(self.dados_escalonados['quantidade_norm'], bins=50, alpha=0.7, color='gold', edgecolor='black')
        axes[1, 1].set_title('Normalized Quantity [0,1]', fontsize=14, fontweight='bold')
        axes[1, 1].set_xlabel('Normalized Value')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].grid(True, alpha=0.3)
        
        stats_text_norm = f'Min: {np.min(self.dados_escalonados["quantidade_norm"]):.4f}\\nMax: {np.max(self.dados_escalonados["quantidade_norm"]):.4f}\\nMean: {np.mean(self.dados_escalonados["quantidade_norm"]):.4f}'
        axes[1, 1].text(0.02, 0.98, stats_text_norm, transform=axes[1, 1].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # 3. CUSTO TOTAL
        axes[2, 0].hist(self.dados_originais['custo_total'], bins=50, alpha=0.7, color='plum', edgecolor='black')
        axes[2, 0].set_title('Original Total Cost (R$)', fontsize=14, fontweight='bold')
        axes[2, 0].set_xlabel('Cost (R$)')
        axes[2, 0].set_ylabel('Frequency')
        axes[2, 0].grid(True, alpha=0.3)
        
        stats_text = f'Min: R$ {self.estatisticas["custo_total"]["minimo"]:.2f}\\nMax: R$ {self.estatisticas["custo_total"]["maximo"]:.2f}\\nMean: R$ {self.estatisticas["custo_total"]["media"]:.2f}'
        axes[2, 0].text(0.02, 0.98, stats_text, transform=axes[2, 0].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        axes[2, 1].hist(self.dados_escalonados['custo_total_z'], bins=50, alpha=0.7, color='orange', edgecolor='black')
        axes[2, 1].set_title('Standardized Total Cost (Z-Score)', fontsize=14, fontweight='bold')
        axes[2, 1].set_xlabel('Z-Score (standard deviations)')
        axes[2, 1].set_ylabel('Frequency')
        axes[2, 1].grid(True, alpha=0.3)
        
        # Add standard normal distribution line
        x_norm = np.linspace(self.dados_escalonados['custo_total_z'].min(), 
                            self.dados_escalonados['custo_total_z'].max(), 100)
        y_norm = len(self.dados_escalonados) * 0.5 * (1/np.sqrt(2*np.pi)) * np.exp(-0.5 * x_norm**2)
        axes[2, 1].plot(x_norm, y_norm, 'r--', linewidth=2, label='Standard Normal')
        axes[2, 1].legend()
        
        stats_text_z = f'Min: {np.min(self.dados_escalonados["custo_total_z"]):.4f}\\nMax: {np.max(self.dados_escalonados["custo_total_z"]):.4f}\\nMean: {np.mean(self.dados_escalonados["custo_total_z"]):.4f}'
        axes[2, 1].text(0.02, 0.98, stats_text_z, transform=axes[2, 1].transAxes, 
                       verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig('documents/grafico_1_histogramas_comparativos.png', dpi=300, bbox_inches='tight')
        plt.savefig('documents/grafico_1_histogramas_comparativos.pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        
        print("✓ Graph 1 saved: grafico_1_histogramas_comparativos.png/.pdf")
    
    def grafico_2_dispersao_correlacoes(self):
        """
        GRAPH 2: Scatter Plots - Preserved Correlations
        """
        print("\\n" + "="*60)
        print("CREATING GRAPH 2: SCATTER PLOTS AND CORRELATIONS")
        print("="*60)
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('GRAPH 2: Scatter Plots - Correlation Preservation', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        # Dados originais
        axes[0,0].scatter(self.dados_originais['contador'], self.dados_originais['custo_total'], 
                         alpha=0.6, color='blue', s=20)
        axes[0,0].set_xlabel('Counter (km)')
        axes[0,0].set_ylabel('Total Cost (R$)')
        axes[0,0].set_title('Original: Counter vs Cost', fontweight='bold')
        axes[0,0].grid(True, alpha=0.3)
        
        axes[0,1].scatter(self.dados_originais['quantidade'], self.dados_originais['custo_total'], 
                         alpha=0.6, color='green', s=20)
        axes[0,1].set_xlabel('Quantity')
        axes[0,1].set_ylabel('Total Cost (R$)')
        axes[0,1].set_title('Original: Quantity vs Cost', fontweight='bold')
        axes[0,1].grid(True, alpha=0.3)
        
        axes[0,2].scatter(self.dados_originais['contador'], self.dados_originais['quantidade'], 
                         alpha=0.6, color='red', s=20)
        axes[0,2].set_xlabel('Counter (km)')
        axes[0,2].set_ylabel('Quantity')
        axes[0,2].set_title('Original: Counter vs Quantity', fontweight='bold')
        axes[0,2].grid(True, alpha=0.3)
        
        # Dados escalonados
        axes[1,0].scatter(self.dados_escalonados['contador_norm'], self.dados_escalonados['custo_total_z'], 
                         alpha=0.6, color='blue', s=20)
        axes[1,0].set_xlabel('Normalized Counter')
        axes[1,0].set_ylabel('Cost Z-Score')
        axes[1,0].set_title('Scaled: Counter vs Cost', fontweight='bold')
        axes[1,0].grid(True, alpha=0.3)
        
        axes[1,1].scatter(self.dados_escalonados['quantidade_norm'], self.dados_escalonados['custo_total_z'], 
                         alpha=0.6, color='green', s=20)
        axes[1,1].set_xlabel('Normalized Quantity')
        axes[1,1].set_ylabel('Cost Z-Score')
        axes[1,1].set_title('Scaled: Quantity vs Cost', fontweight='bold')
        axes[1,1].grid(True, alpha=0.3)
        
        axes[1,2].scatter(self.dados_escalonados['contador_norm'], self.dados_escalonados['quantidade_norm'], 
                         alpha=0.6, color='red', s=20)
        axes[1,2].set_xlabel('Normalized Counter')
        axes[1,2].set_ylabel('Normalized Quantity')
        axes[1,2].set_title('Scaled: Counter vs Quantity', fontweight='bold')
        axes[1,2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('documents/grafico_2_dispersao_correlacoes.png', dpi=300, bbox_inches='tight')
        plt.savefig('documents/grafico_2_dispersao_correlacoes.pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        
        # Correlation verification
        print("\\nCORRELATION VERIFICATION:")
        print("="*50)
        
        # Original correlations
        corr_orig = self.dados_originais[['contador', 'quantidade', 'custo_total']].corr()
        print("Original Correlations:")
        print(corr_orig.round(4))
        
        # Scaled correlations
        corr_esc = self.dados_escalonados[['contador_norm', 'quantidade_norm', 'custo_total_z']].corr()
        print("\\nScaled Correlations:")
        print(corr_esc.round(4))
        
        # Difference
        diferenca_max = np.abs(corr_orig.values - corr_esc.values).max()
        print(f"\\nMaximum difference: {diferenca_max:.6f}")
        
        if diferenca_max < 0.001:
            print("✓ CORRELATIONS PERFECTLY PRESERVED!")
        else:
            print("⚠️ WARNING: Correlations were not adequately preserved")
        
        print("✓ Graph 2 saved: grafico_2_dispersao_correlacoes.png/.pdf")
    
    def grafico_3_boxplots_outliers(self):
        """
        GRAPH 3: Comparative Box Plots - Outliers and Quartiles
        """
        print("\\n" + "="*60)
        print("CREATING GRAPH 3: BOX PLOTS AND OUTLIERS")
        print("="*60)
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('GRAPH 3: Comparative Box Plots - Outliers and Quartiles', 
                     fontsize=16, fontweight='bold', y=0.98)
        
        # Dados originais
        axes[0,0].boxplot(self.dados_originais['contador'], patch_artist=True, 
                         boxprops=dict(facecolor='skyblue', alpha=0.7))
        axes[0,0].set_title('Original Counter', fontweight='bold')
        axes[0,0].set_ylabel('Mileage (km)')
        axes[0,0].grid(True, alpha=0.3)
        
        axes[0,1].boxplot(self.dados_originais['quantidade'], patch_artist=True,
                         boxprops=dict(facecolor='lightgreen', alpha=0.7))
        axes[0,1].set_title('Original Quantity', fontweight='bold')
        axes[0,1].set_ylabel('Quantity')
        axes[0,1].grid(True, alpha=0.3)
        
        axes[0,2].boxplot(self.dados_originais['custo_total'], patch_artist=True,
                         boxprops=dict(facecolor='plum', alpha=0.7))
        axes[0,2].set_title('Original Total Cost', fontweight='bold')
        axes[0,2].set_ylabel('Cost (R$)')
        axes[0,2].grid(True, alpha=0.3)
        
        # Dados escalonados
        axes[1,0].boxplot(self.dados_escalonados['contador_norm'], patch_artist=True,
                         boxprops=dict(facecolor='lightcoral', alpha=0.7))
        axes[1,0].set_title('Normalized Counter', fontweight='bold')
        axes[1,0].set_ylabel('Normalized Value')
        axes[1,0].grid(True, alpha=0.3)
        
        axes[1,1].boxplot(self.dados_escalonados['quantidade_norm'], patch_artist=True,
                         boxprops=dict(facecolor='gold', alpha=0.7))
        axes[1,1].set_title('Normalized Quantity', fontweight='bold')
        axes[1,1].set_ylabel('Normalized Value')
        axes[1,1].grid(True, alpha=0.3)
        
        axes[1,2].boxplot(self.dados_escalonados['custo_total_z'], patch_artist=True,
                         boxprops=dict(facecolor='orange', alpha=0.7))
        axes[1,2].set_title('Standardized Total Cost', fontweight='bold')
        axes[1,2].set_ylabel('Z-Score')
        axes[1,2].grid(True, alpha=0.3)
        
        # Add reference lines in Z-Score
        axes[1,2].axhline(y=3, color='red', linestyle='--', alpha=0.7, label='±3σ (outliers)')
        axes[1,2].axhline(y=-3, color='red', linestyle='--', alpha=0.7)
        axes[1,2].axhline(y=0, color='black', linestyle='-', alpha=0.5, label='Mean')
        axes[1,2].legend()
        
        plt.tight_layout()
        plt.savefig('documents/grafico_3_boxplots_outliers.png', dpi=300, bbox_inches='tight')
        plt.savefig('documents/grafico_3_boxplots_outliers.pdf', bbox_inches='tight')
        plt.show()
        plt.close()
        
        # Outlier analysis
        print("\\nOUTLIER ANALYSIS:")
        print("="*50)
        
        for col in ['contador', 'quantidade', 'custo_total']:
            Q1 = self.dados_originais[col].quantile(0.25)
            Q3 = self.dados_originais[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = self.dados_originais[(self.dados_originais[col] < lower_bound) | 
                                          (self.dados_originais[col] > upper_bound)][col]
            print(f"{col.upper()}:")
            print(f"  Outliers detected: {len(outliers)} ({len(outliers)/len(self.dados_originais)*100:.1f}%)")
            print(f"  Normal range: [{lower_bound:.2f}, {upper_bound:.2f}]")
        
        # Z-Score outliers
        z_outliers = self.dados_escalonados[abs(self.dados_escalonados['custo_total_z']) > 3]['custo_total_z']
        print(f"\\nCUSTO_TOTAL_Z (Z-Score):")
        print(f"  Outliers (|z| > 3): {len(z_outliers)} ({len(z_outliers)/len(self.dados_escalonados)*100:.1f}%)")
        
        print("✓ Graph 3 saved: grafico_3_boxplots_outliers.png/.pdf")
    
    def criar_tabela_comparativa(self):
        """
        Cria tabela comparativa dos primeiros 10 registros
        """
        print("\\n" + "="*60)
        print("CREATING COMPARATIVE TABLE")
        print("="*60)
        
        # Primeiros 10 registros
        primeiros_10_orig = self.dados_originais.head(10).copy()
        
        # Aplicar escalonamento aos primeiros 10
        primeiros_10_esc = pd.DataFrame()
        
        # Contador normalizado
        contador_vals = primeiros_10_orig['contador'].values.reshape(-1, 1)
        primeiros_10_esc['contador_norm'] = self.escaladores['contador'].transform(contador_vals).flatten()
        
        # Quantidade normalizada
        quantidade_vals = primeiros_10_orig['quantidade'].values.reshape(-1, 1)
        primeiros_10_esc['quantidade_norm'] = self.escaladores['quantidade'].transform(quantidade_vals).flatten()
        
        # Custo padronizado
        custo_vals = primeiros_10_orig['custo_total'].values.reshape(-1, 1)
        primeiros_10_esc['custo_total_z'] = self.escaladores['custo_total'].transform(custo_vals).flatten()
        
        # Display tables
        print("\\nTABLE 1: FIRST 10 RECORDS - ORIGINAL DATA")
        print("-" * 60)
        primeiros_10_orig_display = primeiros_10_orig.copy()
        primeiros_10_orig_display['contador'] = primeiros_10_orig_display['contador'].apply(lambda x: f"{x:,.0f} km")
        primeiros_10_orig_display['quantidade'] = primeiros_10_orig_display['quantidade'].apply(lambda x: f"{x:.0f} un")
        primeiros_10_orig_display['custo_total'] = primeiros_10_orig_display['custo_total'].apply(lambda x: f"R$ {x:,.2f}")
        primeiros_10_orig_display.index = range(1, 11)
        print(primeiros_10_orig_display.to_string())
        
        print("\\n\\nTABLE 2: FIRST 10 RECORDS - SCALED DATA")
        print("-" * 60)
        primeiros_10_esc_display = primeiros_10_esc.copy()
        primeiros_10_esc_display['contador_norm'] = primeiros_10_esc_display['contador_norm'].apply(lambda x: f"{x:.4f}")
        primeiros_10_esc_display['quantidade_norm'] = primeiros_10_esc_display['quantidade_norm'].apply(lambda x: f"{x:.4f}")
        primeiros_10_esc_display['custo_total_z'] = primeiros_10_esc_display['custo_total_z'].apply(lambda x: f"{x:.4f}")
        primeiros_10_esc_display.index = range(1, 11)
        print(primeiros_10_esc_display.to_string())
        
        # Save CSVs
        primeiros_10_orig.to_csv('documents/dados_originais_10_registros.csv', index=True)
        primeiros_10_esc.to_csv('documents/dados_escalonados_10_registros.csv', index=True)
        
        print(f"\\n✓ Tables saved:")
        print(f"  - documents/dados_originais_10_registros.csv")
        print(f"  - documents/dados_escalonados_10_registros.csv")
    
    def gerar_relatorio_final(self):
        """
        Generates final report with statistics and equations
        """
        print("\\n" + "="*80)
        print("FINAL SCALING REPORT")
        print("="*80)
        
        # Statistics table
        df_stats = pd.DataFrame()
        
        for var, stats in self.estatisticas.items():
            df_stats[var.upper()] = [
                f"{stats['n']:,}",
                f"{stats['minimo']:,.2f}",
                f"{stats['maximo']:,.2f}",
                f"{stats['media']:,.2f}",
                f"{stats['desvio_padrao']:,.2f}",
                f"{stats['mediana']:,.2f}",
                f"{stats['iqr']:,.2f}",
                f"{stats['assimetria']:.3f}",
                f"{stats['curtose']:.3f}"
            ]
        
        df_stats.index = ['N', 'Minimum', 'Maximum', 'Mean', 'Standard Deviation', 'Median', 'IQR', 'Skewness', 'Kurtosis']
        
        print("\\nDESCRIPTIVE STATISTICS TABLE:")
        print("-" * 60)
        print(df_stats.to_string())
        
        # Save table
        df_stats.to_csv('documents/estatisticas_descritivas.csv')
        
        # Scaling equations
        print("\\n" + "="*80)
        print("APPLIED SCALING EQUATIONS")
        print("="*80)
        
        print("\\n1. COUNTER (Min-Max Normalization):")
        contador_min = self.escaladores['contador'].data_min_[0]
        contador_max = self.escaladores['contador'].data_max_[0]
        print(f"   X_norm = (X - {contador_min:,.0f}) / ({contador_max:,.0f} - {contador_min:,.0f})")
        print(f"   X_norm = (X - {contador_min:,.0f}) / {contador_max - contador_min:,.0f}")
        
        print("\\n2. QUANTITY (Min-Max Normalization):")
        quantidade_min = self.escaladores['quantidade'].data_min_[0]
        quantidade_max = self.escaladores['quantidade'].data_max_[0]
        print(f"   X_norm = (X - {quantidade_min:.0f}) / ({quantidade_max:.0f} - {quantidade_min:.0f})")
        print(f"   X_norm = (X - {quantidade_min:.0f}) / {quantidade_max - quantidade_min:.0f}")
        
        print("\\n3. TOTAL COST (Z-Score Standardization):")
        custo_mean = self.escaladores['custo_total'].mean_[0]
        custo_std = self.escaladores['custo_total'].scale_[0]
        print(f"   Z = (X - {custo_mean:.2f}) / {custo_std:.2f}")
        
        print(f"\\n✓ Report saved: documents/estatisticas_descritivas.csv")
    
    def executar_analise_completa(self, caminho_arquivo=None):
        """
        Executes complete scaling analysis with the 3 most important graphs
        """
        print("="*80)
        print("COMPLETE VARIABLE SCALING ANALYSIS")
        print("Including the 3 Most Important Graphs")
        print("="*80)
        
        # 1. Carregar dados
        df = self.carregar_dados(caminho_arquivo)
        
        # 2. Preparar dados
        self.preparar_dados(df)
        
        # 3. Calculate statistics
        self.calcular_estatisticas()
        
        # 4. Aplicar escalonamento
        self.aplicar_escalonamento()
        
        # 5. Create the 3 most important graphs
        self.grafico_1_histogramas_comparativos()
        self.grafico_2_dispersao_correlacoes()
        self.grafico_3_boxplots_outliers()
        
        # 6. Criar tabela comparativa
        self.criar_tabela_comparativa()
        
        # 7. Generate final report
        self.gerar_relatorio_final()
        
        print("\\n" + "="*80)
        print("ANALYSIS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("Generated files:")
        print("  📊 GRAPHS:")
        print("    • documents/grafico_1_histogramas_comparativos.png/.pdf")
        print("    • documents/grafico_2_dispersao_correlacoes.png/.pdf")
        print("    • documents/grafico_3_boxplots_outliers.png/.pdf")
        print("  📋 DATA:")
        print("    • documents/dados_originais_10_registros.csv")
        print("    • documents/dados_escalonados_10_registros.csv")
        print("    • documents/estatisticas_descritivas.csv")
        
        print("\\n🎯 THE 3 MOST IMPORTANT GRAPHS:")
        print("  1. Histograms: Validate distribution preservation")
        print("  2. Scatter Plots: Confirm correlations preserved")
        print("  3. Box Plots: Identify outliers and quartiles")
        
        return {
            'dados_originais': self.dados_originais,
            'dados_escalonados': self.dados_escalonados,
            'estatisticas': self.estatisticas,
            'escaladores': self.escaladores
        }

def main():
    """
        Main function - executes complete analysis
    """
    analisador = AnalisadorEscalonamentoCompleto()
    
        # Try to load real data, otherwise use simulated
    caminhos_possiveis = [
        'data/BASE_DADOS_INTELI_FADEL_V4.xlsx',
        '../data/BASE_DADOS_INTELI_FADEL_V4.xlsx',
        'BASE_DADOS_INTELI_FADEL_V4.xlsx'
    ]
    
    dados_carregados = False
    for caminho in caminhos_possiveis:
        try:
            resultados = analisador.executar_analise_completa(caminho)
            dados_carregados = True
            break
        except:
            continue
    
    if not dados_carregados:
        print("Using simulated data based on real analysis...")
        resultados = analisador.executar_analise_completa()
    
    return resultados

if __name__ == "__main__":
    resultados = main()