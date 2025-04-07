# 📊 SHL Assessment Recommender

A smart assessment recommendation system that suggests the most relevant SHL assessments based on a provided job description. Built using Python, Streamlit, and a custom similarity-based recommender model.

---

## 🚀 Features

- 🔍 Input any job description and get tailored SHL assessments.
- 🎯 Evaluation metrics: Precision@K, NDCG@K, MRR, Diversity.
- 🧠 Cleaned & processed SHL catalog for structured recommendations.
- 📊 Interactive Streamlit frontend with advanced filters:
  - Job Level
  - Test Type
  - Duration
  - Language
  - Remote Testing Support
  - Adaptive IRT
- 📁 Modular code with clean architecture.
- 📈 Evaluation plotted and saved in `/data/evaluation/`.

---

## 🗂️ Project Structure

```
shl_recommender/
├── app/
│   ├── evaluation/
│   │   ├── benchmark.py
│   │   ├── metrics.py
│   ├── recommender.py
│   ├── main.py
│   ├── utils.py
│   └── scraper.py
├── data/
│   ├── raw/
│   ├── processed/
│   ├── debug/
│   └── evaluation/
├── frontend/
│   └── app.py
```

---

## 📦 Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/saurabhbisht076/shl_recommender.git
cd shl_recommender
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # on Linux/Mac
venv\Scripts\activate     # on Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🧪 Run Evaluation

To test your recommender with benchmarking metrics:

```bash
python -m app.evaluation.benchmark
```

Outputs precision, MRR, NDCG, and diversity stats in console and saves plot in `data/evaluation/`.

---

## 💡 Run the Frontend App

To launch the Streamlit frontend:

```bash
cd frontend
streamlit run app.py
```

This opens a browser interface to interact with the SHL recommender.

---

## 📈 Sample Result

<img src="../data/evaluation/benchmark_results.png" alt="Benchmark Results" width="500"/>

---
## Demo Video
[🎥 Watch Demo](demovideo/19-28-44.mp4)

## 🤝 Author

**Saurabh Bisht**  
Backend Developer | AI Tools Engineer  
GitHub: [@Saurabh-Bisht](https://github.com/saurabhbisht076)

---

## 🏁 Future Improvements

- Add cosine/TFIDF-based scoring
- Integrate LLM for semantic understanding
- Deploy on HuggingFace Spaces / Vercel

---

## 📝 License

MIT License. Feel free to fork and modify for educational use.
```

