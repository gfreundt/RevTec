
with open('placas_original.txt', mode='r', encoding='unicode_escape') as file:
    all_data = file.readlines()
    all_data = [i.strip() for i in all_data]

counter = [0]*8
all_data_split=[[],[],[],[],[],[],[],[]]

for data in all_data:
    counter[len(data)] += 1
    all_data_split[len(data)].append(data)

with open('placas.txt', mode='w', encoding='utf-8', newline="\n") as file:
    for item in all_data_split[6]:
        file.write(f'{item}\n')
