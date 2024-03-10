create_table_query = """
            CREATE TABLE carpark(
                carparkid TEXT,
                area TEXT,
                development TEXT,
                location TEXT,
                availablelots INTEGER,
                lottype TEXT,
                agency TEXT,
                timestamp TIMESTAMP
            );

            CREATE TABLE erprates(
                vehicletype TEXT,
                daytype TEXT,
                starttime TIME,
                endtime TIME,
                zoneid TEXT,
                chargeamount DECIMAL,
                effectivedate DATE,
                timestamp TIMESTAMP
            );

            CREATE TABLE esttraveltimes(
                name TEXT,
                direction INT,
                farendoint TEXT,
                startpoint TEXT,
                endpoint TEXT,
                esttime INT,
                timestamp TIMESTAMP
            );

            CREATE TABLE faultytrafficlights (
                alarmid TEXT,
                nodeid INT,
                type INT,
                startdate TIMESTAMP,
                enddate TIMESTAMP,
                message TEXT,
                timestamp TIMESTAMP
            );

            CREATE TABLE roadopenings (
                eventid TEXT,
                startdate TEXT,
                enddate TEXT,
                svcdept TEXT,
                roadname TEXT,
                other TEXT,
                timestamp TIMESTAMP
            );
            CREATE TABLE roadworks (
                eventid TEXT,
                startdate TEXT,
                enddate TEXT,
                svcdept TEXT,
                roadname TEXT,
                other TEXT,
                timestamp TIMESTAMP
            );

            CREATE TABLE trafficimages (
                cameraid TEXT,
                latitude TEXT,
                longitude TEXT,
                imagelink TEXT
            );

            CREATE TABLE trafficincidents (
                type TEXT,
                latitude DECIMAL,
                longitude DECIMAL,
                message TEXT,
                timestamp TIMESTAMP
            );

            CREATE TABLE trafficspeedbands (
                linkid TEXT,
                roadname TEXT,
                roadcategory TEXT,
                speedband TEXT,
                minimumspeed INTEGER,
                maximumspeed INTEGER,
                startlon DECIMAL,
                startlat DECIMAL,
                endlon DECIMAL,
                endlat DECIMAL,
                timestamp TIMESTAMP
            );

            CREATE TABLE vms(
                equipmentid TEXT,
                latitude DECIMAL,
                longitude DECIMAL,
                message TEXT,
                timestamp TIMESTAMP
            );


            """