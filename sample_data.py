"""
Generate sample historical data for testing
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_sample_data(start_date, end_date, output_file='data/historical_prices.csv'):
    """Generate random price data for testing"""
    
    # Create data directory
    import os
    os.makedirs('data', exist_ok=True)
    
    # Generate timestamps (every 1 minute)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    timestamps = pd.date_range(start, end, freq='1min')
    
    assets = ['BTC', 'ETH', 'SOL', 'XRP']
    
    data = []
    
    # Generate random walk prices for each asset
    for asset in assets:
        price = 0.5  # Start at 50%
        
        for ts in timestamps:
            # Random walk
            change = np.random.normal(0, 0.02)  # Small random changes
            price = max(0.0, min(1.0, price + change))  # Keep in [0, 1]
            
            data.append({
                'timestamp': ts,
                'asset': asset,
                'price': round(price, 4)
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    df = df.sort_values('timestamp')
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"✅ Generated {len(df)} price records")
    print(f"📁 Saved to: {output_file}")
    print(f"📊 Assets: {', '.join(assets)}")
    print(f"📅 Date range: {start_date} to {end_date}")


if __name__ == "__main__":
    generate_sample_data('2024-09-01', '2024-12-01')