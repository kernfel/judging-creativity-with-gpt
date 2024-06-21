import time
import warnings
import types
import openai
import asyncio
import anthropic

import apikeys  # Never commit this module, which should contain: keys={'gpt': ['keys', 'here'], 'claude': ['more', 'keys']}


model = 'gpt-4-turbo-preview'


_library = None
_claudeobj = None
_models={
    'gpt': 'gpt-4-turbo-preview',
    'claude': 'claude-3-5-sonnet-20240620'
}


def setkey(n : int, library='gpt'):
    key = apikeys.keys[library][n]

    global model, _claudeobj, _library
    _library = library
    model = _models[library]

    if library == 'gpt':
        openai.api_key = key
    elif library == 'claude':
        _claudeobj = anthropic.AsyncAnthropic(api_key=key)


async def entrypoint(requests, num_procs=10, **kwargs):
    if _library == 'claude':
        num_procs = min(num_procs, 2)
    sem = asyncio.Semaphore(num_procs)
    try:
        total = len(requests)
    except TypeError:
        total = 'unknown'
    if 'model' not in kwargs:
        kwargs['model'] = model
    await asyncio.gather(*(request(sem, i, total, rq, **kwargs) for i, rq in enumerate(requests)))


async def request(sem, i, total, rq, **kwargs):
    async with sem:
        print(f'Request {i+1} of {total}')
        while kwargs:
            completion = await acomplete(messages=rq['messages'], **kwargs)
            if 'process' in rq:
                kwargs = rq['process'](rq, completion, **kwargs)
                if kwargs:
                    print(f'Retrying request {i+1} with params {kwargs}')
            else:
                rq['completion'] = completion
                rq['kwargs'] = kwargs
                break


async def acomplete(**kwargs):
    backoff = 5 # seconds
    if _library == 'gpt':
        if 'system' in kwargs:
            kwargs['messages'].append({'role': 'system', 'content': kwargs.pop('system')})
        while True:
            try:
                return await openai.ChatCompletion.acreate(**kwargs)
            except openai.OpenAIError as e:
                print(e)
                print(f'Retrying in {backoff} s...')
                time.sleep(backoff)  # Deliberately not awaited: Error may be rate limit.
                backoff *= 2
    elif _library == 'claude':
        if 'messages' in kwargs and 'system' not in kwargs:
            system = []
            messages = []
            for m in kwargs['messages']:
                if m['role'] == 'system':
                    system.append(m['content'])
                else:
                    messages.append(m)
            kwargs['system'] = '\n'.join(system)
            kwargs['messages'] = messages
        if kwargs.pop('n', 1) != 1:
            warnings.warn('Claude API does not support "n" parameter, ignoring (n=1).')
        if 'max_tokens' not in kwargs:
            kwargs['max_tokens'] = 4096
        while True:
            try:
                response = await _claudeobj.messages.create(**kwargs)
                # Patch into OpenAI format
                response.choices = [types.SimpleNamespace(index=0, message=types.SimpleNamespace(role=response.role, content=response.content[0].text))]
                return response
            except (anthropic.RateLimitError, anthropic.InternalServerError) as e:
                print(e)
                print(f'Retrying in {backoff} s...')
                time.sleep(backoff)
                backoff *= 2
