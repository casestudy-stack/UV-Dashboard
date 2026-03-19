import requests
import pandas as pd
from datetime import datetime

class UVDoseCalculator:
    def __init__(self, api_key: str = None, email: str = None):
        # We keep these arguments so app.py doesn't break, but we no longer need an API key!
        pass

    def fetch_nsrdb_data(self, lat: float, lon: float, year: int) -> pd.DataFrame:
        # We fetch a solid, recent year of NASA Satellite Telemetry (2023) as our "Clinical Baseline".
        # This makes it infinitely dynamic for future dates, bypassing NREL entirely.
        
        url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN", # The NASA scientific code for GHI (W/m^2)
            "community": "RE", # Renewable Energy baseline
            "longitude": lon,
            "latitude": lat,
            "start": "20230101",
            "end": "20231231",
            "format": "JSON",
            "time-standard": "LST" # Local Solar Time aligns perfectly with sun exposure
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status() 

        data = response.json()
        
        # Extract the hourly data from the NASA JSON envelope
        hourly_data = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        
        # Convert directly to a Pandas DataFrame
        df = pd.DataFrame(list(hourly_data.items()), columns=['timestamp', 'GHI'])
        
        # Clean the data (NASA uses -999 for missing values, we reset them to 0)
        df.loc[df['GHI'] < 0, 'GHI'] = 0.0
        
        # Parse the timestamp (NASA Format: YYYYMMDDHH)
        df['datetime'] = pd.to_datetime(df['timestamp'], format="%Y%m%d%H")
        df['Month'] = df['datetime'].dt.month
        df['Day'] = df['datetime'].dt.day
        df['Hour'] = df['datetime'].dt.hour
        df['Minute'] = 0 
        
        return df

    def calculate_dose(self, df: pd.DataFrame, date_str: str, start_time: str, end_time: str) -> dict:
        target_date = pd.to_datetime(date_str)
        target_month = target_date.month
        target_day = target_date.day
        
        start_hour = int(start_time.split(':')[0])
        end_hour = int(end_time.split(':')[0])
        
        # DYNAMIC FILTER: Match the Month, Day, and Time exactly from the NASA baseline.
        mask = (
            (df['Month'] == target_month) & 
            (df['Day'] == target_day) &
            (df['Hour'] >= start_hour) &
            (df['Hour'] < end_hour)
        )
        
        window_df = df.loc[mask].copy()
        
        if if window_df.empty:
            return {
                "broadband_uvr_j_m2": 0.0,
                "avg_ghi_w_m2": 0.0,
                "peak_uv_w_m2": 0.0
            }

        # The Speedometer (Rate in W/m^2)
        # We grab the raw GHI average so you can compare it directly to the NASA CSV!
        avg_ghi = window_df['GHI'].mean()
        
        # Calculate UV Irradiance (6% of GHI)
        window_df['uv_w_m2'] = window_df['GHI'] * 0.06
        peak_uv = window_df['uv_w_m2'].max()

        # The Odometer (Total Dose in J/m^2)
        # 3600 seconds in an hour
        total_dose = (window_df['uv_w_m2'] * 3600).sum()
        
        return {
            "broadband_uvr_j_m2": round(total_dose, 2),
            "avg_ghi_w_m2": round(avg_ghi, 2),
            "peak_uv_w_m2": round(peak_uv, 2)
        }

        # Calculate clinical dose. UV is roughly 6% of the total shortwave radiation (GHI).
        # Interval is 3600 seconds for NASA's hourly data.
        window_df['uv_w_m2'] = window_df['GHI'] * 0.06
        total_dose = (window_df['uv_w_m2'] * 3600).sum()
        
        return {"broadband_uvr_j_m2": round(total_dose, 2)}
