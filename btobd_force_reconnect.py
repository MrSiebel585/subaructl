import obd, time

while True:
    try:
        connection = obd.OBD("/dev/rfcomm0", fast=False)
        if connection.is_connected():
            print("Connected to OBD")
            # Run logging loop
            while True:
                rpm = connection.query(obd.commands.RPM)
                print(rpm.value)
                time.sleep(1)
        else:
            print("Retrying...")
    except Exception as e:
        print("Connection lost:", e)
    time.sleep(3)  # wait and retry
