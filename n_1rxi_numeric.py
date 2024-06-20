import rate as rate_m
import common

prompts = [{'role': 'user', 'content': (
        'We aim to evaluate the creativity of ideas in an Alternative Uses Tests (AUT) based on specific criteria. '
        'Please rate our ideas, given below, in terms of their {Measure}, which is defined as follows:'
        '\n'
        '{definition}'
        '\n\n'
        'Provide your ratings as a numbered list with one item per line, in purely numeric format. '
        'Do evaluate each of the {chunk_size} ideas below individually, even if there are repetitions. '
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


async def rate(data, chunk_size=20, measures=['novelty', 'feasibility', 'value']):
    requests = get_requests(data, chunk_size, measures)
    return rate_m.entrypoint(requests, temperature=0)


def get_requests(data, chunk_size, measures):
    requests = []
    qids = data['Question id'].unique()
    for qid in qids:
        chunks = []
        
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
                        measure=measure, Measure=measure.capitalize(), definition=common.definitions[measure],
                        qalist='\n'.join(qalist), Question=data.loc[chunk[0], 'Question'], chunk_size=qid_chunk_size)})
                requests.append({'messages': prompt, 'ichunk': ichunk, 'data': data, 'measure': measure, 'indices': chunk,
                                'n_chunks': len(chunks), 'duplicate_rows': duplicate_rows, 'chunk_size': qid_chunk_size})
    return requests


def process(requests):
    for rqi, request in enumerate(requests):
        response = request['completion'].choices[0].message.content
        try:
            parsed = parse(response, request)
            for i, (item, idx) in enumerate(zip(parsed, request['indices'])):
                if request['ichunk'] < request['n_chunks']-1 or i >= request['duplicate_rows']:
                    request['data'].loc[idx, item.keys()] = item
        except RuntimeError as e:
            print(f'Failed parse (chunk {request["ichunk"]}, request #{rqi}). Prompt:\n\'\'\'{request["messages"][0]["content"]}\'\'\'\nResponse:\n\'\'\'{response}\'\'\'\nError: {e}')


def parse(response, request):
    results = []
    i = 1
    for line in (response).splitlines():
        line = line.strip()
        if '.' not in line:
            raise RuntimeError(f'Expected period in line, found {line}.')
        if line.endswith('円') or line.endswith('¥'):
            line = line[:-1]
        elif line.endswith('JPY'):
            line = line[:-3]
        
        j, val = map(int, line.split('.'))
        if j != i:
            raise RuntimeError(f'Expected line number {i}, got {j}.')
        i = i+1
        results.append({request['measure']: val})
    
    
    if len(results) != request["chunk_size"]:
        raise RuntimeError(f'Unexpected number of items, found {len(results)} instead of {request["chunk_size"]}.')
    
    return results
