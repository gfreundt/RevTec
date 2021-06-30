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
from PIL import Image
import hashlib
import gpyocr


class Basics:
    def __init__(self, ses):
        self.monitor = [0 for _ in range(ses)]
        #self.captcha_table_data, self.captcha_table_keys = self.load_captcha_hashes()
        self.webdriver_options = self.load_webdriver_options()
        self.url = 'https://portal.mtc.gob.pe/reportedgtt/form/frmconsultaplacaitv.aspx'
        self.exceptions = 0
        self.next_pending_image = len(os.listdir('/home/gabriel/pythonCode/RevTec/pending_images/')) + 1

    def load_captcha_hashes(self):
        with open('/home/gabriel/pythonCode/RevTec/captcha_hashes.txt', mode='r', encoding='utf-8') as hash_file:
            hashes = hash_file.readlines()
        captcha_table = {h.split('.')[0].strip():int(h.split('.')[1]) for h in hashes}
        return captcha_table, captcha_table.keys()
    
    def load_webdriver_options(self):
        options = WebDriverOptions()
        options.add_argument("--window-size=800,800")
        options.add_argument("--headless")
        #options.add_argument("--disable-gpu")
        options.add_argument("--silent")
        options.add_argument("--disable-notifications")
        options.add_argument("--incognito")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        return options


def split(q):
    with open('todo_placas.txt', mode='r', encoding='utf-8') as file:
            data_base = [i.strip() for i in file.readlines()]
            records = len(data_base)
            block = records//q
    for n in range(q):
        with open('placas' + str(n) + '.txt', mode='w', encoding='utf-8') as file:
            data_pendiente = [f'{i}\n' for i in data_base[block*n:block*(n+1)]]
            file.writelines(data_pendiente)


def consolidate(q):
    for i in range(q):
        filenum = str(i)
        with open('placas'+filenum+'.txt', mode='r', encoding='utf-8') as file:
            data_base = [i.strip() for i in file.readlines()]
        with open('resultados'+filenum+'.txt', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='|')
            data_resultados = [i[0] for i in reader]
            r = len(data_resultados)
        with open('placas'+filenum+'.txt', mode='w', encoding='utf-8') as file:
            data_pendiente = [f'{i}\n' for i in tqdm(data_base, desc='File'+str(i)) if i not in data_resultados]
            file.writelines(data_pendiente)
            s = len(data_pendiente)
        print(f'File: {i} - Completas: {r} / Totales: {s}  =  {r/s*100:.2f}%')


def list_of_pending_placas(ses):
    with open('placas'+ses+'.txt', mode='r', encoding='utf-8') as file:
        p = [i.strip() for i in file.readlines()]
        return p


def extract(placa, url, ses):
    driver = webdriver.Chrome('/usr/bin/chromedriver', options = run.webdriver_options)
    while True:  # Loop infinito hasta salir con placa consultada
        captcha = ""
        while not captcha:
            driver.get(url)
            urllib.request.urlretrieve(driver.find_element_by_xpath('//img').get_attribute('src'), 'captcha'+ses+'.jpg')
            
            # See if hash in database to avoid using OCR
            #captcha_hash = hashlib.md5(Image.open('captcha'+ses+'.jpg').tobytes())
            #captcha_hash = captcha_hash.hexdigest()
            #if captcha_hash in captcha_table_keys:
            #    captcha = captcha_table_data[captcha_hash]
            #    print('*** Woohoo ***')
            #else:  # If hash not in database, go with OCR
            captcha = ocr4('captcha'+ses+'.jpg')
            if not captcha:
                # Copy captcha into directory to be processed some other time
                os.system('cp captcha'+ses+'.jpg ' + os.path.join('pending_images',f'pend{run.next_pending_image:06}.jpg'))
                run.next_pending_image += 1

                
        driver.find_element_by_id('txtPlaca').send_keys(placa)      # Llenar campo "Nro de placa"
        driver.find_element_by_id('txtCaptcha').send_keys(captcha)  # Llenar campo de Captcha
        driver.find_element_by_id('BtnBuscar').click()              # Click Botón Buscar
        time.sleep(0.5)
        respuestas = [i.text for i in driver.find_elements_by_class_name('gridItemGroup')]  # Recoge resultados
        if respuestas:      # Datos completos
            # Save captcha correctly identified
            os.system('cp --backup=numbered captcha'+ses+'.jpg ' +  os.path.join("images",captcha+".jpg"))
            driver.quit()
            return respuestas
        elif "no es correcto" in driver.find_element_by_id('lblAlertaMensaje').text:  # Error en captcha ingresado
            pass
        else: # No se obtuvo datos de la placa
            # Save captcha correctly identified
            os.system('cp --backup=numbered captcha'+ses+'.jpg ' +  os.path.join("images",captcha+".jpg"))
            driver.quit()
            return None


def valid_placa(placa):
    if len(placa) != 6:
        return False
    if placa[0].isdigit():
        return False
    if placa[3].isalpha() or placa[4].isalpha() or placa[5].isalpha():
        return False
    return True
    

def ocr4(image_path):
    try:
        r = gpyocr.tesseract_ocr(image_path, psm=7)[0].strip()
        captcha_guessed = ''.join([i for i in r if i.isdigit()])
        if len(captcha_guessed) == 6:
            return captcha_guessed
        else:
            return ''
    except:
        return ''

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


def thread_monitor(ses, iterations):
    print(f'{" Progress ":-^{ses*8+1}}')
    while True:
        monitor = [i/(iterations+1) for i in run.monitor]
        p = ''
        for mon in monitor:
            p += '| ' + f'{mon:05.1%}' + ' '
        p += '| Running: ' + str(sum(run.monitor)-ses+1)
        print(p, end='\r', flush=True)
        if monitor.count(1) == ses:
            print('\n')
            return
        time.sleep(2)


def dashboard(start, opt=True):
    total = len(os.listdir(IMAGE_FOLDER))
    # Count records for done and pending
    with open('todo_placas.txt', mode='r') as file:
        placas = len([i for i in file.readlines()])
    with open('todo_resultados.txt', mode='r') as file:
        resultados = len([i for i in file.readlines()])

    print('*'*10, 'Stats', '*'*10)
    print(f'Total Captchas: {total:,}')
    print(f'Total Results: {resultados:,} ({resultados/placas*100:.2f}%)\nPlacas Pending: {placas:,}')
    if opt:
        records = int(sys.argv[1]) * int(sys.argv[2])
        time_taken = dt.now() - start
        print(f'Total Exceptions: {run.exceptions:,} = {run.exceptions/records:.2%}')
        print(f'Process Rate: {records:,} records in {time_taken} = {records/time_taken.total_seconds():.2f} records/second')
    print('*'*10, 'End Stats', '*'*10)


def cleaner(fpath):
    # Clean captchas without 'jpg' in name
    for f in os.listdir(IMAGE_FOLDER):
        if 'jpg' not in f:
            os.remove(os.path.join(IMAGE_FOLDER,f))
    # Eliminate duplicates from placas source file
    with open(fpath, mode='r', encoding='utf-8') as file:
        all_data = set([i.strip() for i in file.readlines()])
        pure = [i for i in tqdm(all_data) if valid_placa(i)]
    with open(fpath, mode='w', encoding='utf-8', newline="\n") as file:
        for item in pure:
            file.write(f'{item}\n')


def hasher(directory):
    desc = 'Hashing Captchas'
    files = os.listdir(directory)
    md5hashes = []
    for file in tqdm(files, desc=desc):
        if '~' not in file:
            md5hash = hashlib.md5(Image.open(os.path.join(directory,file)).tobytes())
            md5hashes.append(md5hash.hexdigest()+'.'+file[:6])
    with open('/home/gabriel/pythonCode/RevTec/captcha_hashes.txt', mode='w', encoding='utf-8') as hash_file:
        data_to_write = [f'{i}\n' for i in md5hashes]
        hash_file.writelines(data_to_write)
    print(f'Total unique hashes: {len(data_to_write):,} out of {len(files):,} files.')


def main_loop():
    this_thread = int(thread)
    for k, placa in enumerate(list_of_pending_placas(str(this_thread))):
        run.monitor[this_thread] += 1
        if k == iterations:
            return
        try:
            scrape = extract(placa, run.url, str(this_thread))
            resultado = analizar_respuesta(placa, scrape)
            add_to_file('resultados'+str(this_thread)+'.txt', resultado)
        except KeyboardInterrupt:
            quit()
        except:
            run.exceptions += 1
            print(f'Exception Thread: {this_thread}')



# Start Program

if __name__ == '__main__':

    # Init variables
    IMAGE_FOLDER = '/home/gabriel/pythonCode/RevTec/images'
    start_time = dt.now()
    sessions = int(sys.argv[1])
    iterations = int(sys.argv[2])
    run = Basics(sessions)

    # Checks for file that indicates completed previous run
    if os.path.exists('/home/gabriel/pythonCode/RevTec/completed.sig'):

        # Remove file that indicates process complete
        os.remove('/home/gabriel/pythonCode/RevTec/completed.sig')
    
        # Print current state    
        dashboard(0, opt=False)

        if len(sys.argv) < 3:
            raise Exception('Need two arguments')

        # Take main input file with placas and split into files with max_placas each
        split(sessions)

        # Create threads to extract in parallel
        all_threads = []
        for thread in range(sessions):
            new_thread = threading.Thread(target=main_loop)
            all_threads.append(new_thread)
            new_thread.start()

        # Ensure all threads end before moving forward
        thread_monitor(sessions, iterations)
        #_ = [i.join() for i in all_threads]
        
        # Join all split result files into big one
        print('Consolidando bases de datos')
        os.system('cat resultados*.txt >> todo_resultados.txt')

    else:
        print('Completing previous run')
        sessions = len([i for i in os.listdir('/home/gabriel/pythonCode/RevTec/') if 'resultados' in i]) - 1

    # Clean placas split files by removing processed placas
    consolidate(sessions)

    # Join all split placas files into big one
    os.system('cat placas*.txt > todo_placas.txt')

    # Erase all temporary files
    os.system('rm captcha*.jpg')
    os.system('rm resultados*.txt')
    os.system('rm placas*.txt')

    # Clean files and directories
    cleaner('todo_placas.txt')

    # Create hash for all images into txt file
    hasher(IMAGE_FOLDER)

    # Backup main files in Google Drive
    if 'NOBACK' not in sys.argv:
        print('Backing up in Google Drive')
        try:
            os.system('rclone copy todo_resultados.txt gDrive:/TechData/RevTec')
            os.system('rclone copy todo_placas.txt gDrive:/TechData/RevTec')
            os.system('rclone copy captcha_hashes.txt gDrive:/TechData/RevTec')
        except:
            print('Error with GDrive backup!')

    # Close with stats
    dashboard(start_time)

    # Normal exit... write file that marks as completed
    with open('/home/gabriel/pythonCode/RevTec/completed.sig', 'w') as file:
        file.write(' ')
