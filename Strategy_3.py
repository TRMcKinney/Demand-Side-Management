import numpy as np
import pandas as pd
import csv
import os
import glob
pd.options.mode.chained_assignment = None  # default='warn'



GRID_LIMIT = 12000




#load in all the houses at once
path = os.getcwd()
csv_files = glob.glob(os.path.join(path, "*.csv"))
#put all these .csv house data files into a dictionary
car_input_dict = {}
for i, f in zip(range(1380), csv_files):
    df = pd.read_csv(f)
    x = f.split("\\")[-1]
    #print(x)
    id = x.split(".")[0]
    #print(id)
    new = {id:df}
    car_input_dict.update(new)
print('There are', len(car_input_dict.keys()), 'cars loaded in')




#load in grid power file
power = pd.read_csv(r"C:\Users\mckin\Desktop\Demand Side Management\Grid Power.csv")
#print(power)




#combine the charging power of every car at every timestep
weeks = 4
week_codes = list(range(1,weeks+1))
days_of_week = ['Mon', 'Tue', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']
week_day_numbers = []
for week in week_codes:
    for day in days_of_week:
        p = day + str(week)
        week_day_numbers.append(p)
#print(week_day_numbers)


column_headings = []
for daynum in week_day_numbers:
    p = daynum + ' Charging Power'
    column_headings.append(p)





charging_power = []
#working through each timestep
for day in week_day_numbers:
    for i in range(48):
        #charging_power = []
        for car in car_input_dict:
            #print(car)
            CarData = car_input_dict[car]
            c_p = CarData[day + ' Charging Power'][i]
            charging_power.append(c_p)
        #sum the charging_power list to get the original, required (for full charging capability)
        #power from ev charging at that timestep
        EV_power = sum(charging_power)
        #print('On', day, 'at Index', i, 'Power required is', EV_power, 'kW')
        charging_power = [] #reset charging power list so that it doesn't give us a cumulative value through the timesteeps
        #retrieve the grid power at this timestep

        GRID_power = power[day + ' Grid Power'][i]
        #print(GRID_power)

        #Add EV and GRID power together
        TOTAL_power = EV_power + GRID_power
        #print(TOTAL_power)

        #check if grid limit is broken through
        if TOTAL_power > GRID_LIMIT:
            #print('breakthrough on', day, 'at Index', i, ' - total power = ', TOTAL_power)
            #calculate by how much it is over
            delta = TOTAL_power - GRID_LIMIT
            #print(delta)
            #need the total number of chargers in use at this timestep
            chargers = 0
            for car in car_input_dict:
                CarData = car_input_dict[car]
                if CarData[day + ' Charging Power'][i] == 6.6:
                    chargers = chargers + 1
            #divide the delta by the number of chargers, so we know by how much each
            #charger power needs to reduce to meet the grid limit
            reduction = delta/chargers
            #print('Each charger needs to reduce power output by: ', reduction)
            #then need to reduce the charging power by this amount in the original individual spreadsheets
            for car in car_input_dict:
                CarData = car_input_dict[car]
                if CarData[day + ' Charging Power'][i] == 6.6:
                    CarData[day + ' Charging Power'][i] = 6.6 - reduction
                    charge_energy = CarData[day + ' Charging Energy'][i]
                    CarData[day + ' Charging Energy'][i] = CarData[day + ' Charging Power'][i]/2 #new charging energy
                    #recalculate Battery Capacity column value for this timestep
                    #bat_cap_change = charge_energy - CarData[day + ' Charging Energy'][i]
                    CarData[day + ' Battery Capacity'][i] = CarData[day + ' Battery Capacity'][i-1] + CarData[day + ' Charging Energy'][i]
                    #80% SOC check
                    if CarData[day + ' Battery Capacity'][i] < 29.6:
                        if CarData[day + " Location Code"][i+1] == 0:
                            if i+1 < 14:
                                CarData[day + ' Charging Power'][i+1] = 6.6
                            else:
                                CarData[day + ' Charging Power'][i+1] = 0
                        else:
                            CarData[day + ' Charging Power'][i+1] = 0
                    else:
                        overshoot = CarData[day + ' Battery Capacity'][i] - 29.6
                        CarData[day + ' Battery Capacity'][i] = 29.6
                        CarData[day + ' Charging Power'][i+1] = 0
                        CarData[day + ' Charging Energy'][i] = CarData[day + ' Charging Energy'][i] - overshoot
        else: #no power reduction but still charging
            for car in car_input_dict:
                CarData = car_input_dict[car]
                if CarData[day + ' Charging Power'][i] == 6.6:
                    #if HouseData[day + " Location Code"][i] == 0: #don't need this, if its 6.6 its at home anyway
                    if i < 14: #make sure its in economy hours
                        CarData[day + " Charging Energy"][i] = 3.3
                        CarData[day + " Battery Capacity"][i] = CarData[day + " Battery Capacity"][i-1] + 3.3
                        if CarData[day + " Battery Capacity"][i] >= 29.6:
                            delta = CarData[day + " Battery Capacity"][i] - 29.6
                            CarData[day + " Charging Energy"][i] = 3.3 - delta
                            CarData[day + " Battery Capacity"][i] = 29.6
                            CarData[day + ' Charging Power'][i+1] = 0
                        else:
                            CarData[day + ' Charging Power'][i+1] = 6.6
                    else: #car outside economy hours
                        CarData[day + ' Charging Power'][i] = 0
                        CarData[day + ' Charging Energy'][i] = 0
                        CarData[day + " Battery Capacity"][i] = CarData[day + " Battery Capacity"][i-1]
        for car in car_input_dict:
            CarData = car_input_dict[car]
            CarData[day + ' State of Charge (%)'][i] = (CarData[day + ' Battery Capacity'][i]/37)*100
        #print("--------------------------------")
    print(day, ' completed')

#save the new dataframes
for car in car_input_dict:
    CarData = car_input_dict[car]
    newpath = r'C:\Users\mckin\Desktop\Demand Side Management\DSM Scenario 3 Results\12000 Limit'
    if not os.path.exists(newpath):
        os.makedirs(newpath)

    CarData.to_csv(r'C:\Users\mckin\Desktop\Demand Side Management\DSM Scenario 3 Results\12000 Limit\ '+str(car)+ '.csv')
print('All Vehicles SAVED')
