CREATE_TABLE_QUERY = """
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
                effectivedate DATE
            );

            CREATE TABLE esttraveltimes(
                name TEXT,
                direction INT,
                farendoint TEXT,
                startpoint TEXT,
                endpoint TEXT,
                esttime INT
            );

            CREATE TABLE faultytrafficlights (
                alarmid TEXT,
                nodeid INT,
                type INT,
                startdate TIMESTAMP,
                enddate TIMESTAMP,
                message TEXT
            );

            CREATE TABLE roadopenings (
                eventid TEXT,
                startdate TEXT,
                enddate TEXT,
                svcdept TEXT,
                roadname TEXT,
                other TEXT
            );
            CREATE TABLE roadworks (
                eventid TEXT,
                startdate TEXT,
                enddate TEXT,
                svcdept TEXT,
                roadname TEXT,
                other TEXT
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
                message TEXT
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
            );

            CREATE TABLE vms(
                equipmentid TEXT,
                latitude DECIMAL,
                longitude DECIMAL,
                message TEXT
            );


            """