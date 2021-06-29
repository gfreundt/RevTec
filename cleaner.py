from tqdm import tqdm


def valid_placa(placa):
    if len(placa) != 6:
        return False
    if placa[0].isdigit():
        return False
    if placa[3].isalpha() or placa[4].isalpha() or placa[5].isalpha():
        return False
    return True


with open('todo_placas.txt', mode='r', encoding='unicode_escape') as file:
    all_data = file.readlines()
    all_data = set([i.strip() for i in all_data])

pure = [i for i in tqdm(all_data) if valid_placa(i)]

with open('todo_placas.txt', mode='w', encoding='utf-8', newline="\n") as file:
    for k, item in enumerate(pure):
        file.write(f'{item}\n')
    print(k)