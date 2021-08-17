import os
from tqdm import tqdm
import stats

def valid_placa(placa):
    if len(placa) != 6:
        return False
    if placa[0].isdigit():
        return False
    if placa[3].isalpha() or placa[4].isalpha() or placa[5].isalpha():
        return False
    return True

def not_today():
    # Cross-reference placas and resultados files and only keep placas with no results
    with open('todo_placas.txt', mode='r', encoding='utf-8') as file:
        placas = [i.strip() for i in file.readlines()]
    with open('todo_resultados.txt', mode='r', encoding='utf-8') as file:
        resultados = [i[0] for i in file.readlines()]

    placas_left = [f'{i}\n' for i in tqdm(placas, desc='Cross-Referencing Placas database') if i not in resultados]

    with open('todo_placas.txt', mode='w', encoding='utf-8') as file:
        file.writelines(placas_left)

def clean_placas():
    with open('todo_placas.txt', mode='r', encoding='utf-8') as file:
        placas = [i.strip() for i in file.readlines()]
        print(len(placas))

    placas_left = [f'{i}\n' for i in tqdm(placas, desc='Cleaning Placas database') if valid_placa(i)]

    with open(os.path.join('todo_placas.txt'), mode='w', encoding='utf-8') as file:
        file.writelines(placas_left)
        print(len(placas_left))

stats.main()
clean_placas()
not_today()
stats.main()