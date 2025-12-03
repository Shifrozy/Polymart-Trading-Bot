"""
Generate sample historical data for backtesting
Creates realistic 15-minute price data with signals
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


def generate_sample_data(start_date: str, end_date: str, output_dir: str = 'data'):
    """Generate sample historical price data"""
    
    print(f"Generating sample data: {start_date} to {end_date}")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamps (every 1 minute)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    timestamps = pd.date_range(start, end, freq='1min')
    
    assets = ['BTC', 'ETH', 'SOL', 'XRP']
    
    data = []
    
    # Generate correlated random walk prices
    np.random.seed(42)
    
    for asset in assets:
        price = 0.5  # Start at 50%
        
        for i, ts in enumerate(timestamps):
            # Add correlation - assets tend to move together
            if i > 0 and i % 30 == 0:
                # Create occasional signal scenarios
                scenario = np.random.choice(['up_signal', 'down_signal', 'neutral'], p=[0.15, 0.15, 0.7])
                
                if scenario == 'up_signal' and asset in ['BTC', 'ETH', 'SOL']:
                    # Group high
                    price = np.random.uniform(0.75, 0.95)
                elif scenario == 'up_signal' and asset == 'XRP':
                    # Laggard low
                    price = np.random.uniform(0.10, 0.45)
                elif scenario == 'down_signal' and asset in ['BTC', 'ETH', 'XRP']:
                    # Group low
                    price = np.random.uniform(0.05, 0.25)
                elif scenario == 'down_signal' and asset == 'SOL':
                    # Laggard high
                    price = np.random.uniform(0.55, 0.90)
                else:
                    # Normal random walk
                    change = np.random.normal(0, 0.02)
                    price = max(0.01, min(0.99, price + change))
            else:
                # Small random walk
                change = np.random.normal(0, 0.015)
                price = max(0.01, min(0.99, price + change))
            
            data.append({
                'timestamp': ts,
                'asset': asset,
                'price': round(price, 4)
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    df = df.sort_values(['timestamp', 'asset'])
    
    # Save to CSV
    output_file = os.path.join(output_dir, 'historical_prices.csv')
    df.to_csv(output_file, index=False)
    
    print(f"\n{'='*60}")
    print("SAMPLE DATA GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Records:      {len(df):,}")
    print(f"Assets:       {', '.join(assets)}")
    print(f"Date range:   {start_date} to {end_date}")
    print(f"Output file:  {output_file}")
    print(f"File size:    {os.path.getsize(output_file) / 1024:.1f} KB")
    print(f"{'='*60}\n")
    
    return output_file


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate sample historical data')
    parser.add_argument('--start', default='2024-09-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', default='2024-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', default='data', help='Output directory')
    
    args = parser.parse_args()
    
    generate_sample_data(args.start, args.end, args.output)