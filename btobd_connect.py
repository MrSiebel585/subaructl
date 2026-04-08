import obd, time, json

connection = obd.OBD("/dev/rfcomm0")
cmd_list = [obd.commands.RPM, obd.commands.SPEED, obd.commands.COOLANT_TEMP]

while True:
    data = {str(c.name): connection.query(c).value for c in cmd_list}
    data["timestamp"] = time.time()
    with open("/opt/logs/obd_bt.log","a") as f:
        f.write(json.dumps(data)+"\n")
    time.sleep(1)
