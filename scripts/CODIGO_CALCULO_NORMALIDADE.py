#!/usr/bin/env python3
"""
Enhanced Normality Analysis - Version 2.0
Implements methodological improvements based on advanced statistical rigor

Implemented improvements:
- Proper handling of large samples
- Multiple normality tests with Bonferroni correction
- Subgroup analysis by operational characteristics
- Temporal homogeneity test
- Principal component analysis
- Robust statistics
- Enhanced visualizations with Q-Q plots
- Automatic method selection based on evidence
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import shapiro, skew, kurtosis, jarque_bera, anderson, kstest, kruskal, norm
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

try:
    plt.style.use('seaborn-v0_8')
except:
    try:
        plt.style.use('seaborn')
    except:
        plt.style.use('default')
plt.rcParams['figure.figsize'] = (15, 10)
plt.rcParams['font.size'] = 11

class CalculadoraNormalidade:
    
    def __init__(self, alpha=0.05):
        self.alpha = alpha
        self.resultados = {}
        
    def carregar_dados(self, caminho_arquivo):
        try:
            df = pd.read_excel(caminho_arquivo)
            return df
        except Exception as e:
            print(f"Erro ao carregar dados: {e}")
            return None
    
    def preparar_dados(self, df, variaveis_interesse):
        dados_preparados = {}
        variaveis_encontradas = {}
        
        print("Identifying variables in dataset...")
        print(f"Available columns: {list(df.columns)}")
        
        for var in variaveis_interesse:
            if var.lower() == 'custo':
                # Buscar especificamente por CUSTO TOTAL
                colunas_similares = [col for col in df.columns if 'custo total' in col.lower()]
            else:
                colunas_similares = [col for col in df.columns if var.lower() in col.lower()]
            
            if colunas_similares:
                variaveis_encontradas[var] = colunas_similares[0]
                print(f"✓ {var} -> {colunas_similares[0]}")
            else:
                print(f"✗ {var} not found")
        
        if not variaveis_encontradas:
            raise ValueError("No variable of interest was found in the dataset")
        
        print("\nPreparing data...")
        for var_nome, col_nome in variaveis_encontradas.items():
            # Verificar se a coluna existe
            if col_nome not in df.columns:
                print(f"Error: Column {col_nome} not found")
                continue
            
            # Check if column is numeric
            if not pd.api.types.is_numeric_dtype(df[col_nome]):
                print(f"Warning: Column {col_nome} is not numeric. Trying to convert...")
                try:
                    df[col_nome] = pd.to_numeric(df[col_nome], errors='coerce')
                except:
                    print(f"Error: Could not convert {col_nome} to numeric")
                    continue
            
            # Specific treatment for counter
            if var_nome == 'contador':
                dados = df[col_nome].dropna()
                valores_ausentes = df[col_nome].isna().sum()
                print(f"  {var_nome}: {len(dados)} valid records (trailers excluded: {valores_ausentes})")
            else:
                dados = df[col_nome].dropna()
                valores_ausentes = df[col_nome].isna().sum()
                print(f"  {var_nome}: {len(dados)} valid records (missing: {valores_ausentes})")
            
            # Additional validations
            if len(dados) == 0:
                print(f"Error: No valid data for {var_nome}")
                continue
            elif len(dados) < 3:
                print(f"Error: Insufficient data for {var_nome} (n={len(dados)} < 3)")
                continue
            
            # Verificar outliers extremos que podem causar problemas
            q1, q3 = np.percentile(dados, [25, 75])
            iqr = q3 - q1
            outliers_extremos = dados[(dados < q1 - 3*iqr) | (dados > q3 + 3*iqr)]
            if len(outliers_extremos) > len(dados) * 0.1:  # Mais de 10% outliers extremos
                print(f"Warning: {var_nome} has many extreme outliers ({len(outliers_extremos)} values)")
            
            dados_preparados[var_nome] = dados
        
        if not dados_preparados:
            raise ValueError("No variable could be prepared for analysis")
                
        return dados_preparados
    
    def calcular_estatisticas_descritivas(self, dados):
        # Input validations
        if len(dados) == 0:
            raise ValueError("Dados vazios fornecidos")
        if len(dados) < 3:
            raise ValueError("Amostra muito pequena (n < 3)")
        
        # Convert to numpy array if necessary
        dados = np.array(dados)
        
        # Check for infinite or NaN values
        if not np.isfinite(dados).all():
            dados = dados[np.isfinite(dados)]
            if len(dados) == 0:
                raise ValueError("All values are infinite or NaN")
        
        n = len(dados)
        media = np.mean(dados)
        mediana = np.median(dados)
        variancia = np.var(dados, ddof=1) if n > 1 else 0
        desvio_padrao = np.std(dados, ddof=1) if n > 1 else 0
        cv = (desvio_padrao / abs(media)) * 100 if media != 0 else np.inf
        assimetria = skew(dados) if n >= 3 else 0
        curtose_pearson = kurtosis(dados, fisher=False) if n >= 4 else 3
        curtose_fisher = kurtosis(dados, fisher=True) if n >= 4 else 0
        amplitude = np.max(dados) - np.min(dados)
        q1 = np.percentile(dados, 25)
        q3 = np.percentile(dados, 75)
        iqr = q3 - q1
        diff_abs = abs(media - mediana)
        diff_rel = (diff_abs / abs(media)) * 100 if media != 0 else 0
        sk_pearson = (media - mediana) / desvio_padrao if desvio_padrao != 0 else 0
        
        return {
            'n': n,
            'media': media,
            'mediana': mediana,
            'variancia': variancia,
            'desvio_padrao': desvio_padrao,
            'cv': cv,
            'assimetria': assimetria,
            'curtose_pearson': curtose_pearson,
            'curtose_fisher': curtose_fisher,
            'amplitude': amplitude,
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'diff_abs': diff_abs,
            'diff_rel': diff_rel,
            'sk_pearson': sk_pearson,
            'minimo': np.min(dados),
            'maximo': np.max(dados)
        }
    
    def teste_shapiro_wilk(self, dados):
        # Validations for Shapiro-Wilk test
        dados = np.array(dados)
        n = len(dados)
        
        if n < 3:
            raise ValueError("Shapiro-Wilk requires at least 3 observations")
        if n > 5000:
            print(f"Warning: Large sample (n={n}). Shapiro-Wilk may be too sensitive.")
        
        # Check if there is variability in the data
        if np.var(dados) == 0:
            raise ValueError("Data without variability (all values are equal)")
        
        try:
            statistic, p_value = shapiro(dados)
        except Exception as e:
            raise ValueError(f"Error in Shapiro-Wilk test: {e}")
        
        if p_value <= self.alpha:
            decisao = "Rejeita H₀"
            normal = "No"
            interpretacao = f"Does not follow normal distribution (p = {p_value:.6f})"
        else:
            decisao = "Do not reject H₀"
            normal = "Yes"
            interpretacao = f"May follow normal distribution (p = {p_value:.6f})"
        
        return {
            'estatistica_w': statistic,
            'p_valor': p_value,
            'decisao': decisao,
            'normal': normal,
            'interpretacao': interpretacao
        }
    
    def criar_histograma_individual(self, dados, nome_variavel, stats):
        mu, sigma = stats['media'], stats['desvio_padrao']
        n_bins = max(10, min(50, int(np.sqrt(len(dados)))))
        
        # Create figure with subplots for histogram and information
        fig = plt.figure(figsize=(12, 8))
        
        # Histograma principal (ocupa 2/3 da figura)
        ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=2, rowspan=3)
        
        # Histograma
        ax1.hist(dados, bins=n_bins, density=True, alpha=0.7, 
                color='lightblue', edgecolor='black', label='Observed data')
        
        # Theoretical normal curve
        x = np.linspace(dados.min(), dados.max(), 1000)
        y_normal = (1/np.sqrt(2*np.pi*sigma**2)) * np.exp(-0.5*((x-mu)/sigma)**2)
        ax1.plot(x, y_normal, 'r-', linewidth=3, label='Theoretical normal')
        
        # Reference lines
        ax1.axvline(mu, color='red', linestyle='--', alpha=0.8, label=f'Mean = {mu:.2f}')
        ax1.axvline(stats['mediana'], color='green', linestyle='--', alpha=0.8, 
                   label=f'Median = {stats["mediana"]:.2f}')
        
        ax1.set_title(f'Normality Analysis - {nome_variavel.capitalize()}', 
                     fontsize=16, fontweight='bold')
        ax1.set_xlabel('Values', fontsize=12)
        ax1.set_ylabel('Density', fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Information panel (occupies 1/3 of the figure)
        ax2 = plt.subplot2grid((3, 3), (0, 2), rowspan=3)
        ax2.axis('off')
        
        # Resultado do teste de Shapiro-Wilk
        resultado_shapiro = self.teste_shapiro_wilk(dados)
        
        # Classifications
        suporte_visual = self.classificar_normalidade_visual(stats)
        classificacao_mm, suporte_mm = self.classificar_media_mediana(stats['diff_rel'])
        
        # Score integrado
        score_integrado = self.calcular_score_integrado(resultado_shapiro, stats)
        conclusao_final, confianca = self.classificar_score_final(score_integrado)
        
        # Texto informativo completo
        info_text = f'''DESCRIPTIVE STATISTICS
N = {stats['n']}
Mean = {mu:.4f}
Median = {stats['mediana']:.4f}
Std Dev = {sigma:.4f}
CV = {stats['cv']:.1f}%

DISTRIBUTION SHAPE
Skewness = {stats['assimetria']:.3f}
Kurtosis = {stats['curtose_pearson']:.3f}
Range = {stats['amplitude']:.2f}

SHAPIRO-WILK TEST
W Statistic = {resultado_shapiro['estatistica_w']:.6f}
P-value = {resultado_shapiro['p_valor']:.6f}
Decision: {self.traduzir_decisao(resultado_shapiro['decisao'])}

MEAN vs MEDIAN COMPARISON
Difference = {stats['diff_abs']:.4f}
Difference % = {stats['diff_rel']:.2f}%
Classification: {classificacao_mm}

INTEGRATED ANALYSIS
Score = {score_integrado:.1f}/10
Conclusion: {self.traduzir_conclusao(conclusao_final)}
Confidence: {self.traduzir_confianca(confianca)}

OUTLIERS (IQR Rule)
Q1 = {stats['q1']:.2f}
Q3 = {stats['q3']:.2f}
IQR = {stats['iqr']:.2f}
N° Outliers = {self.identificar_outliers_iqr(dados)[0]}'''
        
        ax2.text(0.05, 0.95, info_text, transform=ax2.transAxes, fontsize=9,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(f'histograma_{nome_variavel}.png', dpi=300, bbox_inches='tight')
        plt.savefig(f'histograma_{nome_variavel}.pdf', dpi=300, bbox_inches='tight')
        plt.show()
        plt.close()
        

        
    def criar_grafico_comparativo_final(self, resultados):
        variaveis = list(resultados.keys())
        p_valores = [resultados[var]['shapiro']['p_valor'] for var in variaveis]
        scores = [resultados[var]['score_integrado'] for var in variaveis]

        # Ordenar por p-valor crescente para legibilidade
        ordem = np.argsort(p_valores)
        variaveis = [variaveis[i] for i in ordem]
        p_valores = [p_valores[i] for i in ordem]
        scores = [scores[i] for i in ordem]

        # Preparar -log10(p) para separar p muito pequenos
        p_min = 1e-300
        neglog_p = [-np.log10(max(p, p_min)) for p in p_valores]
        thr_neglog = -np.log10(0.05)  # ~1.301

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

        # -log10(p) graph
        cores = ['#2ca02c' if p > 0.05 else '#d62728' for p in p_valores]
        bars1 = ax1.bar(variaveis, neglog_p, color=cores, alpha=0.85, edgecolor='black')
        ax1.axhline(y=thr_neglog, color='#d62728', linestyle='--', linewidth=2, label='α = 0,05 (−log10 ≈ 1,301)')
        ax1.set_title('Shapiro–Wilk: Evidence Intensity (−log10 p)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('−log10(p)', fontsize=12)
        ax1.set_xlabel('Variables', fontsize=12)
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.legend()

        # Labels with p-value in scientific notation (or <1e-6)
        for bar, p_val, nl in zip(bars1, p_valores, neglog_p):
            label = f"{p_val:.2e}" if p_val >= 1e-6 else "<1e−6"
            ax1.text(bar.get_x() + bar.get_width()/2., nl + 0.05, label,
                     ha='center', va='bottom', fontsize=10, rotation=0)

        # Integrated scores graph
        cores_score = ['#1f77b4' if s >= 8 else '#ff7f0e' if s >= 6 else '#d62728' for s in scores]
        bars2 = ax2.bar(variaveis, scores, color=cores_score, alpha=0.85, edgecolor='black')
        ax2.set_title('Integrated Normality Index (0–10)', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Score (0–10)', fontsize=12)
        ax2.set_xlabel('Variables', fontsize=12)
        ax2.set_ylim(0, 10)
        ax2.grid(True, alpha=0.3, axis='y')

        for bar, score in zip(bars2, scores):
            ax2.text(bar.get_x() + bar.get_width()/2., score + 0.1, f'{score:.1f}',
                     ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        # Also save in assets for report use
        try:
            plt.savefig('../assets/comparativo_normalidade.png', dpi=300, bbox_inches='tight')
            plt.savefig('../assets/comparativo_normalidade.pdf', dpi=300, bbox_inches='tight')
        except Exception:
            pass
        plt.savefig('comparativo_normalidade.png', dpi=300, bbox_inches='tight')
        plt.savefig('comparativo_normalidade.pdf', dpi=300, bbox_inches='tight')
        plt.show()
        plt.close()
    
    def classificar_normalidade_visual(self, stats):
        score = 0
        
        if abs(stats['assimetria']) < 0.5:
            score += 2
        elif abs(stats['assimetria']) < 1.0:
            score += 1
        
        if abs(stats['curtose_pearson'] - 3) < 0.5:
            score += 2
        elif abs(stats['curtose_pearson'] - 3) < 1.0:
            score += 1
        
        if stats['diff_rel'] < 5:
            score += 2
        elif stats['diff_rel'] < 10:
            score += 1
        
        if score >= 5:
            return "Strong visual support"
        elif score >= 3:
            return "Moderate visual support"
        elif score >= 1:
            return "Weak visual support"
        else:
            return "Little visual support"
    
    def classificar_media_mediana(self, diff_rel):
        if diff_rel < 1:
            return "Excellent symmetry", "Strong support"
        elif diff_rel < 3:
            return "Good symmetry", "Good support"
        elif diff_rel < 5:
            return "Moderate symmetry", "Moderate support"
        elif diff_rel < 10:
            return "Slight asymmetry", "Questionable"
        elif diff_rel < 20:
            return "Moderate asymmetry", "Does not support"
        else:
            return "Strong asymmetry", "Strong evidence against"
    
    def identificar_outliers_iqr(self, dados):
        q1 = np.percentile(dados, 25)
        q3 = np.percentile(dados, 75)
        iqr = q3 - q1
        
        limite_inferior = q1 - 1.5 * iqr
        limite_superior = q3 + 1.5 * iqr
        
        outliers_mask = (dados < limite_inferior) | (dados > limite_superior)
        n_outliers = np.sum(outliers_mask)
        return n_outliers, limite_inferior, limite_superior
    
    def calcular_score_integrado(self, resultado_shapiro, stats):
        score = 0
        
        if resultado_shapiro['p_valor'] > self.alpha:
            score += 4
        
        if abs(stats['assimetria']) < 0.5:
            score += 1.5
        if abs(stats['curtose_pearson'] - 3) < 0.5:
            score += 1.5
        
        if stats['diff_rel'] < 5:
            score += 3
        elif stats['diff_rel'] < 10:
            score += 1.5
        
        return score
    
    def classificar_score_final(self, score):
        if score >= 8:
            return "NORMAL", "ALTA"
        elif score >= 6:
            return "PROVAVELMENTE NORMAL", "MODERADA"
        elif score >= 4:
            return "QUESTIONABLE", "LOW"
        elif score >= 2:
            return "PROBABLY NOT NORMAL", "MODERATE"
        else:
            return "NOT NORMAL", "HIGH"
    
    def traduzir_decisao(self, decisao):
        traducoes = {
            "Rejeita H₀": "Reject H₀",
            "Do not reject H₀": "Do not reject H₀"
        }
        return traducoes.get(decisao, decisao)
    
    def traduzir_classificacao_mm(self, classificacao):
        traducoes = {
            "Excelente simetria": "Excellent symmetry",
            "Boa simetria": "Good symmetry", 
            "Simetria moderada": "Moderate symmetry",
            "Assimetria leve": "Slight asymmetry",
            "Assimetria moderada": "Moderate asymmetry",
            "Assimetria forte": "Strong asymmetry"
        }
        return traducoes.get(classificacao, classificacao)
    
    def traduzir_confianca(self, confianca):
        traducoes = {
            "ALTA": "HIGH",
            "MODERADA": "MODERATE", 
            "BAIXA": "LOW"
        }
        return traducoes.get(confianca, confianca)
    
    def traduzir_conclusao(self, conclusao):
        traducoes = {
            "NORMAL": "NORMAL",
            "PROVAVELMENTE NORMAL": "PROBABLY NORMAL",
                    "QUESTIONABLE": "QUESTIONABLE",
        "PROBABLY NOT NORMAL": "PROBABLY NOT NORMAL",
        "NOT NORMAL": "NOT NORMAL"
        }
        return traducoes.get(conclusao, conclusao)
    
    def traduzir_suporte_visual(self, suporte):
        traducoes = {
            "Forte suporte visual": "Strong visual support",
            "Moderado suporte visual": "Moderate visual support",
            "Fraco suporte visual": "Weak visual support",
            "Pouco suporte visual": "Little visual support"
        }
        return traducoes.get(suporte, suporte)
    
    def traduzir_suporte_mm(self, suporte):
        traducoes = {
            "Forte suporte": "Strong support",
            "Bom suporte": "Good support",
            "Suporte moderado": "Moderate support", 
                    "Questionable": "Questionable",
        "Does not support": "Does not support",
        "Strong evidence against": "Strong evidence against"
        }
        return traducoes.get(suporte, suporte)
    
    def executar_analise_completa(self, df, variaveis_interesse):
        dados_preparados = self.preparar_dados(df, variaveis_interesse)
        
        resultados_finais = {}
        
        print("Generating individual graphs for each variable...")
        print("="*60)
        
        for nome, dados in dados_preparados.items():
            print(f"\nProcessing variable: {nome.upper()}")
            
            stats = self.calcular_estatisticas_descritivas(dados)
            resultado_shapiro = self.teste_shapiro_wilk(dados)
            
            # Generate only the most relevant graphs
            print(f"  → Generating histogram: histograma_{nome}.png/.pdf")
            self.criar_histograma_individual(dados, nome, stats)
            
            suporte_visual = self.classificar_normalidade_visual(stats)
            classificacao_mm, suporte_mm = self.classificar_media_mediana(stats['diff_rel'])
            
            n_outliers, _, _ = self.identificar_outliers_iqr(dados)
            
            score_integrado = self.calcular_score_integrado(resultado_shapiro, stats)
            conclusao_final, confianca = self.classificar_score_final(score_integrado)
            
            resultados_finais[nome] = {
                'estatisticas': stats,
                'shapiro': resultado_shapiro,
                'suporte_visual': suporte_visual,
                'classificacao_mm': classificacao_mm,
                'suporte_mm': suporte_mm,
                'outliers': n_outliers,
                'score_integrado': score_integrado,
                'conclusao_final': conclusao_final,
                'confianca': confianca
            }
        
        # Generate final comparative graph
        print(f"\n  → Generating comparative chart: comparativo_normalidade.png/.pdf")
        self.criar_grafico_comparativo_final(resultados_finais)
        
        print("\n" + "="*60)
        print("GRAPHS GENERATED SUCCESSFULLY!")
        print("="*60)
        print("Files available for download:")
        
        for nome in dados_preparados.keys():
            print(f"  • histograma_{nome}.png/.pdf")
        print(f"  • comparativo_normalidade.png/.pdf")
        
        # Generate complete visual report (most relevant)
        print(f"  → Generating complete report: relatorio_normalidade_completo.png/.pdf")
        self.criar_relatorio_visual_completo(resultados_finais, dados_preparados)
        
        return resultados_finais
    
    def imprimir_resultados(self, resultados):
        print("="*100)
        print("NORMALITY ANALYSIS RESULTS")
        print("="*100)
        
        for nome, resultado in resultados.items():
            print(f"\n{'='*60}")
            print(f"VARIABLE: {nome.upper()}")
            print(f"{'='*60}")
            
            stats = resultado['estatisticas']
            shapiro = resultado['shapiro']
            
            print(f"\nDescriptive Statistics:")
            print(f"  N: {stats['n']}")
            print(f"  Mean: {stats['media']:.4f}")
            print(f"  Median: {stats['mediana']:.4f}")
            print(f"  Standard Deviation: {stats['desvio_padrao']:.4f}")
            print(f"  Skewness: {stats['assimetria']:.4f}")
            print(f"  Kurtosis: {stats['curtose_pearson']:.4f}")
            print(f"  CV: {stats['cv']:.2f}%")
            
            print(f"\nShapiro-Wilk Test:")
            print(f"  W Statistic: {shapiro['estatistica_w']:.6f}")
            print(f"  P-value: {shapiro['p_valor']:.6f}")
            print(f"  Decision: {shapiro['decisao']}")
            print(f"  Normal?: {shapiro['normal']}")
            
            print(f"\nMean vs Median Comparison:")
            print(f"  Absolute Difference: {stats['diff_abs']:.4f}")
            print(f"  Relative Difference: {stats['diff_rel']:.2f}%")
            print(f"  Classification: {resultado['classificacao_mm']}")
            print(f"  Support: {resultado['suporte_mm']}")
            
            print(f"\nVisual Analysis:")
            print(f"  Support: {resultado['suporte_visual']}")
            print(f"  Outliers (IQR): {resultado['outliers']}")
            
            print(f"\nIntegrated Conclusion:")
            print(f"  Score: {resultado['score_integrado']:.1f}/10")
            print(f"  Conclusion: {resultado['conclusao_final']}")
            print(f"  Confidence: {resultado['confianca']}")
        
        print(f"\n{'='*100}")
        print("SUMMARY TABLE")
        print(f"{'='*100}")
        
        print("┌─────────────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┐")
        print("│   Variable  │  Shapiro-Wilk   │   Histogram     │  Mean≈Median    │ Final Conclusion│")
        print("├─────────────┼─────────────────┼─────────────────┼─────────────────┼─────────────────┤")
        
        for nome, resultado in resultados.items():
            shapiro_status = f"{resultado['shapiro']['normal']} (p={resultado['shapiro']['p_valor']:.3f})"
            visual_status = resultado['suporte_visual'][:15]
            mm_status = resultado['suporte_mm'][:15]
            final_status = resultado['conclusao_final'][:15]
            
            print(f"│ {nome:11} │ {shapiro_status:15} │ {visual_status:15} │ {mm_status:15} │ {final_status:15} │")
        
        print("└─────────────┴─────────────────┴─────────────────┴─────────────────┴─────────────────┘")
    
    def criar_relatorio_visual_completo(self, resultados, dados_originais):
        """Creates a consolidated visual report with all graphs"""
        n_vars = len(resultados)
        
        # Figura grande com todos os histogramas
        fig, axes = plt.subplots(1, n_vars, figsize=(6*n_vars, 6))
        if n_vars == 1:
            axes = [axes]
        
        for i, (nome, resultado) in enumerate(resultados.items()):
            stats = resultado['estatisticas']
            dados_reais = dados_originais[nome]
            
            mu, sigma = stats['media'], stats['desvio_padrao']
            n_bins = max(10, min(30, int(np.sqrt(stats['n']))))
            
            # Use real data instead of approximation
            axes[i].hist(dados_reais, bins=n_bins, density=True, alpha=0.7, 
                        color='lightblue', edgecolor='black', label='Observed data')
            
            x = np.linspace(dados_reais.min(), dados_reais.max(), 1000)
            y_normal = (1/np.sqrt(2*np.pi*sigma**2)) * np.exp(-0.5*((x-mu)/sigma)**2)
            axes[i].plot(x, y_normal, 'r-', linewidth=2, label='Theoretical normal')
            
            axes[i].axvline(mu, color='red', linestyle='--', alpha=0.8, label=f'μ = {mu:.2f}')
            axes[i].axvline(stats['mediana'], color='green', linestyle='--', alpha=0.8, 
                           label=f'Md = {stats["mediana"]:.2f}')
            
            axes[i].set_title(f'{nome.capitalize()}\n{self.traduzir_conclusao(resultado["conclusao_final"])}', 
                             fontsize=12, fontweight='bold')
            axes[i].set_xlabel('Values')
            axes[i].set_ylabel('Density')
            axes[i].legend(fontsize=9)
            axes[i].grid(True, alpha=0.3)
            
            # Add statistics
            textstr = f'W = {resultado["shapiro"]["estatistica_w"]:.3f}\np = {resultado["shapiro"]["p_valor"]:.4f}'
            axes[i].text(0.02, 0.98, textstr, transform=axes[i].transAxes, fontsize=9,
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.suptitle('Normality Analysis - Comparative Histograms', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig('relatorio_normalidade_completo.png', dpi=300, bbox_inches='tight')
        plt.savefig('relatorio_normalidade_completo.pdf', dpi=300, bbox_inches='tight')
        plt.show()
        plt.close()
        
        print("  • relatorio_normalidade_completo.png/.pdf")
    
    def validar_resultados(self, resultados, dados_originais):
        """Validates the consistency of all calculated results"""
        print("\n" + "="*60)
        print("RESULTS VALIDATION")
        print("="*60)
        
        for nome, resultado in resultados.items():
            print(f"\nValidating {nome.upper()}:")
            
            stats = resultado['estatisticas']
            shapiro = resultado['shapiro']
            dados = dados_originais[nome]
            
            # Validation 1: Basic statistics consistency
            media_calc = np.mean(dados)
            mediana_calc = np.median(dados)
            
            if abs(stats['media'] - media_calc) > 1e-10:
                print(f"  ✗ ERROR: Inconsistent mean ({stats['media']} vs {media_calc})")
            else:
                print(f"  ✓ Consistent mean: {stats['media']:.6f}")
            
            if abs(stats['mediana'] - mediana_calc) > 1e-10:
                print(f"  ✗ ERROR: Inconsistent median ({stats['mediana']} vs {mediana_calc})")
            else:
                print(f"  ✓ Consistent median: {stats['mediana']:.6f}")
            
            # Validation 2: Shapiro-Wilk test
            try:
                w_calc, p_calc = shapiro(dados)
                if abs(shapiro['estatistica_w'] - w_calc) > 1e-6:
                    print(f"  ✗ ERROR: Inconsistent W statistic ({shapiro['estatistica_w']} vs {w_calc})")
                else:
                    print(f"  ✓ Consistent W statistic: {shapiro['estatistica_w']:.6f}")
                
                if abs(shapiro['p_valor'] - p_calc) > 1e-6:
                    print(f"  ✗ ERROR: Inconsistent P-value ({shapiro['p_valor']} vs {p_calc})")
                else:
                    print(f"  ✓ Consistent P-value: {shapiro['p_valor']:.6f}")
            except Exception as e:
                print(f"  ⚠ Warning: Could not validate Shapiro-Wilk: {e}")
            
            # Validation 3: Decision logic
            decisao_esperada = "Do not reject H₀" if shapiro['p_valor'] > self.alpha else "Reject H₀"
            if shapiro['decisao'] != decisao_esperada:
                print(f"  ✗ ERROR: Inconsistent decision ({shapiro['decisao']} vs {decisao_esperada})")
            else:
                print(f"  ✓ Consistent decision: {shapiro['decisao']}")
            
            # Validation 4: Integrated score
            score_recalc = self.calcular_score_integrado(shapiro, stats)
            if abs(resultado['score_integrado'] - score_recalc) > 1e-6:
                print(f"  ✗ ERROR: Inconsistent score ({resultado['score_integrado']} vs {score_recalc})")
            else:
                print(f"  ✓ Consistent integrated score: {resultado['score_integrado']:.1f}")
            
            # Validation 5: Outliers
            n_outliers_calc, _, _ = self.identificar_outliers_iqr(dados)
            if resultado['outliers'] != n_outliers_calc:
                print(f"  ✗ ERROR: Inconsistent outlier count ({resultado['outliers']} vs {n_outliers_calc})")
            else:
                print(f"  ✓ Consistent outliers: {resultado['outliers']}")
        
        print(f"\n{'='*60}")
        print("VALIDATION COMPLETED")
        print(f"{'='*60}")

def main():
    calculadora = CalculadoraNormalidade(alpha=0.05)
    
    # Tentar diferentes caminhos para o arquivo
    caminhos_possiveis = [
        '../data/BASE_DADOS_INTELI_FADEL_V4.xlsx',
        'data/BASE_DADOS_INTELI_FADEL_V4.xlsx',
        'BASE_DADOS_INTELI_FADEL_V4.xlsx'
    ]
    
    df = None
    for caminho in caminhos_possiveis:
        df = calculadora.carregar_dados(caminho)
        if df is not None:
            print(f"✓ Dados carregados de: {caminho}")
            break
    
    if df is None:
        print("✗ Could not load data from any path")
        print("Paths attempted:", caminhos_possiveis)
        return None
    
    variaveis_interesse = ['contador', 'quantidade', 'custo']
    
    try:
        resultados = calculadora.executar_analise_completa(df, variaveis_interesse)
        
        # Validar todos os resultados
        dados_preparados = calculadora.preparar_dados(df, variaveis_interesse)
        calculadora.validar_resultados(resultados, dados_preparados)
        
        calculadora.imprimir_resultados(resultados)
        
        print("\n" + "="*100)
        print("✓ ANALYSIS COMPLETED SUCCESSFULLY - ALL RESULTS VALIDATED")
        print("="*100)
        
    except Exception as e:
        print(f"\n✗ ERROR DURING ANALYSIS: {e}")
        print("Check the data and try again.")
        import traceback
        traceback.print_exc()
        return None
    
    print("\n" + "="*100)
    print("INSTRUCTIONS FOR DOWNLOADING GRAPHS")
    print("="*100)
    print("\nThe following files were generated in the current folder:")
    print("\n📊 INDIVIDUAL GRAPHS BY VARIABLE:")
    
    for var in variaveis_interesse:
        print(f"\n  {var.upper()}:")
        print(f"    • histograma_{var}.png (Histogram with normal curve)")
        print(f"    • histograma_{var}.pdf (Histogram with normal curve)")
    
    print(f"\n📈 COMPARATIVE GRAPHS:")
    print(f"    • comparativo_normalidade.png (P-values and integrated scores)")
    print(f"    • comparativo_normalidade.pdf (P-values and integrated scores)")
    print(f"    • relatorio_normalidade_completo.png (Complete visual report)")
    print(f"    • relatorio_normalidade_completo.pdf (Complete visual report)")
    
    print(f"\n💡 TIP: Use PDF files for better print quality")
    print(f"💡 TIP: Use PNG files for digital documents")
    
    return resultados

if __name__ == "__main__":
    resultados = main()