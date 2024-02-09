import time
import openai
import asyncio


model = 'gpt-4-turbo-preview'


def setkey(n : int):
    keys = ['List', 'your', 'API', 'keys']
    openai.api_key = keys[n]


async def entrypoint(requests, num_procs=10, **kwargs):
    sem = asyncio.Semaphore(num_procs)
    try:
        total = len(requests)
    except TypeError:
        total = 'unknown'
    await asyncio.gather(*(request(sem, i, total, rq, **kwargs) for i, rq in enumerate(requests)))


async def request(sem, i, total, rq, **kwargs):
    async with sem:
        print(f'Request {i+1} of {total}')
        while kwargs:
            completion = await acomplete(messages=rq['messages'], **kwargs)
            kwargs = rq['process'](rq, completion, **kwargs)
            if kwargs:
                print(f'Retrying request {i+1} with params {kwargs}')


async def acomplete(**kwargs):
    backoff = 5 # seconds
    while True:
        try:
            return await openai.ChatCompletion.acreate(**kwargs)
        except openai.OpenAIError as e:
            print(e)
            print(f'Retrying in {backoff} s...')
            time.sleep(backoff)  # Deliberately not awaited: Error may be rate limit.
            backoff *= 2
