import json
import rate as rate_m
import common

json_suffix = {'novelty': '', 'feasibility': '', 'value': ', where x is an integer representing the value in JPY'}

prompts = [{'role': 'user', 'content': (
        'We aim to evaluate the creativity of ideas in an Alternative Uses Tests (AUT) based on specific criteria. '
        'Please rate our ideas, given below, in terms of their {Measure}, which is defined as follows:'
        '\n'
        '{definition}'
        '\n\n'
        'Proceed as follows in your evaluation. '
        'Write 3 lines for each item in the list below. On the first line, write the item number and briefly describe the idea in your own words. '
        'On the second line, {elaboration}. '
        'Finally, on the third line, provide your numeric rating as a json object of the form {{"{measure}":x}}{json_suffix}. '
        'Evaluate each idea in the order provided, leaving one empty line between evaluations. '
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
    await rate_m.entrypoint(requests, n=1, model='gpt-4-turbo-preview', temperature=0)


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
                        elaboration=common.elaborations_list[measure], json_suffix=json_suffix[measure],
                        qalist='\n'.join(qalist), Question=data.loc[chunk[0], 'Question'], chunk_size=qid_chunk_size)})
                requests.append({'messages': prompt, 'ichunk': ichunk, 'process': process, 'data': data, 'measure': measure, 'indices': chunk,
                                'n_chunks': len(chunks), 'duplicate_rows': duplicate_rows, 'chunk_size': qid_chunk_size})
    return requests


def process(request, completion, **kwargs):
    response = completion.choices[0].message.content
    try:
        parsed = parse(response, request)
    except RuntimeError as e:
        print(f'Failed parse (chunk {request["ichunk"]}). Prompt:\n\'\'\'{request["messages"][0]["content"]}\'\'\'\nResponse:\n\'\'\'{response}\'\'\'\nError: {e}')
        if kwargs['temperature'] < 0.5:
            return {**kwargs, 'temperature': kwargs['temperature']+.1}
        else:
            print(f'Giving up.')
            parsed = {f'{request["measure"]}_raw': response}
    
    for i, (item, idx) in enumerate(zip(parsed, request['indices'])):
        if request['ichunk'] < request['n_chunks']-1 or i >= request['duplicate_rows']:
            request['data'].loc[idx, item.keys()] = item


def parse(response, request):
    lines = []
    results = []
    i = 0
    for l in (response + '\n ').splitlines():
        if l.strip():
            lines.append(l.strip())
            continue
        elif lines and len(lines) == 4:
            # Assume, based on examples, that l0 is a copy of the use, l1 translation, l2 explanation, l3 rating.
            lines = ['\n'.join(lines[:2]), lines[2], lines[3]]
        elif lines and len(lines) != 3:
            raise RuntimeError(f'Unexpected number of lines for item {i}.')
        
        if lines:
            results.append(_parse(lines, request['measure']))
            lines = []
            i = i+1
    
    
    if len(results) != request["chunk_size"]:
        raise RuntimeError(f'Unexpected number of items, found {len(results)} instead of {request["chunk_size"]}.')
    
    return results

def _parse(lines, measure):
    result = {f'{measure}_raw': '\n'.join(lines)}
    
    keys = (f'{measure}_idea', measure)
    for key, line in zip(keys, lines):
        result[f'{key}_explanation'] = line
    
    try:
        ratings = json.loads(lines[-1])
        if len(ratings) != 1 or measure not in ratings:
            print(f'WARNING: Aberrant JSON for {measure}: {lines[-1]}')
        result.update(ratings)
    except json.JSONDecodeError:
        raise RuntimeError(f'Final line not valid JSON: {lines[-1]}')
    
    return result
