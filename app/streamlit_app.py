import base64
import streamlit as st
from pathlib import Path
from app.transformation import process_files


def img_to_base64(path: Path) -> str:
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
        /* ── Page background ── */
        .stApp {
            background-color: #f5f7fa;
        }

        /* ── Hero bar ── */
        .hero {
            background: white;
            border: 0.5px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.85rem;
            margin-bottom: 1.25rem;
        }
        .hero-logo-mark {
            width: 36px;
            height: 36px;
            background: #005c9c;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .hero-logo-mark img {
            height: 22px;
            object-fit: contain;
            filter: brightness(0) invert(1);
        }
        .hero-logo-mark-fallback {
            width: 36px;
            height: 36px;
            background: #005c9c;
            border-radius: 8px;
            flex-shrink: 0;
        }
        .hero-title {
            font-size: 1rem;
            font-weight: 600;
            color: #0f172a;
            margin: 0;
        }
        .hero-sub {
            font-size: 0.8rem;
            color: #64748b;
            margin: 0;
        }
        .hero-badge {
            margin-left: auto;
            font-size: 0.7rem;
            font-weight: 500;
            color: #185FA5;
            background: #E6F1FB;
            padding: 3px 10px;
            border-radius: 99px;
            white-space: nowrap;
        }

        /* ── Section label ── */
        .section-label {
            font-size: 0.7rem;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-bottom: 0.5rem;
        }

        /* ── Progress stepper ── */
        .stepper {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-bottom: 1.25rem;
        }
        .step {
            background: white;
            border: 0.5px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.75rem 0.9rem;
            position: relative;
        }
        .step.step-active {
            border-color: #378ADD;
        }
        .step-num {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.65rem;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .step-num-pending { background: #f1f5f9; color: #94a3b8; }
        .step-num-active  { background: #005c9c; color: white; }
        .step-num-done    { background: #EAF3DE; color: #3B6D11; }
        .step-text {
            font-size: 0.75rem;
            color: #64748b;
            line-height: 1.4;
        }
        .step-arrow {
            position: absolute;
            right: -6px;
            top: 50%;
            transform: translateY(-50%);
            color: #cbd5e1;
            font-size: 0.75rem;
            z-index: 2;
            background: #f5f7fa;
            line-height: 1;
        }

        /* ── Upload zones ── */
        .upload-zone {
            background: white;
            border: 1.5px dashed #cbd5e1;
            border-radius: 12px;
            padding: 1.25rem 1rem;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .upload-zone.upload-done {
            border-style: solid;
            border-color: #378ADD;
            background: #f0f7ff;
        }
        .upload-zone-icon  { font-size: 1.25rem; margin-bottom: 6px; }
        .upload-zone-title { font-size: 0.8rem; font-weight: 600; color: #0f172a; margin-bottom: 2px; }
        .upload-zone-hint  { font-size: 0.72rem; color: #94a3b8; }
        .upload-zone-filename { font-size: 0.72rem; font-weight: 500; color: #185FA5; margin-top: 4px; }

        /* ── Info cards ── */
        .info-card {
            background: #f1f5f9;
            border-radius: 10px;
            padding: 0.85rem 1rem;
        }
        .info-card h4 {
            font-size: 0.8rem;
            font-weight: 600;
            color: #0f172a;
            margin: 0 0 5px 0;
        }
        .info-card p {
            font-size: 0.75rem;
            color: #64748b;
            line-height: 1.6;
            margin: 0;
        }

        /* ── Run button ── */
        div.stButton > button {
            background-color: #005c9c;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.65rem 1.2rem;
            font-weight: 600;
            font-size: 0.9rem;
            width: 100%;
        }
        div.stButton > button:hover { background-color: #004b80; color: white; }
        div.stButton > button:disabled {
            background-color: #e2e8f0 !important;
            color: #94a3b8 !important;
            cursor: not-allowed;
        }

        /* ── Download button ── */
        div.stDownloadButton > button {
            background-color: #0f766e;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.65rem 1.2rem;
            font-weight: 600;
            font-size: 0.9rem;
            width: 100%;
        }
        div.stDownloadButton > button:hover { background-color: #0d5f58; color: white; }

        /* ── Status box ── */
        .status-box {
            background: #f0f9ff;
            border: 0.5px solid #bae6fd;
            border-radius: 10px;
            padding: 0.85rem 1rem;
            font-size: 0.82rem;
            color: #0c4a6e;
            margin-bottom: 1rem;
        }

        /* ── Notice bar ── */
        .notice {
            background: #f8fafc;
            border: 0.5px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.65rem 1rem;
            font-size: 0.75rem;
            color: #94a3b8;
            text-align: center;
            margin-top: 0.5rem;
        }

        .spacer { margin-bottom: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Derive file states (must come before any widget renders) ----------
primary_done   = st.session_state.get("primary_file")   is not None
secondary_done = st.session_state.get("secondary_file") is not None
both_done      = primary_done and secondary_done


def _step_num(index: int) -> str:
    """Return the HTML for the step-number bubble at position `index` (1-based)."""
    if index == 1:
        cls, text = ("step-num-done", "✓") if primary_done else ("step-num-active", "1")
    elif index == 2:
        if secondary_done:
            cls, text = "step-num-done", "✓"
        elif primary_done:
            cls, text = "step-num-active", "2"
        else:
            cls, text = "step-num-pending", "2"
    elif index == 3:
        cls, text = ("step-num-active", "3") if both_done else ("step-num-pending", "3")
    else:
        cls, text = "step-num-pending", "4"
    return f'<div class="step-num {cls}">{text}</div>'


def _step_cls(index: int) -> str:
    if index == 1:
        return "step"
    if index == 2:
        return "step step-active" if (primary_done and not secondary_done) else "step"
    if index == 3:
        return "step step-active" if both_done else "step"
    return "step"


# ---------- Hero ----------
logo_path = Path("assets/medtronic_logo.png")
if logo_path.exists():
    logo_b64   = img_to_base64(logo_path)
    logo_inner = f'<img src="data:image/png;base64,{logo_b64}" alt="Medtronic">'
    logo_block = f'<div class="hero-logo-mark">{logo_inner}</div>'
else:
    logo_block = '<div class="hero-logo-mark-fallback"></div>'

st.markdown(
    f"""
    <div class="hero">
        {logo_block}
        <div>
            <p class="hero-title">Medtronic data transformer</p>
            <p class="hero-sub">Upload two files · transform · export CSV</p>
        </div>
        <div class="hero-badge">CSV &nbsp;·&nbsp; XLSX</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Progress stepper ----------
st.markdown('<div class="section-label">Workflow</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="stepper">
        <div class="{_step_cls(1)}">
            {_step_num(1)}
            <div class="step-text">Upload questions file</div>
            <div class="step-arrow">›</div>
        </div>
        <div class="{_step_cls(2)}">
            {_step_num(2)}
            <div class="step-text">Upload answers file</div>
            <div class="step-arrow">›</div>
        </div>
        <div class="{_step_cls(3)}">
            {_step_num(3)}
            <div class="step-text">Run transformation</div>
            <div class="step-arrow">›</div>
        </div>
        <div class="{_step_cls(4)}">
            {_step_num(4)}
            <div class="step-text">Download CSV</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Upload section ----------
st.markdown('<div class="section-label">Upload files</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if primary_done:
        fname = st.session_state["primary_file"].name
        st.markdown(
            f"""
            <div class="upload-zone upload-done">
                <div class="upload-zone-icon">📄</div>
                <div class="upload-zone-title">Content &amp; questions</div>
                <div class="upload-zone-filename">{fname}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="upload-zone">
                <div class="upload-zone-icon">⬆</div>
                <div class="upload-zone-title">Content &amp; questions</div>
                <div class="upload-zone-hint">CSV or XLSX · max 200 MB</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    primary_file = st.file_uploader(
        "Questions file",
        type=["csv", "xlsx"],
        key="primary_file",
        label_visibility="collapsed",
    )

with col2:
    if secondary_done:
        fname = st.session_state["secondary_file"].name
        st.markdown(
            f"""
            <div class="upload-zone upload-done">
                <div class="upload-zone-icon">📄</div>
                <div class="upload-zone-title">Answers</div>
                <div class="upload-zone-filename">{fname}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="upload-zone">
                <div class="upload-zone-icon">⬆</div>
                <div class="upload-zone-title">Answers</div>
                <div class="upload-zone-hint">CSV or XLSX · max 200 MB</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    secondary_file = st.file_uploader(
        "Answers file",
        type=["csv", "xlsx"],
        key="secondary_file",
        label_visibility="collapsed",
    )

st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

# ---------- Info cards ----------
info_col1, info_col2 = st.columns(2)

with info_col1:
    st.markdown(
        """
        <div class="info-card">
            <h4>How it works</h4>
            <p>
                Upload the questions file first, then the answers file.
                The transformer joins and reshapes them into a single flat output table
                ready for analysis or reporting.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with info_col2:
    st.markdown(
        """
        <div class="info-card">
            <h4>Supported formats</h4>
            <p>
                CSV and Excel (.xlsx) files are accepted — up to 200 MB each.
                Column headers must be present in row 1.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)

# ---------- Run button + results ----------
if both_done:
    if st.button("▶  Run transformation"):
        try:
            with st.spinner("Transforming…"):
                result_df = process_files(primary_file, secondary_file)

            display_df = result_df.copy()
            display_df = display_df.astype(object).where(result_df.notna(), "")
            display_df = display_df.astype(str)

            st.markdown(
                f"""
                <div class="status-box">
                    <b>Transformation complete.</b><br>
                    {len(result_df)} rows &nbsp;·&nbsp; {len(result_df.columns)} columns
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown('<div class="section-label">Preview</div>', unsafe_allow_html=True)
            st.dataframe(display_df, width='stretch', height=420)

            csv_data = result_df.to_csv(index=False).encode("utf-8-sig")

            st.markdown(
                '<div class="section-label" style="margin-top:1rem;">Export</div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                label="⬇  Download transformed CSV",
                data=csv_data,
                file_name="transformed_output.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
else:
    st.button("▶  Run transformation", disabled=True)
    missing = []
    if not primary_done:
        missing.append("questions file")
    if not secondary_done:
        missing.append("answers file")
    st.markdown(
        f'<div class="notice">Upload the {" and ".join(missing)} to continue</div>',
        unsafe_allow_html=True,
    )