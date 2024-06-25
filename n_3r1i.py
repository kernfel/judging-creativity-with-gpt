import json
import rate as rate_m
import common

prompts = [{'role': 'user', 'content': (
        'We aim to evaluate the creativity of ideas in an Alternative Uses Tests (AUT) based on specific criteria. '
        'Please rate our idea, given below, in terms of its Novelty, Feasibility, and Value, which are defined as follows:'
        '\n'
        '{definitions[novelty]}'
        '\n'
        '{definitions[feasibility]}'
        '\n'
        '{definitions[value]}'
        '\n\n'
        'Proceed as follows in your evaluation. '
        'First, briefly describe the idea in your own words. '
        'Then, in a short paragraph, {elaborations[novelty]}. '
        'In a second paragraph, {elaborations[feasibility]}. '
        'In a third paragraph, {elaborations[value]}. '
        'Finally, provide your numeric ratings as a json object of the form {{"novelty":x, "feasibility":y, "value":z}}, '
        'where z is an integer representing the value in JPY.'
        '\n\n'
        'Our idea is to use the item "{Question}" as "{Answer}".'
    )},
    {
    'role': 'system',
    'content': common.system
    }
]


async def rate(data):
    requests = get_requests(data)
    await rate_m.entrypoint(requests, temperature=0)
    return requests


def get_requests(data):
    requests = []
    for index, row in data.iterrows():
        prompt = []
        for p in prompts:
            prompt.append({'role': p['role'], 'content': p['content'].format(**row, definitions=common.definitions, elaborations=common.elaborations)})
        requests.append({'messages': prompt, 'index': index, 'data': data})
    return requests


def process(requests):
    failures = []
    for rqi, request in enumerate(requests):
        response = request['completion'].choices[0].message.content
        try:
            parsed = parse(response)
            request['data'].loc[request['index'], parsed.keys()] = parsed
        except RuntimeError as e:
            print(f'Failed parse (row {request["index"]}, request #{rqi}). Prompt:\n\'\'\'{request["messages"][0]["content"]}\'\'\'\nResponse:\n\'\'\'{response}\'\'\'\nError: {e}')
            failures.append(request)
    return failures


def parse(response):
    result = {'raw': response}
    
    lines = [l.strip() for l in response.splitlines() if l.strip()]
    if len(lines) != 5:
        raise RuntimeError('Unexpected number of lines')
    
    keys = ('idea', 'novelty', 'feasibility', 'value')
    for key, line in zip(keys, lines):
        result[f'{key}_explanation'] = line
    
    try:
        ratings = json.loads(lines[-1])
        result.update(ratings)
    except json.JSONDecodeError:
        raise RuntimeError('Final line not valid JSON')
    
    return result
    