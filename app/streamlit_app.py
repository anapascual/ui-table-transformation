import base64
import streamlit as st
from pathlib import Path
from app.transformation import process_files


def img_to_base64(path: Path) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


st.set_page_config(
    page_title="Medtronic Data Transformer",
    page_icon="📊",
    layout="wide",
)

# ---------- Custom CSS ----------
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f4f8fb 0%, #eef5fa 100%);
        }

        .top-bar {
            background: white;
            border-radius: 20px;
            padding: 1.5rem 1.5rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
            margin-bottom: 1.5rem;
        }

        .title {
            font-size: 2.1rem;
            font-weight: 800;
            color: #005c9c;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            font-size: 1rem;
            color: #5b6770;
            margin-bottom: 0;
        }

        .card {
            background: white;
            border-radius: 18px;
            padding: 1.2rem 1.2rem 1rem 1.2rem;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
            border: 1px solid #e6eef5;
            margin-bottom: 1rem;
        }

        .card h3 {
            color: #005c9c;
            margin-top: 0;
            margin-bottom: 0.4rem;
        }

        .muted {
            color: #6b7280;
            font-size: 0.95rem;
        }

        div.stButton > button {
            background-color: #005c9c;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.7rem 1.2rem;
            font-weight: 700;
            width: 100%;
        }

        div.stButton > button:hover {
            background-color: #004b80;
            color: white;
        }

        div.stDownloadButton > button {
            background-color: #00a3ad;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.7rem 1.2rem;
            font-weight: 700;
            width: 100%;
        }

        div.stDownloadButton > button:hover {
            background-color: #008d96;
            color: white;
        }

        .preview-box {
            background: white;
            border-radius: 18px;
            padding: 1rem 1rem 0.5rem 1rem;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
            border: 1px solid #e6eef5;
            margin-top: 1rem;
        }

        .status-box {
            background: #eaf4fb;
            border-left: 5px solid #005c9c;
            border-radius: 12px;
            padding: 0.9rem 1rem;
            color: #264653;
            margin-top: 1rem;
        }

        .hero-card {
            background: white;
            border-radius: 20px;
            padding: 1.5rem 2rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .hero-logo {
            height: 56px;
            object-fit: contain;
        }

        .hero-title {
            font-size: 2.1rem;
            font-weight: 800;
            color: #005c9c;
            margin-bottom: 0.2rem;
        }

        .hero-subtitle {
            font-size: 1rem;
            color: #5b6770;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Header ----------
logo_path = Path("assets/medtronic_logo.png")

logo_html = ""
if logo_path.exists():
    logo_b64 = img_to_base64(logo_path)
    logo_html = f"""<div class="hero-logo-wrap">
<img class="hero-logo" src="data:image/png;base64,{logo_b64}" alt="Medtronic logo">
</div>"""

st.markdown(
    f"""<div class="hero-card">
{logo_html}
<div class="hero-content">
    <div class="hero-title">Medtronic Data Transformer</div>
    <div class="hero-subtitle">
        Upload two structured data files, transform them into a clean standardized output,
        and export the result as a CSV file.
    </div>
</div>
</div>""",
    unsafe_allow_html=True,
)

# ---------- Info cards ----------
info_col1, info_col2 = st.columns([1.2, 1])

with info_col1:
    st.markdown(
        """
        <div class="card">
            <h3>How it works</h3>
            <div class="muted">
                1. Upload the file containing the content name and questions<br>
                2. Upload the file containing answers<br>
                3. Click <b>Run transformation</b><br>
                4. Preview and download the transformed output
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with info_col2:
    st.markdown(
        """
        <div class="card">
            <h3>Supported formats</h3>
            <div class="muted">
                CSV and Excel files are supported.<br>
                Use this tool for structured table reshaping and field-to-column transformations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Upload section ----------
st.markdown("## Upload files")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Input file: Content and Questions")
    primary_file = st.file_uploader(
        "Choose the primary input file",
        type=["csv", "xlsx"],
        key="primary_file"
    )

with col2:
    st.markdown("### Input file: Answers")
    secondary_file = st.file_uploader(
        "Choose the secondary input file",
        type=["csv", "xlsx"],
        key="secondary_file"
    )

if primary_file is not None and secondary_file is not None:
    st.success("Both files uploaded successfully.")

    if st.button("Run transformation"):
        try:
            result_df = process_files(primary_file, secondary_file)

            display_df = result_df.copy()
            display_df = display_df.astype(object).where(result_df.notna(), "")
            display_df = display_df.astype(str)

            st.markdown("### Preview of transformed output")
            st.dataframe(display_df, width='stretch', height=460)

            csv_data = result_df.to_csv(index=False).encode("utf-8-sig")

            st.markdown(
                f"""
                <div class="status-box">
                    <b>Transformation complete.</b><br>
                    Output rows: {len(result_df)}<br>
                    Output columns: {len(result_df.columns)}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("### Download")
            st.download_button(
                label="Download transformed CSV",
                data=csv_data,
                file_name="transformed_output.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
else:
    st.info("Please upload both input files to continue.")