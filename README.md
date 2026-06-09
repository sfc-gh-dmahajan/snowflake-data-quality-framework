##GSCDNA Data Quality Observability Framework

End-to-end Snowflake-native framework for monitoring the cost, health, and operational efficiency of Data Metric Function (DMF) based data quality checks across AT&T GSCDNA data assets.

The project includes a Snowflake setup worksheet, a Streamlit-in-Snowflake observability application, and detailed HTML documentation. The framework creates a governed data model for monitored objects, daily cost history, budget thresholds, anomaly records, alert history, execution quality results, email routing, cost forecasts, and optimization recommendations.

## Contents

- [What This Project Covers](#what-this-project-covers)
- [Repository Contents](#repository-contents)
- [Architecture](#architecture)
- [Snowflake Objects Created](#snowflake-objects-created)
- [Prerequisites](#prerequisites)
- [Deployment Guide](#deployment-guide)
- [Using the Streamlit App](#using-the-streamlit-app)
- [Security and RBAC](#security-and-rbac)
- [Cost, Budget, and Forecast Logic](#cost-budget-and-forecast-logic)
- [Alerting and Notifications](#alerting-and-notifications)
- [Operations](#operations)
- [Verification Queries](#verification-queries)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

## What This Project Covers

The framework is designed to answer these operational questions:

- Which GSCDNA data quality checks are generating the most Snowflake cost?
- Which monitored objects are exceeding budget thresholds?
- Are cost spikes statistically anomalous compared with recent history?
- Which objects provide high quality outcomes for low cost?
- Which checks should be optimized, reduced in frequency, or investigated?
- Which alerts were generated, and were notification emails sent?
- What is the projected monthly DQ monitoring spend?

Key capabilities:

- Snowflake-native setup using SQL tables, views, procedures, tasks, and notification integration.
- Streamlit-in-Snowflake dashboard with 8 pages for leadership, operators, and administrators.
- Role-based access control with viewer, operator, and administrator personas.
- Cost trend, priority tier, budget, anomaly, alert, cost-vs-quality, and optimization views.
- Scheduled cost refresh, anomaly detection, budget checks, and daily summary workflows.
- Email alert routing through a Snowflake notification integration.
- Synthetic sample data for immediate demo readiness, with a refresh procedure for live account usage data.

## Repository Contents

| File | Purpose |
| --- | --- |
| `ATT_GSCDNA_worksheet.sql` | Main Snowflake deployment worksheet. Creates the database, schema, RBAC roles, framework tables, sample data, analytical views, procedures, scheduled tasks, email notification integration, and verification queries. |
| `streamlit_gscdna_dmf_app.py` | Streamlit-in-Snowflake application for interactive cost observability and optimization. Uses Snowpark `get_active_session()`, Plotly charts, cached data loaders, and role-aware controls. |
| `GSCDNA_DQ_Documentation.html` | Standalone HTML documentation with architecture, schema, security model, dashboard details, deployment steps, operations, and troubleshooting. |
| `README.md` | Git-friendly end-to-end project documentation. |

## Architecture

The solution follows a layered Snowflake-native architecture. Snowflake usage and DQ execution data is transformed into curated monitoring tables, exposed through analytical views, automated with stored procedures and tasks, and visualized in Streamlit-in-Snowflake.

```text
Snowflake Account Usage / DMF Activity
              |
              v
  PROC_REFRESH_COST_DATA and sample framework data
              |
              v
GSCDNA_DQ.GSCDNA_DATA_GOV core monitoring tables
              |
              v
Analytical views for KPIs, trends, anomalies, quality, and optimization
              |
              +------------------------------+
              |                              |
              v                              v
Scheduled procedures and tasks       Streamlit-in-Snowflake app
              |                              |
              v                              v
Budget/anomaly alerts and emails     Executive and operational dashboards
```

### Logical Layers

| Layer | Components | Responsibility |
| --- | --- | --- |
| Source and collection | Snowflake account usage views, DMF execution records, sample seed data | Provide raw cost and execution signals. |
| Core data model | `DQ_OBJECTS_MONITORED`, `DQ_COST_DAILY_LOG`, `DQ_EXECUTION_RESULTS`, config and alert tables | Store monitored assets, cost history, execution quality, budgets, routing, and alerts. |
| Analytics | `VW_DQ_COST_*` views | Produce dashboard-ready KPI, trend, priority, anomaly, cost-quality, and recommendation datasets. |
| Automation | Stored procedures and scheduled tasks | Refresh cost data, detect anomalies, check budgets, generate summaries, and update forecasts. |
| Presentation | `streamlit_gscdna_dmf_app.py` | Interactive dashboard, RBAC-aware configuration, charts, tables, and refresh controls. |
| Notification | `GSCDNA_DQ_EMAIL_INTEGRATION`, `DQ_EMAIL_NOTIFICATION_CONFIG` | Send routed email alerts for configured recipients and alert levels. |

## Snowflake Objects Created

The SQL worksheet deploys all framework objects into:

- Database: `GSCDNA_DQ`
- Schema: `GSCDNA_DATA_GOV`
- Default warehouse in examples/tasks: `CORTEX_WH`

### Core Tables

| Table | Purpose |
| --- | --- |
| `DQ_OBJECTS_MONITORED` | Registry of database/schema/table objects under DQ monitoring, including priority tier, owner email, and active flag. |
| `DQ_PRIORITY_TIERS` | Tier definitions from `P0_CRITICAL` through lower-priority tiers, including daily budget guidance and threshold multipliers. |
| `DQ_COST_DAILY_LOG` | Daily cost records per monitored object, including credits used, estimated USD cost, DMF executions, and errors found. |
| `DQ_COST_BUDGET_CONFIG` | Per-object budget configuration with warning and critical multipliers. |
| `DQ_COST_ANOMALY_LOG` | Persisted anomaly records with expected cost, actual cost, standard deviation deviation, severity, resolution state, and timestamps. |
| `DQ_COST_ALERTS_HISTORY` | Alert audit history across budget, anomaly, and summary notifications. |
| `DQ_EXECUTION_RESULTS` | DQ execution metrics and pass/fail outcomes for monitored objects. |
| `DQ_EMAIL_NOTIFICATION_CONFIG` | Email routing rules by config name, object, recipient list, alert level filter, and active flag. |
| `DQ_COST_FORECAST` | Monthly cost and credit projections. |
| `DQ_DMF_CONFIG` | DMF assignment metadata, including DMF key, object name, tag name, DMF type, active flag, and schedule. |

### Analytical Views

| View | Purpose |
| --- | --- |
| `VW_DQ_COST_EXECUTIVE_SUMMARY` | High-level KPI rollup for the executive dashboard. |
| `VW_DQ_COST_TRENDS` | 30-day daily cost trend with day-over-day comparisons. |
| `VW_DQ_COST_BY_PRIORITY` | Cost and object breakdown by priority tier. |
| `VW_DQ_COST_ANOMALIES` | Statistical anomaly detection using recent rolling cost history. |
| `VW_DQ_COST_VS_QUALITY` | Cost-quality correlation by object, pass rate, execution volume, and cost efficiency. |
| `VW_DQ_COST_OPTIMIZATION` | Optimization recommendations based on cost, variability, pass rate, and utilization patterns. |

### Stored Procedures

| Procedure | Purpose |
| --- | --- |
| `PROC_CHECK_COST_ANOMALIES()` | Detects statistical cost anomalies and records warning or critical anomaly events. |
| `PROC_SEND_COST_ALERT_EMAIL(...)` | Sends formatted alert emails through the configured Snowflake notification integration. |
| `PROC_DAILY_COST_SUMMARY()` | Generates daily summary alert records and summary email content. |
| `PROC_CHECK_BUDGET_ALERTS()` | Compares daily object cost with configured budget thresholds and records alerts. |
| `PROC_REFRESH_COST_DATA()` | Refreshes cost data from usage sources and updates forecast projections. |

### Scheduled Tasks

| Task | Schedule | Purpose |
| --- | --- | --- |
| `TASK_DAILY_COST_CHECK` | `USING CRON 0 9 * * * America/New_York` | Runs daily anomaly detection at 9 AM ET. |
| `TASK_DAILY_SUMMARY_EMAIL` | `USING CRON 0 10 * * * America/New_York` | Sends daily cost summary at 10 AM ET. |
| `TASK_BUDGET_ALERT_CHECK` | `60 MINUTE` | Checks budget thresholds hourly. |
| `TASK_WEEKLY_COST_ANALYSIS` | `USING CRON 0 8 * * 1 America/New_York` | Refreshes cost data and forecast weekly on Monday at 8 AM ET. |

### Notification Integration

The worksheet creates `GSCDNA_DQ_EMAIL_INTEGRATION` for email notifications. Update the `ALLOWED_RECIPIENTS` list before using this in a customer or production environment.

## Prerequisites

### Snowflake Privileges

The setup worksheet switches roles by section. Execute each section with the role indicated in the comments:

- `SYSADMIN` for database, schema, tables, views, procedures, and tasks.
- `SECURITYADMIN` for creating and granting framework roles.
- `ACCOUNTADMIN` for account-level grants and notification integration creation.
- `EXECUTE TASK` account privilege granted to the task owner role.

### Warehouse

The worksheet and documentation use `CORTEX_WH`. If you use a different warehouse, update these locations:

- Warehouse grants in the RBAC section.
- Task definitions in Section 6.
- Streamlit app creation/deployment settings.

### Streamlit-in-Snowflake Runtime

The app is designed for Streamlit-in-Snowflake and uses:

- `streamlit`
- `pandas`
- `snowflake.snowpark.context.get_active_session`
- `snowflake.snowpark.exceptions.SnowparkSQLException`
- `plotly.express`
- `plotly.graph_objects`

Because the app uses `get_active_session()`, it expects to run inside Snowflake's Streamlit runtime or another environment that provides an active Snowpark session.

## Deployment Guide

### Step 1: Review and Customize the SQL Worksheet

Before execution, review `ATT_GSCDNA_worksheet.sql` and update environment-specific values:

- Warehouse name, if not using `CORTEX_WH`.
- Notification integration recipients in `ALLOWED_RECIPIENTS`.
- Seeded owner email addresses and routing rules.
- Credit-to-USD conversion rate if your pricing model differs.
- Task schedules if operational windows differ.

The worksheet contains DDL, DML, grants, task resumes, and notification integration creation. Run it only in an approved Snowflake environment.

### Step 2: Execute SQL Framework Sections

In Snowsight:

1. Open a SQL worksheet.
2. Paste or open `ATT_GSCDNA_worksheet.sql`.
3. Execute sections in order:

| Section | Description | Typical role |
| --- | --- | --- |
| 1 | Database and schema setup | `SYSADMIN` |
| 2 | Security roles and grants | `SECURITYADMIN`, `ACCOUNTADMIN`, `SYSADMIN` |
| 3 | Tables and sample data | `SYSADMIN` |
| 4 | Dashboard views | `SYSADMIN` |
| 5 | Stored procedures | `SYSADMIN` |
| 6 | Scheduled tasks | `SYSADMIN` with task execution privilege |
| 7 | Notification integration | `ACCOUNTADMIN` |
| 8 | Verification queries | Any sufficiently privileged validation role |

### Step 3: Deploy the Streamlit App

In Snowsight:

1. Navigate to Streamlit.
2. Create a new Streamlit app.
3. Use the following settings:

| Setting | Value |
| --- | --- |
| App name | `GSCDNA_DQ_Cost_Monitor` or your preferred name |
| Warehouse | `CORTEX_WH` or your configured warehouse |
| Database | `GSCDNA_DQ` |
| Schema | `GSCDNA_DATA_GOV` |

4. Replace the default Streamlit code with `streamlit_gscdna_dmf_app.py`.
5. Run the app.

### Step 4: Grant User Access

Assign users to the appropriate framework role:

```sql
GRANT ROLE DQ_VIEWER_ROLE TO USER <username>;
GRANT ROLE DQ_OPERATOR_ROLE TO USER <username>;
GRANT ROLE DQ_ADMIN_ROLE TO USER <username>;
```

## Using the Streamlit App

The Streamlit app provides an 8-page operational dashboard. It uses `GSCDNA_DQ.GSCDNA_DATA_GOV` as the fully qualified schema prefix and reads from the framework tables and views.

### App Behavior

- Connection: Snowpark active session via `get_active_session()`.
- Layout: wide page layout with sidebar navigation.
- Branding: AT&T GSCDNA blue theme with light/dark mode support.
- Charts: Plotly Express and Plotly Graph Objects.
- Caching: `@st.cache_data(ttl=300)` on data loaders, giving a 5-minute cache TTL.
- Refresh: sidebar refresh button clears Streamlit cached data and reruns the app.
- Access display: sidebar shows current Snowflake role and resolved access level.

### Dashboard Pages

| Page | Audience | What it shows |
| --- | --- | --- |
| Executive Dashboard | Leadership and program owners | Total 30-day cost, budget utilization, active anomalies, monitored objects, health score, 7-day trend, and quick stats. |
| Cost Trends | Operators and FinOps | Daily cost trend, day-over-day changes, and top costliest objects. |
| Cost by Priority | Data owners and governance teams | Cost distribution by P0-P4 priority tiers and object counts per tier. |
| Anomaly Detection | Operators | Active and resolved anomalies, critical counts, anomaly cards, severity distribution, and anomaly timeline. |
| Budget Alerts | Operators and owners | Active budget alerts, object-level budget utilization, and alert history. |
| Cost vs Quality | Quality engineering and platform owners | Cost vs pass-rate analysis, cost per execution, quality per credit, and performance quadrant summaries. |
| Optimization | Platform and DQ owners | Recommendations such as reducing frequency, investigating variability, or keeping optimal configurations. |
| Configuration | Administrators | Budget thresholds, email routes, priority tiers, monitored object registry, and admin actions. |

### Access Levels in the App

The app maps roles to access levels:

| Snowflake role | App access level |
| --- | --- |
| `DQ_VIEWER_ROLE` | `VIEWER` |
| `DQ_OPERATOR_ROLE` | `OPERATOR` |
| `DQ_ADMIN_ROLE` | `ADMIN` |
| `SYSADMIN` | `ADMIN` |
| `ACCOUNTADMIN` | `ADMIN` |
| Unknown or missing role | `VIEWER` |

## Security and RBAC

The security model is hierarchical:

```text
DQ_ADMIN_ROLE
      |
      v
DQ_OPERATOR_ROLE
      |
      v
DQ_VIEWER_ROLE
```

### Role Responsibilities

| Role | Permissions and intended use |
| --- | --- |
| `DQ_VIEWER_ROLE` | Read-only access to framework tables and views. Intended for dashboard consumers. |
| `DQ_OPERATOR_ROLE` | Viewer privileges plus table DML and procedure usage. Intended for operational teams managing alerts and workflow state. |
| `DQ_ADMIN_ROLE` | Full schema privileges and inherited operator/viewer permissions. Intended for framework administrators. |

The worksheet grants future table, view, and procedure privileges so new framework objects remain accessible to the expected roles.

## Cost, Budget, and Forecast Logic

### Credit-to-USD Conversion

The framework uses a configurable credit-to-USD conversion in cost refresh logic:

```text
ESTIMATED_COST_USD = CREDITS_USED * 0.00056
```

Update this constant in `PROC_REFRESH_COST_DATA()` if your actual contract or internal showback rate differs.

### Budget Thresholds

Budget alerts are calculated from each object's configured daily budget and multipliers:

```text
WARNING  = actual_cost >= daily_budget * warning_multiplier
CRITICAL = actual_cost >= daily_budget * critical_multiplier
```

Default examples use warning at 2.0x and critical at 3.0x, but each object can have its own values in `DQ_COST_BUDGET_CONFIG`.

### Anomaly Detection

The anomaly view compares daily object cost against recent history. The HTML documentation describes a 7-day rolling lookback with warning and critical severity based on standard deviation thresholds:

- Warning: cost is at least 2.0 standard deviations above the rolling baseline.
- Critical: cost is at least 3.0 standard deviations above the rolling baseline.
- Current day is excluded from the baseline window.

### Forecast Model

The forecast procedure uses a simple next-month projection:

```text
Next month credits = current month credits * 1.05
Next month cost    = current month cost * 1.05
Growth rate        = 5%
```

Use this as a baseline model and replace it with a more sophisticated forecast if production planning requires seasonality or workload-specific behavior.

## Alerting and Notifications

Alerting uses two layers:

- Alert generation tables and procedures in `GSCDNA_DQ.GSCDNA_DATA_GOV`.
- Snowflake email notification integration `GSCDNA_DQ_EMAIL_INTEGRATION`.

Alert types include:

- Budget warning or critical alerts.
- Cost anomaly warning or critical alerts.
- Daily summary records.

Email routing is controlled by `DQ_EMAIL_NOTIFICATION_CONFIG`. Each rule defines a config name, object, recipient list, alert level filter, and active flag. Recipients must also be allowed in the Snowflake notification integration.

## Operations

### Refresh Cost Data Manually

```sql
CALL GSCDNA_DQ.GSCDNA_DATA_GOV.PROC_REFRESH_COST_DATA();
```

### Run Anomaly Detection Manually

```sql
CALL GSCDNA_DQ.GSCDNA_DATA_GOV.PROC_CHECK_COST_ANOMALIES();
```

### Run Budget Checks Manually

```sql
CALL GSCDNA_DQ.GSCDNA_DATA_GOV.PROC_CHECK_BUDGET_ALERTS();
```

### Check Task Status

```sql
SHOW TASKS IN SCHEMA GSCDNA_DQ.GSCDNA_DATA_GOV;
```

### Resume Tasks

```sql
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_DAILY_COST_CHECK RESUME;
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_DAILY_SUMMARY_EMAIL RESUME;
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_BUDGET_ALERT_CHECK RESUME;
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_WEEKLY_COST_ANALYSIS RESUME;
```

### Suspend Tasks

```sql
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_DAILY_COST_CHECK SUSPEND;
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_DAILY_SUMMARY_EMAIL SUSPEND;
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_BUDGET_ALERT_CHECK SUSPEND;
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_WEEKLY_COST_ANALYSIS SUSPEND;
```

## Verification Queries

After deployment, validate the framework with the read-only verification queries from Section 8 of the worksheet.

```sql
-- Verify base tables
SELECT TABLE_NAME, ROW_COUNT, BYTES, CREATED
FROM GSCDNA_DQ.INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'GSCDNA_DATA_GOV'
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;

-- Verify views
SELECT TABLE_NAME, CREATED
FROM GSCDNA_DQ.INFORMATION_SCHEMA.VIEWS
WHERE TABLE_SCHEMA = 'GSCDNA_DATA_GOV'
ORDER BY TABLE_NAME;

-- Verify procedures
SELECT PROCEDURE_NAME, CREATED
FROM GSCDNA_DQ.INFORMATION_SCHEMA.PROCEDURES
WHERE PROCEDURE_SCHEMA = 'GSCDNA_DATA_GOV'
ORDER BY PROCEDURE_NAME;

-- Verify scheduled tasks
SHOW TASKS IN SCHEMA GSCDNA_DQ.GSCDNA_DATA_GOV;

-- Smoke test dashboard datasets
SELECT * FROM GSCDNA_DQ.GSCDNA_DATA_GOV.VW_DQ_COST_EXECUTIVE_SUMMARY;
SELECT * FROM GSCDNA_DQ.GSCDNA_DATA_GOV.VW_DQ_COST_TRENDS ORDER BY LOG_DATE DESC LIMIT 7;
SELECT * FROM GSCDNA_DQ.GSCDNA_DATA_GOV.VW_DQ_COST_BY_PRIORITY;
SELECT * FROM GSCDNA_DQ.GSCDNA_DATA_GOV.VW_DQ_COST_ANOMALIES WHERE IS_ANOMALY = TRUE LIMIT 10;
SELECT * FROM GSCDNA_DQ.GSCDNA_DATA_GOV.VW_DQ_COST_VS_QUALITY;
SELECT * FROM GSCDNA_DQ.GSCDNA_DATA_GOV.VW_DQ_COST_OPTIMIZATION;
```

## Customization

### Add a New Monitored Object

Option 1: Use the Streamlit Configuration page as an admin.

Option 2: Insert directly into the registry table:

```sql
INSERT INTO GSCDNA_DQ.GSCDNA_DATA_GOV.DQ_OBJECTS_MONITORED
    (DATABASE_NAME, SCHEMA_NAME, TABLE_NAME, PRIORITY_TIER, OWNER_EMAIL, IS_ACTIVE)
VALUES
    ('GSCDNA_DQ', 'GSCDNA_DATA_GOV', 'NEW_TABLE_NAME', 'P2', 'owner@company.com', TRUE);
```

### Add or Update a Budget

```sql
UPDATE GSCDNA_DQ.GSCDNA_DATA_GOV.DQ_COST_BUDGET_CONFIG
SET DAILY_BUDGET_USD = 20.0000,
    WARNING_THRESHOLD_MULTIPLIER = 1.5,
    CRITICAL_THRESHOLD_MULTIPLIER = 2.5,
    UPDATED_TS = CURRENT_TIMESTAMP()
WHERE OBJECT_NAME = 'GSCDNA_BILLING_DETAIL';
```

### Add Email Routing

```sql
INSERT INTO GSCDNA_DQ.GSCDNA_DATA_GOV.DQ_EMAIL_NOTIFICATION_CONFIG
    (CONFIG_NAME, OBJECT_NAME, EMAIL_RECIPIENTS, ALERT_LEVEL_FILTER, IS_ACTIVE)
VALUES
    ('NEW_TEAM_ALERTS', 'GSCDNA_CDR_RECORDS', 'team@company.com', 'WARNING', TRUE);
```

Also add the recipient to `GSCDNA_DQ_EMAIL_INTEGRATION.ALLOWED_RECIPIENTS` and ensure the recipient has verified their email in Snowflake.

### Add a Custom DMF Configuration

```sql
INSERT INTO GSCDNA_DQ.GSCDNA_DATA_GOV.DQ_DMF_CONFIG
    (DMF_KEY, OBJECT_NAME, TAG_NAME, DMF_TYPE, SCHEDULE)
VALUES
    ('CUSTOM_KEY', 'TABLE_NAME', NULL, 'CUSTOM_SQL', '180 MINUTE');
```

The cost is picked up by `PROC_REFRESH_COST_DATA()` on the next refresh, assuming the underlying Snowflake usage data contains the relevant records.

### Change Task Schedules

```sql
ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_DAILY_COST_CHECK
SET SCHEDULE = 'USING CRON 0 8 * * * America/New_York';

ALTER TASK GSCDNA_DQ.GSCDNA_DATA_GOV.TASK_BUDGET_ALERT_CHECK
SET SCHEDULE = '120 MINUTE';
```

### Use a Different Warehouse

Replace `CORTEX_WH` in:

- RBAC warehouse grants.
- Scheduled task definitions.
- Streamlit app warehouse configuration.

## Troubleshooting

### Dashboard Shows No Data

Check these items:

- Section 3 of `ATT_GSCDNA_worksheet.sql` ran successfully and inserted sample data.
- Your active role has `SELECT` access through `DQ_VIEWER_ROLE` or higher.
- The app points to `GSCDNA_DQ.GSCDNA_DATA_GOV`.
- The analytical views return rows when queried directly.
- Streamlit cache is not stale; use the sidebar refresh button.

### Emails Are Not Sent

Check these items:

- `SHOW INTEGRATIONS LIKE 'GSCDNA_DQ_EMAIL%';`
- Recipient emails are listed in `ALLOWED_RECIPIENTS`.
- Recipients have confirmed their email in Snowflake.
- `DQ_EMAIL_NOTIFICATION_CONFIG.IS_ACTIVE = TRUE` for the relevant route.
- The relevant procedure inserts alert rows and attempts email delivery.

### Tasks Are Not Running

Check these items:

- `SHOW TASKS IN SCHEMA GSCDNA_DQ.GSCDNA_DATA_GOV;`
- Tasks are resumed, not suspended.
- The owning role has `EXECUTE TASK` on the account.
- The task warehouse exists and the task owner has warehouse usage.
- Task schedules match your intended timezone and interval.

### Cost Data Looks Wrong or Stays at Zero

Check these items:

- Sample data is synthetic and intended for initial dashboard validation.
- Run `PROC_REFRESH_COST_DATA()` to load live usage-based values.
- Confirm DMFs are running on the monitored objects.
- Confirm Snowflake account usage views contain relevant DMF monitoring records.
- Account usage views can have latency, so recent activity may not appear immediately.
- Confirm the credit-to-USD conversion rate matches your pricing assumptions.

### App Permission Issues

Check these items:

- The current Snowflake role appears in the app sidebar.
- The current role maps to the intended app access level.
- The Streamlit app owner and viewer roles have usage on the database, schema, warehouse, tables, views, and procedures required by the app.
- Admin-only configuration actions require `DQ_ADMIN_ROLE`, `SYSADMIN`, or `ACCOUNTADMIN`.

## Production Readiness Checklist

- Replace sample email addresses and seeded recipients with approved distribution lists.
- Confirm notification integration recipients are approved and verified.
- Confirm task schedules align with operational windows and warehouse availability.
- Replace or validate the credit-to-USD conversion rate.
- Review all sample data and remove demo-only records if needed.
- Assign framework roles to named users or enterprise roles through the standard access process.
- Validate that all dashboard views return expected data volumes.
- Confirm budget thresholds and priority tiers with data owners.
- Confirm Streamlit app deployment database, schema, and warehouse match the SQL framework deployment.

## Ownership

- Framework: AT&T GSCDNA Data Quality Cost Monitoring
- Version: 1.0
- Platform: Snowflake Native Features and Streamlit-in-Snowflake
- Default database/schema: `GSCDNA_DQ.GSCDNA_DATA_GOV`
