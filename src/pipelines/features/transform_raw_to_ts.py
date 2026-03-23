import pandas as pd
from tqdm import tqdm


def add_missing_slots(ts_data: pd.DataFrame) -> pd.DataFrame:
    """
    Add necessary rows to the input 'ts_data' to make sure the output
    has a complete list of
    - pickup_hours
    - pickup_location_ids
    """
    location_ids = range(1, ts_data['pickup_location_id'].max() + 1)

    full_range = pd.date_range(ts_data['pickup_hour'].min(),
                               ts_data['pickup_hour'].max(),
                               freq='h')
    output = pd.DataFrame()
    for location_id in tqdm(location_ids):

        # keep only rides for this 'location_id'
        ts_data_i = ts_data.loc[ts_data.pickup_location_id == location_id, ['pickup_hour', 'rides']]
        
        if ts_data_i.empty:
            # add a dummy entry with a 0
            ts_data_i = pd.DataFrame.from_dict([
                {'pickup_hour': ts_data['pickup_hour'].max(), 'rides': 0}
            ])

        # quick way to add missing dates with 0 in a Series
        # taken from https://stackoverflow.com/a/19324591
        ts_data_i.set_index('pickup_hour', inplace=True)
        ts_data_i.index = pd.DatetimeIndex(ts_data_i.index)
        ts_data_i = ts_data_i.reindex(full_range, fill_value=0)
        
        # add back `location_id` columns
        ts_data_i['pickup_location_id'] = location_id

        output = pd.concat([output, ts_data_i])
    
    # move the pickup_hour from the index to a dataframe column
    output = output.reset_index().rename(columns={'index': 'pickup_hour'})
    
    return output

def transform_raw_data_into_ts_data(
    rides: pd.DataFrame
) -> pd.DataFrame:
    """"""
    # sum rides per location and pickup_hour
    rides['pickup_hour'] = rides['pickup_datetime'].dt.floor('H')
    agg_rides = rides.groupby(['pickup_hour', 'pickup_location_id']).size().reset_index()
    agg_rides.rename(columns={0: 'rides'}, inplace=True)

    # add rows for (locations, pickup_hours)s with 0 rides
    agg_rides_all_slots = add_missing_slots(agg_rides)

    return agg_rides_all_slots