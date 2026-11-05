"""History page — past experiments table with selective delete."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from api_client import ApiError, delete_experiment, history


def _status_bg(val: str) -> str:
    return {
        "completed": "background-color: #e8f5e9; color: #2e7d32",
        "done": "background-color: #e8f5e9; color: #2e7d32",
        "failed": "background-color: #fce4ec; color: #b71c1c",
        "running": "background-color: #e3f2fd; color: #1565c0",
        "queued": "background-color: #fff8e1; color: #f57f17",
        "cancelling": "background-color: #fff3e0; color: #e65100",
        "cancelled": "background-color: #fff3e0; color: #e65100",
        "timeout": "background-color: #fff3e0; color: #e65100",
    }.get(str(val).lower(), "")


def render() -> None:
    st.header("📜 History")
    try:
        rows = history()
    except ApiError as exc:
        st.error(str(exc))
        return

    if not rows:
        st.info("No experiments yet. Run a benchmark first.")
        return

    df = pd.DataFrame(rows)

    # Selective delete -------------------------------------------------------
    if "hist_confirm_all" not in st.session_state:
        st.session_state.hist_confirm_all = False

    st.markdown("### Delete experiments")
    st.caption(
        "Select individual experiments to remove, or use **Remove all history** "
        "to clear everything. Deleting a finished experiment removes it and its "
        "results; deleting a queued/running one cancels it first."
    )

    ids = [int(r.get("id")) for r in rows]

    # Per-row delete buttons (in columns to keep the page compact).
    for i in range(0, len(ids), 4):
        cols = st.columns(4)
        for j, eid in enumerate(ids[i : i + 4]):
            with cols[j]:
                if st.button(f"🗑️ Delete #{eid}", key=f"hist_del_{eid}"):
                    try:
                        delete_experiment(eid)
                        st.success(f"Experiment #{eid} deleted.")
                        st.rerun()
                    except ApiError as exc:
                        st.error(f"Could not delete #{eid}: {exc}")

    st.divider()

    # Bulk remove all --------------------------------------------------------
    st.markdown("### Remove all history")
    if not st.session_state.hist_confirm_all:
        if st.button("🗑️ Remove all history", key="hist_del_all_btn"):
            st.session_state.hist_confirm_all = True
            st.rerun()
    else:
        st.warning(
            "This will permanently delete every experiment and its results. "
            "This cannot be undone."
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete all", key="hist_del_all_confirm"):
                errors = []
                for eid in ids:
                    try:
                        delete_experiment(eid)
                    except ApiError as exc:
                        errors.append(f"#{eid}: {exc}")
                st.session_state.hist_confirm_all = False
                if errors:
                    st.error("Some deletions failed: " + "; ".join(errors))
                else:
                    st.success("All history removed.")
                st.rerun()
        with c2:
            if st.button("Cancel", key="hist_del_all_cancel"):
                st.session_state.hist_confirm_all = False
                st.rerun()

    st.divider()

    # Table ------------------------------------------------------------------
    styled = df.style.map(_status_bg, subset=["status"] if "status" in df.columns else [])
    st.dataframe(styled, width="stretch", hide_index=True)

    pick = st.number_input(
        "Open experiment ID", min_value=1, value=int(rows[0].get("id", 1)), key="hist_pick"
    )
    if st.button("Open →", key="hist_open_btn"):
        st.session_state.experiment_id = int(pick)
        st.success(f"Loaded experiment #{pick}. Switch to **Results**.")
