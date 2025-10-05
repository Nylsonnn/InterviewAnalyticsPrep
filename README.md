#  Water Consumption Analytics 

This project was created as part of a **data analysis interview exercise** to demonstrate the ability to process, analyse, and visualise large datasets — specifically **business water consumption data (2020–2023)**.  
It identifies **patterns, trends, and anomalies** to support **strategic water efficiency decisions** for business customers.

---

## Objectives

The analysis and dashboard directly answer these four key questions based on dummy data given prior to the task:

1. **Which business types use the most water year on year?**  
2. **How much water is consumed by properties listed as “vacant,” and is this trend increasing or decreasing?**  
3. **During 2022 (a particularly hot and dry year), which industries showed significantly higher water usage compared to other years?**  
4. **Which resource zone uses the most water overall?**

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Prepare the data
# Place DRA_exercise.xlsx inside data/raw/
python src/prepare_data.py

# 5. (Optional) Run quick analysis
python src/run_analysis.py

# 6. Launch the Streamlit dashboard
python -m streamlit run dashboards/app.py
```
Made using:

-Python

-Streamlit


