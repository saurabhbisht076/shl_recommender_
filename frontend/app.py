import streamlit as st
import requests
from datetime import datetime

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
        # Clean up the payload to match backend expectations
        payload = {
            "query": query,
            "job_level": job_level if job_level != "All" else None,
            "max_duration": max_duration if max_duration > 0 else None,
            "languages": [lang.lower() for lang in languages] if languages else None,
            "test_type": test_type if test_type != "All" else None,
            "remote_testing": remote_testing,
            "adaptive_irt": adaptive_irt,
            "top_n": top_n
        }
        
        # Debug information
        st.sidebar.markdown("### Debug Info")
        st.sidebar.markdown("**Request Payload:**")
        st.sidebar.json(payload)
        
        response = requests.post(f"{API_URL}/recommend", json=payload)
        
        # Debug response
        st.sidebar.markdown("**Response Status:**")
        st.sidebar.markdown(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            st.sidebar.markdown("**Error Response:**")
            st.sidebar.text(response.text)
            return {"recommended_assessments": []}
            
    except Exception as e:
        st.error(f"Error fetching recommendations: {e}")
        return {"recommended_assessments": []}

# Sidebar
st.sidebar.image("https://www.shl.com/wp-content/uploads/SHL-logo.svg", width=150)
st.sidebar.title("Filters")

# Fetch metadata with error handling
job_levels = fetch_metadata("job-levels", "job_levels")
test_types = fetch_metadata("test-types", "test_types")

# Filters
job_level = st.sidebar.selectbox("Job Level", ["All"] + job_levels)
test_type = st.sidebar.selectbox("Test Type", ["All"] + test_types)
max_duration = st.sidebar.slider("Max Duration (minutes)", 0, 120, 60)
languages = st.sidebar.multiselect("Languages", ["en", "es", "fr", "de"], default=["en"])

# New Filters with proper handling
remote_testing = st.sidebar.radio("Remote Testing Support", ["All", "Yes", "No"], index=0)
adaptive_irt = st.sidebar.radio("Adaptive IRT Support", ["All", "Yes", "No"], index=0)

# Convert radio buttons to boolean or None
remote_testing_bool = None if remote_testing == "All" else (remote_testing == "Yes")
adaptive_irt_bool = None if adaptive_irt == "All" else (adaptive_irt == "Yes")

top_n = st.sidebar.slider("Number of Results", 1, 10, 5)

# Main
st.title("📊 SHL Assessment Recommender")
st.markdown("Enter a job description and we'll recommend the most relevant SHL assessments.")

query = st.text_area("🔍 Job Description", height=150, 
                    placeholder="E.g., Looking for a mid-level project manager with client-facing experience...")

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

        recommendations = results.get("recommended_assessments", [])
        if not recommendations:
            st.warning("No matching assessments found. Try adjusting filters.")
        else:
            st.success(f"Found {len(recommendations)} recommendations")
            for i, rec in enumerate(recommendations):
                with st.expander(f"{i+1}. {rec['name']} (Score: {rec['score']:.2f})"):
                    st.markdown(f"**Description:** {rec['description']}")
                    st.markdown(f"**Duration:** {rec['duration']} minutes")
                    st.markdown(f"**Job Levels:** {', '.join(rec['job_levels'])}")
                    st.markdown(f"**Test Type:** {rec['test_type']}")
                    if 'remote_testing_support' in rec:
                        st.markdown(f"**Remote Testing:** {'Yes' if rec['remote_testing_support'] else 'No'}")
                    if 'adaptive_irt_support' in rec:
                        st.markdown(f"**Adaptive IRT:** {'Yes' if rec['adaptive_irt_support'] else 'No'}")

else:
    st.info("Please provide a job description to get started.")

# Footer
st.markdown("---")
st.markdown(f"""
**Current Date and Time (UTC):** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}  
**Current User:** saurabhbisht076
""")
st.caption("© 2025 SHL Assessment Recommender | Built for SHL AI Intern Assignment")