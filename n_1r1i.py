import json
import rate as rate_m
import common

json_suffix = {'novelty': '', 'feasibility': '', 'value': ', where x is an integer representing the value in JPY'}

prompts = [{'role': 'user', 'content': (
        'We aim to evaluate the creativity of ideas in an Alternative Uses Tests (AUT) based on specific criteria. '
        'Please rate our idea, given below, in terms of its {Measure}, which is defined as follows:'
        '\n'
        '{definition}'
        '\n\n'
        'Proceed as follows in your evaluation. '
        'First, briefly describe the idea in your own words. '
        'Then, in a single short paragraph, {elaboration}. '
        'Finally, provide your numeric rating as a json object of the form {{"{measure}":x}}{json_suffix}.'
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
        for measure, definition in common.definitions.items():
            prompt = []
            for p in prompts:
                prompt.append({'role': p['role'], 'content': p['content'].format(
                    **row, measure=measure, Measure=measure.capitalize(), definition=definition,
                    elaboration=common.elaborations[measure], json_suffix=json_suffix[measure])})
            requests.append({'messages': prompt, 'index': index, 'data': data, 'measure': measure})
    return requests


def process(requests):
    failures = []
    for i, request in enumerate(requests):
        response = request['completion'].choices[0].message.content
        try:
            parsed = parse(response, request["measure"])
            request['data'].loc[request['index'], parsed.keys()] = parsed
        except RuntimeError as e:
            print(f'Failed parse (row {request["index"]}, request #{i}). Prompt:\n\'\'\'{request["messages"][0]["content"]}\'\'\'\nResponse:\n\'\'\'{response}\'\'\'\nError: {e}')
            failures.append(request)
    return failures


def parse(response, measure):
    result = {f'{measure}_raw': response}
    
    lines = [l.strip() for l in response.splitlines() if l.strip()]
    if len(lines) == 4:
        # Assume, based on examples, that l0 is translation, l1-2 explanation, l3 rating.
        lines = [lines[0], '\n'.join(lines[1:3]), lines[3]]
    if len(lines) != 3:
        raise RuntimeError('Unexpected number of lines')
    
    keys = (f'{measure}_idea', measure)
    for key, line in zip(keys, lines):
        result[f'{key}_explanation'] = line
    
    try:
        ratings = json.loads(lines[-1])
        result.update(ratings)
    except json.JSONDecodeError:
        raise RuntimeError('Final line not valid JSON')
    
    return result
