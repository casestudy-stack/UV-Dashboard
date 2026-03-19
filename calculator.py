import io
import requests
import pandas as pd
from datetime import datetime

class UVDoseCalculator:
    def __init__(self, api_key: str, email: str):
        self.api_key = api_key
        self.email = email
        self.session = requests.Session()

    def fetch_nsrdb_data(self, lat: float, lon: float, year: int) -> pd.DataFrame:
        # We put the API key in the URL, but securely package everything else.
        # We are using the TMY endpoint so it never crashes on future/missing years.
        url = f"https://developer.nrel.gov/api/nsrdb/v2/solar/psm3-tmy-download.csv?api_key={self.api_key}"
        
        # The "POST Payload Envelope"
        payload = {
            'email': self.email,
            'wkt': f'POINT({lon} {lat})',
            'names': 'tmy', 
            'leap_day': 'false',
            'interval': '60',
            'utc': 'false',
            'attributes': 'ghi'
        }

        # Notice we are using .post() instead of .get() here!
        response = self.session.post(url, data=payload)
        
        # If the government server complains, this will print the exact reason to your Render logs
        if response.status_code != 200:
            print(f"NREL API Error: {response.text}")
            
        response.raise_for_status() 

        # Parse the CSV data directly into a Pandas DataFrame
        csv_data = "\n".join(response.text.split('\n')[2:])
        df = pd.read_csv(io.StringIO(csv_data))
        
        return df

    def calculate_dose(self, df: pd.DataFrame, date_str: str, start_time: str, end_time: str) -> dict:
        target_date = pd.to_datetime(date_str)
        target_month = target_date.month
        target_day = target_date.day
        
        start_hour = int(start_time.split(':')[0])
        start_minute = int(start_time.split(':')[1])
        end_hour = int(end_time.split(':')[0])
        end_minute = int(end_time.split(':')[1])
        
        # DYNAMIC FILTER: We match the Month, Day, and Time exactly from the TMY baseline.
        mask = (
            (df['Month'] == target_month) & 
            (df['Day'] == target_day) &
            (
                (df['Hour'] > start_hour) | 
                ((df['Hour'] == start_hour) & (df['Minute'] >= start_minute))
            ) &
            (
                (df['Hour'] < end_hour) | 
                ((df['Hour'] == end_hour) & (df['Minute'] <= end_minute))
            )
        )
        
        window_df = df.loc[mask].copy()
        
        if window_df.empty:
            return {"broadband_uvr_j_m2": 0.0}

        # Calculate clinical dose. GHI -> UV is roughly 6%. 
        # Interval is 3600 seconds for hourly TMY data.
        window_df['uv_w_m2'] = window_df['GHI'] * 0.06
        total_dose = (window_df['uv_w_m2'] * 3600).sum()
        
        return {"broadband_uvr_j_m2": round(total_dose, 2)}
