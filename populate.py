import pandas as pd


def read():
    df = load_elo_data(slice(0,-1))  ## BUG: This should be (0,None); as it stands, the final entry is omitted.
    questions, answers = df['Question_ja'], df['Answer']
    return questions, answers, df


def load_elo_data(rows=slice(0,None)):
    df = pd.read_excel('EEGv2.xlsx', sheet_name='EEG_RatingV2_Score')
    try:
        df = df[rows]
    except KeyError:
        df = df.loc[rows]

    # Include Japanese item=question names
    mapping = pd.read_excel('EEGv2.xlsx', sheet_name='Item_mappings').set_index('Item_no')
    df = df.join(mapping, on='Item_no')

    df.rename(columns={'Item_no': 'Question id', 'Japanese': 'Question_ja', 'Item_name': 'Question_en'}, inplace=True)

    return df
