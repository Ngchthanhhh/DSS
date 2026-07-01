"""
ui_utils.py — PLACEHOLDER (skeleton only)

Ban goc chua CSS custom + link Spline scene rieng de render nen dong/hieu
ung neon cho tung trang (da tu chinh sua/luya chon). Da luoc bo vi ly do
bao mat "chat xam" giao dien. Lien he chu repo neu can ban day du.
"""

import streamlit as st


def inject_background_css():
    """[PLACEHOLDER] CSS custom de ep nen trong suot + hieu ung neon."""
    st.markdown(
        """
        <style>
            .stApp { background-color: #0E1117; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def dynamic_move_to_body(element_id: str):
    """[PLACEHOLDER] JS di chuyen element nen ra ngoai body de tranh bi Streamlit che."""
    pass


def render_full_wave():
    """[PLACEHOLDER] Render nen cho trang chu (app.py)."""
    inject_background_css()


def render_full_risk():
    """[PLACEHOLDER] Render nen dong (Spline scene) cho trang Risk Predictor."""
    inject_background_css()


def render_full_churn():
    """[PLACEHOLDER] Render nen dong (Spline scene) cho trang Churn Management."""
    inject_background_css()


def render_full_seller():
    """[PLACEHOLDER] Render nen dong (Spline scene) cho trang Seller Intelligence."""
    inject_background_css()


def render_full_app():
    """[PLACEHOLDER] Render nen dong (Spline scene) cho trang App chinh."""
    inject_background_css()
