import requests
import pandas as pd
from datetime import datetime

class UVDoseCalculator:
    def __init__(self, api_key: str = None, email: str = None):
        # We keep these so app.py doesn't crash, but no API key needed for NASA!
        pass

    def fetch_nsrdb_data(self, lat: float, lon: float, year: int) -> pd.DataFrame:
        # NASA POWER API - The Clinical Baseline
        url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN", 
            "community": "RE", 
            "longitude": lon,
            "latitude": lat,
            "start": "20230101",
            "end": "20231231",
            "format": "JSON",
            "time-standard": "LST" 
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status() 

        data = response.json()
        hourly_data = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        
        df = pd.DataFrame(list(hourly_data.items()), columns=['timestamp', 'GHI'])
        df.loc[df['GHI'] < 0, 'GHI'] = 0.0
        
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
        
        # DYNAMIC FILTER
        mask = (
            (df['Month'] == target_month) & 
            (df['Day'] == target_day) &
            (df['Hour'] >= start_hour) &
            (df['Hour'] < end_hour)
        )
        
        window_df = df.loc[mask].copy()
        
        if window_df.empty:
            return {
                "broadband_uvr_j_m2": 0.0,
                "avg_ghi_w_m2": 0.0,
                "peak_uv_w_m2": 0.0
            }

        # The Speedometer (Rate in W/m^2)
        avg_ghi = window_df['GHI'].mean()
        
        window_df['uv_w_m2'] = window_df['GHI'] * 0.06
        peak_uv = window_df['uv_w_m2'].max()

        # The Odometer (Total Dose in J/m^2)
        total_dose = (window_df['uv_w_m2'] * 3600).sum()
        
        return {
            "broadband_uvr_j_m2": round(total_dose, 2),
            "avg_ghi_w_m2": round(avg_ghi, 2),
            "peak_uv_w_m2": round(peak_uv, 2)
        }
