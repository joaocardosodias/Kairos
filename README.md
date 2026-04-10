# Inteli - Institute of Technology and Leadership

<p align="center">
<a href= "https://www.inteli.edu.br/"><img src="assets/inteli.png" alt="Inteli - Institute of Technology and Leadership" border="0"></a>
</p>

# Kairos

## Ilariê

## :student: Team Members:

- <a href="https://www.linkedin.com/in/clara-benito/">Clara de Borba Gutierrez Benito</a>
- <a href="https://www.linkedin.com/in/debora-pereira-nogueira/">Débora Pereira Nogueira</a>
- <a href="https://www.linkedin.com/in/jo%C3%A3ocardosodias/">João Cardoso Dias</a>
- <a href="https://www.linkedin.com/in/marcus-valente/">Marcus Felipe dos Santos Valente</a>
- <a href="https://www.linkedin.com/in/paulovictorbatista/">Paulo Victor Batista de Souza</a>
- <a href="https://www.linkedin.com/in/rafael-nakahara-bb5100351/">Rafael Ryu Tati Nakahara</a>
- <a href="https://www.linkedin.com/in/sachakefif/">Sacha Kefif</a>
- <a href="https://www.linkedin.com/in/peresvivian/">Vivian de Assis Peres</a>

## :teacher: Faculty:

### Supervisor

- <a href="https://www.linkedin.com/in/juliastateri/">Julia Stateri</a>

### Instructors

- <a href="https://www.linkedin.com/in/bruna-mayer/">Bruna Mayer Costa</a>
- <a href="https://www.linkedin.com/in/egondaxbacher/">Egon Ferreira Daxbacher</a>
- <a href="https://www.linkedin.com/in/filipe-gon%C3%A7alves-08a55015b/">Filipe Gonçalves</a>
- <a href="https://www.linkedin.com/in/henrique-mohallem-paiva-6854b460/">Henrique Mohallem Paiva</a>
- <a href="https://www.linkedin.com/in/thaisneubauer/">Thais Rodrigues Neubauer</a>

## 📝 Description

**Kairos** is a predictive maintenance solution developed for vehicle fleet management, designed to anticipate corrective maintenance needs and optimize operational costs. The project addresses the critical challenge of unexpected vehicle breakdowns that can disrupt operations and generate significant unplanned expenses.

**Problem Statement:**
Fleet managers face the constant challenge of balancing preventive maintenance costs with the risk of unexpected breakdowns. Traditional reactive maintenance approaches lead to:

- Unplanned operational disruptions
- Higher repair costs due to emergency interventions
- Reduced vehicle availability and productivity
- Difficulty in budget planning and resource allocation

**Proposed Solution:**
Kairos implements a machine learning-based predictive model using RandomForest classification to forecast the likelihood of corrective maintenance within a 30-day window. The solution analyzes historical maintenance data, vehicle usage patterns, and operational metrics to provide actionable insights.

**Key Features:**

- **Predictive Analytics**: 30-day breakdown prediction with detailed probability scores
- **Data-Driven Insights**: Feature importance analysis to identify key breakdown indicators
- **Temporal Validation**: Time-based model validation ensuring real-world applicability
- **Reusable Model**: This model can be applied to new datasets with the same structure by re-running the data pipeline for data preparation and model.

The model processes vehicle maintenance records, filters valid automotive parts, and creates predictive features including odometer readings, maintenance frequency, breakdown history, and usage intensity. This enables fleet managers to proactively schedule maintenance, optimize inventory, and reduce operational disruptions.

**Impact:**
By implementing Kairos, organizations can transition from reactive to predictive maintenance strategies, potentially reducing unplanned downtime and optimizing maintenance budgets through better resource planning and parts inventory management.

<b>Link to demo video:</b> <a href="https://youtu.be/jyvsgElWJAI">Demo Video</a>

## 📁 Project Structure

```
2025-2A-T16-IN03-G03/
├── 📁 assets/                    # Images and media files for documentation
├── 📁 documents/                 # Project documentation and reports
├── 📁 models/                    # Auxiliary files such as preprocessors and configuration files
├── 📁 notebooks/                 # Jupyter notebooks for analysis and modeling, and trained machine learning models
│   └── 📁 data/                  # Datasets and data processing files
├── 📁 scripts/                   # Python scripts and utilities
├── .gitignore                    # Git ignore configuration
└── README.md                     # Project documentation (this file)
```


## 💻 Running the Project

### Prerequisites

- Python 3.8 or higher
- Jupyter Notebook or JupyterLab
- Required Python packages (see requirements below)

### Required Python Packages

Install the following packages using pip:

```bash
pip install pandas numpy matplotlib seaborn scikit-learn xgboost openpyxl jupyter shap
```


### Data Requirements

The project requires the data file containing vehicle maintenance records. Ensure the file includes the following columns:

- `ASSET CODE`: Vehicle identifier
- `SERVICE ORDER ORIGINAL DATE`: Maintenance date
- `COUNTER OF SERVICE ORDER`: Odometer reading
- `PRODUCT DESCRIPTION`: Part/service description
- `GRAND TOTAL`: Cost of maintenance
- `PREVENTIVE_CORRECTIVE MAINTENANCE`: Maintenance type
* `MODEL_TYPE_CODE`: ID of the model
* `ASSET_STATUS`: indicates whether the vehicle ative or inative
* `TIER`: vehicle category
* `PRODUCT_CODE`: ID of the product
* `PRODUCT_QUANTITY`: total quantity of the product purchased for the service
* `UNIT_VALUE`: price per unit of the product
* `ASSET_FAMILY_CODE`: ID of the vehicle family
* `MANUFACTURER_CODE`: ID of the vehicle manufacturer
* `MANUFACTURE_YEAR`: year the vehicle was manufactured


### Running Locally (VS Code/Local Environment)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Inteli-College/2025-2A-T16-IN03-G03.git
   cd 2025-2A-T16-IN03-G03
   ```

2. **Set up the data:**

   - Place the data file in the `notebooks/data/` directory
   - Ensure the file path matches the notebook expectations

3. **Launch Jupyter:**

   ```bash
   jupyter notebook
   # or
   jupyter lab
   ```

4. **Run the notebooks:**
   - Start with `09_random_forest_breakdown_prediction.ipynb` for the main predictive model
   

### Running in Google Colab

1. **Upload to Google Drive:**

   - Save a copy of the notebook to your Google Drive to preserve changes
   - Upload `SERVICE_ORDER_BASE.xlsx` to your Colab environment

2. **Install packages:**

   ```python
   !pip install xgboost openpyxl
   ```

3. **Upload data file:**

   ```python
   from google.colab import files
   uploaded = files.upload()  # Upload data file
   ```

4. **Run the notebooks:**
   - Execute cells sequentially
   - Modify file paths if necessary for Colab environment

### Key Notebooks

- **`06_data_processing_pipeline.ipynb`**: data processing pipeline that transforms the raw `SERVICE_ORDER_BASE.xlsx` dataset into a clean, ML-ready format
- **`09_random_forest_breakdown_prediction.ipynb`**: Main predictive model


### Expected Outputs

- Trained Random Forest classification model
- Model performance metrics (precision, recall, F1-score)



## 🗃 Release History


- **v1.4** – [Sprint 5] 10/09/2025  
  - Release of the first version of the predictive model with documentation.  
- **v1.3** – [Sprint 4] 09/26/2025  
  - Predictive model comparison and hyperparameter tuning.  
- **v1.2** – [Sprint 3] 09/12/2025  
  - Data preparation and preliminary predictive model.  
- **v1.1** – [Sprint 2] 08/29/2025  
  - Exploratory analysis, hypothesis development, data preprocessing, missing data treatment and outlier removal.  
- **v1.0** – [Sprint 1] 08/15/2025  
  - Business understanding documentation, LGPD Privacy Policy, personas and user journey maps.



## 📋 License

<a href="https://github.com/Inteli-College/2025-2A-T16-IN03-G03">Kairos</a> © 2025 by <a href="https://github.com/Inteli-College/2025-2A-T16-IN03-G03">Inteli, Clara de Borba Gutierrez Benito, Débora Pereira Nogueira, João Cardoso Dias, Marcus Felipe dos Santos Valente, Paulo Victor Batista de Souza, Rafael Ryu Tati Nakahara, Sacha Kefif, Vivian de Assis Peres</a> is licensed under <a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International</a><img src="https://mirrors.creativecommons.org/presskit/icons/cc.svg" alt="" style="max-width: 1em;max-height:1em;margin-left: .2em;"><img src="https://mirrors.creativecommons.org/presskit/icons/by.svg" alt="" style="max-width: 1em;max-height:1em;margin-left: .2em;">
