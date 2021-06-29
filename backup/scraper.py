from datetime import datetime as dt
import urllib.request
import csv, time, os, sys, io
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as WebDriverOptions
from selenium.webdriver.support.select import Select
from google.cloud import vision
import threading
from tqdm import tqdm



def split(q, mplacas):
    print("Split in ", q)
    with open('placas.txt', mode='r', encoding='utf-8') as file:
            data_base = [i.strip() for i in file.readlines()]
            records = len(data_base)
            block = records//q
    for n in range(q):
        with open('placas' + str(n) + '.txt', mode='w', encoding='utf-8') as file:
            data_pendiente = [f'{i}\n' for k, i in enumerate(data_base[block*n:block*(n+1)]) if k < mplacas]
            file.writelines(data_pendiente)


def consolidate(q):
    print('Consolidando bases de datos...')
    for i in range(q):
        file = str(i)
        with open('placas'+file+'.txt', mode='r', encoding='utf-8') as file:
            data_base = [i.strip() for i in file.readlines()]
        with open('resultados'+file+'.txt', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='|')
            data_resultados = [i[0] for i in reader]
            r = len(data_resultados)
        with open('placas'+file+'.txt', mode='w', encoding='utf-8') as file:
            data_pendiente = [f'{i}\n' for i in tqdm(data_base) if i not in data_resultados]
            file.writelines(data_pendiente)
            s = len(data_pendiente)
        print(f'File: {i} - Completas: {r} / Totales: {s}  =  {r/s*100:.2f}%')


def list_of_pending_placas(ses):
    with open('placas'+ses+'.txt', mode='r', encoding='utf-8') as file:
        p = [i.strip() for i in file.readlines()]
        return p


def driver_options():
    options = WebDriverOptions()
    options.add_argument("--window-size=800,800")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--silent")
    options.add_argument("--disable-notifications")
    options.add_argument("--incognito")
    options.add_argument("--log-level=3")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return options


def extract(placa, url, ses):
    driver = webdriver.Chrome('/usr/bin/chromedriver', options = driver_options())
    while True:  # Loop infinito hasta salir con placa consultada
        captcha = ""
        while not captcha:
            driver.get(url)
            urllib.request.urlretrieve(driver.find_element_by_xpath('//img').get_attribute('src'), 'captcha'+ses+'.jpg')
            captcha = ocr3('captcha'+ses+'.jpg')
        driver.find_element_by_id('txtPlaca').send_keys(placa)      # Llenar campo "Nro de placa"
        driver.find_element_by_id('txtCaptcha').send_keys(captcha)  # Llenar campo de Captcha
        driver.find_element_by_id('BtnBuscar').click()              # Click Botón Buscar
        time.sleep(1)
        respuestas = [i.text for i in driver.find_elements_by_class_name('gridItemGroup')]  # Recoge resultados
        if respuestas:      # Datos completos
            print("Resultado: OK")
            os.system('cp captcha'+ses+'.jpg ' +  os.path.join("images",captcha+".jpg"))
            driver.quit()
            return respuestas
        elif "no es correcto" in driver.find_element_by_id('lblAlertaMensaje').text:  # Error en captcha ingresado
            print("CAPTCHA INCORRECTO | ",end="", flush = True) # Reinicia loop
        else: # No se obtuvo datos de la placa
            print("Resultado: NO HAY INFORMACIÓN DE PLACA")
            driver.quit()
            return None


def ocr3(image_path):
    client = vision.ImageAnnotatorClient.from_service_account_json('google-vision-keys.json')
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description.strip()


def analizar_respuesta(placa,respuesta):
    fecha_hoy = dt.strftime(dt.now(),"%m/%d/%Y")
    if not respuesta:
        return [placa]+[""]*8+[fecha_hoy]
    empresa = respuesta[0]
    segunda_linea = respuesta[1].split(" ")
    cert = segunda_linea[1]
    fecha_inspec = segunda_linea[2]
    if len(segunda_linea) > 4:
        fecha_finvig = segunda_linea[3]
        estado_vigencia = segunda_linea[5]
        aprobacion = segunda_linea[4]
    else:
        fecha_finvig = ""
        estado_vigencia = ""
        aprobacion = segunda_linea[3]
    tercera_linea = respuesta[2][:max(respuesta[2].find("Sin"),respuesta[2].find("."))-1].split(" ",1)
    ambito = tercera_linea[0]
    tipo = tercera_linea[1]
    return [placa,empresa,cert,fecha_inspec,fecha_finvig,aprobacion,estado_vigencia,ambito,tipo,fecha_hoy]


def add_to_file(filename, result):
    with open(filename, mode='a', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter="|")
        writer.writerow(result)


def main_loop():
    this_thread = int(thread)
    print(f'*** Starting Thread {this_thread} ***')
    url = 'https://portal.mtc.gob.pe/reportedgtt/form/frmconsultaplacaitv.aspx'
    for k, placa in enumerate(list_of_pending_placas(str(this_thread))):
        if k == 5:
            print(f'End session {this_thread}')
            return
        print(f'({this_thread}){k} Placa:{placa}|', end='')
        try:
            scrape = extract(placa, url, str(this_thread))
            resultado = analizar_respuesta(placa, scrape)
            add_to_file('resultados'+str(this_thread)+'.txt', resultado)
        except KeyboardInterrupt:
            quit()
        except:
            pass


# Start Program

if len(sys.argv) != 3:
    print('Need two arguments')
    quit()

sessions = int(sys.argv[1])
max_placas = int(sys.argv[2])

# Take main input file with placas and split into files with max_placas each
split(sessions, max_placas)

all_threads = []
for thread in range(sessions):
    new_thread = threading.Thread(target=main_loop)
    all_threads.append(new_thread)
    new_thread.start()

_ = [i.join() for i in all_threads]  # Ensures all threads end before moving forward

os.system('cat resultados?.txt >> resultados.txt')
os.system('cat placas?.txt > placas.txt')

consolidate() # Takes forever...