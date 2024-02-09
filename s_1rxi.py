import rate as rate_m
import common
import annotate

from n_1rxi import process

json_suffix = {'novelty': '', 'feasibility': '', 'value': ', where x is an integer representing the value in JPY'}

prompts = [{'role': 'user', 'content': (
        'We aim to evaluate the creativity of ideas in an Alternative Uses Tests (AUT) based on specific criteria. '
        'Please rate our ideas, given below, in terms of their {Measure}, which is defined as follows:'
        '\n'
        '{definition}'
        '\n\n'
        'Proceed as follows in your evaluation. '
        'Write 3 (three) lines for each item in the list below. On the first line, write the item number and briefly describe the idea in your own words. '
        'On the second line, {elaboration}. '
        'Finally, on the third line, provide your numeric rating as a json object of the form {{"{measure}":x}}{json_suffix}. '
        'Evaluate each idea in the order provided, leaving one empty line between evaluations. '
        'Do evaluate each of the {chunk_size} ideas below individually, even if there are repetitions. '
        '\n\n'
        'The following examples illustrate the expected range of final {Measure} ratings for alternative uses of the item "{Question}":'
        '\n'
        '{samples}'
        '\n\n'
        'Our ideas are to use the item "{Question}" in the following ways:'
        '\n'
        '{qalist}'
    )},
    {
    'role': 'system',
    'content': common.system
    }
]

list_item = '{i}. {Answer}'
training_list_item = 'Example {i}: {Answer} -- {value}'


async def rate(data, chunk_size=20):
    requests = get_requests(data, chunk_size)
    await rate_m.entrypoint(requests, n=1, model=rate_m.model, temperature=0)


def get_requests(data, chunk_size):
    requests = []
    qids = data['Question id'].unique()
    for qid in qids:
        chunks = []

        samples = {measure: get_samples_string(measure, qid) for measure in common.definitions.keys()}
        
        mask = data['Question id']==qid
        n_items = mask.sum()
        qid_chunk_size = chunk_size if n_items >= chunk_size else n_items
        n_chunks = n_items // qid_chunk_size
        indices = data.index[mask]
        for i in range(n_chunks):
            start, end = i*qid_chunk_size, (i+1)*qid_chunk_size
            chunks.append(indices[start:end])

        duplicate_rows = (qid_chunk_size - (n_items % qid_chunk_size)) % qid_chunk_size
        if duplicate_rows > 0:
            chunks.append(indices[-qid_chunk_size:])

        for ichunk, chunk in enumerate(chunks):
            qalist = [list_item.format(**data.loc[idx], i=i+1) for i, idx in enumerate(chunk)]
            for measure, definition in common.definitions.items():
                prompt = []
                for p in prompts:
                    prompt.append({'role': p['role'], 'content': p['content'].format(
                        measure=measure, Measure=measure.capitalize(), definition=definition, chunk_size=qid_chunk_size,
                        elaboration=common.elaborations_list[measure], json_suffix=json_suffix[measure],
                        qalist='\n'.join(qalist), Question=data.loc[chunk[0], 'Question'], samples=samples[measure])})
                requests.append({'messages': prompt, 'ichunk': ichunk, 'process': process, 'data': data, 'measure': measure, 'indices': chunk,
                                'n_chunks': len(chunks), 'duplicate_rows': duplicate_rows, 'chunk_size': qid_chunk_size})
    return requests


def get_samples_string(measure, qid):
    samples = annotate.get_samples(measure, qid)
    items = samples.sort_values(f'{measure}_transformed').reset_index(drop=True, inplace=False)
    strings = [training_list_item.format(i=i+1, value=row[f'{measure}_transformed'], **row) for i, row in items.iterrows()]
    return '\n'.join(strings)
