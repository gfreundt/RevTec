from datetime import timedelta, datetime as dt
import urllib.request
import csv, time, os, sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as WebDriverOptions
import threading
import easyocr
import warnings
from tqdm import tqdm


class Basics:
    def __init__(self):
        # Volume arguments
        self.sessions = int(sys.argv[1])
        self.iterations = int(sys.argv[2])
        self.cycles = int(sys.argv[3])
        # Web scraping information
        self.url = 'https://portal.mtc.gob.pe/reportedgtt/form/frmconsultaplacaitv.aspx'
        self.webdriver_options = self.load_webdriver_options()
        # Define paths
        self.base_dir = '/home/gabriel/pythonCode/RevTec/'
        self.temp_dir = os.path.join(self.base_dir, 'temp')
        # Define blank counters
        self.reset_counters()

    def load_webdriver_options(self):
        '''Define options for Chromedriver'''
        options = WebDriverOptions()
        options.add_argument("--window-size=800,800")
        options.add_argument("--headless")
        options.add_argument("--silent")
        options.add_argument("--disable-notifications")
        options.add_argument("--incognito")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        return options

    def reset_counters(self):
        '''Restart all counters'''
        self.monitor = [0 for _ in range(self.sessions)]
        self.exceptions = 0
        self.results = [[] for _ in range(self.sessions)]
        self.done = [False for _ in range(self.sessions)]


def split(ses, iters):
    '''Breaks up main placas text file into the amount of files and records specified in the arguments'''
    with open(os.path.join(RUN.base_dir, 'todo_placas.txt'), mode='r', encoding='utf-8') as file:
            data_base = [i.strip() for i in file.readlines()]
            block = len(data_base)//ses
    for n in range(ses):
        with open(os.path.join(RUN.temp_dir, 'placas' + str(n) + '.txt'), mode='w', encoding='utf-8') as file:
            data_pendiente = [f'{i}\n' for i in data_base[block*n:block*(n+1)]]
            file.writelines(data_pendiente[:iters])

def consolidate_partials():
    '''Join all split result files into big one'''
    print('\nConsolidando bases de datos')
    resultados = []
    # Integrate all partial results into main file
    with open(os.path.join(RUN.base_dir,'todo_resultados.txt'), mode='a', encoding='utf-8') as file:
        for result in RUN.results:
            for item in result:
                writer = csv.writer(file, delimiter="|")
                writer.writerow(item)
                resultados.append(item[0])
    with open(os.path.join(RUN.base_dir, 'todo_placas.txt'), mode='r', encoding='utf-8') as file:
        placas = [i.strip() for i in file.readlines()]
        placas_left = [f'{i}\n' for i in tqdm(placas) if i not in resultados]
    with open(os.path.join(RUN.base_dir, 'todo_placas.txt'), mode='w', encoding='utf-8') as file:
        file.writelines(placas_left)

def list_of_pending_placas(ses):
    '''Create list with all placas in session file'''
    with open(os.path.join(RUN.temp_dir,'placas'+ses+'.txt'), mode='r', encoding='utf-8') as file:
        return [i.strip() for i in file.readlines()]

def extract(placa, url, ses):
    '''Open webpage, get captcha, solve it and retrieve placa information'''
    driver = webdriver.Chrome('/usr/bin/chromedriver', options = RUN.webdriver_options)
    while True:  # Loop infinito hasta salir con placa consultada
        captcha = ""
        while not captcha:
            driver.get(url)
            # Retrieve captcha image from web and save in temp folder as generic 'captcha#.jpg'
            captcha_filename = os.path.join(RUN.temp_dir,'captcha'+str(ses)+'.jpg')
            urllib.request.urlretrieve(driver.find_element_by_xpath('//img').get_attribute('src'), captcha_filename)
            captcha = ocr(captcha_filename)
            if not valid_captcha(captcha):
                captcha = None
        driver.find_element_by_id('txtPlaca').send_keys(placa)      # Llenar campo "Nro de placa"
        driver.find_element_by_id('txtCaptcha').send_keys(captcha)  # Llenar campo de Captcha
        driver.find_element_by_id('BtnBuscar').click()              # Click Botón Buscar
        time.sleep(0.5)
        respuestas = [i.text for i in driver.find_elements_by_class_name('gridItemGroup')]  # Recoge resultados
        if respuestas:      # Datos completos
            driver.quit()
            return respuestas
        elif "no es correcto" in driver.find_element_by_id('lblAlertaMensaje').text:  # Error en captcha ingresado
            pass
        else: # No se obtuvo datos de la placa
            driver.quit()
            return None

def valid_captcha(captcha):
    '''Validate that captcha obtained after OCR makes sense'''
    if len(captcha) != 6:
        return False
    elif not captcha.isdigit():
        return False
    return True

def valid_placa(placa):
    '''Validate that placa from list makes sense (should, because file was cleaned, but just in case)'''
    if len(placa) != 6:
        return False
    if placa[0].isdigit():
        return False
    if placa[3].isalpha() or placa[4].isalpha() or placa[5].isalpha():
        return False
    return True

def ocr(image_path):
    '''Use offline EasyOCR to convert captcha image to text'''
    result = READER.readtext(image_path)
    if len(result) > 0 and len(result[0]) > 0:
        return result[0][1]
    else:
        return ''

def analizar_respuesta(placa,respuesta):
    '''Parse the webpage response after getting placa information'''
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
    '''Write new record to split text file'''
    with open(filename, mode='a', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter="|")
        writer.writerow(result)

def thread_monitor(ses, iterations):
    '''Shows progress for each thread and controls that all finish before moving on'''
    print(f'{" Progreso ":-^{ses*8+1}}')
    while True:
        monitor = [i/iterations for i in RUN.monitor]
        p = ''
        for mon in monitor:
            p += '| ' + f'{mon:05.1%}' + ' '
        p += '| Total: ' + str(sum(RUN.monitor))
        print(p, end='\r', flush=True)
        if all(RUN.done):
            return
        time.sleep(2)

def cleaner():
    '''Erase all content from "temp" folder'''
    for file in os.listdir(RUN.temp_dir):
        os.remove(os.path.join(RUN.temp_dir, file))

def main_loop(thread):
    '''Manages the placas loop for each thread'''
    this_thread = int(thread)
    for placa in list_of_pending_placas(str(this_thread)):
        if valid_placa(placa):
            RUN.monitor[this_thread] += 1
            try:
                scrape = extract(placa, RUN.url, str(this_thread))
                resultado = analizar_respuesta(placa, scrape)
                RUN.results[this_thread].append(resultado)
            except KeyboardInterrupt:
                quit()
            except:
                RUN.exceptions += 1
    RUN.done[this_thread] = True

def main():
    fin_proceso = dt.now()+timedelta(seconds=RUN.sessions*RUN.iterations*RUN.cycles/1.6)
    print(f'Tiempo estimado = {(RUN.sessions*RUN.iterations*RUN.cycles/1.6/3600):.2f} horas. ({fin_proceso})')
    # Start cycling
    for repeat in range(int(sys.argv[3])):
        RUN.reset_counters()
        print(f'\nCiclo: {repeat+1} de {sys.argv[3]} ({(repeat+1)/int(sys.argv[3]):.1%})')
        # Take main input file with placas and split into files with max_placas each
        split(RUN.sessions, RUN.iterations)
        # Create threads to extract in parallel
        all_threads = []
        for thread in range(RUN.sessions):
            new_thread = threading.Thread(target=main_loop, args=(thread,))
            all_threads.append(new_thread)
            new_thread.start()
        # Gives control to monitor and ensures all threads end before moving forward
        thread_monitor(RUN.sessions, RUN.iterations)
        # Take results and integrate them into existing results
        consolidate_partials()
        # Clean temp files
        cleaner()
    # Backup main files in Google Drive
    if 'NOBACK' not in sys.argv:
        print('Backup en Google Drive')
        os.system('rclone copy todo_resultados.txt gDrive:/TechData/RevTec')
        os.system('rclone copy todo_placas.txt gDrive:/TechData/RevTec')
    # Close showing stats and total time
    print(f'Velocidad: {RUN.sessions*RUN.iterations*RUN.cycles:,} registros en {dt.now()-start_time} = {(RUN.sessions*RUN.iterations*RUN.cycles)/(dt.now()-start_time).total_seconds():.2f} registros/segundo.')


# Start Program
if __name__ == '__main__':
    # Init Timer
    start_time = dt.now()   
    # Init OCR
    warnings.filterwarnings('ignore')
    READER = easyocr.Reader(['en'], gpu=False)
    # Validate arguments for Threads (sessions), Iterations and Cycles
    if len(sys.argv) < 3:
        raise Exception('Obligatorio tres argumentos. Formato: scraper.py #hilos #búsquedas por hilo #ciclos')
    # Init Global variables
    RUN = Basics()
    # Start Program
    main()