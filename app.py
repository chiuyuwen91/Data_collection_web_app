from flask import Flask, render_template, request, redirect, jsonify, send_from_directory
import decimal
# import mysql.connector
import os
import psycopg2
from flask_cors import CORS
import input_demo
import logging
import pandas as pd

app = Flask(__name__, static_folder='app')
# app._static_folder = 'app'
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_connection():
    connection = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=5432,
        database="postgres",
        user="postgres",
        password=1234
    )
    return connection

@app.route('/')
def serve_index():
    return render_template('main_menu.html') #render_template('main_menu.html')# send_from_directory(app.static_folder, 'index.html')

@app.route('/household_info')
def household_info():
    return render_template('household_info.html')

@app.route('/new_appliance', methods=['GET'])
def new_appliance():
    return render_template('add_appliance.html')

@app.route('/main_menu', methods=['GET'])
def main_menu():
    return render_template('main_menu.html')

@app.route('/water_heater_statistics_by_state', methods=['GET'])
def water_heater_statistics():
    return render_template('water_heater_statistics_by_state.html')

@app.route('/water_heater_drill_down', methods=['GET'])
def water_drill_down():
    state = request.args.get('state', 'state')
    return render_template('water_heater_drill_down.html', state=state)

@app.route('/radius', methods=['GET'])
def radius():
    return render_template('radius.html')

@app.route('/top_25_report', methods=['GET'])
def top_25_report():
    return render_template('top_25_report.html')

@app.route('/heating_cooling_method_details', methods=['GET'])
def heating_cooling():
    return render_template('heating_cooling_method_details.html')

@app.route('/off_grid', methods=['GET'])
def off_grid():
    return render_template('off_grid.html')

@app.route('/wrapping_up', methods=['GET'])
def wrapping_up():
    return render_template('wrapping_up.html')

@app.route('/test/postalcode')
def tester():
    # Fetch all names from the 'test' table
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM postalcode where postal_code = '6077'")
    rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            "postal_code":row[0],
            "city": row[1],
            "state": row[2],
            "latitude": row[3],
            "longitude": row[4]
        })
    cursor.close()
    connection.close()

    return jsonify(data)

def check_temp(temp_bool, temp):
    if temp_bool is True:
        return None
    else:
        try:
            temp = int(temp)
            return temp
        except Exception as e:
            return "FAILED"

def remove_null(columns, values):
    """
    Remove null values from the provided columns and values.
    Args:
        columns (list): List of column names.
        values (list): List of corresponding values.
    Returns:
        tuple: A tuple containing the updated columns and a tuple of non-null values.
    """
    delete_indexes = []

    # Find the indexes of null values in the 'values' list
    for i, val in enumerate(values):
        if val is None:
                delete_indexes.append(i)

        # Remove columns and values corresponding to null indexes
        columns = [i for j, i in enumerate(columns) if j not in delete_indexes]
        values = [i for j, i in enumerate(values) if j not in delete_indexes]

        if len(values)>1:
            tup = tuple(values)
        else:
            # Issue with single value tuples with sql query formatting
            tup = f"('{values[0]}')"

    columns = ','.join(columns)
    return columns, tup

def execute_query(cursor, connection, query):
    """
    Executes the given query using the provided cursor and connection objects.
    Args:
        cursor: The database cursor object.
        connection: The database connection object.
        query (str): The SQL query to execute.
    Returns:
        int: 0 if the query is executed successfully, 1 otherwise.
    """
    try:
        cursor.execute(query)
        connection.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        connection.rollback()
        cursor.close()
        return 1

@app.route('/household', methods=['POST'])
def add_household():
    """
    Endpoint for adding a new household to the database.
    Returns:
        - If the email already exists in the database:
            - Returns a JSON response with an error message.
        - If the postal code is not valid:
            - Returns a JSON response with an error message.
        - If the 'squareFootage' cannot be converted to an integer:
            - Returns a JSON response with an error message.
        - If the temperature settings are invalid:
            - Returns a JSON response with an error message.
        - If all validations pass and the household data is successfully inserted:
            - Returns a JSON response with the inserted household data.
    """
    household_data = request.get_json()

    # Create a database connection and cursor
    connection = create_connection()
    cursor = connection.cursor()

    # Check if the email already exists in the Households table
    email = household_data['email']
    cursor.execute(f"SELECT count(email) FROM Households where email = '{email}'")
    count = cursor.fetchone()[0]
    if count > 0:
        error_message = "Email already exists."
        return jsonify(error=error_message, succeeded=False)

    # Check if the postal code is valid
    postal = household_data['postal']
    cursor.execute(f"SELECT count(postal_code) FROM PostalCode where postal_code = '{postal}'")
    count = cursor.fetchone()[0]
    if count == 0:
        error_message = "Invalid postal code."
        print(error_message)
        return jsonify(error=error_message, succeeded=False)

    try:
        # Convert the square footage to an integer
        square_footage = int(household_data.get('squareFootage'))
    except ValueError:
        error_message = "Square footage cannot be converted to an integer."
        print(error_message)
        return jsonify(error=error_message, succeeded=False)

     # Check if the temperature settings are valid
    heating_temp = check_temp(household_data['noHeat'], household_data['thermostatHeating'])
    cooling_temp = check_temp(household_data['noCooling'], household_data['thermostatCooling'])

    if heating_temp is False or cooling_temp is False:
        error_message = "Temperature cannot be set when the corresponding boolean is true."
        print(error_message)
        return jsonify(error=error_message, succeeded=False)

    # Prepare the column names and values for the Households table
    household_cols = ["email", "postal_code", "household_type", "square_footage", "heating", "cooling"]
    household_values = [email, postal, household_data.get('homeType'), square_footage, heating_temp, cooling_temp]

    # Create and execute the query to insert data into the Households table
    household_cols, household_values = remove_null(household_cols, household_values)
    query = "INSERT INTO Households(%s) VALUES %s" % (household_cols, household_values)
    print(query)
    execute_query(cursor, connection, query)

    pu_cols = ["email", "utility"]
    pu_values = []
    if household_data['hasElectric']:
        pu_values.append([email, 'electric'])
    if household_data['hasGas']:
        pu_values.append([email, 'gas'])
    if household_data['hasSteam']:
        pu_values.append([email, 'steam'])
    if household_data['hasLiquidFuel']:
        pu_values.append([email, 'liquid fuel'])
    for tup in pu_values:
        query = "INSERT INTO publicutilities(%s) VALUES %s" % (','.join(pu_cols), tuple(tup))
        execute_query(cursor, connection, query)

    print(f"Household inputted with {household_cols} and {household_values}, along with these public utilities {pu_values}")
    return jsonify(household_data)

@app.route('/add_appliance', methods=['GET'])
def add_appliance_page():
    args = request.args
    try:
        email = args['email']
    except Exception:
        return render_template('400.html')

    #get a list of manufacturers for the dropdown list on the form
    #manufacturer = session.exec
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM Manufacturer")
    manufacturers = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('add_appliance.html', manufacturers = manufacturers, email=email)

@app.route('/add_appliance', methods=['POST'])
def add_appliance():
    logger.info(request.get_json())
    email = request.get_json()['email']
    appliance_type = request.get_json()['appliance_type']
    model_name = request.get_json()['model_name']
    manufacturer = request.get_json()['manufacturer']
    btu = request.get_json()['btu']
    fan_rpm = request.get_json().get('fan_rpms', None)
    air_conditioner = request.get_json().get('air_conditioner', None)
    heater = request.get_json().get('heater', None)
    heat_pump = request.get_json().get('heat_pump', None)
    energy_source = request.get_json().get('energy_source', None)
    eer = request.get_json().get('energy_efficiency_ratio', None)
    SEER = request.get_json().get('SEER', None)
    HSPF = request.get_json().get('HSPF', None)
    tank_gallons = request.get_json().get('tank_size', None)
    temperature_setting = request.get_json().get('temperature', None)
    energy_source_air = request.get_json().get('energy_source_water', None)
    energy_source_water = request.get_json().get('energy_source_water', None)

    connection = create_connection()
    getCursor = connection.cursor()
    getCursor.execute("SELECT MAX(appliance_number) FROM Appliance WHERE email = '%s'" % email)
    currMaxApplianceNumber = getCursor.fetchone()[0]
    getCursor.close()

    if currMaxApplianceNumber is None:
        currMaxApplianceNumber = 0
    
    if temperature_setting == '':
        temperature_setting = None

    newMaxApplianceNumber = currMaxApplianceNumber + 1

    insertCursor = connection.cursor()

    try:
        insertCursor.execute("INSERT INTO Appliance(email, appliance_number, manufacturer, btu_rating, appliance_type, model_name) VALUES %s" % str(tuple([email, newMaxApplianceNumber, manufacturer, btu, appliance_type, model_name])))


        if appliance_type == "AirHandler":
            logger.info("Inserting air handler")
            insertCursor.execute("INSERT INTO AirHandler (email, appliance_number, fan_rpm) VALUES %s" %str(tuple([email, newMaxApplianceNumber, fan_rpms])))
            if air_conditioner:
                insertCursor.execute("INSERT INTO AirConditioner(email, appliance_number, eer) VALUES %s" % str(tuple([email, newMaxApplianceNumber, eer])))
            if heater:
                insertCursor.execute("INSERT INTO Heater(email, appliance_number, energy_source) VALUES %s" % str(tuple([email, newMaxApplianceNumber, energy_source_air])))
            if heat_pump:
                insertCursor.execute("INSERT INTO HeatPump(email, appliance_number, SEER, HSPF) VALUES %s" % str(tuple([email, newMaxApplianceNumber, SEER, HSPF])))
        elif appliance_type == "WaterHeater":
                logger.info("Inserting water heater")
                insertCursor.execute("INSERT INTO WaterHeater(email, appliance_number, model_name, manufacturer, tank_gallons, temperature_setting, energy_source) VALUES (%s, %s, %s, %s, %s, %s, %s)", (email, newMaxApplianceNumber, model_name, manufacturer, tank_gallons, temperature_setting, energy_source_water))


        # logger.info("INSERT INTO Appliance (email, appliance_number, appliance_type, model_name) VALUES %s" % str(tuple([email, currMaxApplianceNumber + 1, appliance_type, model_name])))
        
    except Exception as e:
        logger.error("Error inserting appliance", e)

    connection.commit()

    insertCursor.close()
    connection.close()

    return redirect('list_appliance?email=%s' % email)

@app.route('/list_appliance', methods=['GET'])
def list_appliance():
    args = request.args
    try:
        email = args['email']
    except Exception:
        return render_template('400.html')
    
    connection = create_connection()
    getCursor = connection.cursor()

    getCursor.execute("SELECT * FROM Appliance WHERE email = '%s'" % email)
    appliances = getCursor.fetchall()

    getCursor.execute("SELECT * FROM Appliance where email = '{email}'".format(email = email))
    appliance = getCursor.fetchall()

    valid_appliance = len(appliance) == 0 
    logger.info(appliances)

    getCursor.close()
    connection.close()

    return render_template('list_appliance.html', appliances = appliances, email = email, disable_finish = valid_appliance and len(appliance) == 0)

@app.route('/delete_appliance', methods=['POST'])
def delete_appliance():
    appliance_number = request.get_json()['appliance_number']
    email = request.get_json()['email']

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("""DELETE FROM AirHandler WHERE email = '%s' and appliance_number = %d; 
        DELETE FROM WaterHeater WHERE email = '%s' and appliance_number = %d; 
        DELETE FROM Appliance WHERE email = '%s' and appliance_number = %d;""" % (email, appliance_number, email, appliance_number, email, appliance_number)) 
 
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify(success=True)

@app.route('/add_power_generation', methods=['GET'])
def power_gen_add():
    args = request.args
    try:
        email = args['email']
    except Exception:
        return render_template('400.html')

    connection = create_connection()
    cursor = connection.cursor()

    # Check if off grid
    cursor.execute("SELECT * FROM PublicUtilities where email = '{email}'".format(email = email))
    utilities = cursor.fetchall()

    cursor.close()
    connection.close()

    is_off_grid = len(utilities) == 0 
    return render_template('add_power_gen.html', is_off_grid = is_off_grid, email=email)

@app.route('/add_power_generation', methods=['POST'])
def create_power_gen():
    logger.info(request.form)
    email = request.form['email']
    power_gen_type = request.form['power_gen_type']
    power_gen_monthlykwh = request.form.get('power_gen_monthlykwh')
    power_gen_storagekwh = request.form.get('power_gen_storagekwh')

    connection = create_connection()
    getCursor = connection.cursor()
    getCursor.execute("SELECT MAX(power_generator_number) FROM PowerGeneration WHERE email = '%s'" % email)
    currMaxPowerGenNumber = getCursor.fetchone()[0]
    getCursor.close()

    if currMaxPowerGenNumber is None:
        currMaxPowerGenNumber = 0

    if power_gen_storagekwh != '':
        power_gen_storagekwh = int(power_gen_storagekwh)
    else:
        power_gen_storagekwh = None

    logger.info(currMaxPowerGenNumber)
    insertCursor = connection.cursor()
    logger.info("INSERT INTO PowerGeneration (email, power_generator_number, type, monthly_kWh, storage_kWh) VALUES %s" % str(tuple([email, currMaxPowerGenNumber + 1, power_gen_type, power_gen_monthlykwh, power_gen_storagekwh])))
    try:
        insertCursor.execute("INSERT INTO PowerGeneration(email, power_generator_number, type, monthly_kWh, storage_kWh) VALUES (%s, %s, %s, %s, %s)", (email, currMaxPowerGenNumber + 1, power_gen_type, power_gen_monthlykwh, power_gen_storagekwh))
    except Exception as e:
        logger.error("Error inserting power generation", e)
    connection.commit()

    insertCursor.close()
    connection.close()

    return redirect('list_power_generation?email=%s' % email)

@app.route('/list_power_generation', methods=['GET'])
def list_power_gen():
    args = request.args
    try:
        email = args['email']
    except Exception:
        return render_template('400.html')
    
    connection = create_connection()
    getCursor = connection.cursor()

    getCursor.execute("SELECT * FROM PowerGeneration WHERE email = '%s'" % email)
    power_generations = getCursor.fetchall()

    getCursor.execute("SELECT * FROM PublicUtilities where email = '{email}'".format(email = email))
    utilities = getCursor.fetchall()

    is_off_grid = len(utilities) == 0 

    logger.info(power_generations)

    getCursor.close()
    connection.close()

    return render_template('list_power_gen.html', power_generations = power_generations, email = email, disable_finish = is_off_grid and len(power_generations) == 0)

@app.route('/delete_power_generation', methods=['POST'])
def delete_power_gen():
    power_generation_number = request.get_json()['power_generation_number']
    email = request.get_json()['email']

    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM PowerGeneration WHERE email = '%s' and power_generator_number = %d" % (email, power_generation_number))
    
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify(success=True)

@app.route('/list_reports', methods=['GET'])
def list_reports():
    return render_template('list_reports.html')

@app.route('/manufacturer_model_search', methods=['GET'])
def manufacturer_model_search():
    try:
        user_input = request.args['user_input']
    except Exception:
        return render_template('manufacturer_model_search.html', manufacturer_model_result = [])

    logger.info(request.form)
    connection = create_connection()
    getCursor = connection.cursor()
    getCursor.execute("SELECT manufacturer, model_name FROM Appliance WHERE UPPER(manufacturer) LIKE '%%%s%%' OR UPPER(model_name) LIKE '%%%s%%' ORDER BY manufacturer ASC, model_name ASC" % (user_input.upper(), user_input.upper()))
    result = getCursor.fetchall()

    getCursor.close()
    connection.close()

    return render_template('manufacturer_model_search.html', manufacturer_model_result = result, query = user_input)

@app.route('/get_heating_cooling', methods=['GET'])
def heating_cooling_method_details():
    connection = create_connection()
    getCursor = connection.cursor()
    query = f"""
    -- First query: Heater data
        WITH HeaterData AS (    
            SELECT hd.household_type::text,
            'Heater' as AirHandlerType,
            hd.count,
            hd.average_BTUs,
            hd.average_RPM,
            es.energy_source
            FROM (
            SELECT
                h.household_type::text,
                COUNT(*) AS count,
                AVG(a.btu_rating) AS average_BTUs,
                AVG(ah.fan_rpm) AS average_RPM
            FROM
                Households h
            JOIN
                Appliance a ON h.email = a.email
            JOIN
                AirHandler ah ON a.email = ah.email AND a.appliance_number = ah.appliance_number
            JOIN
                Heater hp ON ah.email = hp.email AND ah.appliance_number = hp.appliance_number
            WHERE
                a.appliance_type = 'AirHandler'
            GROUP BY
                h.household_type
        ) hd
        JOIN (
            SELECT
                with_RN.household_type,
                with_RN.energy_source
            FROM (
                SELECT
                    h.household_type::text,
                    hp.energy_source,
                    ROW_NUMBER() OVER (PARTITION BY h.household_type ORDER BY COUNT(*) DESC) AS RN
                FROM
                    Households h
                JOIN
                    Appliance a ON h.email = a.email
                JOIN
                    AirHandler ah ON a.email = ah.email AND a.appliance_number = ah.appliance_number
                JOIN
                    Heater hp ON ah.email = hp.email AND ah.appliance_number = hp.appliance_number
                GROUP BY
                    h.household_type,
                    a.appliance_type,
                    hp.energy_source
            ) with_RN
            WHERE
                RN = 1
        ) es ON hd.household_type::text = es.household_type::text
            ),

            AirConditionerData AS (
                -- Second query: Air Conditioner data
                        SELECT h.household_type::text,
                        'AirConditioner' as AirHandlerType,
                        COUNT(*) AS count,
                        AVG(a.btu_rating) AS average_BTUs,
                        AVG(ah.fan_rpm) AS average_RPM,
                        AVG(ac.EER) AS average_EER
                        FROM
                            Households h
                        JOIN Appliance a ON h.email = a.email
                        JOIN AirHandler ah ON a.email = ah.email AND a.appliance_number = ah.appliance_number
                        JOIN AirConditioner ac ON ah.email = ac.email AND ah.appliance_number = ac.appliance_number
                        WHERE
                            a.appliance_type = 'AirHandler'
                        GROUP BY
                            h.household_type, AirHandlerType
            ),

            HeatPumpData AS (
                -- Third query: Heat Pump data
                        SELECT 
                            ht.household_type::text,
                            COALESCE(s.AirHandlerType, 'HeatPump') as AirHandlerType,
                            COALESCE(s.count, 0) as count,
                            COALESCE(s.average_BTUs, 0) as average_BTUs,
                            COALESCE(s.average_RPM, 0) as average_RPM,
                            COALESCE(s.average_SEER, 0) as average_SEER,
                            COALESCE(s.average_HSPF, 0) as average_HSPF
                        FROM
                            (SELECT unnest(enum_range(NULL::householdType))::text AS household_type) ht left JOIN
                        (SELECT
                            h.household_type::text,
                            'HeatPump' as AirHandlerType,
                            COUNT(*) AS count,
                            AVG(a.btu_rating) AS average_BTUs,
                            AVG(ah.fan_rpm) AS average_RPM,
                            AVG(hp.seer) AS average_SEER,
                            AVG(hp.hspf) AS average_HSPF
                        FROM
                            Households h
                            JOIN Appliance a ON h.email = a.email
                            JOIN AirHandler ah ON a.email = ah.email AND a.appliance_number = ah.appliance_number
                            JOIN HeatPump hp ON ah.email = hp.email AND ah.appliance_number = hp.appliance_number
                        WHERE
                            a.appliance_type = 'AirHandler'
                        GROUP BY
                            h.household_type, AirHandlerType) s
                        ON ht.household_type = s.household_type
                        ORDER BY ht.household_type

            )

            -- Combine the results using UNION ALL and sort by household_type
                SELECT household_type, AirHandlerType, count, cast(round(average_BTUs, 0) as int), round(cast(average_RPM as decimal), 1), cast(energy_source as varchar(20)), cast(null as decimal) as average_HSPF FROM HeaterData
                UNION ALL
                SELECT household_type, AirHandlerType, count, cast(round(average_BTUs, 0) as int), round(cast(average_RPM as decimal), 1), cast(round(cast(average_EER as decimal), 1) as varchar(20)), cast(null as decimal) as average_HSPF FROM AirConditionerData
                UNION ALL
                SELECT household_type, AirHandlerType, count, cast(round(average_BTUs, 0) as int), round(cast(average_RPM as decimal), 1), cast(round(cast(average_SEER as decimal), 1) as varchar(20)), round(cast(average_HSPF as decimal), 1) FROM HeatPumpData
                ORDER BY household_type;

            """
    getCursor.execute(query)
    combined_results = getCursor.fetchall()
    # print(combined_results)
    heater_data = []
    aircon_data = []
    heatpump_data = []

    for row in combined_results:
        if row[1] == "Heater":
            heater_data.append({
                "Home Type":row[0],
                "Heater Count": row[2],
                "Average BTU": row[3],
                "Average RPM": float(row[4]),
                "Most Common Energy Source": row[5]
            })
        elif row[1] == "AirConditioner":
            aircon_data.append({
                "Home Type":row[0],
                "Air Conditioner Count": row[2],
                "Average BTU": row[3],
                "Average RPM": float(row[4]),
                "Average EER": float(row[5])
            })
        elif row[1] == "HeatPump":
            heatpump_data.append({
                "Home Type":row[0],
                "Heat Pump Count": row[2],
                "Average BTU": row[3],
                "Average RPM": float(row[4]),
                "Average SEER": float(row[5]),
                "Average HSPF": float(row[6])
            })
    
    final_data = {
        "Heater":heater_data,
        "Air Conditioner":aircon_data,
        "Heat Pump":heatpump_data

    }

    getCursor.close()
    connection.close()

    return final_data  
    

@app.route('/water_heater_statistics_info', methods=['GET'])
def get_water_heater_statistics():
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            water_heater_query = """
                        SELECT
                          p.state,
                          s.avg_tank_size,
                          s.avg_btu,
                          s.avg_temperature_setting,
                          s.num_temp_not_null,
                          s.num_temp_null 
                        FROM
                            (SELECT DISTINCT(state) FROM PostalCode ) p left JOIN
                            (SELECT
                                p.state,
                                cast(ROUND(AVG(wh.tank_gallons)) as int) AS avg_tank_size,
                                cast(ROUND(AVG(A.btu_rating)) as int) AS avg_btu,
                                ROUND(cast(AVG(wh.temperature_setting) as decimal), 1) AS avg_temperature_setting,
                                COUNT(NULLIF(wh.temperature_setting, NULL)) AS num_temp_not_null,
                                COUNT(NULLIF(wh.temperature_setting IS NULL, FALSE)) AS num_temp_null
                            FROM
                                Households AS h
                            INNER JOIN
                                PostalCode AS p ON h.postal_code = p.postal_code
                            LEFT JOIN
                                WaterHeater AS wh ON h.email = wh.email
                            LEFT JOIN
                                Appliance AS A ON h.email = A.email
                            GROUP BY
                                p.state
                            ORDER BY
                                p.state ASC) s
                            ON p.state = s.state
                        ORDER BY
                        p.state;
                """
            cursor.execute(water_heater_query)
            water_heater_data = cursor.fetchall()
            stats_info = {}
            for state in water_heater_data:
                stats_info[state[0]] = [
                    state[1],
                    state[2],
                    state[3],
                    state[4],
                    state[5]
                ]

                for i, x in enumerate(stats_info[state[0]]):
                    if x is None:
                        stats_info[state[0]][i] = ""
                    elif i != 3:
                        stats_info[state[0]][i] = str(int(stats_info[state[0]][i]))
                    elif i == 3:
                        stats_info[state[0]][i] = str(float(stats_info[state[0]][i]))

            return {"water_heater_stats":water_heater_data}

    except psycopg2.Error as e:
            print("Error executing the query:", e)
            return jsonify({'error': 'Failed to fetch data from the database'})    
    
@app.route('/drill_down', methods=['GET'])
def get_drill_down():
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            state_arg = request.args.get('state')
            water_heater_query = f"""
                    SELECT
                          es.energy_source,
                          s.minimum_size,
                          s.average_size,
                          s.maximum_size,
                          s.mininimum_setting,
                          s.average_setting,
                          s.maximum_setting
                    FROM
                        (SELECT DISTINCT(energy_source) FROM WaterHeater ) es left JOIN
                        (SELECT  
                            p.state,
                            wh.energy_source,  
                            round(min(wh.tank_gallons)) AS minimum_size,  
                            round(avg(wh.tank_gallons)) AS average_size,  
                            round(max(wh.tank_gallons)) AS maximum_size,  
                            round(min(wh.temperature_setting), 1) AS mininimum_setting,  
                            round(avg(wh.temperature_setting), 1) AS average_setting,  
                            round(max(wh.temperature_setting), 1) AS maximum_setting  
                        FROM
                            Households AS h
                        INNER JOIN
                            PostalCode AS p ON h.postal_code = p.postal_code
                        LEFT JOIN
                            WaterHeater AS wh ON h.email = wh.email
                        LEFT JOIN
                            Appliance AS A ON h.email = A.email
                        WHERE
                            p.state = '{state_arg}'
                        GROUP BY   
                        p.state,
                        wh.energy_source  
                        ORDER BY   
                        wh.energy_source ASC
                        ) s ON es.energy_source = s.energy_source
                    ORDER BY   
                        es.energy_source ASC
                    ; 

                """
            cursor.execute(water_heater_query)
            water_heater_data = cursor.fetchall()
            stats_info = {}
            for state in water_heater_data:
                stats_info[state[0]] = [
                    state[1],
                    state[2],
                    state[3],
                    state[4],
                    state[5],
                    state[6]
                ]

                for i, x in enumerate(stats_info[state[0]]):
                    if x is None:
                        stats_info[state[0]][i] = ""
                    elif i in [1, 2, 3]:
                        stats_info[state[0]][i] = str(int(stats_info[state[0]][i]))
                    elif i in [4, 5, 6]:
                        stats_info[state[0]][i] = str(float(stats_info[state[0]][i]))
            return {"water_heater_stats":water_heater_data}

    except psycopg2.Error as e:
            print("Error executing the query:", e)
            return jsonify({'error': 'Failed to fetch data from the database'})   

@app.route('/off_grid_info', methods=['GET'])
def get_off_grid_info():
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
        
        ########## OFF GRID STATE ##########
            mostOffGridStateQuery = """
                SELECT p.state, COUNT(*) as off_grid_households 
                FROM Households h 
                JOIN PostalCode p ON h.postal_code = p.postal_code 
                WHERE h.email NOT IN (SELECT email FROM PublicUtilities) 
                GROUP BY p.state 
                ORDER BY off_grid_households DESC; 
            """

            cursor.execute(mostOffGridStateQuery)
            mostoffGridState = cursor.fetchone()

        ########## AVERAGE BATTERY ##########
            averageBatteryQuery = """
                SELECT ROUND(AVG(storage_kWh), 0) AS average_battery_capacity 
                FROM PowerGeneration pg 
                JOIN Households h ON h.email = pg.email 
                WHERE h.email NOT IN ( 
                    SELECT email FROM PublicUtilities 
                ); 
            """
            cursor.execute(averageBatteryQuery)
            averageBattery = cursor.fetchone()

        ########## Generation Type ##########
            generationTypeQuery = """
            WITH off_grid_total as (SELECT email, 
                CASE 
                    WHEN windturbine > 0 AND solar > 0 then 'mixed'  
                    WHEN windturbine > 0 AND solar = 0 then 'windturbine' 
                    else 'solar' 
                    END as pg_type 
                FROM ( 
                    SELECT email, SUM(windturbine) as windturbine, SUM(solar) as solar FROM ( 
                        SELECT h.email, 
                        CASE WHEN pg.type = 'wind turbine' then 1 else 0 end as windturbine, 
                        CASE WHEN pg.type = 'solar' then 1 else 0 end as solar 
                        FROM Households h join PowerGeneration pg 
                        on h.email = pg.email 
                        where h.email NOT IN ( 
                            SELECT email FROM PublicUtilities 
                        ) 
                    ) a 
                    GROUP BY email 
                ) b) 
            SELECT pg_type, round(cast(count(*) as decimal)*100/(SELECT COUNT(*) FROM off_grid_total), 1) as type_percentage FROM off_grid_total group by pg_type; 
            """
            cursor.execute(generationTypeQuery)
            generationType = cursor.fetchall()
            genTypePercent = {}
            for genType in generationType:
                genTypePercent[genType[0]] = float(genType[1])

            ########## HOUSEHOLD TYPE ##########
            householdTypeQuery = """
            WITH off_grid_total AS ( 
                SELECT h.household_type  
                FROM PowerGeneration pg  
                JOIN Households h ON h.email = pg.email  
                WHERE h.email NOT IN ( 
                    SELECT email FROM PublicUtilities 
                ) 
            ) 
            SELECT  
                household_type,  
                round(cast(count(*) as decimal)*100 / (SELECT COUNT(*) FROM off_grid_total), 1) AS type_percentage 
            FROM off_grid_total  
            GROUP BY household_type; 
            """
            cursor.execute(householdTypeQuery)
            householdType = cursor.fetchall()
            householdTypePercent = {}
            for householdType in householdType:
                householdTypePercent[householdType[0]] = float(householdType[1])

            ########## WATER HEATER TANK SIZE ##########
            waterHeaterQuery = """
            WITH off_grid AS ( 
                SELECT round(cast(avg(w.tank_gallons) as decimal),1) as average_tank_gallons 
                FROM WaterHeater w 
                JOIN Households h ON h.email = w.email 
                WHERE  h.email NOT IN (SELECT email FROM PublicUtilities) 
                ),  
                on_grid AS ( 
                SELECT round(cast(avg(w.tank_gallons) as decimal),1) as average_tank_gallons 
                FROM WaterHeater w 
                JOIN Households h ON h.email = w.email 
                WHERE h.email IN (SELECT email FROM PublicUtilities) 
                ) 
                SELECT average_tank_gallons FROM off_grid 
                UNION ALL 
                SELECT average_tank_gallons FROM on_grid; 
            """
            cursor.execute(waterHeaterQuery)
            waterHeaterTankSizes = cursor.fetchall()
            waterHeaterTankSizes = {"Off Grid Households": waterHeaterTankSizes[0],
                                    "On Grid Households": waterHeaterTankSizes[1]}
            
            ########## APPLIANCES ##########
            applianceQuery = """
            WITH off_grid_total AS ( 
                SELECT h.email  
                FROM PowerGeneration pg  
                JOIN Households h ON h.email = pg.email  
                WHERE h.email NOT IN ( 
                    SELECT email FROM PublicUtilities 
                ) 
            ), 
            off_grid_appliances AS ( 
                SELECT a.email, a.appliance_number, a.btu_rating 
                FROM off_grid_total o  
                JOIN appliance a ON o.email = a.email 
            ),
            AirConCount AS ( 
            SELECT 'AirConditioner' as atype, min(o.btu_rating) as min_btu, cast(round(avg(o.btu_rating),0) as int) as avg_btu, max(o.btu_rating) as max_btu 
            FROM off_grid_appliances o  
            JOIN AirConditioner ac ON o.email = ac.email AND o.appliance_number = ac.appliance_number 
            GROUP BY atype), 
            HeatPumpCount AS ( 
            SELECT 'HeatPump' as atype, min(o.btu_rating) as min_btu, cast(round(avg(o.btu_rating),0) as int) as avg_btu, max(o.btu_rating) as max_btu 
            FROM off_grid_appliances o  
            JOIN HeatPump hp ON o.email = hp.email AND o.appliance_number = hp.appliance_number 
            GROUP BY atype), 
            HeaterCount AS ( 
            SELECT 'Heater' as atype, min(o.btu_rating) as min_btu, cast(round(avg(o.btu_rating),0) as int) as avg_btu, max(o.btu_rating) as max_btu 
            FROM off_grid_appliances o  
            JOIN Heater h ON o.email = h.email AND o.appliance_number = h.appliance_number 
            GROUP BY atype), 
            WaterHeaterCount AS ( 
            SELECT 'WaterHeater' as atype, min(o.btu_rating) as min_btu, cast(round(avg(o.btu_rating),0) as int) as avg_btu, max(o.btu_rating) as max_btu 
            FROM off_grid_appliances o  
            JOIN WaterHeater wh ON o.email = wh.email AND o.appliance_number = wh.appliance_number 
            GROUP BY atype) 
            SELECT atype, min_btu, avg_btu, max_btu FROM AirConCount 
            UNION ALL 
            SELECT atype, min_btu, avg_btu, max_btu FROM HeatPumpCount 
            UNION ALL 
            SELECT atype, min_btu, avg_btu, max_btu FROM HeaterCount 
            UNION ALL 
            SELECT atype, min_btu, avg_btu, max_btu FROM WaterHeaterCount; 
            """
            cursor.execute(applianceQuery)
            applianceData = cursor.fetchall()
            applianceStats = {}
            for applianceType in applianceData:
                applianceStats[applianceType[0]] = [
                    int(applianceType[1]),
                    int(applianceType[2]),
                    int(applianceType[3])
                ]
            print(applianceStats)
            return {"most_off_grid":mostoffGridState,
                    "average_battery":int(averageBattery[0]), 
                    "generation_type_percents":genTypePercent,
                    "household_type_percents":householdTypePercent,
                    "water_tank_sizes":waterHeaterTankSizes,
                    "appliance_stats":applianceStats}

    except psycopg2.Error as e:
            print("Error executing the query:", e)
            return jsonify({'error': 'Failed to fetch data from the database'})
    
@app.route('/radius_info', methods=['GET'])
def get_radius_info():
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            # Check if the postal code is valid
            postal = request.args.get('postal')
            cursor.execute(f"SELECT count(postal_code) FROM PostalCode where postal_code = '{postal}'")
            count = cursor.fetchone()[0]
            if count == 0:
                error_message = "Invalid postal code."
                print(error_message)
                return jsonify(error=error_message, succeeded=False)
            radius = request.args.get('radius')
            query = f"""
                WITH SearchPostalCodes AS ( 
                    SELECT initial_postal_code, radius_postal_code, distance FROM 
                    (SELECT p1.postal_code as initial_postal_code, p2.postal_code as radius_postal_code, ( 3959 * acos( cos( radians(p1.latitude) ) * cos( radians( p2.latitude ) ) * cos( radians(p2.longitude) - radians(p1.longitude) ) + sin( radians(p1.latitude) ) * sin( radians(p2.latitude)))) AS distance 
                    FROM PostalCode p1 cross join PostalCode p2) joined_p 
                    WHERE initial_postal_code = '{postal}' 
                    AND distance <= CAST('{radius}' AS INT)), 
                    InRadiusHouseholds AS ( 
                    SELECT sp.initial_postal_code, h.email, sp.distance, household_type, square_footage, heating, cooling 
                    FROM households h join SearchPostalCodes sp 
                    on h.postal_code = sp.initial_postal_code 
                    OR 
                    h.postal_code = sp.radius_postal_code), 
                    off_grid_total AS ( 
                        SELECT h.initial_postal_code, count(*) as off_grid_count 
                        FROM PowerGeneration pg  
                        JOIN InRadiusHouseholds h ON h.email = pg.email  
                        WHERE h.email NOT IN ( 
                            SELECT email FROM PublicUtilities 
                        ) 
                        GROUP BY  
                        h.initial_postal_code 
                    ), 
                    PowerGenerationInRadius AS ( 
                    SELECT h.email, h.initial_postal_code, pg.type, pg.monthly_kwh, pg.storage_kwh 
                    FROM InRadiusHouseholds h join PowerGeneration pg 
                    ON h.email = pg.email),  
                    
                    /* Battery Storage */ 
                    BatteryStorage AS ( 
                    SELECT pgr.initial_postal_code, count(*) as households_with_battery_storage FROM PowerGenerationInRadius pgr 
                    WHERE pgr.storage_kwh is not null 
                    GROUP BY 
                    pgr.initial_postal_code), 

                    /* Average monthly power generation and count of homes*/ 
                    AvgGeneration AS  (SELECT pgr.initial_postal_code, round(avg(pgr.monthly_kwh), 0) as average_monthly_generation, count(*) as power_generation_count 
                    FROM PowerGenerationInRadius pgr 
                    GROUP BY 
                    pgr.initial_postal_code), 

                    /* Most Common Generation Method */ 
                    MostCommonGeneration AS (SELECT pgr.initial_postal_code, pgr.type, count(*) as type_count 
                    FROM PowerGenerationInRadius pgr  
                    GROUP BY 
                    pgr.initial_postal_code, 
                    pgr.type 
                    ORDER BY type_count DESC 
                    LIMIT 1), 

                    /* Public Utilities */ 
                    UsedUtilitiies AS ( 
                        SELECT irh.initial_postal_code, array_to_string(ARRAY_AGG(DISTINCT(pu.utility)), ',') as utilities 
                        FROM 
                            InRadiusHouseholds irh JOIN PublicUtilities pu 
                        ON  
                            irh.email = pu.email 
                        GROUP BY 
                            irh.initial_postal_code), 

                    /* Average Household Information */ 
                    AverageHouseholdInfo AS ( 
                    SELECT  irh.initial_postal_code, 
                            round(avg(irh.cooling), 1)  as average_cooling_temperature, 
                            round(avg(irh.heating), 1)  as average_heating_temperature,  
                            round(avg(irh.square_footage), 0) as average_square_footage 
                    FROM 
                        InRadiusHouseholds irh 
                    GROUP BY 
                        irh.initial_postal_code), 

                    /* Household Type Count */ 
                    HouseHoldTypeCount AS ( 
                        SELECT 
                            initial_postal_code, 
                            max(house) as house, 
                            max(apartment) as apartment, 
                            max(townhome) as townhome, 
                            max(condominium) as condominum, 
                            max(modular_home) as modular_home, 
                            max(tiny_house) as tiny_house 
                        FROM 
                            (SELECT  
                                initial_postal_code, 
                                CASE WHEN all_household_types = 'house' then ht_count end as house, 
                                CASE WHEN all_household_types = 'apartment' then ht_count end as apartment, 
                                CASE WHEN all_household_types = 'townhome' then ht_count end as townhome, 
                                CASE WHEN all_household_types = 'condominium' then ht_count end as condominium, 
                                CASE WHEN all_household_types = 'modular home' then ht_count end as modular_home, 
                                CASE WHEN all_household_types = 'tiny house' then ht_count end as tiny_house 
                            FROM 
                                (SELECT a.initial_postal_code, b.all_household_types, COALESCE(ht_count, 0)  as ht_count 
                                FROM  
                                    (SELECT UNNEST(enum_range(NULL::HouseholdType)) as all_household_types) b 
                                    LEFT JOIN  
                                    (SELECT initial_postal_code, household_type, count(*) as ht_count 
                                        FROM InRadiusHouseholds 
                                    GROUP BY  
                                        initial_postal_code, 
                                        household_type) a 
                                    ON b.all_household_types = a.household_type) counts) counts2 
                        GROUP BY initial_postal_code), 
            
                    /* Household Count */ 
                    HouseHoldCount AS ( 
                    SELECT initial_postal_code, count(*) as household_count 
                    FROM  
                        InRadiusHouseholds 
                    GROUP BY initial_postal_code), 
                    MaxDistance AS ( 
                        SELECT irh.initial_postal_code, max(irh.distance) as distance 
                        FROM 
                            InRadiusHouseholds irh 
                        GROUP BY 
                            irh.initial_postal_code
                    ) 

                    /* FINAL QUERY */ 
                    SELECT  irh.initial_postal_code, 
                            md.distance, 
                            hhc.household_count, 
                            hhtc.house, 
                            hhtc.apartment, 
                            hhtc.townhome, 
                            hhtc.condominum, 
                            hhtc.modular_home, 
                            hhtc.tiny_house, 
                            cast(round(ahhi.average_square_footage, 0) as int),
                            round(cast(ahhi.average_heating_temperature as decimal), 1), 
                            round(cast(ahhi.average_cooling_temperature as decimal), 1), 
                            uu.utilities, 
                            oot.off_grid_count, 
                            ag.power_generation_count, 
                            mcg.type as most_common_type, 
                            cast(round(ag.average_monthly_generation, 0) as int), 
                            bs.households_with_battery_storage
                    FROM  
                        (SELECT distinct(initial_postal_code) FROM InRadiusHouseholds) irh  
                    LEFT JOIN 
                        MaxDistance md 
                        ON irh.initial_postal_code = md.initial_postal_code 
                    LEFT JOIN 
                        HouseHoldCount hhc 
                        ON irh.initial_postal_code = hhc.initial_postal_code 
                    LEFT JOIN 
                        HouseHoldTypeCount hhtc 
                        ON irh.initial_postal_code = hhtc.initial_postal_code 
                    LEFT JOIN 
                        AverageHouseholdInfo ahhi 
                        ON irh.initial_postal_code = ahhi.initial_postal_code 
                    LEFT JOIN 
                        UsedUtilitiies uu 
                        ON irh.initial_postal_code = uu.initial_postal_code 
                    LEFT JOIN 
                        off_grid_total oot 
                        ON irh.initial_postal_code = oot.initial_postal_code 
                    LEFT JOIN 
                        MostCommonGeneration mcg 
                        ON irh.initial_postal_code = mcg.initial_postal_code 
                    LEFT JOIN 
                        AvgGeneration ag 
                        ON irh.initial_postal_code = ag.initial_postal_code 
                    LEFT JOIN 
                        BatteryStorage bs 
                        ON irh.initial_postal_code = bs.initial_postal_code; 
            """
            cursor.execute(query)
            postalCodeData = list(cursor.fetchone())
            keys = [
                "Postal Code",
                "Radius",
                "Household Count",
                "House Count",
                "Apartment Count", 
                "Townhome Count",
                "Condominum Count",
                "Modular Home Count",
                "Tiny House Count",
                "Average Square Footage",
                "Average Heating Temperature",
                "Average Cooling Temperature",
                "Utilities",
                "Off-the-grid Household Count",
                "Households with Power Generation Count",
                "Most Common Power Generation Source",
                "Average Monthly Power Generation (kWh)",
                "Households with Battery Storage Count"
            ]
            for i, x in enumerate(postalCodeData):
                if i == 1:
                    postalCodeData[i] = int(radius)
                if isinstance(x, decimal.Decimal):
                    postalCodeData[i] = float(x)
                if x is None:
                    postalCodeData[i] = 0
            # postalCodeData[1] = radius
            return {"keys":keys, "data":postalCodeData}
    except psycopg2.Error as e:
            print("Error executing the query:", e)
            return jsonify({'error': 'Failed to fetch data from the database'})   

@app.route('/top_25', methods=['GET'])
def get_top_25_info():
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            query = f"""
                WITH counts AS (
                    SELECT Manufacturer, COUNT(*) AS num_appliances 
                    FROM Appliance 
                    GROUP BY Manufacturer 
                )

                SELECT Manufacturer, num_appliances 
                FROM counts 
                ORDER BY num_appliances  DESC
                LIMIT 25;
            """
            cursor.execute(query)
            merchantData = list(cursor.fetchall())

            return {"data":merchantData}
    except psycopg2.Error as e:
            print("Error executing the query:", e)
            return jsonify({'error': 'Failed to fetch data from the database'})       

@app.route('/manufacturer_appliance_report', methods=['GET'])
def manufacturer_appliance_report():
    return render_template('manufacturer_appliance.html')


@app.route('/manufacturer_appliances', methods=['GET'])
def manufacturer_appliances():
    args = request.args
    try:
       manufacturer = args['manufacturer']
    except Exception:
        return render_template('400.html')
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            query = f"""
                WITH SelectedManufacturer AS (
                    SELECT * FROM Appliance WHERE manufacturer = '{manufacturer}'
                )
                SELECT 
                    (SELECT COUNT(*) FROM SelectedManufacturer WHERE appliance_type = 'AirHandler') AS Air_Handlers, 
                    (SELECT COUNT(*) FROM SelectedManufacturer WHERE appliance_type = 'WaterHeater') AS Water_Heaters, 
                    (SELECT COUNT(*) FROM SelectedManufacturer sm JOIN AirConditioner ac ON sm.email = ac.email AND sm.appliance_number = ac.appliance_number) AS Air_Conditioners, 
                    (SELECT COUNT(*) FROM SelectedManufacturer sm JOIN Heater h ON sm.email = h.email AND sm.appliance_number = h.appliance_number) AS Heaters, 
                    (SELECT COUNT(*) FROM SelectedManufacturer sm JOIN HeatPump hp ON sm.email = hp.email AND sm.appliance_number = hp.appliance_number) AS Heat_pumps
                FROM 
                    SelectedManufacturer
                GROUP BY manufacturer
            """
            cursor.execute(query)

            rows = cursor.fetchall()
            column_names = [column[0] for column in cursor.description]
            applianceData = [dict(zip(column_names, row)) for row in rows]

            return jsonify({
                "data": applianceData
            })
    except psycopg2.Error as e:
            print("Error executing the query:", e)
            return jsonify({'error': 'Failed to fetch data from the database'})        
     

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)