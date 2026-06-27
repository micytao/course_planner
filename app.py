"""UC Course Planner — Entry point with grouped navigation."""

import streamlit as st

st.set_page_config(
    page_title="UC Course Planner",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation(
    {
        "Planning": [
            st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True),
            st.Page("pages/1_Chat_Advisor.py", title="Chat Advisor", icon="💬"),
            st.Page("pages/2_Course_Wizard.py", title="Course Wizard", icon="📋"),
            st.Page("pages/3_Demo_Scenarios.py", title="Sample Scenarios", icon="🎭"),
        ],
        "Knowledge": [
            st.Page("pages/4_Skills_Manager.py", title="Skills Manager", icon="📖"),
            st.Page("pages/5_MCP_Dashboard.py", title="MCP Dashboard", icon="🔌"),
            st.Page("pages/6_Datasets.py", title="Datasets", icon="🗄️"),
        ],
    },
    position="sidebar",
)

pg.run()
