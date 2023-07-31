import pandas as pd
import psycopg2
import psycopg2.extras as extras
import os
import numpy as np

def create_connection():
    connection = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=5432,
        database="postgres",
        user="postgres",
        password=1234
    )
    return connection

def check():
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT postal_code FROM postalcode where postal_code = '6077'")
    rows = cursor.fetchall()
    if len(rows) > 0:
        return False
    else:
        return True


def initialize(todo):
    if todo:
        postal_codes = pd.read_csv("./sql/postal_codes.csv")
        postal_codes = postal_codes.rename(columns = {
            "Zip":"postal_code"
        })
        postal_codes['postal_code'] = postal_codes['postal_code'].astype(str)
        postal_codes['postal_code'] = postal_codes['postal_code'].str.lstrip('0')
        postal_codes['City'] = postal_codes['City'].str.replace("'", '"')

        household_df = pd.read_csv('./sql/Household.tsv', sep='\t')
        household_df.where(pd.notnull(household_df), None) 

        publicUtilities = household_df[["email", "utilities"]]
        publicUtilities['utilities'] = publicUtilities['utilities'].str.split(',')
        publicUtilities = publicUtilities.explode(["utilities"])
        publicUtilities = publicUtilities[publicUtilities['utilities'].notna()]
        publicUtilities.columns = ["email", "utility"]

        household_df = household_df[[
            "email",
            "postal_code",
            "household_type",
            "square_footage",
            "heating",
            "cooling"
        ]]
        household_df['postal_code'] = household_df['postal_code'].astype(str)

        appliances = pd.read_csv('./sql/Appliance.tsv', sep='\t')

        appliances = appliances.rename(columns={
                            "household_email":"email",
                            "rpm":"fan_rpm",
                            "manufacturer_name":"manufacturer",
                            "model":"model_name",
                            "btu":"btu_rating",
                            "tank_size":"tank_gallons",
                            "temperature":"temperature_setting"
                            })

        air_handlers = appliances[appliances['appliance_type']=="air_handler"]


        air_conditioners = air_handlers[air_handlers['air_handler_types'].str.contains("air_conditioner")]
        air_conditioners = air_conditioners[["email", "appliance_number", "eer"]]


        heater = air_handlers[air_handlers['air_handler_types'].str.contains("heater")]
        heater.loc[heater['energy_source']=="thermosolar", "energy_source"] = "solar"

        heater = heater[["email", "appliance_number", "energy_source"]]

        heat_pump = air_handlers[air_handlers["air_handler_types"].str.contains("heatpump")]
        heat_pump = heat_pump[["email", "appliance_number", "seer", "hspf"]]

        air_handlers = air_handlers[["email", "appliance_number", "fan_rpm"]]


        water_heaters = appliances[appliances["appliance_type"]=="water_heater"]
        water_heaters = water_heaters[[
            "email",
            "appliance_number",
            "model_name",
            "manufacturer",
            "tank_gallons",
            "temperature_setting",
            "energy_source"
        ]]


        appliances = appliances[[
            "email",
            "appliance_number",
            "model_name",
            "manufacturer",
            "btu_rating",
            "appliance_type"
        ]]

        
        appliances.loc[appliances['appliance_type']=="water_heater", "appliance_type"] = "WaterHeater"
        appliances.loc[appliances['appliance_type']=="air_handler", "appliance_type"] = "AirHandler"



        manufacturers = pd.read_csv('./sql/Manufacturer.tsv', sep='\t')
        manufacturers = manufacturers.rename(columns={"manufacturer_name":"manufacturer"})

        powers = pd.read_csv('./sql/Power.tsv', sep='\t')
        powers = powers.rename(columns={
                "household_email":"email",
                "power_number":"power_generator_number",
                "energy_source":"type",
                "kilowatt_hours":"monthly_kWh",
                "battery":"storage_kWh"
        })
        powers.loc[powers['type']=="wind-turbine", "type"] = "wind turbine"

        def execute_values(conn, df, table):
        
            tuples = [list(x) for x in df.to_numpy()]
        
            # cols = ','.join(list(df.columns))
            # SQL query to execute
            cursor = conn.cursor()
            try:
                for t in tuples:
                    clean_cols = list(df.columns)
                    delete_indexes = []
                    for i, val in enumerate(t):
                        if pd.isna(val):
                            delete_indexes.append(i)
                    clean_cols = [i for j, i in enumerate(clean_cols) if j not in delete_indexes]
                    t = [i for j, i in enumerate(t) if j not in delete_indexes]
                    if len(t)>1:
                        tup = tuple(t)
                    else:
                        tup = f"('{t[0]}')"
                    clean_cols = ','.join(clean_cols)
                    query = "INSERT INTO %s(%s) VALUES %s" % (table, clean_cols, tup)
                    cursor.execute(query)
                print("executing")
                conn.commit()
            except (Exception, psycopg2.DatabaseError) as error:
                print("Error: %s" % error)
                conn.rollback()
                cursor.close()
                return 1
            print(f"the dataframe {table} is inserted")
            cursor.close()
        
        
        conn = psycopg2.connect(
            database="postgres", user='postgres', password='1234', host=os.environ.get('DB_HOST'), port='5432'
        )


        execute_values(conn, postal_codes, "PostalCode")
        execute_values(conn, manufacturers, "Manufacturer")
        execute_values(conn, household_df, "Households")
        execute_values(conn, appliances, "Appliance")
        execute_values(conn, air_handlers, "AirHandler")
        execute_values(conn, air_conditioners, "AirConditioner")
        execute_values(conn, heater, "Heater")
        execute_values(conn, heat_pump, "HeatPump")
        execute_values(conn, water_heaters, "WaterHeater")
        execute_values(conn, powers, "PowerGeneration")
        execute_values(conn, publicUtilities, "PublicUtilities")


todo = check()
initialize(todo)
