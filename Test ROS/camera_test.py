#!/usr/bin/env python

from dronekit import connect, VehicleMode, LocationGlobalRelative
import time
import math

# Connect to the vehicle (SITL usually on localhost)
vehicle = connect('127.0.0.1:14550', wait_ready=True)

# Set mode to GUIDED and arm
vehicle.mode = VehicleMode("GUIDED")
vehicle.armed = True

while not vehicle.armed:
    print("Waiting for arming...")
    time.sleep(1)

# Take off to 5 meters
target_altitude = 5
vehicle.simple_takeoff(target_altitude)


# Wait before forward movement
time.sleep(15)

vehicle.close()
print("Mission complete.")

