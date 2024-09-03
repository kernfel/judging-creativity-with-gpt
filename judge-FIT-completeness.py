import pandas as pd
import numpy as np


### Set API key
import rate
rate.setkey(0)


### Preprocessing
# Read
fname = 'MitAut_20231222'
raw = pd.read_excel(f'{fname}.xlsx', 'MIT')

# Stack multiple answers
stacked = raw.set_index(raw.columns[:9].to_list()).stack().reset_index().rename(columns={0:'Answer', 'Item 1': 'Item_1', 'Item 2': 'Item_2'})

# Assign "Time left" := -1 on non-final answers (recorded time left only applies to final answer)
first_answer = stacked['level_9']=='Answer'
last_answer = pd.concat([first_answer[1:], pd.Series([True])]).reset_index(drop=True)
stacked.loc[~last_answer, 'Time_left'] = -1
data = stacked.drop(columns='level_9')

# Remove empty answers
data['Answer'] = data['Answer'].apply(lambda x: x.strip() if x.strip() else np.nan)
data.dropna(subset=['Answer'], inplace=True)


### Judge element inclusion
# Setup
data['both_items_included'] = 0
best_of_n = 3
q = 'In the scenario "{Answer}", the two items "{Item_1}" and "{Item_2}" both play a role: Yes/No'

def process(rq, completion, **kwargs):
    a = completion['choices'][0]['message']['content']
    if a.startswith('Yes'):
        data.loc[rq['i'], 'both_items_included'] += 1


# Ask GPT
requests = [{'messages': [{'role': 'user', 'content': q.format(**row)}], 'process': process, 'i': i} for i, row in data.iterrows()]
for _ in range(best_of_n):
    await rate.entrypoint(requests, model=rate.model, max_tokens=1, temperature=0)


### Save
data.to_excel(f'{fname}_element-use.xlsx')
