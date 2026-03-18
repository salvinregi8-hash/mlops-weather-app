import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go


st.set_page_config(
    page_title="Weather Pulse | Thiruvananthapuram",
    layout="wide",
)


st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(91, 141, 239, 0.16), transparent 30%),
                radial-gradient(circle at top right, rgba(54, 179, 126, 0.12), transparent 26%),
                linear-gradient(180deg, #f5f8fc 0%, #eef3f9 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        .hero-card,
        .info-card,
        .metric-card {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(18, 52, 86, 0.08);
            border-radius: 20px;
            box-shadow: 0 18px 45px rgba(28, 51, 84, 0.08);
            backdrop-filter: blur(10px);
        }

        .hero-card {
            padding: 1.6rem 1.8rem;
            margin-bottom: 1rem;
        }

        .hero-eyebrow {
            color: #2d6cdf;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .hero-title {
            color: #18324b;
            font-size: 2.2rem;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 0.45rem;
        }

        .hero-copy {
            color: #4f6378;
            font-size: 1rem;
            line-height: 1.6;
            margin: 0;
        }

        .info-card {
            padding: 1rem 1.1rem;
            margin: 0.35rem 0 1rem 0;
        }

        .info-label {
            color: #6a7d91;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.3rem;
        }

        .info-value {
            color: #16314a;
            font-size: 1.15rem;
            font-weight: 700;
        }

        .metric-card {
            padding: 1rem 1.1rem;
            margin-top: 0.4rem;
        }

        .metric-label {
            color: #71859a;
            font-size: 0.82rem;
            margin-bottom: 0.2rem;
        }

        .metric-value {
            color: #14314b;
            font-size: 1.45rem;
            font-weight: 700;
        }

        .metric-note {
            color: #5d7083;
            font-size: 0.82rem;
            margin-top: 0.2rem;
        }

        .section-note {
            color: #53687d;
            font-size: 0.95rem;
            margin: 0.2rem 0 1rem 0;
        }

        div[data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        button[data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.72);
            border-radius: 999px;
            padding: 0.45rem 0.9rem;
            border: 1px solid rgba(22, 49, 74, 0.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


LOCATIONS = {
    "Technopark": {
        "lat": 8.5574,
        "lon": 76.8800,
        "caption": "A quick view of near-term temperature movement around the campus zone.",
    },
    "Thampanoor": {
        "lat": 8.4875,
        "lon": 76.9525,
        "caption": "A compact forecast snapshot for the city-center corridor.",
    },
}


@st.cache_data(ttl=3600)
def fetch_recent_actuals(lat, lon):
    end_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=3)).strftime("%Y-%m-%d")

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "timezone": "Asia/Kolkata",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    df = pd.DataFrame(response.json()["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


@st.cache_data(ttl=1800)
def fetch_live_forecast(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "forecast_days": 2,
        "timezone": "Asia/Kolkata",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    forecast_df = pd.DataFrame(response.json()["hourly"])
    forecast_df["time"] = pd.to_datetime(forecast_df["time"])

    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None).floor("h")
    forecast_df = forecast_df[forecast_df["time"] >= now].head(24).copy()
    return forecast_df


def make_forecast(name, lat, lon):
    try:
        df = fetch_recent_actuals(lat, lon).dropna(subset=["temperature_2m"]).copy()
        live_forecast_df = fetch_live_forecast(lat, lon).dropna(subset=["temperature_2m"]).copy()

        forecast_df = live_forecast_df.rename(
            columns={
                "temperature_2m": "temperature",
                "relative_humidity_2m": "humidity",
                "precipitation": "precipitation",
                "wind_speed_10m": "wind_speed",
            }
        )
        actuals_df = (
            df[["time", "temperature_2m"]]
            .tail(48)
            .rename(columns={"temperature_2m": "temperature"})
        )

        return forecast_df, actuals_df, df, live_forecast_df
    except Exception as exc:
        st.error(f"Forecast error for {name}: {exc}")
        return None, None, None, None


def info_card(label, value):
    st.markdown(
        f"""
        <div class="info-card">
            <div class="info-label">{label}</div>
            <div class="info-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, note):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_chart(location_name, actuals_df, forecast_df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=actuals_df["time"],
            y=actuals_df["temperature"],
            mode="lines",
            name="Observed",
            line=dict(color="#1f77b4", width=3),
            hovertemplate="%{x|%d %b, %I:%M %p}<br>%{y:.1f} deg C<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=forecast_df["time"],
            y=forecast_df["temperature"],
            mode="lines",
            name="Forecast",
            line=dict(color="#2ca58d", width=3, dash="dash"),
            hovertemplate="%{x|%d %b, %I:%M %p}<br>%{y:.1f} deg C<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"{location_name} Temperature Outlook",
        height=420,
        margin=dict(l=20, r=20, t=55, b=20),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0.45)",
        hovermode="x unified",
        xaxis_title="Time",
        yaxis_title="Temperature (deg C)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.01),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(31, 48, 68, 0.09)", zeroline=False)

    return fig


def render_tab(name, details):
    forecast_df, actuals_df, raw_df, live_forecast_df = make_forecast(
        name, details["lat"], details["lon"]
    )

    if forecast_df is None:
        st.warning("Could not generate forecast.")
        return

    latest_observed = actuals_df["temperature"].iloc[-1]
    forecast_min = forecast_df["temperature"].min()
    forecast_max = forecast_df["temperature"].max()
    latest_humidity = live_forecast_df["relative_humidity_2m"].dropna().iloc[0]
    latest_wind = live_forecast_df["wind_speed_10m"].dropna().iloc[0]
    next_rain = live_forecast_df["precipitation"].fillna(0).head(24).max()

    st.markdown(f"### {name}")
    st.markdown(
        f'<p class="section-note">{details["caption"]}</p>',
        unsafe_allow_html=True,
    )

    top_col1, top_col2, top_col3 = st.columns(3)
    with top_col1:
        info_card("Latest observed", f"{latest_observed:.1f} deg C")
    with top_col2:
        info_card("Humidity", f"{latest_humidity:.0f}%")
    with top_col3:
        info_card("Wind speed", f"{latest_wind:.1f} km/h")

    st.caption("Forecast uses Open-Meteo live weather data for the next 24 hours.")

    st.plotly_chart(
        build_chart(name, actuals_df, forecast_df),
        use_container_width=True,
    )

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        metric_card("Next 24h low", f"{forecast_min:.1f} deg C", "Lowest predicted value")
    with metric_col2:
        metric_card("Next 24h high", f"{forecast_max:.1f} deg C", "Warmest predicted hour")
    with metric_col3:
        metric_card("Rain chance signal", f"{next_rain:.1f} mm", "Peak hourly precipitation")


st.markdown(
    """
    <div class="hero-card">
        <div class="hero-eyebrow">Weather Dashboard</div>
        <div class="hero-title">Simple local forecasts for Thiruvananthapuram</div>
        <p class="hero-copy">
            Compare the latest observed temperatures with a short-term outlook for two key
            locations. The layout stays minimal, but the presentation is cleaner, calmer,
            and easier to scan.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

summary_col1, summary_col2, summary_col3 = st.columns(3)
with summary_col1:
    info_card("Coverage", "2 city locations")
with summary_col2:
    info_card("Observed window", "Last 48 hours")
with summary_col3:
    info_card("Forecast horizon", "Next 24 hours")

tab1, tab2 = st.tabs(list(LOCATIONS.keys()))

with tab1:
    render_tab("Technopark", LOCATIONS["Technopark"])

with tab2:
    render_tab("Thampanoor", LOCATIONS["Thampanoor"])
