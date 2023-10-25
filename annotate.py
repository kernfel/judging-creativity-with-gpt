import pandas as pd
import numpy as np
import populate
    

measures = ('novelty', 'feasibility', 'value')


def get_annotated():
    _, _, source = populate.read('EEGv2.xlsx')
    source.rename(columns={'Question_ja': 'Question'}, inplace=True)
    source.drop_duplicates(['Question', 'Answer'], inplace=True)

    for key in measures:
        source[f'sample_for_{key}'] = False

    for key in measures:
        for qid in source['Question id'].unique():
            pick_samples(source, qid, key)
        
        lo = source[key.capitalize()].min()
        hi = source[key.capitalize()].max()
        slope = (100 - 1) / (hi - lo)
        intercept = 1 - lo * slope
        source = source.assign(**{f'{key}_transformed': lambda x: (slope * x[key.capitalize()] + intercept + 0.5).astype(int)})
    
    return source


def pick_samples(source, qid, key, n_samples=10):
    df = source[source['Question id'] == qid]
    df_sorted = df.sort_values(by=key.capitalize())

    # Stretch (0,) 1, .., n, (n+1) to (0,) .., (|df|)
    floats = np.arange(1, n_samples+1) * (len(df_sorted)-1) / (n_samples+1)
    ints = (floats + .5).astype(int)
    
    play = np.diff(np.concatenate([[0], ints, [len(df_sorted)-1]])).min() // 2
    representative_rows = []
    for index in ints:
        ival = df_sorted.iloc[index-play:index+play+1]
        idx = pick_sparse(ival)
        representative_row = ival.iloc[idx]
        representative_rows.append(representative_row)

    source.loc[pd.DataFrame(representative_rows).index, f'sample_for_{key}'] = True


def pick_sparse(df):
    center_index = len(df) // 2
    already_picked = sum([df[f'sample_for_{key}'] for key in measures])
    if already_picked.sum() == 0:
        # No pre-existing samples in this interval => pick the center
        return center_index
    else:
        # Some samples already picked => pick the one closest to the center
        left_index = center_index
        right_index = center_index

        # Loop while both left and right indices are within the bounds of the Series
        while left_index >= 0 and right_index < len(df):
            # Check the left side
            if already_picked.iloc[left_index] != 0:
                return left_index
            # Check the right side
            if already_picked.iloc[right_index] != 0:
                return right_index
            # Move towards the center
            left_index -= 1
            right_index += 1
        
        # Only non-zero entry is at index 0, and len(df) is even; the above motions leave this case out.
        return 0


def get_clean(qid=None):
    df = get_annotated()
    columns = [f'sample_for_{key}' for key in measures]
    rowsum = df[columns].sum(axis=1)
    qselect = True if qid is None else df['Question id']==qid
    return df[(rowsum == 0) & qselect]

def get_samples(measure, qid):
    df = get_annotated()
    return df[(df['Question id'] == qid) & df[f'sample_for_{measure}']]
