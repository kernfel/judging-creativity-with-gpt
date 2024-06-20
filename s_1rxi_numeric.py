import rate as rate_m
import common

from n_1rxi_numeric import process
from s_1rxi import get_samples_string

prompts = [{'role': 'user', 'content': (
        'We aim to evaluate the creativity of ideas in an Alternative Uses Tests (AUT) based on specific criteria. '
        'Please rate our ideas, given below, in terms of their {Measure}, which is defined as follows:'
        '\n'
        '{definition}'
        '\n\n'
        'Provide your ratings as a numbered list with one item per line, in purely numeric format. '
        'Do evaluate each of the {chunk_size} ideas below individually, even if there are repetitions. '
        '\n\n'
        'The following examples illustrate the expected range of {Measure} ratings for alternative uses of the item "{Question}":'
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


async def rate(data, chunk_size=20, measures=['novelty', 'feasibility', 'value'], num_procs=10):
    requests = get_requests(data, chunk_size, measures)
    await rate_m.entrypoint(requests, temperature=0)
    return requests


def get_requests(data, chunk_size, measures):
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
            for measure in measures:
                prompt = []
                for p in prompts:
                    prompt.append({'role': p['role'], 'content': p['content'].format(
                        measure=measure, Measure=measure.capitalize(), definition=common.definitions[measure], chunk_size=qid_chunk_size,
                        qalist='\n'.join(qalist), Question=data.loc[chunk[0], 'Question'], samples=samples[measure])})
                requests.append({'messages': prompt, 'ichunk': ichunk, 'data': data, 'measure': measure, 'indices': chunk,
                                'n_chunks': len(chunks), 'duplicate_rows': duplicate_rows, 'chunk_size': qid_chunk_size})
    return requests
