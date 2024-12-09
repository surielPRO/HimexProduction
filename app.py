from flask import Flask, jsonify, render_template
import pandas as pd
import pyodbc
from datetime import datetime

# Configuración de la base de datos


# Crear aplicación Flask
app = Flask(__name__)

# Ruta principal (Dashboard)
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

# Ruta para Justo a Tiempo
@app.route('/jit')
def jit():
    return render_template('jit.html')

@app.route('/speed')
def speed():
    return render_template('speed.html')

# Ruta para datos de producción (API)
@app.route('/api/data')
def get_data():
    try:
        # Conexión a la base de datos
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
        )
        today = datetime.now().strftime('%Y-%m-%d')

        # Consulta SQL para datos del día actual y máquinas en rango
        query = f"""
            SELECT 
                productiondata_timestamp, 
                productiondata_quantity, 
                productiondata_scrap,
                productiondata__device_id
            FROM mde.productiondata
            WHERE CAST(productiondata_timestamp AS DATE) = '{today}'
              AND productiondata__device_id BETWEEN 1 AND 14
            ORDER BY productiondata_timestamp ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return jsonify({'hourly_data': [], 'metrics': {}})

        # Inicializar variables de seguimiento por máquina
        previous_values = {machine_id: {'production': 0, 'scrap': 0} for machine_id in df['productiondata__device_id'].unique()}
        total_production = 0
        total_scrap = 0

        # Iterar por filas para ajustar los totales
        for _, row in df.iterrows():
            device_id = row['productiondata__device_id']
            current_production = row['productiondata_quantity']
            current_scrap = row['productiondata_scrap']

            # Obtener valores previos
            prev_production = previous_values[device_id]['production']
            prev_scrap = previous_values[device_id]['scrap']

            # Ajustar totales según cambios
            if current_production != prev_production:
                total_production += current_production - prev_production
            if current_scrap != prev_scrap:
                total_scrap += current_scrap - prev_scrap

            # Actualizar valores previos
            previous_values[device_id]['production'] = current_production
            previous_values[device_id]['scrap'] = current_scrap

        # Calcular la eficiencia
        efficiency = (total_production / (total_production + total_scrap)) * 100 if total_production > 0 else 0

        # Agrupación por hora
        df['hour'] = df['productiondata_timestamp'].dt.hour
        hourly_data = df.groupby('hour').agg({
            'productiondata_quantity': 'sum',  # Producción real por hora
            'productiondata_scrap': 'sum'     # Scrap por hora
        }).reset_index()

        # Convertir los datos por hora en una lista
        hourly_chart_data = hourly_data.to_dict(orient='records')

        data = {
            'metrics': {
                'total_production': total_production,
                'total_scrap': total_scrap,
                'efficiency': round(efficiency, 2)
            },
            'hourly_data': hourly_chart_data
        }

        return jsonify(data)

    except Exception as e:
        print(f"Error en el servidor: {e}")
        return jsonify({'error': 'Error retrieving data'})


@app.route('/api/jit')
def calculate_jit():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
        )
        today = datetime.now().strftime('%Y-%m-%d')

        query = f"""
            SELECT 
                productiondata_timestamp, 
                productiondata_quantity, 
                productiondata_target_quantity,
                productiondata__device_id
            FROM mde.productiondata
            WHERE CAST(productiondata_timestamp AS DATE) = '{today}'
              AND productiondata__device_id BETWEEN 1 AND 14
            ORDER BY productiondata_timestamp ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return jsonify({'jit_data': [], 'total_actual': 0, 'total_planned': 0})

        # Inicializar variables de seguimiento por máquina
        previous_values = {machine_id: {'actual': 0, 'planned': 0} for machine_id in df['productiondata__device_id'].unique()}
        total_actual = 0
        total_planned = 0

        # Iterar por filas para ajustar los totales
        for _, row in df.iterrows():
            device_id = row['productiondata__device_id']
            current_actual = row['productiondata_quantity']
            current_planned = row['productiondata_target_quantity']

            # Obtener valores previos
            prev_actual = previous_values[device_id]['actual']
            prev_planned = previous_values[device_id]['planned']

            # Ajustar totales según cambios
            if current_actual != prev_actual:
                total_actual += current_actual - prev_actual
            if current_planned != prev_planned:
                total_planned += current_planned - prev_planned

            # Actualizar valores previos
            previous_values[device_id]['actual'] = current_actual
            previous_values[device_id]['planned'] = current_planned

        # Agrupación por hora
        df['hour'] = df['productiondata_timestamp'].dt.hour
        hourly_data = df.groupby('hour').agg({
            'productiondata_quantity': 'sum',
            'productiondata_target_quantity': 'sum'
        }).reset_index()

        jit_data = []
        for _, row in hourly_data.iterrows():
            hour = row['hour']
            planned = row['productiondata_target_quantity']
            actual = row['productiondata_quantity']
            compliance = (actual / planned) * 100 if planned > 0 else 0

            jit_data.append({
                'hour': hour,
                'planned': planned,
                'actual': actual,
                'compliance': round(compliance, 2)
            })

        return jsonify({
            'jit_data': jit_data,
            'total_actual': total_actual,
            'total_planned': total_planned
        })

    except Exception as e:
        print(f"Error en el servidor: {e}")
        return jsonify({'error': 'Error retrieving data'})



# Ruta para la velocidad de producción (API)
@app.route('/api/speed')
def production_speed():
    try:
        # Conexión a la base de datos
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
        )
        today = datetime.now().strftime('%Y-%m-%d')

        # Consulta SQL para datos de velocidad de producción
        query = f"""
            SELECT 
                productiondata_timestamp, 
                productiondata_speed, 
                productiondata__device_id
            FROM mde.productiondata
            WHERE CAST(productiondata_timestamp AS DATE) = '{today}'
              AND productiondata__device_id BETWEEN 1 AND 14
            ORDER BY productiondata_timestamp ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return jsonify({'speed_data': [], 'average_speed': 0})

        # Calcular la velocidad promedio global
        average_speed = df['productiondata_speed'].mean()

        # Agrupar por máquina para obtener velocidad promedio por máquina
        speed_data_by_machine = df.groupby('productiondata__device_id').agg({
            'productiondata_speed': 'mean'
        }).reset_index()

        # Convertir los datos en formato JSON
        speed_data = speed_data_by_machine.to_dict(orient='records')

        return jsonify({
            'speed_data': speed_data,  # Velocidad por máquina
            'average_speed': round(average_speed, 2)  # Velocidad promedio global
        })

    except Exception as e:
        print(f"Error en el servidor: {e}")
        return jsonify({'error': 'Error retrieving speed data'})



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


