import streamlit as st
import requests

# Config
st.set_page_config(page_title="SHL Assessment Recommender", page_icon="📊", layout="wide")
API_URL = "https://shl-recommender-1-9bpx.onrender.com"

# Helper Functions
def fetch_metadata(endpoint, label):
    try:
        res = requests.get(f"{API_URL}/{endpoint}")
        return res.json().get(label, [])
    except Exception as e:
        st.warning(f"Couldn't fetch {label.replace('_', ' ')}: {e}")
        return []

def get_recommendations(query, job_level=None, max_duration=None, languages=None, test_type=None,
                        remote_testing=None, adaptive_irt=None, top_n=5):
    try:
        payload = {
            "query": query,
            "job_level": None if job_level == "All" else job_level,
            "max_duration": None if max_duration <= 0 else max_duration,
            "languages": languages or None,
            "test_type": None if test_type == "All" else test_type,
            "remote_testing": remote_testing,
            "adaptive_irt": adaptive_irt,
            "top_n": top_n
        }
        res = requests.post(f"{API_URL}/recommend", json=payload)
        return res.json()
    except Exception as e:
        st.error(f"Error fetching recommendations: {e}")
        return {"recommendations": []}

# Sidebar
st.sidebar.image("https://www.shl.com/wp-content/uploads/SHL-logo.svg", width=150)
st.sidebar.title("Filters")

job_level = st.sidebar.selectbox("Job Level", ["All"] + fetch_metadata("job-levels", "job_levels"))
test_type = st.sidebar.selectbox("Test Type", ["All"] + fetch_metadata("test-types", "test_types"))
max_duration = st.sidebar.slider("Max Duration (minutes)", 0, 120, 60)
languages = st.sidebar.multiselect("Languages", ["english", "german", "french", "spanish"], default=["english"])

# ✅ New Filters
remote_testing = st.sidebar.radio("Remote Testing Support", ["All", "Yes", "No"], index=0)
adaptive_irt = st.sidebar.radio("Adaptive IRT Support", ["All", "Yes", "No"], index=0)

# Convert to backend logic
remote_testing_bool = None if remote_testing == "All" else (remote_testing == "Yes")
adaptive_irt_bool = None if adaptive_irt == "All" else (adaptive_irt == "Yes")

top_n = st.sidebar.slider("Number of Results", 1, 10, 5)

# Main
st.title("📊 SHL Assessment Recommender")
st.markdown("Enter a job description and we'll recommend the most relevant SHL assessments.")

query = st.text_area("🔍 Job Description", height=150, placeholder="E.g., Looking for a mid-level project manager with client-facing experience...")

if st.button("Get Recommendations"):
    if not query.strip():
        st.warning("Please provide a meaningful job description.")
    else:
        with st.spinner("Analyzing and finding best matches..."):
            results = get_recommendations(
                query=query,
                job_level=job_level,
                max_duration=max_duration,
                languages=languages,
                test_type=test_type,
                remote_testing=remote_testing_bool,
                adaptive_irt=adaptive_irt_bool,
                top_n=top_n
            )

        recommendations = results.get("recommendations", [])
        if not recommendations:
            st.warning("No matching assessments found. Try adjusting filters.")
        else:
            st.success(f"Found {len(recommendations)} recommendations")
            for i, rec in enumerate(recommendations):
                assessment = rec["assessment"]
                sim = rec["similarity"]

                with st.expander(f"{i+1}. {assessment['name']} (Match: {sim:.2%})"):
                    st.markdown(f"**📝 Description:** {assessment['description']}")
                    cols = st.columns(3)
                    cols[0].markdown(f"**📂 Test Type:** {assessment.get('test_type', 'N/A')}")
                    cols[1].markdown(f"**⏱️ Duration:** {assessment.get('duration', 'N/A')}")
                    cols[2].markdown(f"**📶 Similarity Score:** `{sim:.2%}`")

                    info = f"""
                    **👥 Job Levels:** {", ".join(assessment.get("job_levels", []))}  
                    **🌐 Languages:** {", ".join(assessment.get("languages", []))}  
                    **🧪 Remote Testing:** `{assessment.get("remote_testing_support", False)}`  
                    **🧠 Adaptive/IRT:** `{assessment.get("adaptive_irt_support", False)}`
                    """
                    st.markdown(info)

                    if assessment.get("pdf_link"):
                        st.markdown(f"📄 [Download Fact Sheet]({assessment['pdf_link']})", unsafe_allow_html=True)

                    st.markdown(f"[🔗 View on SHL Website]({assessment['url']})")

else:
    st.info("Please provide a job description to get started.")

# Footer
st.markdown("---")
st.caption("© 2025 SHL Assessment Recommender | Built for SHL AI Intern Assignment")
