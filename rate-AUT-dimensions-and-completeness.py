import pandas as pd
import n_1rxi as method


### Set API key
import rate
rate.setkey(0)


### Ratings
# Setup
chunk_size = 20
fname = 'MitAut_20231222'
raw = pd.read_excel(f'{fname}.xlsx', 'AUT').rename(columns={'Item_name': 'Question', 'Item_no': 'Question id'})
data = raw.sample(frac=1, random_state=8)

# Rate
await method.rate(data, chunk_size=chunk_size, measures=['novelty', 'feasibility'])
data = data.sort_index()


### Answer completeness
# Setup
q = 'The string "{Answer}" is a participant\'s answer to the question of alternative uses of the item "{Question}". Input was cut off after a time limit. Does the answer, which may be extremely brief, appear to have been cut off? Yes/No'
data['answer_complete'] = 0

def process(rq, completion, **kwargs):
    a = completion['choices'][0]['message']['content']
    answer_complete = a.startswith('No')
    if answer_complete:
        data.loc[rq['i'], 'answer_complete'] = 1

# Ask only for non-obvious cases
requests = []
for i, row in data.iterrows():
    if row['Answer'].endswith('。'):
        row.loc[i, 'answer_complete'] = 1
    elif row['Answer'] == row['Question']:
        row.loc[i, 'answer_complete'] = 0
    else:
        requests.append({'messages': [{'role': 'user', 'content': q.format(**row)}], 'process': process, 'i': i})

# Ask GPT
await rate.entrypoint(requests, model=rate.model, max_tokens=1, temperature=0)


### Save
data.to_excel(f'{fname}_AUT-ratings.xlsx')
