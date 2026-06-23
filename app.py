import streamlit as st
from agent_graph import graph

# Set page configuration
st.set_page_config(
    page_title="AM Research Copilot",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling for Sleek Professional Engineering Dashboard
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Base typography and theme setup */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif;
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    
    /* Top title gradient banner */
    .title-banner {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 2.5rem;
        margin-bottom: 2.2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .title-banner h1 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 3rem;
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .title-banner p {
        font-size: 1.1rem;
        color: #94a3b8;
        margin-top: 0.6rem;
        margin-bottom: 0;
    }
    
    /* Input query styling */
    .stTextArea textarea {
        background-color: #1e293b;
        color: #f8fafc;
        border: 1px solid #475569;
        border-radius: 8px;
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
    }
    .stTextArea textarea:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 1px #6366f1;
    }
    
    /* Streamlit buttons custom design */
    .stButton>button {
        background: linear-gradient(90deg, #4f46e5, #7c3aed);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 2.2rem;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #4338ca, #6d28d9);
        box-shadow: 0 6px 16px rgba(99, 102, 241, 0.5);
        transform: translateY(-1px);
    }
    
    /* Clean layout container card for output reports */
    .report-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 2.5rem;
        margin-top: 2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* Technical mono blocks */
    code, pre {
        font-family: 'JetBrains Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)

# Header section
st.markdown("""
<div class="title-banner">
    <h1>Additive Manufacturing Optimization for Ceramic with Metal Additives</h1>
    <p>Autonomous Research Workflow orchestrating ADK 2.0 Graphs & MCP Manufacturing Databases</p>
</div>
""", unsafe_allow_html=True)

st.write("Enter your advanced manufacturing or materials research query below:")

# Text input for query with default placeholder
query = st.text_area(
    label="Research Query Input",
    value="Design a zirconia dental crown with improved fracture toughness",
    height=90,
    label_visibility="collapsed"
)

# Execute workflow on action click
if st.button("Run Analysis"):
    if not query.strip():
        st.warning("Please enter a non-empty research query to continue.")
    else:
        # Create interactive visual status expander
        with st.status("Executing Research Workflow Node Pipeline...", expanded=True) as status:
            status.write("🚀 Running multi-agent graph workflow nodes...")
            status.write("🛡️ Guardrail checks, materials database queries, and sintering planning are active...")
            # Invoke the graph using the invoke() structure
            final_state = graph.invoke({"user_query": query})
            status.update(label="Workflow completed successfully!", state="complete", expanded=False)
            
        # Display the compiled report inside a styled dashboard container card
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown(final_state.get("final_report", "Error generating report"))
        st.markdown('</div>', unsafe_allow_html=True)
