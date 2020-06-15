# -*- coding: utf-8 -*-


from opentrons import protocol_api
#from opentrons import simulate
import itertools
import json


#protocol = simulate.get_protocol_api('2.4')


metadata = {
    'protocolName': 'Pooling Test',
    'author': 'Mario Moncada Soria, Andrés Montes Cabrero, Sergio Perez Raya, Victoriano Giralt',
    'source': 'Hospital Regional Universitario de Málaga',
    'apiLevel': '2.4',
    'description': 'Prueba Pooling con Máquina A1',
    'lastModification' : '14:04 09/06/2020'
}
''' #Ejemplo de configuración
configuracion = {
    'numero_muestras' : 96,
    'numeroMuestras_porPool' : 6,
    'volumen_transferencia': 200,
    'velocidad_aspiracion':100,
    'altura_aspiracion': 5,
    'posicion_primera_punta' : 'A1'
            }
'''
def getList_wellsByRow(labware): #Returns a list of wells ordered by row 
    
    labware_by_rows = labware.rows()
    
    return_list = list(itertools.chain.from_iterable(labware_by_rows))
    
    return return_list
        
'''    
def imprimir_lista_prueba(lista_prueba):

    print('\n\n\n')
    for tubo_salida in lista_prueba:
        print('Tubo de salida:', tubo_salida[0])
        print(' ')
        print('Tubos de muestra:')
        for muestra in tubo_salida[1]:
            print(muestra)
        print('------------------------------------------')
        print(' ')
'''
    
def generar_lista_prueba(configuracion, lista_racks_muestras, lista_racks_salidas):
    
    #lista_muestras = muestras_1.rows()
    #lista_muestras.append(muestras_2.rows())
    
    # !!! Guarrada, hay que cambiarlo.
    muestras = getList_wellsByRow(lista_racks_muestras[0])
    muestras += getList_wellsByRow(lista_racks_muestras[1])
    muestras += getList_wellsByRow(lista_racks_muestras[2])
    muestras += getList_wellsByRow(lista_racks_muestras[3])
    salidas = getList_wellsByRow(lista_racks_salidas)
    lista_prueba = []
    
    if configuracion['numeroMuestras_porPool'] > configuracion['numero_muestras']:
        configuracion['numero_muestras'] = configuracion['numeroMuestras_porPool']

    for i in range(0,int(configuracion['numero_muestras']/configuracion['numeroMuestras_porPool'])):
        lista_1 = []
        lista_1.append(salidas[i])
        lista_2 = muestras[i*configuracion['numeroMuestras_porPool']:configuracion['numeroMuestras_porPool']+i*configuracion['numeroMuestras_porPool']]
        lista_1.append(lista_2)
        lista_prueba.append(lista_1)
    
    if configuracion['numero_muestras'] % configuracion['numeroMuestras_porPool'] > 0:
        i+=1 # Para que sea el siguiente tubo de salida
        lista_1 = []
        lista_1.append(salidas[i])
        lista_2 = muestras[i*configuracion['numeroMuestras_porPool']:(configuracion['numero_muestras'] % configuracion['numeroMuestras_porPool'])+i*configuracion['numeroMuestras_porPool']]
        lista_1.append(lista_2)
        lista_prueba.append(lista_1)
        
        
    return lista_prueba

def get_remainingTips(labware): # Como sacar el numero de pipetas que quedan en un objeto de tipo Labware de tipracks usando la API
    
    if type(labware) is list: 
        remainingTips=0
        for tipRack in labware: 
            remainingTips+=sum([well.has_tip for well in tipRack.wells()])
        
    elif type(labware) is protocol_api.labware.Labware:
        remainingTips = sum([well.has_tip for well in labware.wells()]) # Como sacar el numero de pipetas que quedan en un tiprack
   
    else:
        remainingTips = 0
        
    return remainingTips


def transferencia_customizada (pipeta,configuracion, origen, destino):
    
    # Copiamos los valores del diccionario. 
    volumen_aspiracion = configuracion['volumen_transferencia']
    volumen_dispensacion = configuracion['volumen_transferencia']
    velocidad_aspiracion = configuracion['velocidad_aspiracion']
    altura_aspiracion = configuracion['altura_aspiracion']
    
    # Transferencia
    pipeta.pick_up_tip()
    
    pipeta.flow_rate.aspirate = velocidad_aspiracion 
    
    pipeta.aspirate(volumen_aspiracion, origen.bottom(z= altura_aspiracion))
    
    pipeta.dispense(volumen_dispensacion, destino)
    
    pipeta.blow_out(destino)
    
    pipeta.drop_tip()
    
    

def configurar_tipRack(tipRack, posicion_primera_punta):  # Quitamos puntas de del tipRack, objeto Labware. Para que la api se apañe con las puntas que tiene el tipRack.
    
    # !!! Esto es una guarrada, hay que cambiarlo. 
    tipRack.wells_by_name()
    
    if len(posicion_primera_punta) < 3:
        posicion_primera_punta += ' '
        
    for well in tipRack.wells():
        
        if well.display_name[0:3] == posicion_primera_punta:
            break
        else:
            well.has_tip = False
    num_tips = get_remainingTips(tipRack)
    
    
    return num_tips

def get_configuracion(protocol, tipRack):
    
    if not protocol.is_simulating():
        with open('/var/lib/jupyter/notebooks/configuracion_pooling.json', 'r') as archivo:
            configuracion = json.load(archivo)
    else:
        configuracion = {
            'numero_muestras' : 96,
            'numeroMuestras_porPool' : 6,
            'volumen_transferencia': 200,
            'velocidad_aspiracion':100,
            'altura_aspiracion': 5,
            'posicion_primera_punta' : 'A1'
                    }
    num_tips = configurar_tipRack(tipRack, configuracion['posicion_primera_punta'])
    
    if (configuracion['numero_muestras'] < 1) or (configuracion['numero_muestras'] > 96) :
        raise ValueError('Número de muestras fuera de parámetros')
        
    if (configuracion['volumen_transferencia'] < 50) or (configuracion['volumen_transferencia'] > 900) :
        raise ValueError('Volumen de transferencia incorrecto')
        
    if (configuracion['altura_aspiracion'] < 1) or (configuracion['altura_aspiracion'] > 30) :
        raise ValueError('Volumen de transferencia incorrecto')

    if (configuracion['velocidad_aspiracion'] < 50) or (configuracion['velocidad_aspiracion'] > 130) :
        raise ValueError('Velocidad aspiración incorrecta')
        
    if configuracion['numeroMuestras_porPool']<1:
        raise ValueError('Valor del número de muestras por pool incorrecto')
    
    if configuracion['numero_muestras'] > num_tips:
        raise ValueError('Número de puntas insuficiente')
        
    
    
    return configuracion
        

def run (protocol : protocol_api.ProtocolContext):

    #--------------CARGA DE LABWARE-----------------------------
    
    #Definición labware muestras de entrada.
    muestras_1 = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_screwcap', 4)
    muestras_2 = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_screwcap', 1)
    muestras_3 = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_screwcap', 6)
    muestras_4 = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_screwcap', 3)
    
    #Definición labware tubos de salida. 'opentronstubos_24_aluminumblock_5000ul'
    tubos_salida = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_screwcap',2)
    
    #Definición TipRacks
    tipRack_1000 = protocol.load_labware('opentrons_96_tiprack_1000ul', 10)
    
    
    #--------------CARGAR CONFIGURACION-------------------------
    configuracion = get_configuracion(protocol, tipRack_1000)
    

    #Definición pipetas
    p1000 = protocol.load_instrument('p1000_single_gen2', 'left', tip_racks=[tipRack_1000])
    
    #Generar una lista (de listas) con los tubos de salidas y sus respectivas entradas por cada uno
    lista_prueba = generar_lista_prueba(configuracion,[muestras_1,muestras_2,muestras_3,muestras_4],tubos_salida)
    

    for ronda in lista_prueba:
        salida = ronda[0]
        for muestra in ronda[1]:
            transferencia_customizada (p1000,configuracion, muestra, salida)
            
    
    
#run(protocol)


    
