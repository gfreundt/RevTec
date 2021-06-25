from datetime import datetime as dt
import urllib.request
import csv, time, json
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as WebDriverOptions
from selenium.webdriver.support.select import Select
import os
from google.cloud import vision
import io
import sys


def consolidate():
    print('Consolidando bases de datos...')
    with open('placas.txt', mode='r', encoding='utf-8') as file:
        data_base = [i.strip() for i in file.readlines()]
    with open('resultados.txt', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='|')
        data_resultados = [i[0] for i in reader]
        r = len(data_resultados)
    with open('placas.txt', mode='w', encoding='utf-8') as file:
        data_pendiente = [f'{i}\n' for i in data_base if i not in data_resultados]
        file.writelines(data_pendiente)
        s = len(data_pendiente)
    print(f'Completas: {r} / Totales: {s}  =  {r/s*100:.2f}%')


def list_of_pending_placas():
    with open('placas'+str(session)+'.txt', mode='r', encoding='utf-8') as file:
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


def extract(placa, url):
    driver = webdriver.Chrome('/usr/bin/chromedriver', options = driver_options())
    while True:  # Loop infinito hasta salir con placa consultada
        captcha = ""
        while not captcha:
            # Activar página web
            driver.get(url)
            # Obtener y grabar imagen del captcha
            urllib.request.urlretrieve(driver.find_element_by_xpath('//img').get_attribute('src'), 'captcha'+str(session)+'.jpg')
            # Leer imagen de captcha grabado en disco
            #captcha = ocr2('captcha.jpg', api_key=ocr_key)
            captcha = ocr3('captcha'+str(session)+'.jpg')
            #if miss_counter == 10:
            #    raise Exception # force an error to switch to the next OCR key
            #else:
            #    miss_counter += 1
        driver.find_element_by_id('txtPlaca').send_keys(placa)      # Llenar campo "Nro de placa"
        driver.find_element_by_id('txtCaptcha').send_keys(captcha)  # Llenar campo de Captcha
        driver.find_element_by_id('BtnBuscar').click()              # Click Botón Buscar
        time.sleep(1)
        respuestas = [i.text for i in driver.find_elements_by_class_name('gridItemGroup')]  # Recoge resultados
        if respuestas:      # Datos completos
            print("Resultado: OK")
            save_captcha(captcha)
            driver.quit()
            return respuestas
        elif "no es correcto" in driver.find_element_by_id('lblAlertaMensaje').text:  # Error en captcha ingresado
            print("CAPTCHA INCORRECTO | ",end="", flush = True) # Reinicia loop
        else: # No se obtuvo datos de la placa
            print("Resultado: NO HAY INFORMACIÓN DE PLACA")
            driver.quit()
            return None

def save_captcha(captcha):
    n = 0
    while True:
        if os.path.exists(os.path.join("images",captcha+".jpg")):
            n += 1
        else:
            os.system('cp captcha.jpg ' +  os.path.join("images",captcha+'_'+str(n)+".jpg"))
            return


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


def main():
    url = 'https://portal.mtc.gob.pe/reportedgtt/form/frmconsultaplacaitv.aspx'
    for k, placa in enumerate(list_of_pending_placas()):
        print(f'({session}){k} Placa:{placa}|', end='')
        try:
            scrape = extract(placa, url)
            resultado = analizar_respuesta(placa, scrape)
            add_to_file('resultados'+str(session)+'.txt', resultado)
        except KeyboardInterrupt:
            quit()
        except:
            pass



try:
    session = sys.argv[1] 
except:
    consolidate()
    quit()

main()
