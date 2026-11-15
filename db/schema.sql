-- BIOFACTORY 4.0 — esquema PostgreSQL (generado desde los modelos)

CREATE TABLE companies (
	id SERIAL NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	ruc VARCHAR(30), 
	country VARCHAR(60) NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	weight_unit VARCHAR(8) NOT NULL, 
	sale_price_per_kg FLOAT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);


CREATE TABLE alert_rules (
	id SERIAL NOT NULL, 
	method VARCHAR(10) NOT NULL, 
	max_temp_c FLOAT, 
	max_duration_min INTEGER, 
	active BOOLEAN NOT NULL, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_alert_rules_company_id ON alert_rules (company_id);

CREATE TABLE fruit_types (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	pulp_yield_pct FLOAT NOT NULL, 
	seed_pct FLOAT NOT NULL, 
	peel_pct FLOAT NOT NULL, 
	wash_loss_pct FLOAT NOT NULL, 
	notes TEXT, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_fruit_types_company_id ON fruit_types (company_id);

CREATE TABLE inventory_items (
	id SERIAL NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	quantity FLOAT NOT NULL, 
	unit VARCHAR(15) NOT NULL, 
	min_stock FLOAT NOT NULL, 
	lot_number VARCHAR(40), 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_inventory_items_company_id ON inventory_items (company_id);

CREATE TABLE notifications (
	id SERIAL NOT NULL, 
	message VARCHAR(300) NOT NULL, 
	level VARCHAR(10) NOT NULL, 
	read BOOLEAN NOT NULL, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_notifications_company_id ON notifications (company_id);

CREATE TABLE plants (
	id SERIAL NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	location VARCHAR(200), 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_plants_company_id ON plants (company_id);

CREATE TABLE suppliers (
	id SERIAL NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	contact VARCHAR(150), 
	location VARCHAR(150), 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_suppliers_company_id ON suppliers (company_id);

CREATE TABLE telemetry_readings (
	id SERIAL NOT NULL, 
	device_id VARCHAR(60) NOT NULL, 
	sensor_type VARCHAR(30) NOT NULL, 
	value FLOAT NOT NULL, 
	unit VARCHAR(10) NOT NULL, 
	simulated BOOLEAN NOT NULL, 
	ts TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_telemetry_readings_company_id ON telemetry_readings (company_id);
CREATE INDEX ix_telemetry_readings_device_id ON telemetry_readings (device_id);

CREATE TABLE lots (
	id SERIAL NOT NULL, 
	lot_number VARCHAR(40) NOT NULL, 
	fruit_id INTEGER NOT NULL, 
	supplier_id INTEGER, 
	plant_id INTEGER, 
	received_on DATE NOT NULL, 
	weight_kg FLOAT NOT NULL, 
	quality VARCHAR(15) NOT NULL, 
	condition VARCHAR(20) NOT NULL, 
	notes TEXT, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (company_id, lot_number), 
	FOREIGN KEY(fruit_id) REFERENCES fruit_types (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id), 
	FOREIGN KEY(plant_id) REFERENCES plants (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_lots_lot_number ON lots (lot_number);
CREATE INDEX ix_lots_company_id ON lots (company_id);

CREATE TABLE machines (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	station VARCHAR(30) NOT NULL, 
	capacity_kg_h FLOAT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	plant_id INTEGER, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(plant_id) REFERENCES plants (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_machines_company_id ON machines (company_id);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR(200) NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	password_hash VARCHAR(100) NOT NULL, 
	role VARCHAR(30) NOT NULL, 
	active BOOLEAN NOT NULL, 
	plant_id INTEGER, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(plant_id) REFERENCES plants (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_users_company_id ON users (company_id);
CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE activity_log (
	id SERIAL NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(30) NOT NULL, 
	entity VARCHAR(40) NOT NULL, 
	entity_id INTEGER, 
	detail VARCHAR(300), 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_activity_log_company_id ON activity_log (company_id);

CREATE TABLE cost_entries (
	id SERIAL NOT NULL, 
	category VARCHAR(30) NOT NULL, 
	amount FLOAT NOT NULL, 
	incurred_on DATE NOT NULL, 
	lot_id INTEGER, 
	description VARCHAR(200), 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_cost_entries_company_id ON cost_entries (company_id);

CREATE TABLE freezing_records (
	id SERIAL NOT NULL, 
	lot_id INTEGER NOT NULL, 
	recorded_on DATE NOT NULL, 
	product_type VARCHAR(20) NOT NULL, 
	method VARCHAR(10) NOT NULL, 
	temp_c FLOAT NOT NULL, 
	duration_min INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	alert BOOLEAN NOT NULL, 
	alert_message VARCHAR(300), 
	notes TEXT, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_freezing_records_company_id ON freezing_records (company_id);
CREATE INDEX ix_freezing_records_lot_id ON freezing_records (lot_id);

CREATE TABLE inventory_movements (
	id SERIAL NOT NULL, 
	item_id INTEGER NOT NULL, 
	kind VARCHAR(10) NOT NULL, 
	quantity FLOAT NOT NULL, 
	lot_number VARCHAR(40), 
	reason VARCHAR(200), 
	user_id INTEGER, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(item_id) REFERENCES inventory_items (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_inventory_movements_item_id ON inventory_movements (item_id);
CREATE INDEX ix_inventory_movements_company_id ON inventory_movements (company_id);

CREATE TABLE packaging_records (
	id SERIAL NOT NULL, 
	lot_id INTEGER NOT NULL, 
	recorded_on DATE NOT NULL, 
	bag_grams INTEGER NOT NULL, 
	units INTEGER NOT NULL, 
	rejected_units INTEGER NOT NULL, 
	total_kg FLOAT NOT NULL, 
	bags_used INTEGER NOT NULL, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_packaging_records_lot_id ON packaging_records (lot_id);
CREATE INDEX ix_packaging_records_company_id ON packaging_records (company_id);

CREATE TABLE password_resets (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	used BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_password_resets_token_hash ON password_resets (token_hash);

CREATE TABLE pulping_records (
	id SERIAL NOT NULL, 
	lot_id INTEGER NOT NULL, 
	recorded_on DATE NOT NULL, 
	initial_kg FLOAT NOT NULL, 
	pulp_kg FLOAT NOT NULL, 
	seed_kg FLOAT NOT NULL, 
	peel_kg FLOAT NOT NULL, 
	other_kg FLOAT NOT NULL, 
	yield_pct FLOAT NOT NULL, 
	company_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(lot_id) REFERENCES lots (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id)
);

CREATE INDEX ix_pulping_records_lot_id ON pulping_records (lot_id);
CREATE INDEX ix_pulping_records_company_id ON pulping_records (company_id);

