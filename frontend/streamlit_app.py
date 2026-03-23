import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st

DEFAULT_BACKEND_URL = os.getenv("STREAMLIT_BACKEND_URL", "http://localhost:8000/analyze")

st.set_page_config(page_title="Jewellery Valuation Engine", page_icon="💍", layout="wide")
st.title("Jewellery Valuation Engine")
st.caption("Two-stage OpenAI vision pipeline for jewellery decomposition and valuation.")

backend_url = st.text_input("Backend endpoint", value=DEFAULT_BACKEND_URL)
uploaded_file = st.file_uploader("Upload a jewellery image", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded image", use_container_width=True)

if st.button("Analyze image", type="primary", disabled=uploaded_file is None):
    if uploaded_file is None:
        st.error("Upload an image before running analysis.")
    else:
        boundary = "streamlit-form-boundary"
        file_bytes = uploaded_file.getvalue()
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{uploaded_file.name}"\r\n'
            f"Content-Type: {uploaded_file.type or 'application/octet-stream'}\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        request = Request(
            backend_url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )

        with st.spinner("Analyzing image with the valuation pipeline..."):
            try:
                with urlopen(request, timeout=180) as response:
                    result = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                error_payload = exc.read().decode("utf-8", errors="replace")
                st.error(f"Backend returned HTTP {exc.code}: {error_payload}")
                st.stop()
            except URLError as exc:
                st.error(f"Could not reach backend: {exc.reason}")
                st.stop()
            except Exception as exc:
                st.error(f"Unexpected frontend error: {exc}")
                st.stop()

        st.subheader("Structured JSON")
        st.json(result)

        items = result.get("items", [])
        if items:
            st.subheader("Valuation Items")
            st.dataframe(items, use_container_width=True)

        stage1_output = result.get("stage1_visual_decomposition")
        if stage1_output:
            st.subheader("Stage 1 Visual Decomposition")
            st.text(stage1_output)
