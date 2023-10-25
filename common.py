definitions = {
    'novelty': (
        'Novelty: Rate the novelty of the idea on a scale of 1 to 100, with 1 being not novel at all and 100 being extremely novel. '
        'Consider how unique, original, or surprising the idea is, while disregarding its feasibility and value.'
    ),
    'feasibility': (
        'Feasibility: Rate the feasibility of the idea on a scale of 1 to 100, with 1 being not feasible at all and 100 being extremely feasible. '
        'Consider how practical or doable the idea is in real-life settings, while disregarding its novelty and value.'
    ),
    'value': (
        'Value: Estimate the potential commercial value of the idea in Japanese yen, while disregarding its novelty and feasibility.'
    )
}

elaborations = {
    'novelty': 'consider a few other unconventional uses of the item, and compare the idea to these in terms of its Novelty',
    'feasibility': 'consider the Feasibility of our idea, outlining possible challenges to implementation',
    'value': 'consider existing products achieving the same purpose as our idea, and estimate their value'
}

elaborations_list = {
    **elaborations,
    'novelty': 'consider other unconventional uses of the item, including those listed, and compare the idea to these in terms of its Novelty'
}

system = (
    'You are an advanced instruction-following AI agent. '
    'You are highly trained in English and Japanese and intricately aware of Japanese culture. '
    'Your responses summarize the average opinions of the Japanese general public.'
)