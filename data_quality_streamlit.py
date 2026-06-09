"""
AT&T GSCDNA Data Quality Cost Monitor
Streamlit-in-Snowflake Application for DQ Cost Monitoring & Optimization
Role-Based Access Control: DQ_VIEWER_ROLE, DQ_OPERATOR_ROLE, DQ_ADMIN_ROLE
"""

import streamlit as st

st.set_page_config(
    page_title="GSCDNA DQ Observability Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.exceptions import SnowparkSQLException
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Compatibility: st.rerun() was added in Streamlit 1.27; older versions use st.experimental_rerun()
if not hasattr(st, 'rerun'):
    st.rerun = st.experimental_rerun

# Custom CSS for AT&T GSCDNA Branding
st.markdown("""
<style>
    /* AT&T GSCDNA Blue Theme */
    :root {
        --att-blue-dark: #1A4D6E;
        --att-blue-light: #29B5E8;
        --att-gray-dark: #1A1A1A;
        --att-gray: #6B6B6B;
        --att-gray-light: #F5F5F5;
    }
    
    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #1A4D6E 0%, #29B5E8 100%);
        padding: 20px;
        border-radius: 10px;
        margin-top: -2rem;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin: 5px 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #1A4D6E;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(26,77,110,0.2);
        border-left: 6px solid #29B5E8;
    }
    
    .metric-card h3 {
        color: #000000;
        margin: 0 0 10px 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    .metric-card p {
        color: #000000;
        margin: 0;
        font-size: 0.9rem;
    }
    
    /* Status badges */
    .status-active {
        background-color: #28a745;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-critical {
        background-color: #dc3545;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-warning {
        background-color: #ffc107;
        color: #333;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    .status-info {
        background-color: #17a2b8;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #1A4D6E 0%, #29B5E8 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        font-size: 0.8rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(26,77,110,0.3);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(41,181,232,0.4);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #F5F5F5;
        border-radius: 5px 5px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1A4D6E;
        color: white;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #E8F4FD;
        border-left: 4px solid #29B5E8;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .warning-box {
        background-color: #FFF3E0;
        border-left: 4px solid #FB8C00;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .success-box {
        background-color: #E8F5E9;
        border-left: 4px solid #43A047;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION & ACCESS CONTROL
# ============================================================

def get_snowflake_session():
    """Get active Snowflake session for Streamlit in Snowflake"""
    return get_active_session()


@st.cache_data(ttl=300)
def get_current_role(_session):
    """Get current active role"""
    try:
        result = _session.sql("SELECT CURRENT_ROLE() AS ROLE").collect()
        return result[0]['ROLE']
    except Exception:
        return None


def determine_access_level(current_role):
    """Determine user's access level based on current role"""
    if current_role is None:
        return 'VIEWER'
    role_upper = current_role.upper()
    if role_upper in ('DQ_ADMIN_ROLE', 'SYSADMIN', 'ACCOUNTADMIN'):
        return 'ADMIN'
    elif role_upper == 'DQ_OPERATOR_ROLE':
        return 'OPERATOR'
    elif role_upper == 'DQ_VIEWER_ROLE':
        return 'VIEWER'
    elif role_upper in ('SYSADMIN', 'ACCOUNTADMIN'):
        return 'ADMIN'
    return 'VIEWER'


def check_permission(access_level, required_level):
    """Check if user has required permission level"""
    levels = {'ADMIN': 3, 'OPERATOR': 2, 'VIEWER': 1, 'NONE': 0}
    return levels.get(access_level, 0) >= levels.get(required_level, 0)


# ============================================================
# DATA LOADING FUNCTIONS
# ============================================================

SCHEMA_PREFIX = "GSCDNA_DQ.GSCDNA_DATA_GOV"


@st.cache_data(ttl=300)
def load_executive_summary(_session):
    """Load executive summary KPIs"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.VW_DQ_COST_EXECUTIVE_SUMMARY").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_cost_trends(_session):
    """Load 30-day cost trends"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.VW_DQ_COST_TRENDS ORDER BY LOG_DATE").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_cost_by_priority(_session):
    """Load cost breakdown by priority tier"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.VW_DQ_COST_BY_PRIORITY").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_anomalies(_session):
    """Load anomaly detection data"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.VW_DQ_COST_ANOMALIES WHERE IS_ANOMALY = TRUE ORDER BY LOG_DATE DESC").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_anomaly_log(_session):
    """Load anomaly log table"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_COST_ANOMALY_LOG ORDER BY DETECTED_TS DESC").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_alerts_history(_session):
    """Load alerts history"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_COST_ALERTS_HISTORY ORDER BY ALERT_TS DESC").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_cost_vs_quality(_session):
    """Load cost vs quality correlation"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.VW_DQ_COST_VS_QUALITY").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_optimization(_session):
    """Load optimization recommendations"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.VW_DQ_COST_OPTIMIZATION").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_budget_config(_session):
    """Load budget configuration"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_COST_BUDGET_CONFIG").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_objects_monitored(_session):
    """Load monitored objects"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_OBJECTS_MONITORED ORDER BY PRIORITY_TIER, TABLE_NAME").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_email_config(_session):
    """Load email notification config"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_EMAIL_NOTIFICATION_CONFIG").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_cost_daily_log(_session):
    """Load daily cost log"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_COST_DAILY_LOG ORDER BY LOG_DATE DESC").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_forecast(_session):
    """Load cost forecast"""
    try:
        df = _session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_COST_FORECAST ORDER BY FORECAST_MONTH").to_pandas()
        return df
    except Exception:
        return pd.DataFrame()


# ============================================================
# PAGE FUNCTIONS
# ============================================================

def page_executive_dashboard(session):
    """Executive Dashboard - KPIs and health overview"""
    st.markdown("### Executive Dashboard")

    summary_df = load_executive_summary(session)

    if summary_df.empty:
        st.info("No data available for executive summary.")
        return

    row = summary_df.iloc[0]

    # KPI Metric Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        cost_30d = row.get('COST_30D_USD', 0) or 0
        st.markdown(f"""
        <div class="metric-card">
            <h3>${cost_30d:,.4f}</h3>
            <p>Total Cost (30 Days)</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        budget_pct = row.get('BUDGET_UTILIZATION_PCT', 0) or 0
        st.markdown(f"""
        <div class="metric-card">
            <h3>{budget_pct:.1f}%</h3>
            <p>Budget Utilization</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        anomalies = int(row.get('ACTIVE_ANOMALIES', 0) or 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>{anomalies}</h3>
            <p>Active Anomalies</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        objects = int(row.get('OBJECTS_MONITORED', 0) or 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>{objects}</h3>
            <p>Objects Monitored</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Health Score Gauge and Cost Trend
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Health Score")
        health_score = max(0, min(100, 100 - float(budget_pct)))
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "DQ Cost Health"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#29B5E8"},
                'steps': [
                    {'range': [0, 40], 'color': "#ffcccc"},
                    {'range': [40, 70], 'color': "#fff3cd"},
                    {'range': [70, 100], 'color': "#d4edda"}
                ],
                'threshold': {
                    'line': {'color': "#1A4D6E", 'width': 4},
                    'thickness': 0.75,
                    'value': health_score
                }
            }
        ))
        fig.update_layout(height=300, margin=dict(t=50, b=0, l=30, r=30))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### 7-Day Cost Trend")
        trends_df = load_cost_trends(session)
        if not trends_df.empty:
            recent = trends_df.tail(7)
            fig = px.line(
                recent, x='LOG_DATE', y='TOTAL_COST_USD',
                markers=True,
                color_discrete_sequence=['#29B5E8']
            )
            fig.update_layout(
                height=300,
                margin=dict(t=20, b=30, l=30, r=30),
                xaxis_title="Date",
                yaxis_title="Cost (USD)",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trend data available.")

    # Quick Stats Table
    st.markdown("#### Quick Stats")
    stats_data = {
        "Metric": ["Today's Cost", "Yesterday's Cost", "7-Day Total", "30-Day Total", "Avg Daily (7d)", "Day-over-Day Change"],
        "Value": [
            f"${row.get('TODAY_COST_USD', 0) or 0:,.6f}",
            f"${row.get('YESTERDAY_COST_USD', 0) or 0:,.6f}",
            f"${row.get('COST_7D_USD', 0) or 0:,.6f}",
            f"${cost_30d:,.6f}",
            f"${row.get('AVG_DAILY_COST_7D_USD', 0) or 0:,.6f}",
            f"{row.get('DAY_OVER_DAY_CHANGE_PCT', 0) or 0:,.2f}%"
        ]
    }
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True)


def page_cost_trends(session):
    """Cost Trends - 30-day analysis"""
    st.markdown("### Cost Trends")

    trends_df = load_cost_trends(session)

    if trends_df.empty:
        st.info("No cost trend data available.")
        return

    # Date range filter
    col1, col2 = st.columns(2)
    with col1:
        days_back = st.selectbox("Time Range", [7, 14, 30], index=2, key="trends_range")

    filtered = trends_df.tail(days_back)

    # 30-day line chart
    st.markdown("#### Daily Cost Trend")
    fig = px.line(
        filtered, x='LOG_DATE', y='TOTAL_COST_USD',
        markers=True,
        color_discrete_sequence=['#1A4D6E']
    )
    fig.update_layout(
        height=400,
        xaxis_title="Date",
        yaxis_title="Cost (USD)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # Day-over-day change bar chart
    st.markdown("#### Day-over-Day Change (%)")
    if 'DAY_OVER_DAY_CHANGE_PCT' in filtered.columns:
        change_df = filtered.dropna(subset=['DAY_OVER_DAY_CHANGE_PCT'])
        if not change_df.empty:
            colors = ['#dc3545' if x > 0 else '#28a745' for x in change_df['DAY_OVER_DAY_CHANGE_PCT']]
            fig2 = go.Figure(go.Bar(
                x=change_df['LOG_DATE'],
                y=change_df['DAY_OVER_DAY_CHANGE_PCT'],
                marker_color=colors
            ))
            fig2.update_layout(
                height=300,
                xaxis_title="Date",
                yaxis_title="Change (%)"
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Top 5 costliest objects
    st.markdown("#### Top 5 Costliest Objects (30 Days)")
    daily_log = load_cost_daily_log(session)
    if not daily_log.empty:
        top5 = daily_log.groupby('OBJECT_NAME')['ESTIMATED_COST_USD'].sum().nlargest(5).reset_index()
        top5.columns = ['Object Name', 'Total Cost (USD)']
        st.dataframe(top5, use_container_width=True)
    else:
        st.info("No daily log data available.")


def page_cost_by_priority(session):
    """Cost by Priority Tier"""
    st.markdown("### Cost by Priority Tier")

    priority_df = load_cost_by_priority(session)

    if priority_df.empty:
        st.info("No priority cost data available.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Cost Distribution by Tier")
        fig = px.pie(
            priority_df, values='TOTAL_COST_30D_USD', names='PRIORITY_TIER',
            color_discrete_sequence=['#1A4D6E', '#29B5E8', '#5DADE2', '#85C1E9', '#AED6F1']
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Objects per Tier")
        fig2 = px.bar(
            priority_df, x='PRIORITY_TIER', y='OBJECT_COUNT',
            color='PRIORITY_TIER',
            color_discrete_sequence=['#1A4D6E', '#29B5E8', '#5DADE2', '#85C1E9', '#AED6F1']
        )
        fig2.update_layout(height=350, showlegend=False, xaxis_title="Tier", yaxis_title="Objects")
        st.plotly_chart(fig2, use_container_width=True)

    # Tier details table
    st.markdown("#### Tier Details")
    display_cols = ['PRIORITY_TIER', 'TIER_DESCRIPTION', 'OBJECT_COUNT', 'TOTAL_COST_30D_USD', 'AVG_DAILY_COST_USD', 'MAX_BUDGET_DAILY_USD', 'COST_SHARE_PCT']
    available_cols = [c for c in display_cols if c in priority_df.columns]
    st.dataframe(priority_df[available_cols], use_container_width=True)


def page_anomaly_detection(session):
    """Anomaly Detection page"""
    st.markdown("### Anomaly Detection")

    anomaly_log = load_anomaly_log(session)

    if anomaly_log.empty:
        st.info("No anomalies detected.")
        return

    # Active vs resolved stats
    active = anomaly_log[anomaly_log['IS_RESOLVED'] == False]
    resolved = anomaly_log[anomaly_log['IS_RESOLVED'] == True]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Anomalies", len(active))
    with col2:
        st.metric("Resolved", len(resolved))
    with col3:
        critical_count = len(active[active['SEVERITY'] == 'CRITICAL']) if not active.empty else 0
        st.metric("Critical", critical_count)

    st.markdown("---")

    # Active anomalies table with severity badges
    st.markdown("#### Active Anomalies")
    if not active.empty:
        for _, row in active.iterrows():
            severity = row.get('SEVERITY', 'WARNING')
            badge_class = 'status-critical' if severity == 'CRITICAL' else 'status-warning'
            st.markdown(f"""
            <div style="padding:10px; margin:5px 0; border-radius:5px; background:#f8f9fa; border-left:4px solid {'#dc3545' if severity == 'CRITICAL' else '#ffc107'};">
                <span class="{badge_class}">{severity}</span>
                <strong style="margin-left:10px;">{row.get('OBJECT_NAME', 'Unknown')}</strong>
                <span style="margin-left:10px; color:#666;">Expected: ${row.get('EXPECTED_COST', 0) or 0:,.6f} | Actual: ${row.get('ACTUAL_COST', 0) or 0:,.6f} | Dev: {row.get('DEVIATION_STDDEV', 0) or 0:.1f} std</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No active anomalies!")

    # Anomaly timeline
    st.markdown("#### Anomaly Timeline")
    if not anomaly_log.empty and 'ANOMALY_DATE' in anomaly_log.columns:
        timeline = anomaly_log.groupby(['ANOMALY_DATE', 'SEVERITY']).size().reset_index(name='COUNT')
        if not timeline.empty:
            fig = px.bar(
                timeline, x='ANOMALY_DATE', y='COUNT', color='SEVERITY',
                color_discrete_map={'CRITICAL': '#dc3545', 'WARNING': '#ffc107', 'INFO': '#17a2b8'}
            )
            fig.update_layout(height=300, xaxis_title="Date", yaxis_title="Anomalies")
            st.plotly_chart(fig, use_container_width=True)

    # Severity distribution
    st.markdown("#### Severity Distribution")
    if not anomaly_log.empty:
        sev_dist = anomaly_log['SEVERITY'].value_counts().reset_index()
        sev_dist.columns = ['Severity', 'Count']
        fig2 = px.pie(sev_dist, values='Count', names='Severity',
                      color_discrete_map={'CRITICAL': '#dc3545', 'WARNING': '#ffc107', 'INFO': '#17a2b8'})
        fig2.update_layout(height=300)
        st.plotly_chart(fig2, use_container_width=True)


def page_budget_alerts(session):
    """Budget Alerts page"""
    st.markdown("### Budget Alerts")

    alerts_df = load_alerts_history(session)
    budget_df = load_budget_config(session)

    # Active alerts
    st.markdown("#### Active Alerts")
    if not alerts_df.empty:
        active_alerts = alerts_df[alerts_df['RESOLVED_TS'].isna()]
        if not active_alerts.empty:
            for _, row in active_alerts.iterrows():
                level = row.get('ALERT_LEVEL', 'INFO')
                if level == 'CRITICAL':
                    badge_class = 'status-critical'
                elif level == 'WARNING':
                    badge_class = 'status-warning'
                else:
                    badge_class = 'status-info'
                st.markdown(f"""
                <div style="padding:10px; margin:5px 0; border-radius:5px; background:#f8f9fa; border-left:4px solid {'#dc3545' if level == 'CRITICAL' else '#ffc107' if level == 'WARNING' else '#17a2b8'};">
                    <span class="{badge_class}">{level}</span>
                    <strong style="margin-left:10px;">{row.get('ALERT_TYPE', '')}</strong>
                    <span style="margin-left:10px; color:#666;">{row.get('OBJECT_NAME', 'All Objects')}</span>
                    <p style="margin:5px 0 0 0; font-size:0.9rem;">{row.get('MESSAGE', '')}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No active alerts!")
    else:
        st.info("No alert history available.")

    st.markdown("---")

    # Budget utilization progress bars
    st.markdown("#### Budget Utilization by Object")
    if not budget_df.empty:
        daily_log = load_cost_daily_log(session)
        if not daily_log.empty:
            today_costs = daily_log[daily_log['LOG_DATE'] == daily_log['LOG_DATE'].max()]
            for _, budget_row in budget_df.iterrows():
                obj_name = budget_row.get('OBJECT_NAME', '')
                daily_budget = float(budget_row.get('DAILY_BUDGET_USD', 10))
                obj_cost = today_costs[today_costs['OBJECT_NAME'] == obj_name]['ESTIMATED_COST_USD'].sum()
                utilization = min(float(obj_cost) / daily_budget * 100, 100) if daily_budget > 0 else 0
                color = '#28a745' if utilization < 70 else '#ffc107' if utilization < 90 else '#dc3545'
                st.markdown(f"**{obj_name}** - ${obj_cost:.6f} / ${daily_budget:.4f} ({utilization:.1f}%)")
                st.progress(min(utilization / 100, 1.0))
        else:
            st.info("No daily cost data to calculate utilization.")

    st.markdown("---")

    # Alert history table
    st.markdown("#### Alert History")
    if not alerts_df.empty:
        alert_filter = st.selectbox("Filter by Level", ['ALL', 'CRITICAL', 'WARNING', 'INFO'], key="alert_filter")
        filtered_alerts = alerts_df if alert_filter == 'ALL' else alerts_df[alerts_df['ALERT_LEVEL'] == alert_filter]
        display_cols = ['ALERT_TS', 'ALERT_TYPE', 'ALERT_LEVEL', 'OBJECT_NAME', 'MESSAGE', 'EMAIL_SENT']
        available = [c for c in display_cols if c in filtered_alerts.columns]
        st.dataframe(filtered_alerts[available].head(20), use_container_width=True)


def page_cost_vs_quality(session):
    """Cost vs Quality correlation"""
    st.markdown("### Cost vs Quality")

    cq_df = load_cost_vs_quality(session)

    if cq_df.empty:
        st.info("No cost vs quality data available.")
        return

    # Scatter plot: cost vs pass rate
    st.markdown("#### Cost vs Pass Rate by Object")
    fig = px.scatter(
        cq_df, x='TOTAL_COST_USD', y='PASS_RATE_PCT',
        text='OBJECT_NAME',
        color='PERFORMANCE_QUADRANT',
        color_discrete_map={
            'EFFICIENT': '#28a745',
            'HIGH_COST_HIGH_QUALITY': '#ffc107',
            'LOW_COST_LOW_QUALITY': '#17a2b8',
            'NEEDS_OPTIMIZATION': '#dc3545'
        },
        size='TOTAL_EXECUTIONS'
    )
    fig.update_traces(textposition='top center', textfont_size=9)
    fig.update_layout(
        height=450,
        xaxis_title="Total Cost (USD, 30 Days)",
        yaxis_title="Pass Rate (%)"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Metrics table
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Cost per Execution")
        if 'COST_PER_EXECUTION_USD' in cq_df.columns:
            cost_per_exec = cq_df[['OBJECT_NAME', 'COST_PER_EXECUTION_USD', 'TOTAL_EXECUTIONS']].sort_values('COST_PER_EXECUTION_USD', ascending=False)
            st.dataframe(cost_per_exec, use_container_width=True)

    with col2:
        st.markdown("#### Quality per Credit")
        if 'QUALITY_PER_CREDIT' in cq_df.columns:
            qpc = cq_df[['OBJECT_NAME', 'QUALITY_PER_CREDIT', 'PASS_RATE_PCT']].sort_values('QUALITY_PER_CREDIT', ascending=False)
            st.dataframe(qpc, use_container_width=True)

    # Quadrant summary
    st.markdown("#### Performance Quadrant Classification")
    if 'PERFORMANCE_QUADRANT' in cq_df.columns:
        quadrant_summary = cq_df['PERFORMANCE_QUADRANT'].value_counts().reset_index()
        quadrant_summary.columns = ['Quadrant', 'Count']
        st.dataframe(quadrant_summary, use_container_width=True)


def page_optimization(session):
    """Optimization recommendations"""
    st.markdown("### Cost Optimization")

    opt_df = load_optimization(session)

    if opt_df.empty:
        st.info("No optimization data available.")
        return

    # Recommendations table
    st.markdown("#### Optimization Recommendations")
    if 'OPTIMIZATION_RECOMMENDATION' in opt_df.columns:
        for _, row in opt_df.iterrows():
            rec = row.get('OPTIMIZATION_RECOMMENDATION', '')
            obj = row.get('OBJECT_NAME', '')
            total_cost = row.get('TOTAL_COST_30D', 0) or 0
            if 'OPTIMAL' in rec:
                icon = "checkmark"
                color = "#28a745"
            elif 'REDUCE' in rec:
                icon = "arrow_down"
                color = "#ffc107"
            elif 'INVESTIGATE' in rec:
                icon = "search"
                color = "#dc3545"
            else:
                icon = "info"
                color = "#17a2b8"
            st.markdown(f"""
            <div style="padding:10px; margin:5px 0; border-radius:5px; background:#f8f9fa; border-left:4px solid {color};">
                <strong>{obj}</strong> (30d cost: ${total_cost:,.6f})
                <p style="margin:5px 0 0 0; font-size:0.9rem; color:#666;">{rec}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Potential savings
    st.markdown("#### Potential Savings")
    if 'POTENTIAL_WEEKEND_SAVINGS_USD' in opt_df.columns:
        total_savings = opt_df['POTENTIAL_WEEKEND_SAVINGS_USD'].sum()
        st.metric("Estimated Monthly Weekend Savings", f"${total_savings:,.6f}")
        savings_detail = opt_df[['OBJECT_NAME', 'POTENTIAL_WEEKEND_SAVINGS_USD', 'WEEKEND_UTILIZATION_RATIO']].sort_values('POTENTIAL_WEEKEND_SAVINGS_USD', ascending=False)
        st.dataframe(savings_detail, use_container_width=True)

    st.markdown("---")

    # High variability objects
    st.markdown("#### High Variability Objects")
    if 'VARIABILITY_COEFFICIENT' in opt_df.columns:
        high_var = opt_df[opt_df['VARIABILITY_COEFFICIENT'] > 0.3][['OBJECT_NAME', 'VARIABILITY_COEFFICIENT', 'AVG_DAILY_COST', 'COST_STDDEV']].sort_values('VARIABILITY_COEFFICIENT', ascending=False)
        if not high_var.empty:
            st.dataframe(high_var, use_container_width=True)
        else:
            st.success("No objects with high cost variability detected.")

    # Weekend utilization
    st.markdown("#### Weekend Utilization Analysis")
    if 'WEEKEND_UTILIZATION_RATIO' in opt_df.columns:
        fig = px.bar(
            opt_df.sort_values('WEEKEND_UTILIZATION_RATIO', ascending=False),
            x='OBJECT_NAME', y='WEEKEND_UTILIZATION_RATIO',
            color_discrete_sequence=['#29B5E8']
        )
        fig.add_hline(y=0.8, line_dash="dash", line_color="red", annotation_text="High Weekend Usage")
        fig.update_layout(height=350, xaxis_title="Object", yaxis_title="Weekend/Weekday Ratio")
        st.plotly_chart(fig, use_container_width=True)


def page_configuration(session, access_level):
    """Configuration page (ADMIN only)"""
    st.markdown("### Configuration")

    if not check_permission(access_level, 'ADMIN'):
        st.warning("Admin access required to modify configuration.")
        st.info("You can view the current configuration below.")

    tab1, tab2, tab3, tab4 = st.tabs(["Budget Thresholds", "Email Notifications", "Priority Tiers", "Monitored Objects"])

    with tab1:
        st.markdown("#### Budget Thresholds")
        budget_df = load_budget_config(session)
        if not budget_df.empty:
            st.dataframe(budget_df, use_container_width=True)
        else:
            st.info("No budget configuration found.")

        if check_permission(access_level, 'ADMIN'):
            st.markdown("---")
            st.markdown("#### Update Budget")
            if not budget_df.empty:
                obj_name = st.selectbox("Object", budget_df['OBJECT_NAME'].tolist(), key="budget_obj")
                new_budget = st.number_input("Daily Budget (USD)", min_value=0.0, value=10.0, step=0.5, key="new_budget")
                warn_mult = st.number_input("Warning Multiplier", min_value=1.0, value=2.0, step=0.5, key="warn_mult")
                crit_mult = st.number_input("Critical Multiplier", min_value=1.0, value=3.0, step=0.5, key="crit_mult")
                if st.button("Update Budget", key="btn_update_budget"):
                    try:
                        session.sql(f"""
                            UPDATE {SCHEMA_PREFIX}.DQ_COST_BUDGET_CONFIG
                            SET DAILY_BUDGET_USD = {new_budget},
                                WARNING_THRESHOLD_MULTIPLIER = {warn_mult},
                                CRITICAL_THRESHOLD_MULTIPLIER = {crit_mult},
                                UPDATED_TS = CURRENT_TIMESTAMP()
                            WHERE OBJECT_NAME = '{obj_name}'
                        """).collect()
                        st.success(f"Budget updated for {obj_name}")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error updating budget: {str(e)}")

    with tab2:
        st.markdown("#### Email Notification Configuration")
        email_df = load_email_config(session)
        if not email_df.empty:
            st.dataframe(email_df, use_container_width=True)
        else:
            st.info("No email configuration found.")

    with tab3:
        st.markdown("#### Priority Tier Definitions")
        try:
            tiers_df = session.sql(f"SELECT * FROM {SCHEMA_PREFIX}.DQ_PRIORITY_TIERS ORDER BY TIER_LEVEL").to_pandas()
            if not tiers_df.empty:
                st.dataframe(tiers_df, use_container_width=True)
            else:
                st.info("No tier definitions found.")
        except Exception:
            st.info("Unable to load priority tiers.")

    with tab4:
        st.markdown("#### Monitored Objects")
        objects_df = load_objects_monitored(session)
        if not objects_df.empty:
            st.dataframe(objects_df, use_container_width=True)
        else:
            st.info("No monitored objects found.")

        if check_permission(access_level, 'ADMIN'):
            st.markdown("---")
            st.markdown("#### Register New Object")
            with st.form("register_object"):
                new_db = st.text_input("Database", value="GSCDNA_DQ")
                new_schema = st.text_input("Schema", value="GSCDNA_DATA_GOV")
                new_table = st.text_input("Table Name")
                new_tier = st.selectbox("Priority Tier", ['P0', 'P1', 'P2', 'P3', 'P4'])
                new_email = st.text_input("Owner Email")
                submitted = st.form_submit_button("Register Object")
                if submitted and new_table:
                    try:
                        session.sql(f"""
                            INSERT INTO {SCHEMA_PREFIX}.DQ_OBJECTS_MONITORED 
                            (DATABASE_NAME, SCHEMA_NAME, TABLE_NAME, PRIORITY_TIER, OWNER_EMAIL, IS_ACTIVE)
                            VALUES ('{new_db}', '{new_schema}', '{new_table}', '{new_tier}', '{new_email}', TRUE)
                        """).collect()
                        st.success(f"Object {new_table} registered successfully!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error registering object: {str(e)}")


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    """Main application entry point"""
    try:
        session = get_snowflake_session()
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {str(e)}")
        return

    # Get access level
    current_role = get_current_role(session)
    access_level = determine_access_level(current_role)

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>GSCDNA Data Quality Observability Platform</h1>
        <p>Data Quality Cost Monitoring & Optimization Platform | AT&T GSCDNA</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("""
        <div style="padding: 0.5rem 1rem; text-align: center;">
            <div style="font-size: 2rem; font-weight: 700; color: #009FDB; letter-spacing: 2px;">AT&T (GSCDNA)</div>
            <div style="font-size: 0.75rem; color: #6B6B6B; margin-top: 2px;">Data Quality Framework</div>
        </div>
        """, unsafe_allow_html=True)
    st.sidebar.markdown("---")

    # Initialize page state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Executive Dashboard'

    # Navigation buttons
    pages = [
        "Executive Dashboard",
        "Cost Trends",
        "Cost by Priority",
        "Anomaly Detection",
        "Budget Alerts",
        "Cost vs Quality",
        "Optimization",
        "Configuration"
    ]

    for page in pages:
        if st.sidebar.button(page, key=f"nav_{page}", use_container_width=True):
            st.session_state.current_page = page
            st.rerun()

    page = st.session_state.current_page

    st.sidebar.markdown("---")
    current_theme = st.session_state.get('theme', 'light')
    theme = st.sidebar.selectbox("🎨 Theme", ["light", "dark"], index=0 if current_theme == 'light' else 1, format_func=lambda x: x.upper())
    if theme != current_theme:
        st.session_state.theme = theme
        st.rerun()

    if st.session_state.get('theme', 'light') == 'dark':
        st.markdown("""
        <style>
            [data-testid="stAppViewContainer"] {
                background: linear-gradient(135deg, #001A2C 0%, #00263A 50%, #003150 100%);
                color: #FFFFFF;
            }
            [data-testid="stHeader"] { background: transparent; }
            [data-testid="stSidebar"] { background: linear-gradient(180deg, #001A2C 0%, #00263A 100%); }
            [data-testid="stSidebar"] > div:first-child { background: transparent; }
            .stMarkdown, .stText, p, span, label { color: #FFFFFF !important; }
            h1, h2, h3, h4, h5, h6 { color: white !important; }
            .metric-card {
                background: linear-gradient(135deg, rgba(0,38,58,0.8) 0%, rgba(0,49,80,0.8) 100%) !important;
                border: 1px solid rgba(0,159,219,0.2) !important;
                border-left: 4px solid #009FDB !important;
            }
            .metric-card h3 { color: #FFFFFF !important; }
            .metric-card p { color: rgba(255,255,255,0.7) !important; }
            .info-box {
                background-color: rgba(0,159,219,0.15) !important;
                color: #FFFFFF !important;
            }
            .warning-box {
                background-color: rgba(251,140,0,0.15) !important;
                color: #FFFFFF !important;
            }
            .success-box {
                background-color: rgba(67,160,71,0.15) !important;
                color: #FFFFFF !important;
            }
            [data-testid="stDataFrame"] {
                background: rgba(0,38,58,0.5);
                border-radius: 12px;
                border: 1px solid rgba(0,159,219,0.15);
            }
            .stTabs [data-baseweb="tab-list"] {
                background: rgba(0,38,58,0.5) !important;
            }
            .stTabs [data-baseweb="tab"] {
                background: transparent !important;
                color: rgba(255,255,255,0.7) !important;
            }
        </style>
        """, unsafe_allow_html=True)

    # Sidebar User Info at bottom
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
    **👤 User Information**  
    Role: `{current_role}`  
    Access: `{access_level}`  
    Database: `GSCDNA_DQ`
    """)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Last Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Route to selected page

    if page == "Executive Dashboard":
        page_executive_dashboard(session)
    elif page == "Cost Trends":
        page_cost_trends(session)
    elif page == "Cost by Priority":
        page_cost_by_priority(session)
    elif page == "Anomaly Detection":
        page_anomaly_detection(session)
    elif page == "Budget Alerts":
        page_budget_alerts(session)
    elif page == "Cost vs Quality":
        page_cost_vs_quality(session)
    elif page == "Optimization":
        page_optimization(session)
    elif page == "Configuration":
        page_configuration(session, access_level)


if __name__ == "__main__":
    main()
