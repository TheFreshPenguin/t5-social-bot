def parse(file_location):
    prompts = {}

    with open(file_location, 'r', encoding="utf-8") as file:
        prompts_raw = file.read()

    for p in prompts_raw.split('#-- ')[1:]:
        prompt = p.split(' --#')
        prompts[prompt[0]] = prompt[1]

    return prompts