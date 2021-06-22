from datetime import datetime as dt
import urllib.request

'''import csv
from PIL import Image
import pytesseract
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as WebDriverOptions
from selenium.webdriver.support.select import Select

'''

def list_of_pending_placas():
    with open('placas30.txt', mode='r', encoding='utf-8') as file:
        data_base = [i.strip() for i in file.readlines()]
    with open('resultados.txt', mode='r', encoding='utf-8') as file:
        data_resultados = [i.strip() for i in file.readlines()]
    return [i for i in data_base if i not in data_resultados]


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


def ocr(archivo_imagen):   # Local
    escala_gris = 170
    imagen_std = Image.open(archivo_imagen)
    imagen_gris = imagen_std.convert('L')
    imagen_bn = imagen_gris.point(lambda x: 0 if x < escala_gris else 255, '1')
    return pytesseract.image_to_string(imagen_bn,lang="eng")


def analizar_respuesta(placa,respuesta):
    fecha_hoy = dt.strftime(dt.now(),dt.strftime("%m/%d/%Y"))
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


def extract(placa, url):
    driver = webdriver.Chrome('/usr/bin/chromedriver', options = driver_options())
    while True:  # Loop infinito hasta salir con placa consultada
        captcha = ""
        while not captcha:
            # Activar página web
            driver.get(url)
            # Obtener y grabar imagen del captcha
            urllib.request.urlretrieve(driver.find_element_by_xpath('//img').get_attribute('src'), 'captcha.jpg')
            # Leer imagen de captcha grabado en disco
            captcha = ocr('captcha.jpg')
        driver.find_element_by_id('txtPlaca').send_keys(placa)      # Llenar campo "Nro de placa"
        driver.find_element_by_id('txtCaptcha').send_keys(captcha)  # Llenar campo de Captcha
        driver.find_element_by_id('BtnBuscar').click()              # Click Botón Buscar
        time.sleep(1)
        respuestas = [i.text for i in driver.find_elements_by_class_name('gridItemGroup')]  # Recoge resultados
        if respuestas:      # Datos completos
            print("Resultado: OK")
            driver.quit()
            return respuestas
        elif "no es correcto" in driver.find_element_by_id('lblAlertaMensaje').text:  # Error en captcha ingresado
            print("CAPTCHA INCORRECTO | ",end="", flush = True) # Reinicia loop
        else: # No se obtuvo datos de la placa
            print("Resultado: NO HAY INFORMACIÓN DE PLACA")
            driver.quit()
            return None


def main():
    url = 'https://portal.mtc.gob.pe/reportedgtt/form/frmconsultaplacaitv.aspx'
    for placa in list_of_pending_placas():
        scrape = extract(placa, url)
