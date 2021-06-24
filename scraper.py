from datetime import datetime as dt
import urllib.request
import csv, time, json
from PIL import Image
import pytesseract
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as WebDriverOptions
from selenium.webdriver.support.select import Select
import requests
import os


def consolidate():
    with open('placas.txt', mode='r', encoding='utf-8') as file:
        data_base = [i.strip() for i in file.readlines()]
        print(len(data_base))
    with open('resultados.txt', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='|')
        data_resultados = [i[0] for i in reader]
        print(len(data_resultados))
    with open('placas.txt', mode='w', encoding='utf-8') as file:
        data_pendiente = [f'{i}\n' for i in data_base if i not in data_resultados]
        file.writelines(data_pendiente)
        print(len(data_pendiente))


def get_ocr_keys():
    with open('ocr_keys.json', mode='r') as file:
        data = json.load(file)['data']
        keys = [i['key'] for i in data]
    return keys


def list_of_pending_placas():
    with open('placas.txt', mode='r', encoding='utf-8') as file:
        return [i.strip() for i in file.readlines()]


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


def extract(placa, url, ocr_key):
    driver = webdriver.Chrome('/usr/bin/chromedriver', options = driver_options())
    while True:  # Loop infinito hasta salir con placa consultada
        miss_counter = 0
        captcha = ""
        while not captcha:
            # Activar página web
            driver.get(url)
            # Obtener y grabar imagen del captcha
            urllib.request.urlretrieve(driver.find_element_by_xpath('//img').get_attribute('src'), 'captcha.jpg')
            # Leer imagen de captcha grabado en disco
            captcha = ocr2('captcha.jpg', api_key=ocr_key)
            if miss_counter == 10:
                raise Exception # force an error to switch to the next OCR key
            else:
                miss_counter += 1
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


def ocr2(image_path, api_key, overlay=False, language='eng'):   # API
    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    with open(image_path, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={image_path: f},
                          data=payload,
                          )
    respuesta = r.content.decode()

    if "ParsedText" in respuesta:
        pos0 = respuesta.index("ParsedText") + 13
        pos1 = respuesta.index('"',pos0)
        return respuesta[pos0:pos1-4]
    else:
        return ""


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
    ocr_keys = get_ocr_keys()
    use_ocr_key = ocr_keys[0]
    ocr_key_index = 0
    url = 'https://portal.mtc.gob.pe/reportedgtt/form/frmconsultaplacaitv.aspx'
    
    for k, placa in enumerate(list_of_pending_placas()):
        try:
            print(k, placa,"|",end="")
            scrape = extract(placa, url, use_ocr_key)
            resultado = analizar_respuesta(placa, scrape)
            add_to_file('resultados.txt', resultado)
        except:
            ocr_key_index += 1
            if ocr_key_index < len(ocr_keys):
                use_ocr_key = ocr_keys[ocr_key_index]
                print('Cambio de OCR Key')
            else:
                print('End of OCR keys')
                return




consolidate()
main()
