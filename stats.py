import pandas as pd
import os
from datetime import datetime as dt


def load_data():
    # Define paths
    base_dir = '/home/gabriel/pythonCode/RevTec/'
    pendientes = os.path.join(base_dir, 'todo_placas.txt')
    resultados = os.path.join(base_dir, 'todo_resultados.txt')
    # Into Arrays
    return pd.read_csv(pendientes, delimiter='|', header=None), pd.read_csv(resultados,delimiter='|', header=None)

def linea(text):
    return f'{text:-^33}'

def caja(text):
    s = linea('') + '\n' + f'{text:^33}' + '\n' + linea('')
    return s

def main():
    df1, df2 = load_data()
    df1.columns = ['Placa']
    df2.columns = ['Placa', 'Empresa_Certificadora', 'Certificado', 'Vigente_Desde', 'Vigente_Hasta', 'Resultado_Inspeccion', 'Estado', 'Ambito', 'Tipo_Servicio', 'Fecha_Consulta']
    df2['Vigente_Desde'] = pd.to_datetime(df2['Vigente_Desde'])
    df2['Vigente_Hasta'] = pd.to_datetime(df2['Vigente_Hasta'])
    df2['Fecha_Consulta'] = pd.to_datetime(df2['Fecha_Consulta'])

    pendientes = df1['Placa'].count()
    procesados = df2['Placa'].count()
    total = pendientes + procesados

    sin_certi = sum(pd.isnull(df2['Vigente_Hasta']))
    con_certi = procesados - sin_certi

    vencidos = df2[df2['Vigente_Hasta']<dt.now()].count()['Placa']
    vigentes = df2[df2['Vigente_Hasta']>=dt.now()].count()['Placa']

    #EC = df2['Empresa_Certificadora'].value_counts()

    print(caja('Bases de Datos'))
    print(f' Procesados: {procesados:>10,} ({procesados/total:.2%})')
    print(f' Pendientes: {pendientes:>10,} ({pendientes/total:.2%})')
    print(f'      Total: {total:>10,}')
    print(caja('Procesados'))
    print(f' Sin Certificado: {sin_certi:>10,} ({sin_certi/procesados:.2%})')
    print(f' Con Certificado: {con_certi:>10,} ({con_certi/procesados:.2%})')
    print(caja('Con Certificado'))
    print(f' Vigentes: {vigentes:>10,} ({vigentes/con_certi:.2%})')
    print(f' Vencidos: {vencidos:>10,} ({vencidos/con_certi:.2%})')

if __name__ == '__main__':
    main()