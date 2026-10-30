# UH Energy Data Explorer

Black-background interactive Streamlit dashboard for the provided University of Hawaiʻi energy workbook.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate with `.venv\\Scripts\\activate` instead.

The dashboard opens at http://localhost:8501. Choose the metric, campuses, fiscal-year range, and line/bar view from the sidebar. Upload an updated workbook or a CSV with the same column layout if desired.

The dashboard uses the `Sheet1` worksheet by default, excludes aggregate Total rows, and does not replace missing values with zero. The `Net Zero` worksheet has a different layout and is not treated as a campus-by-year dataset.
