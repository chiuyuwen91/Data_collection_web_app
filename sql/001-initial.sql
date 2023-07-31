-- DROP DATABASE IF EXISTS mydb;
-- CREATE DATABASE IF NOT EXISTS mydb;
-- USE mydb;

/* ---------------- POSTALCODE ---------------- */
DROP TABLE IF EXISTS POSTALCODE CASCADE;

CREATE TABLE PostalCode ( 

  postal_code CHAR(5) NOT NULL, 

  city VARCHAR(50) NOT NULL, 

  state VARCHAR(50) NOT NULL, 

  latitude FLOAT(6) NOT NULL, 

  longitude FLOAT(6) NOT NULL, 

  PRIMARY KEY(postal_code) 

); 

/* ---------------- HOUSEHOLDS ---------------- */

DROP TABLE IF EXISTS Households CASCADE;

DROP TYPE IF EXISTS householdType; 

CREATE TYPE householdType AS ENUM('house','apartment', 'townhome', 'condominium', 'modular home', 'tiny house');

CREATE TABLE Households ( 

  email VARCHAR(250) NOT NULL, 

  postal_code VARCHAR(5) NOT NULL, 

  household_type householdType NOT NULL, 

  square_footage INT NOT NULL, 

  heating INT DEFAULT NULL, 

  cooling INT DEFAULT NULL, 

  PRIMARY KEY (email),

  UNIQUE (email) 

); 

/* ---------------- PublicUtilities ---------------- */

DROP TABLE IF EXISTS PublicUtilities;

DROP TYPE IF EXISTS utilityType; 

CREATE TYPE utilityType AS ENUM('electric','gas', 'steam', 'liquid fuel');

CREATE TABLE PublicUtilities( 

  email varchar(250) NOT NULL, 

  utility utilityType NOT NULL, 

  PRIMARY KEY(email, utility),

  UNIQUE (email, utility)

); 

/* ---------------- APPLIANCES ---------------- */

DROP TABLE IF EXISTS Appliance CASCADE;

DROP TYPE IF EXISTS applianceType; 

CREATE TYPE applianceType AS ENUM('AirHandler','WaterHeater');

CREATE TABLE Appliance( 

  email varchar(250) NOT NULL, 

  appliance_number int NOT NULL, 

  model_name varchar(250) DEFAULT NULL, 

  manufacturer varchar(250) NOT NULL, 

  btu_rating int NOT NULL, 

  appliance_type applianceType NOT NULL, 

  PRIMARY KEY(email, appliance_number), 

  UNIQUE (email, appliance_number)

); 

/* ---------------- AirHandler ---------------- */

DROP TABLE IF EXISTS AirHandler CASCADE;

CREATE TABLE AirHandler ( 

  email varchar(250) NOT NULL, 

  appliance_number int NOT NULL, 

  fan_rpm int NOT NULL, 

  PRIMARY KEY(email, appliance_number),  

  UNIQUE (email, appliance_number)

  /*air_conditioner composite DEFAULT NULL, 
  Heater composite DEFAULT NULL, 
  heat_pump composite type DEFAULT NULL */
); 

/* ---------------- AirConditioner ---------------- */

DROP TABLE IF EXISTS AirConditioner;

CREATE TABLE AirConditioner ( 

  email varchar(250) NOT NULL, 

  appliance_number int NOT NULL, 

  eer float(10) NOT NULL, 

  PRIMARY KEY(email, appliance_number),  

  UNIQUE (email, appliance_number)

); 

/* ---------------- Heater ---------------- */

DROP TABLE IF EXISTS Heater;

DROP TYPE IF EXISTS energySource; 

CREATE TYPE energySource AS ENUM('electric','gas', 'solar');

CREATE TABLE Heater ( 

  email varchar(250) NOT NULL, 

  appliance_number int NOT NULL, 

  energy_source energySource NOT NULL, 

  PRIMARY KEY(email, appliance_number), 

  UNIQUE (email, appliance_number) 

); 

/* ---------------- HeatPump ---------------- */

DROP TABLE IF EXISTS HeatPump;

CREATE TABLE HeatPump ( 

  email varchar(250) NOT NULL, 

  appliance_number int NOT NULL, 

  SEER float(10) NOT NULL, 

  HSPF float (10) NOT NULL, 

  PRIMARY KEY(email, appliance_number), 

  UNIQUE (email, appliance_number) 

); 

/* ---------------- WaterHeater ---------------- */

DROP TABLE IF EXISTS WaterHeater;

DROP TYPE IF EXISTS waterHeaterEnergySource; 

CREATE TYPE waterHeaterEnergySource AS ENUM('electric','fuel oil', 'gas', 'heat pump');

CREATE TABLE WaterHeater ( 

  email varchar(250) NOT NULL, 

  appliance_number int NOT NULL, 

  model_name varchar(250) DEFAULT NULL, 

  manufacturer varchar(250) NOT NULL, 

  tank_gallons float(10) NOT NULL, 

  temperature_setting int DEFAULT NULL, 

  energy_source waterHeaterEnergySource NOT NULL, 

  PRIMARY KEY(email, appliance_number), 

  UNIQUE (email, appliance_number) 

); 


/* ---------------- Manufacturer ---------------- */

DROP TABLE IF EXISTS Manufacturer;

CREATE TABLE Manufacturer ( 

  manufacturer varchar(250) NOT NULL,

  PRIMARY KEY(manufacturer) 

); 

/* ---------------- PowerGeneration ---------------- */

DROP TABLE IF EXISTS PowerGeneration;

DROP TYPE IF EXISTS powerGenerationType; 

CREATE TYPE powerGenerationType AS ENUM('solar', 'wind turbine');

CREATE TABLE PowerGeneration ( 

  email varchar(250) NOT NULL, 

  power_generator_number int NOT NULL, 

  "type" powerGenerationType NOT NULL, 

  monthly_kWh int NOT NULL, 

  storage_kWh int DEFAULT NULL, 

  PRIMARY KEY(email, power_generator_number),

  UNIQUE (email, power_generator_number) 

); 



/* ---------------- CONSTRAINTS ---------------- */

/* --- Households --- */
ALTER Table Households
  ADD FOREIGN KEY(postal_code) REFERENCES PostalCode(postal_code); 

/* --- PublicUtilities --- */
ALTER Table PublicUtilities

  ADD FOREIGN KEY(email) REFERENCES Households(email);  

/* --- Appliances --- */
ALTER Table Appliance

  ADD FOREIGN KEY(email) REFERENCES Households(email),
  ADD FOREIGN KEY(manufacturer) REFERENCES Manufacturer(manufacturer); 

/* --- AirHandler --- */
ALTER Table AirHandler

  ADD FOREIGN KEY(email, appliance_number) REFERENCES Appliance(email, appliance_number);

/* --- AirConditioner --- */
ALTER Table AirConditioner

  ADD FOREIGN KEY(email, appliance_number) REFERENCES AirHandler(email, appliance_number);

/* --- Heater --- */
ALTER Table Heater

  ADD FOREIGN KEY(email, appliance_number) REFERENCES Heater(email, appliance_number);

/* --- HeatPump --- */
ALTER Table HeatPump

  ADD FOREIGN KEY(email, appliance_number) REFERENCES HeatPump(email, appliance_number);

/* --- WaterHeater --- */
ALTER Table WaterHeater

  ADD FOREIGN KEY(email, appliance_number) REFERENCES Appliance(email, appliance_number);

/* --- PowerGeneration --- */
ALTER Table PowerGeneration

  ADD FOREIGN KEY(email) REFERENCES Households(email);
