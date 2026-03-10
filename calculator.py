import requests
import pandas as pd
from datetime import datetime

class UVDoseCalculator:
    def __init__(self, api_key: str, email: str):
        # We keep these arguments so we don't have to touch your app.py,
        # but we are officially ignoring the broken NREL key!
        self.api_key = api_key
        self.email = email

    def fetch_nsrdb_data(self, lat: float, lon: float, year: int) -> pd.DataFrame:
        # Swapping to Open-Meteo's highly reliable Historical API
        url = "https://archive-api.open-meteo.com/v1/archive"
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{year}-01-01",
            "end_date": f"{year}-12-31",
            "hourly": "shortwave_radiation", # The scientific equivalent of GHI
            "timezone": "auto" # Automatically adjusts to the local time of the city!
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert the JSON data directly into our Pandas DataFrame
        df = pd.DataFrame({
            "datetime": pd.to_datetime(data["hourly"]["time"]),
            "GHI": data["hourly"]["shortwave_radiation"]
        })
        
        df.set_index('datetime', inplace=True)
        return df

    def calculate_dose(self, df: pd.DataFrame, date_str: str, start_time: str, end_time: str) -> dict:
        start_dt = pd.to_datetime(f"{date_str} {start_time}")
        end_dt = pd.to_datetime(f"{date_str} {end_time}")
        
        mask = (df.index >= start_dt) & (df.index < end_dt)
        window_df = df.loc[mask].copy()
        
        if window_df.empty:
            return {"broadband_uvr_j_m2": 0.0}

        # Open-Meteo gives data in 1-hour blocks (3600 seconds)
        # UV is roughly 6% of the total shortwave radiation (GHI)
        window_df['uv_w_m2'] = window_df['GHI'] * 0.06
        total_dose = (window_df['uv_w_m2'] * 3600).sum()
        
        return {"broadband_uvr_j_m2": round(total_dose, 2)}