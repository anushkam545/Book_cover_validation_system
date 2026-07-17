import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000/analyze")

st.set_page_config(
    page_title="Cover Desk",
    page_icon="\U0001F4D6",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Design tokens & global styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <style>
        :root {
            --ink:        #0E1626;
            --ink-panel:  #161F35;
            --ink-line:   #2A3552;
            --paper:      #F3EFE6;
            --paper-dim:  #B9C0D4;
            --brass:      #C89B3C;
            --brass-dim:  #8A6F2C;
            --stamp-pass: #4F8F6B;
            --stamp-review: #C1553D;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 15% 0%, #16203A 0%, var(--ink) 45%),
                var(--ink);
            color: var(--paper);
        }

        section[data-testid="stSidebar"] {
            background: var(--ink-panel);
            border-right: 1px solid var(--ink-line);
        }

        h1, h2, h3 {
            font-family: 'Fraunces', serif !important;
            color: var(--paper) !important;
            letter-spacing: 0.2px;
        }

        .desk-header {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            border-bottom: 1px solid var(--ink-line);
            padding-bottom: 18px;
            margin-bottom: 28px;
        }

        .desk-eyebrow {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            letter-spacing: 3px;
            color: var(--brass);
            text-transform: uppercase;
        }

        .desk-title {
            font-family: 'Fraunces', serif;
            font-size: 40px;
            font-weight: 600;
            margin: 4px 0 0 0;
            color: var(--paper);
        }

        .desk-sub {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: var(--paper-dim);
        }

        /* Card */
        .cover-card {
            background: var(--ink-panel);
            border: 1px solid var(--ink-line);
            border-radius: 4px;
            padding: 28px 30px;
            position: relative;
        }

        .cover-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0;
            width: 3px; height: 100%;
            background: var(--brass);
        }

        .field-label {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: var(--paper-dim);
            margin-bottom: 4px;
        }

        .field-value {
            font-size: 16px;
            color: var(--paper);
            margin-bottom: 18px;
        }

        /* Stamp badge */
        .stamp {
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 22px;
            letter-spacing: 4px;
            text-transform: uppercase;
            padding: 10px 26px;
            border: 3px solid currentColor;
            border-radius: 6px;
            transform: rotate(-4deg);
            opacity: 0.95;
        }

        .stamp-pass {
            color: var(--stamp-pass);
            box-shadow: 0 0 0 3px rgba(79,143,107,0.15) inset;
        }

        .stamp-review {
            color: var(--stamp-review);
            box-shadow: 0 0 0 3px rgba(193,85,61,0.15) inset;
        }

        /* Confidence bar */
        .conf-track {
            width: 100%;
            height: 8px;
            background: var(--ink-line);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 6px;
        }
        .conf-fill {
            height: 100%;
            border-radius: 4px;
        }

        /* Issue list */
        .issue-row {
            display: flex;
            gap: 10px;
            padding: 10px 0;
            border-bottom: 1px solid var(--ink-line);
            font-size: 14px;
        }
        .issue-row:last-child { border-bottom: none; }
        .issue-dot {
            color: var(--stamp-review);
            font-size: 18px;
            line-height: 1.1;
        }
        .instruction-dot { color: var(--brass); font-size: 18px; line-height: 1.1; }

        .empty-note {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: var(--paper-dim);
        }

        div.stButton > button {
            background: var(--brass);
            color: var(--ink);
            border: none;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            font-size: 12px;
            padding: 10px 22px;
            border-radius: 3px;
            font-weight: 600;
        }
        div.stButton > button:hover {
            background: var(--brass-dim);
            color: var(--paper);
        }

        [data-testid="stFileUploaderDropzone"] {
            background: var(--ink);
            border: 1px dashed var(--ink-line);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — submission form
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="desk-eyebrow">Submission</div>', unsafe_allow_html=True)
    st.markdown('<div class="desk-title" style="font-size:26px;">New Cover</div>', unsafe_allow_html=True)
    st.write("")

    isbn = st.text_input("ISBN", placeholder="978-0-000-00000-0")
    uploaded_file = st.file_uploader("Cover file", type=["pdf", "png"])

    st.write("")
    submit = st.button("Submit for Review", use_container_width=True)

    st.write("")
    st.markdown('<div class="empty-note">Accepted formats: PDF, PNG</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="desk-header">
        <div>
            <div class="desk-eyebrow">Editorial Desk</div>
            <div class="desk-title">Cover Validation</div>
        </div>
        <div class="desk-sub">AUTOMATED REVIEW SYSTEM</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Submission handling
# ---------------------------------------------------------------------------
if "result" not in st.session_state:
    st.session_state.result = None

if submit:
    if not isbn:
        st.error("Enter an ISBN before submitting.")
    elif not uploaded_file:
        st.error("Attach a cover file before submitting.")
    else:
        with st.spinner("Reading the cover, checking margins, scanning for text..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"isbn": isbn}
                response = requests.post(FASTAPI_URL, files=files, data=data, timeout=120)
                response.raise_for_status()
                st.session_state.result = response.json()
                st.session_state.preview = uploaded_file
            except requests.exceptions.RequestException as exc:
                st.error(f"Could not reach the analysis service: {exc}")

# ---------------------------------------------------------------------------
# Result display
# ---------------------------------------------------------------------------
result = st.session_state.result

if result is None:
    st.markdown(
        '<div class="cover-card"><span class="empty-note">'
        "No submission yet — attach a cover on the left and press "
        '"Submit for Review".</span></div>',
        unsafe_allow_html=True,
    )
else:
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        annotated_url = result.get("annotated_image_url")
        if annotated_url:
            st.image(annotated_url, use_container_width=True, caption="Annotated result")
        elif st.session_state.get("preview") is not None and st.session_state.preview.type == "image/png":
            st.image(st.session_state.preview, use_container_width=True)
        else:
            st.markdown(
                '<div class="cover-card" style="text-align:center; padding:60px 20px;">'
                '<span class="empty-note">PDF submitted — preview not rendered here.</span>'
                "</div>",
                unsafe_allow_html=True,
            )

    with right:
        status = result.get("status", "UNKNOWN")
        confidence = result.get("confidence", 0)
        issues = result.get("issues", [])
        instructions = result.get("instructions", [])

        stamp_class = "stamp-pass" if status == "PASS" else "stamp-review"
        bar_color = "var(--stamp-pass)" if status == "PASS" else "var(--stamp-review)"

        st.markdown('<div class="cover-card">', unsafe_allow_html=True)

        st.markdown(f'<div class="stamp {stamp_class}">{status}</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

        st.markdown('<div class="field-label">ISBN</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value">{result.get("isbn", "—")}</div>', unsafe_allow_html=True)

        st.markdown('<div class="field-label">Confidence</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="field-value">{confidence}%</div>
            <div class="conf-track">
                <div class="conf-fill" style="width:{confidence}%; background:{bar_color};"></div>
            </div>
            <div style="height:22px;"></div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="field-label">Detected Issues</div>', unsafe_allow_html=True)
        if issues:
            rows = "".join(
                f'<div class="issue-row"><span class="issue-dot">&#9679;</span><span>{issue}</span></div>'
                for issue in issues
            )
            st.markdown(rows, unsafe_allow_html=True)
        else:
            st.markdown('<span class="empty-note">None found.</span>', unsafe_allow_html=True)

        st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="field-label">Correction Instructions</div>', unsafe_allow_html=True)
        if instructions:
            rows = "".join(
                f'<div class="issue-row"><span class="instruction-dot">&#9679;</span><span>{step}</span></div>'
                for step in instructions
            )
            st.markdown(rows, unsafe_allow_html=True)
        else:
            st.markdown('<span class="empty-note">No corrections required.</span>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
