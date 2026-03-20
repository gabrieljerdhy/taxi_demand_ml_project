from pathlib import Path

import requests
from src.utils.paths import RAW_DATA_DIR

def download_one_file_of_raw_data(year: int, month: int) -> Path:
    """
    Downloads Parquet file with historical taxi rides for the given `year` and
    `month`
    """
    URL = f'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{year}-{month:02d}.parquet'
    response = requests.get(URL)

    if response.status_code == 200:
        path = RAW_DATA_DIR / f'rides_{year}-{month:02d}.parquet'
        open(path, "wb").write(response.content)
        return path
    else:
        raise Exception(f'{URL} is not available')