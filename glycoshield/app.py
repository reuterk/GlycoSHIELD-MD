import os
import glob
import base64
import zipfile
import pathlib
import numpy as np
import streamlit as st
import MDAnalysis as mda
from .lib import glycoshield, glycotraj, glycosasa


# --- functions for configuration management ---
def init_config():
    # we use Streamlit's session state to store variables and state between user interaction events
    cfg = st.session_state
    # set up directory and file names
    cfg["tutorial_dir"] = "TUTORIAL"
    cfg["glycan_library_dir"] = "GLYCAN_LIBRARY"
    cfg["work_dir"] = "webapp_work"
    cfg["output_dir"] = "webapp_output"
    cfg["pdb_input"] = ""
    pathlib.Path(cfg["work_dir"]).mkdir(exist_ok=True)
    pathlib.Path(cfg["output_dir"]).mkdir(exist_ok=True)
    cfg["output_zip"] = cfg["output_dir"] + ".zip"
    # flags to implement a finite state machine for the various steps
    cfg["glycoshield_done"] = False
    cfg["glycotraj_done"] = False
    cfg["glycosasa_done"] = False
    cfg["have_input"] = False
    cfg["input_lines"] = ['#']
    cfg["init"] = True


def get_config():
    if "init" not in st.session_state:
        init_config()
    return st.session_state


def reset_webapp():
    cfg = get_config()
    remove_files = glob.glob(cfg["work_dir"]+"/*") + glob.glob(cfg["output_dir"]+"/*")
    for file in remove_files:
        os.unlink(file)
    init_config()


# --- functions defining the steps of the pipeline ---


def store_uploaded_file(uploaded_file):
    cfg = get_config()
    file_name = os.path.join(cfg["work_dir"], uploaded_file.name)
    with open(file_name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    cfg["pdb_input"] = file_name
    cfg["have_input"] = True


def use_default_input():
    cfg = get_config()
    default_pdb = os.path.join(cfg["tutorial_dir"], "EC5.pdb")
    cfg["pdb_input"] = default_pdb
    cfg["have_input"] = True


def print_input_pdb():
    cfg = get_config()
    file_name = cfg["pdb_input"]
    st.write("Using {}".format(file_name))


def webapp_output_ready():
    cfg = get_config()
    if cfg["glycoshield_done"] and cfg["glycotraj_done"] and cfg["glycosasa_done"]:
        return True
    else:
        return False


def zip_webapp_output():
    # zip-directory function inspired from <https://stackoverflow.com/a/1855118>
    def zipdir(path, zip_fh):
        for root, dirs, files in os.walk(path):
            for file in files:
                zip_fh.write(
                    os.path.join(root, file),
                    os.path.relpath(os.path.join(root, file),
                                    os.path.join(path, '..')
                    )
                )
    cfg = get_config()
    if webapp_output_ready():
        with zipfile.ZipFile(os.path.join(cfg["work_dir"], cfg["output_zip"]), 'w',
                        compression=zipfile.ZIP_DEFLATED, compresslevel=1) as zip_fh:
            zipdir(cfg["output_dir"], zip_fh)


def get_webapp_output():
    cfg = get_config()
    if webapp_output_ready():
        zipfile = os.path.join(cfg["work_dir"], cfg["output_zip"])
        with open(zipfile, "rb") as f:
            data = f.read()
        size = os.path.getsize(zipfile) / 1024. / 1024.
    else:
        data = ""
        size = 0
    return data, size


def store_inputs(inputs):
    cfg = get_config()
    with open(os.path.join(cfg["work_dir"], "input_sugaring"), 'w') as f:
        f.write(inputs)


def run_glycoshield(bar):
    cfg = get_config()
    pdbtraj = os.path.join(cfg["output_dir"], "test_pdb.pdb")
    pdbtrajframes = 30
    gs = glycoshield(
        protpdb=cfg["pdb_input"],
        protxtc=None,
        inputfile=os.path.join(cfg["work_dir"], "input_sugaring"),
        pdbtraj=pdbtraj,
        pdbtrajframes=pdbtrajframes,
    )
    occ = gs.run(streamlit_progressbar=bar)
    st.write(occ)
    cfg["gs"] = gs
    cfg["occ"] = occ
    cfg["glycoshield_done"] = True


def check_glycoshield(bar=None):
    cfg = get_config()
    if cfg["glycoshield_done"]:
        # st.write("Done!")
        if bar is not None:
            bar.progress(1.0)
    return cfg["glycoshield_done"]


def run_glycotraj(bar_1, bar_2):
    cfg = get_config()
    gs = cfg["gs"]
    occ = cfg["occ"]
    path = cfg["output_dir"]
    maxframe = np.min(occ[0])
    pdblist = gs.pdblist
    xtclist = gs.xtclist
    chainlist = gs.chainlist
    reslist = gs.reslist
    outname = os.path.join(path, "merged_traj")
    pdbtraj = os.path.join(path, "test_merged_pdb.pdb")
    pdbtrajframes = 30
    glycotraj(
        maxframe,
        outname,
        pdblist,
        xtclist,
        chainlist,
        reslist,
        pdbtraj,
        pdbtrajframes,
        path,
        streamlit_progressbar_1=bar_1,
        streamlit_progressbar_2=bar_2,
    )
    cfg["glycotraj_done"] = True


def check_glycotraj(bar_1=None, bar_2=None):
    cfg = get_config()
    if cfg["glycotraj_done"]:
        # st.write("Done!")
        if bar_1 is not None:
            bar_1.progress(1.0)
        if bar_2 is not None:
            bar_2.progress(1.0)


def run_glycosasa():
    cfg = get_config()
    gs = cfg["gs"]
    occ = cfg["occ"]
    path = cfg["output_dir"]
    maxframe = np.min(occ[0])
    maxframe = 10  # temporary
    pdblist = gs.pdblist
    xtclist = gs.xtclist
    probelist = [0.14, 0.70]  # Possibly user will have an option to choose one value, makes it faster and easier to manage visualisation
    plottrace = True
    ndots = 15
    mode = "max"
    keepoutput = False
    sasas = glycosasa(
        pdblist=pdblist,
        xtclist=xtclist,
        plottrace=plottrace,
        probelist=probelist,
        ndots=ndots,
        mode=mode,
        keepoutput=keepoutput,
        maxframe=maxframe,
        path=path,
        run_parallel=True,
        streamlit_progressbar=None
    )
    cfg["sasas"] = sasas
    cfg["glycosasa_done"] = True


def check_glycosasa(bar):
    cfg = get_config()
    if cfg["glycosasa_done"]:
        # st.write("Done!")
        if bar is not None:
            bar.progress(1.0)
    return cfg["glycosasa_done"]


def visualize(pdb_list):
    from stmol import showmol
    import py3Dmol
    view = py3Dmol.view()
    # view = py3Dmol.view(query="mmtf:1ycr")
    for pdb in pdb_list:
        view.addModel(open(pdb, 'r').read(), 'pdb')
    view.setStyle({'cartoon': {'color': 'spectrum'}})
    view.zoomTo()
    view.setBackgroundColor('white')
    showmol(view, height=400, width=600)


def visualize_test(pdb):
    from stmol import showmol
    import py3Dmol
    # view = py3Dmol.view()
    # view = py3Dmol.view(query="mmtf:1ycr")
    # for pdb in pdb_list:
        # view.addModel(open(pdb, 'r').read(), 'pdb')
    # view.setStyle(chA, {'cartoon': {'color': 'spectrum'}})

    with open(pdb, 'r') as fp:
        data = fp.read()
    view = py3Dmol.view(
        data=data,
        style={'stick': {'colorscheme': 'greenCarbon'}},
        # style={'cartoon': {'color': 'spectrum'}},
        # query="chain:B"
    )
    chA = {'chain': 'A', 'opacity':0.7, 'color':'white'}

    view.addSurface(py3Dmol.VDW, chA)
    view.zoomTo()
    view.setBackgroundColor('white')
    showmol(view, height=800, width=800)


def visualize_sasa(pdb, height=800, width=1200):
    from stmol import showmol
    import py3Dmol
    with open(pdb, 'r') as fp:
        data = fp.read()
    view = py3Dmol.view(
        data=data,
        style={'stick': {'colorscheme': 'greenCarbon'}},
        width=width,
        height=height
    )
    chA = {'chain': 'A', 'opacity':0.7} #, 'color':'white'}
    view.addSurface(py3Dmol.VDW, chA)
    view.zoomTo()
    view.setBackgroundColor('white')
    showmol(
        view,
        width=width,
        height=height
    )


def get_glycan_library():
    cfg = get_config()
    # lib = {}
    lib = []
    glycan_listdir = os.listdir(cfg["glycan_library_dir"])
    glycan_listdir.sort()
    for dir_raw in glycan_listdir:
        dir_path = os.path.join(cfg["glycan_library_dir"], dir_raw)
        if os.path.isdir(dir_path):
            # files = os.listdir(dir_path)
            # lib[dir_raw] = list(filter(lambda x: x.endswith(('.xtc', '.pdb')), files))
            lib.append(dir_raw)
    return lib


def get_chain_resids():
    cfg = get_config()
    output = {}
    if cfg["have_input"]:
        u = mda.Universe(cfg["pdb_input"])
        prot = u.select_atoms('protein')
        chains = np.unique(sorted(prot.atoms.segids))
        for chain in chains:
            sel = prot.select_atoms('segid ' + chain)
            output[chain] = np.unique(sel.resids)
    return output


def quit_binder_webapp():
    """Shut down a session running within a Docker container on Binder."""
    os.system("skill -u jovyan")


def create_input_line(chain, resid, glycan):
    cfg = get_config()
    resid_m = int(resid) - 1
    resid_p = int(resid) + 1
    glycan_pdb = os.path.join(
        os.path.join(cfg["glycan_library_dir"], glycan),
        "production_merged_noW.pdb"
    )
    glycan_xtc = os.path.join(
        os.path.join(cfg["glycan_library_dir"], glycan),
        "production_merged_noW.xtc"
    )
    output_pdb = os.path.join(
        cfg["output_dir"],
        f"{chain}_{resid}.pdb"
    )
    output_xtc = os.path.join(
        cfg["output_dir"],
        f"{chain}_{resid}.xtc"
    )
    return f"{chain} {resid_m},{resid},{resid_p} 1,2,3 {glycan_pdb} {glycan_xtc} {output_pdb} {output_xtc}"


def add_input_line(line):
    cfg = get_config()
    if line not in cfg["input_lines"]:
        cfg["input_lines"].append(line)


def rem_input_line(line):
    cfg = get_config()
    try:
        cfg["input_lines"].remove(line)
    except:
        pass


def get_input_lines():
    cfg = get_config()
    return cfg["input_lines"]


def clear_input_lines():
    cfg = get_config()
    cfg["input_lines"] = ['#']


def display_html_image_file(streamlit_empty_handle, image_file):
    with open(image_file, "rb") as fp:
        image_data = base64.b64encode(fp.read()).decode("utf-8")
        streamlit_empty_handle.markdown(
            f'<img src="data:image/gif;base64,{image_data}" style="width:25vw; min-width:256px;" alt="{image_file}"/>',
            unsafe_allow_html=True,
        )