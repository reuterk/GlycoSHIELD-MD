import streamlit as st
import glycoshield.app as app


st.set_page_config(
    page_title="GlycoSHIELD",
    layout="wide"
)
app.show_header(title="Upload protein structure", show_glycoshield_logo=False)

if not app.get_config()["have_input"]:
    app.use_default_input()

st.write(
    "Upload protein structure in Protein Data Bank (PDB) format using the uploader below. "
    f"As a default, IG-domain of Mouse N-cadherin is used (EC5, PDBid 3Q2W)"
)

uploaded_file = st.file_uploader(
    label="Upload PDB file",
    accept_multiple_files=False)
if uploaded_file is not None:
    app.store_uploaded_file(uploaded_file)
if st.button("Use default protein", help="Use the 5th IG-domain of Mouse N-cadherin (EC5, PDBid 3Q2W)"):
    app.use_default_input()
# app.print_input_pdb()

app.show_sidebar()
