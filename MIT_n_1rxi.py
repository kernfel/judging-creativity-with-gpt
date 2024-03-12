import json
import rate as rate_m
import common

prompts = [{'role': 'user', 'content': (
        'We aim to evaluate {Measure} in responses to a creativity task. '
        'The task instructions were to creatively combine two elements, "{Item_1}" and "{Item_2}", to achieve the goal of "{Goal}".'
        '\n'
        'Please rate each idea in the list below in terms of its {Measure}, which is defined as follows:'
        '\n'
        '{Measure}: {definition}'
        '\n\n'
        'Proceed as follows in your evaluation. '
        'Write 3 lines for each response in the list below. On the first line, write the item number and briefly describe the idea in your own words. '
        'On the second line, write several sentences to {elaboration}. '
        'Finally, on the third line, provide your numeric rating as a json object of the form {{"{measure}":x}}. '
        'Evaluate each idea in the order provided, leaving one empty line between evaluations. '
        'Do evaluate each idea below individually, even if there are repetitions. '
        '\n\n'
        '{thelist}'
    )},
    {
    'role': 'system',
    'content': common.system + ' You respond in English.'
    }
]

list_item = '{i}. {Answer}'

Measures = {
    'novelty': 'Novelty of Combination',
    'feasibility': 'Feasibility of Combination',
    'goal': 'Goal Attainment Level'
}

definitions = {
    'novelty':
        'Rate the novelty of the combination of the two elements on a scale of 1 to 100, with 1 being not novel at all and 100 being extremely novel. '
        'Consider how unique, original, or surprising the combination is, regardless of its feasibility and regardless of whether it achieves the goal.',
    'feasibility':
        'Rate the feasibility of the combination of the two elements on a scale of 1 to 100, with 1 being not feasible at all and 100 being extremely feasible. '
        'Consider how practical or doable the combination is in real-life settings, regardless of its novelty and regardless of whether it achieves the goal.',
    'goal':
        'Rate the degree to which the described scenario can achieve the goal on a scale of 1 to 100, '
        'with 1 indicating an utter failure to achieve the goal, and 100 indicating that the goal is unquestionably achieved to an outstanding degree. '
        'Consider the level of goal attainment of the scenario regardless of how novel or feasible it is to combine the elements in the described way.'
}

elaborations = {
    'novelty': 'consider how the two elements interact in the described scenario, and compare this to typical uses of the elements',
    'feasibility': 'outline possible challenges to combining the two elements in the way described',
    'goal': 'estimate the impact the scenario might have on the set goal, assuming challenges to combining the elements as described have been overcome'
}


async def rate(data, chunk_size=20, measures=['novelty', 'feasibility', 'goal']):
    requests = get_requests(data, chunk_size, measures)
    await rate_m.entrypoint(requests, n=1, model=rate_m.model, temperature=0)


def get_requests(data, chunk_size, measures):
    requests = []
    qids = data['MIT_Question_no'].unique()
    for qid in qids:
        chunks = []
        
        mask = data['MIT_Question_no']==qid
        n_items = mask.sum()
        if chunk_size > 0:
            qid_chunk_size = min(chunk_size, n_items)
        else:
            qid_chunk_size = n_items
        n_chunks = n_items // qid_chunk_size
        indices = data.index[mask]
        for i in range(n_chunks):
            start, end = i*qid_chunk_size, (i+1)*qid_chunk_size
            chunks.append(indices[start:end])

        duplicate_rows = (qid_chunk_size - (n_items % qid_chunk_size)) % qid_chunk_size
        if duplicate_rows > 0:
            chunks.append(indices[-qid_chunk_size:])

        for ichunk, chunk in enumerate(chunks):
            thelist = [list_item.format(**data.loc[idx], i=i+1) for i, idx in enumerate(chunk)]
            for measure in measures:
                prompt = []
                for p in prompts:
                    prompt.append({'role': p['role'], 'content': p['content'].format(
                        measure=measure, Measure=Measures[measure], definition=definitions[measure],
                        elaboration=elaborations[measure],
                        thelist='\n'.join(thelist), **data.loc[chunk[0], 'Item_1':'Goal'], chunk_size=qid_chunk_size)})
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
