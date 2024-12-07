import os
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import numpy as np
import pandas as pd
import requests

app = Flask(__name__)
CORS(app) 

current_dir = os.path.dirname(os.path.abspath(__file__))

path_nombre_archivos_provincia = os.path.join(current_dir,'data','modelos','PROV','precio_por_localidad_prov.csv')
path_nombre_archivos_CABA = os.path.join(current_dir,'data','modelos','CABA','precios_por_localidad_caba.csv')
path_nombre_archivos_BSAS = os.path.join(current_dir,'data','modelos','BSAS','precios_por_localidad_bsas.csv')

df_localidades_caba = pd.read_csv(path_nombre_archivos_CABA)
df_localidades_prov = pd.read_csv(path_nombre_archivos_provincia)
df_localidades_bsas = pd.read_csv(path_nombre_archivos_BSAS)

def obtener_localidades(df_localidades_bsas, df_localidades_prov,df_localidades_caba):
    df_localidades = pd.merge(df_localidades_bsas,df_localidades_prov, on=['localidad', 'provincia'], how='outer')
    df_localidades['cantidad_de_ambiente'] = df_localidades['cantidad_de_ambiente_x'].combine_first(df_localidades['cantidad_de_ambiente_y'])
    df_localidades['precio_m2_cubierto_medio_localidad'] = df_localidades['precio_m2_cubierto_medio_localidad_x'].combine_first(df_localidades['precio_m2_cubierto_medio_localidad_y'])
    df_localidades['precio_medio'] = df_localidades['precio_medio_x'].combine_first(df_localidades['precio_medio_y'])
    df_localidades.drop(columns=['precio_m2_cubierto_medio_localidad_x','precio_m2_cubierto_medio_localidad_y', 'cantidad_de_ambiente_y', 'cantidad_de_ambiente_x','precio_medio_x','precio_medio_y'], inplace=True)
    df_localidades = pd.merge(df_localidades, df_localidades_caba, on=['localidad', 'provincia'], how='outer')
    df_localidades['precio_medio'] = df_localidades['precio_medio_x'].combine_first(df_localidades['precio_medio_y'])
    df_localidades.drop(columns=['precio_medio_x', 'precio_medio_y'], inplace=True)
    return df_localidades

df_localidades = obtener_localidades(df_localidades_bsas,df_localidades_prov,df_localidades_caba)

model_path_caba = os.path.join(current_dir, 'data','modelos','CABA','modelo_filtrado_CABA.pkl')
scaler_path_caba = os.path.join(current_dir, 'data','modelos','CABA','scaler_CABA.joblib')
model_caba = joblib.load(model_path_caba)
scaler_caba = joblib.load(scaler_path_caba)

model_path_prov = os.path.join(current_dir, 'data','modelos','PROV','model_prov.pkl')
scaler_path_prov = os.path.join(current_dir, 'data','modelos','PROV','scaler_prov.joblib')
model_prov = joblib.load(model_path_prov)
scaler_prov = joblib.load(scaler_path_prov)

model_path_bsas = os.path.join(current_dir, 'data','modelos','BSAS','model_bsas.pkl')
scaler_path_bsas = os.path.join(current_dir, 'data','modelos','BSAS','scaler_bsas.joblib')
model_bsas = joblib.load(model_path_bsas)
scaler_bsas = joblib.load(scaler_path_bsas)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    print(data)
    
    provincia_data = data['provincia']
    localidad_data = data['localidad']
    superficie_total = data['superficie_total']
    superficie_cubierta = data['superficie_cubierta']
    cantidad_dormitorios = data['cantidad_dormitorios']
    cantidad_baños = data['cantidad_baños']
    cantidad_ambientes = data['cantidad_ambientes']

    if provincia_data == "Ciudad Autonoma de Buenos Aires":
        print("Nombres features scaler: " + scaler_caba.feature_names_in_)
        localidad = df_localidades_caba[df_localidades_caba['localidad'] == localidad_data]
        datos_entrada = [[superficie_total,superficie_cubierta,cantidad_ambientes,localidad["precio_m2_medio"].values[0],localidad["precio_m2_medio"].values[0]]]
        datos_entrada_df = pd.DataFrame(datos_entrada, columns=['superficie_total','superficie_cubierta', 'cantidad_de_ambiente', 'precio_m2','precio_m2_medio_localidad'])
        datos_entrada_escalados = scaler_caba.transform(datos_entrada_df)
        prediction = model_caba.predict(datos_entrada_escalados)

    elif provincia_data == "Zona Sur (GBA)" or provincia_data == "Zona Oeste (GBA)" or provincia_data == "Zona Norte (GBA)":
        print("Nombres features scaler: " + scaler_bsas.feature_names_in_)
        
        localidad = df_localidades_bsas[(df_localidades_bsas['localidad'] == localidad_data) & (df_localidades_bsas['cantidad_de_ambiente'] == data['cantidad_ambientes'])]
        if localidad.empty:
            localidad = df_localidades_bsas[df_localidades_bsas['localidad'] == localidad_data]
            precio_medio = localidad['precio_medio'].mean()
            precio_m2_cubierto_medio_localidad = localidad['precio_m2_cubierto_medio_localidad'].mean()
            datos_localidad = [[provincia_data,localidad_data,cantidad_ambientes,precio_m2_cubierto_medio_localidad,0,precio_medio]]
            localidad = pd.DataFrame(datos_localidad, columns=['provincia','localidad','cantidad_de_ambiente','precio_m2_cubierto_medio_localidad','precio_m2_medio','precio_medio'])

        datos_entrada = [[superficie_total,superficie_cubierta,cantidad_ambientes,localidad["precio_m2_cubierto_medio_localidad"].values[0],localidad["precio_medio"].values[0]]]
        
        datos_entrada_df = pd.DataFrame(datos_entrada, columns=['superficie_total','superficie_cubierta', 'cantidad_de_ambiente', 'precio_m2_cubierto_medio_localidad', 'precio_medio_localidad'])
        datos_entrada_escalados = scaler_bsas.transform(datos_entrada)
        
        log_prediction = model_bsas.predict(datos_entrada_escalados)
        prediction = np.exp(log_prediction) * superficie_total
    else:
        print("Nombres features scaler: " + scaler_prov.feature_names_in_)
        
        localidad = df_localidades_prov[(df_localidades_prov['localidad'] == localidad_data) & (df_localidades_prov['cantidad_de_ambiente'] == cantidad_ambientes)]
        if localidad.empty:
            localidad = df_localidades_prov[df_localidades_prov['localidad'] == localidad_data]
            precio_medio = localidad['precio_medio'].mean()
            precio_m2_cubierto_medio_localidad = localidad['precio_m2_cubierto_medio_localidad'].mean()
            datos_localidad = [[provincia_data,localidad_data,cantidad_ambientes,precio_m2_cubierto_medio_localidad,0,precio_medio]]
            localidad = pd.DataFrame(datos_localidad, columns=['provincia','localidad','cantidad_de_ambiente','precio_m2_cubierto_medio_localidad','precio_m2_medio','precio_medio'])

        datos_entrada = [[superficie_total,superficie_cubierta,cantidad_ambientes,localidad["precio_m2_cubierto_medio_localidad"].values[0],localidad["precio_medio"].values[0]]]
        
        datos_entrada_df = pd.DataFrame(datos_entrada, columns=['superficie_total','superficie_cubierta', 'cantidad_de_ambiente', 'precio_m2_cubierto_medio_localidad', 'precio_medio_localidad'])
        datos_entrada_escalados = scaler_prov.transform(datos_entrada)
        
        prediction = model_prov.predict(datos_entrada_escalados) * superficie_total
        

    prediction = round(prediction[0])
    print("Prediccion: ", prediction)

    propiedades_publicadas = obtener_propiedades_en_localidad(data["provincia"], data["localidad"])
    print("Hay " + str(propiedades_publicadas.shape[0]) + " propiedades publicadas en la localidad de " + data["localidad"] + ", provincia de " + data["provincia"])

    propiedades_similares = obtener_propiedades_similares(propiedades_publicadas, cantidad_ambientes)
    print("Hay " + str(propiedades_similares.shape[0]) + " propiedades similares publicadas en la localidad de " + data["localidad"] + ", provincia de " + data["provincia"])

    return jsonify({
    'prediction': prediction,
    'caracteristicas': {
        'propiedadesPublicadas': str(propiedades_publicadas.shape[0]),
        'propiedadesSimilares': str(propiedades_similares.shape[0]),
        'precioPromedio': str(obtener_promedio(propiedades_similares, "precio")),
        'precioMinimo': str(obtener_minimo(propiedades_similares, "precio")),
        'precioMaximo': str(obtener_maximo(propiedades_similares, "precio")),
        'metrosTotalesPromedio': str(obtener_promedio(propiedades_similares,"superficie_total")),
        'metrosCubiertosPromedio': str(obtener_promedio(propiedades_similares,"superficie_cubierta")),
        'cocheraPorcentaje': str(promedio_features_especiales(propiedades_similares,"cantidad_de_cocheras")),
        'seguridadPorcentaje': str(promedio_propiedades_con_seguridad(propiedades_similares)),
        'aireLibrePorcentaje': str(promedio_propiedades_con_patio_o_terraza(propiedades_similares)),
        'parrillaPorcentaje': str(promedio_features_especiales(propiedades_similares,"parrilla")),
        'aptoMascotaPorcentaje': str(promedio_features_especiales(propiedades_similares,"permite_mascotas")),
        'piletaPorcentaje': str(promedio_features_especiales(propiedades_similares,"pileta"))
    }
    })

@app.route('/api/provincias', methods=['GET'])
def get_provincias():
    provincias_unicas = sorted(df_localidades['provincia'].unique().tolist())
    return jsonify(provincias_unicas)

@app.route('/api/localidades', methods=['GET'])
def get_localidades():
    provincia_seleccionada = request.args.get('provincia')

    if provincia_seleccionada:
        localidades_filtradas = df_localidades[df_localidades['provincia'] == provincia_seleccionada]
        localidades = sorted(list(dict.fromkeys(localidades_filtradas['localidad'].tolist())))
    else :
        localidades = sorted(df_localidades['localidad'].tolist())

    return jsonify(localidades)


def obtener_propiedades_en_localidad(provincia, localidad):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("PROV: ",provincia)
    if provincia == "Ciudad Autonoma de Buenos Aires":
        filepath = os.path.join(current_dir, 'data','modelos','CABA','df_inmuebles_caba.csv')
    elif provincia == "Zona Sur (GBA)" or provincia == "Zona Oeste (GBA)" or provincia == "Zona Norte (GBA)":
        filepath = os.path.join(current_dir, 'data','modelos','BSAS','df_inmuebles_bsas.csv')
    else:
        filepath = os.path.join(current_dir, 'data','modelos','PROV','df_inmuebles_prov.csv')
    
    df_propiedades = pd.read_csv(filepath)
    df_propiedades = df_propiedades[(df_propiedades['provincia'] == provincia) & (df_propiedades['localidad'] == localidad)]
    
    return df_propiedades

def obtener_promedio(df_propiedades, feature):
    if len(df_propiedades) > 0:
        return round(df_propiedades[feature].mean(),2)
    return 0

def obtener_propiedades_similares(df_propiedades, ambientes):  
    df_propiedades = df_propiedades[(df_propiedades['cantidad_de_ambiente'] == ambientes)]
    return df_propiedades

def obtener_minimo(df_propiedades, feature):
    if len(df_propiedades) > 0:
        return round(df_propiedades[feature].min(),2)
    return 0

def obtener_maximo(df_propiedades, feature):
    if len(df_propiedades) > 0:
        return round(df_propiedades[feature].max(),2)
    return 0

def promedio_features_especiales(df_propiedades, feature):
    if len(df_propiedades) > 0:
        propiedades_filtradas = df_propiedades[df_propiedades[feature] > 0]
        porcentaje_filtrados = (len(propiedades_filtradas) / len(df_propiedades)) * 100
        return round(porcentaje_filtrados,2)
    return 0    


def promedio_propiedades_con_seguridad(df_propiedades):
    if len(df_propiedades) > 0:
        propiedades_con_seguridad = df_propiedades[(df_propiedades['alarma'] > 0) | (df_propiedades['vigilancia'] > 0)]
        porcentaje_con_seguridad = (len(propiedades_con_seguridad) / len(df_propiedades)) * 100
        return round(porcentaje_con_seguridad,2)
    return 0

def promedio_propiedades_con_patio_o_terraza(df_propiedades):
    if len(df_propiedades) > 0:
        promedio_propiedad_con_patio_o_terraza = df_propiedades[(df_propiedades['patio'] > 0) | (df_propiedades['jardin'] > 0) | (df_propiedades['terraza'] > 0) | (df_propiedades['balcon'] > 0) | (df_propiedades['quincho'] > 0)]
        promedio_propiedad_con_patio_o_terraza = (len(promedio_propiedad_con_patio_o_terraza) / len(df_propiedades)) * 100
        return round(promedio_propiedad_con_patio_o_terraza,2)
    return 0 

def get_val():
    url = "https://dolarhoy.com" 
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        val_div = soup.select_one('.venta .val')
        if val_div:
            val_text = val_div.text.strip() 
            val_int = int(val_text.replace('$', '').replace(',', '')) 
            print(val_int)
            return val_int
    return None

@app.route('/api/dolar', methods=['GET'])
def get_venta():
    val = get_val()
    if val is not None:
        return jsonify({'venta': val}), 200
    else:
        return jsonify({'error': 'No se pudo obtener el dato'}), 500
