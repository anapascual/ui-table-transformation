import streamlit as st
from transformation import process_files

st.set_page_config(
    page_title="UI Table Transformation",
    page_icon="📊",
    layout="wide",
)

# ---- Custom styling ----
st.markdown(
    """
    <style>
        .stApp {
            background-color: #f5f9fc;
        }

        .main-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: #005c9c;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            font-size: 1rem;
            color: #4a5568;
            margin-bottom: 1.5rem;
        }

        .section-card {
            background: white;
            padding: 1.4rem;
            border-radius: 16px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
            border-left: 6px solid #005c9c;
            margin-bottom: 1rem;
        }

        .small-note {
            font-size: 0.9rem;
            color: #718096;
        }

        div.stButton > button {
            background-color: #005c9c;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
        }

        div.stButton > button:hover {
            background-color: #004a7c;
            color: white;
        }

        div.stDownloadButton > button {
            background-color: #00a3ad;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
        }

        div.stDownloadButton > button:hover {
            background-color: #008690;
            color: white;
        }

        .footer-box {
            margin-top: 2rem;
            padding: 1rem;
            border-radius: 12px;
            background-color: #eaf4fb;
            color: #2d3748;
            font-size: 0.95rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- Header ----
st.markdown('<div class="main-title">UI Table Transformation</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Upload the input files, run the transformation, and download the final structured table.</div>',
    unsafe_allow_html=True,
)

# ---- Intro / instructions ----
st.markdown(
    """
    <div class="section-card">
        <h4 style="color:#005c9c; margin-top:0;">How it works</h4>
        <ol style="margin-bottom:0.5rem;">
            <li>Upload the <b>schedule.csv</b> file</li>
            <li>Upload the <b>answers.csv</b> file</li>
            <li>Click <b>Run transformation</b></li>
            <li>Preview and download the transformed output</li>
        </ol>
        <div class="small-note">
            Supported format: CSV files only
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Upload section ----
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Schedule file")
    schedule_file = st.file_uploader("Upload schedule.csv", type=["csv"], key="schedule")

with col2:
    st.markdown("### Answers file")
    answers_file = st.file_uploader("Upload answers.csv", type=["csv"], key="answers")

# ---- Status info ----
if schedule_file is not None and answers_file is not None:
    st.success("Both files uploaded successfully.")

    if st.button("Run transformation"):
        try:
            result_df = process_files(schedule_file, answers_file)

            st.markdown("---")
            st.markdown("## Preview of transformed table")
            st.dataframe(result_df, use_container_width=True, height=450)

            csv_data = result_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download transformed CSV",
                data=csv_data,
                file_name="final_table_transformed.csv",
                mime="text/csv",
            )

            st.markdown(
                f"""
                <div class="footer-box">
                    <b>Transformation complete.</b><br>
                    Output rows: {len(result_df)}<br>
                    Output columns: {len(result_df.columns)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")

else:
    st.info("Please upload both CSV files to continue.")