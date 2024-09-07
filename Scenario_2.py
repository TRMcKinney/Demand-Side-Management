from turtle import xcor
import numpy as np
import pandas as pd
import csv
import os
import glob
import math
from random import sample
import random
from time import sleep
from tqdm import tqdm
pd.options.mode.chained_assignment = None  # default='warn'


GRID_LIMIT = 12000


#load in all the houses at once
path = os.getcwd()
csv_files = glob.glob(os.path.join(path, "*.csv"))
#put all these .csv house data files into a dictionary
car_input_dict = {}
print('Importing Vehicles')
with tqdm(total=1380)  as pbar:
    for i, f in zip(range(1380), csv_files):
        #sleep(0.02)
        df = pd.read_csv(f)
        x = f.split("\\")[-1]
        #print(x)
        id = x.split(".")[0]
        #print(id)
        new = {id:df}
        car_input_dict.update(new)
        pbar.update(1)
print('There are', len(car_input_dict.keys()), 'cars loaded in')

#load in grid power file
power = pd.read_csv(r"C:\Users\mckin\Desktop\Demand_Side_Management\Grid Power.csv")

#work out at each timestep the number of house's (chargepoints) that can have power within the cap
#each charger will still get 6.6kW

#don't worry about number of chargepoints at a single house, treat it from pov of chargepoints,
#so just one chargepoint at a house with three can have power. This is fairer, but just mention as a interesting point =
#of grids were to 'disconnect' chargers how would it be done, that house it limited, or the total power to the whole house is limited?
#as then a house with three chargers could still have power but then a house with one charger would not
#have any power... but for this work, treat each charger as if it is individually plugged directly into the grid

#combine the charging power of every car at every timestep
weeks = 4
week_codes = list(range(1,weeks+1))
days_of_week = ['Mon', 'Tue', 'Wed', 'Thurs', 'Fri', 'Sat', 'Sun']
week_day_numbers = []
for week in week_codes:
    for day in days_of_week:
        p = day + str(week)
        week_day_numbers.append(p)

#making vehicle charging (old and new) dataframe to save as .csv file to keep track
#making the column headings for the dataframe
col_heads = []
for day in week_day_numbers:
    for i in range(48):
        a = day + ' ' + str(i)
        col_heads.append(a)

column_headings = []
for daynum in week_day_numbers:
    p = daynum + ' Charging Power'
    column_headings.append(p)

vehicles_charging_dict = {}
charging_power = []
before_vehicles_charging = [] #the vehicles that are set to charge from previous ev charging model
after_vehicles_charging = [] #the vehicles that are now only allowed to charge due to DSM scenario
#working through each timestep
count = 0
old_vehicles_charging_dict = {} #dictionary for all the vehicles that were originally wanting to charge


with tqdm(total=1344)  as pbar:
    for day in week_day_numbers:
            for i in range(48):
                count = count + 1 #to label the recalculation dictionary entries
                for car in car_input_dict:
                    CarData = car_input_dict[car]
                    c_p = CarData[day + ' Charging Power'][i]
                    charging_power.append(c_p)
                #sum the charging_power list to get the original, required (for full charging capability)
                #power from ev charging at that timestep
                EV_power = sum(charging_power)
                charging_power = [] #reset charging power list so that it doesn't give us a cumulative value after each timestep
                #retrieve the grid power at this timestep
                GRID_power = power[day + ' Grid Power'][i]
                #Add EV and GRID power together
                TOTAL_power = EV_power + GRID_power
                #check if grid limit is broken through
                if TOTAL_power > GRID_LIMIT:

                    AVAILABLE_power = GRID_LIMIT - GRID_power #AVAILABLE_power is the power available to EV charging
                    No_Chargers = math.floor(AVAILABLE_power/6.6) #math.floor rounds down to nearest whole integer

                    #make a list of all the chargepoints that are trying to charge in this timestep
                    for car in car_input_dict:
                        CarData = car_input_dict[car]
                        if CarData[day + ' Charging Power'][i] == 6.6:
                            before_vehicles_charging.append(car)

                    #need to grab the SOC for all these vehicles at this timestep
                    SOC = []
                    for car in before_vehicles_charging:
                        CarData = car_input_dict[car]
                        state = CarData[day + ' State of Charge (%)'][i]
                        SOC.append(state)
                    ordered_vehicles_charging = pd.DataFrame({'Vehicle ID': before_vehicles_charging, 'SOC': SOC})
                    #now need to order this from smallest to largest SOC
                    ordered_vehicles_charging.sort_values(by=['SOC'], inplace=True)
                    before_vehicles_charging = ordered_vehicles_charging['Vehicle ID'].tolist()


                    #selecting the **FIRST** 'X' number of cars that will be able to charge as per the 'No_Chargers' value
                    after_vehicles_charging = before_vehicles_charging[:No_Chargers]
                    recalculation_list = set(before_vehicles_charging).difference(set(after_vehicles_charging)) #work out the vehicle dataframes that will be affected and have to change - they can no longer charge

                    #will need to remember which cars charged in this timestep instance, as those are the ones that need to continue charging
                    #make a dictionary of all the vehicles which charge in each timestep of each day as a new key of the dictionary
                    key = count
                    new = {key:after_vehicles_charging}
                    vehicles_charging_dict.update(new)
                    key = count
                    new = {key:before_vehicles_charging}
                    old_vehicles_charging_dict.update(new)

                    for car in recalculation_list: #going through the recalculation list and amending these dataframes - they can no longer be charging
                        CarData = car_input_dict[car]

                        CarData[day + ' Charging Power'][i] = 0
                        CarData[day + ' Charging Energy'][i] = 0
                        CarData[day + " Battery Capacity"][i] = CarData[day + " Battery Capacity"][i-1]
                        CarData[day + ' State of Charge (%)'][i] = CarData[day + ' State of Charge (%)'][i-1]

                        #Now amend the rest of the column
                        for y in range(i+1, 48):
                            CarData[day + ' Battery Capacity'][y] = CarData[day + ' Battery Capacity'][y-1] - (CarData[day + ' Energy'][y] - CarData[day + ' Energy'][y-1])
                            CarData[day + " Charging Energy"][y] = 0
                            CarData[day + " Charging Power"][y] = 0
                            if CarData[day + ' Battery Capacity'][y] < 29.6:
                                if CarData[day + ' Location Code'][y] == 0: #car is at home so can charge
                                    if y < 15:
                                        CarData[day + " Charging Energy"][y] = 3.3
                                        CarData[day + " Charging Power"][y] = 6.6
                                        CarData[day + ' Battery Capacity'][y] = CarData[day + ' Battery Capacity'][y-1] + 3.3
                                        if CarData[day + " Battery Capacity"][y] >= 29.6:
                                            delta = CarData[day + " Battery Capacity"][y] - 29.6
                                            CarData[day + " Charging Energy"][y] = 3.3 - delta
                                            CarData[day + " Battery Capacity"][y] = 29.6
                                    else: #car at home but not in economy hours so cant charge
                                        continue
                                else: #car is not at home so cant charge
                                    continue
                            else: #does not need charging
                                continue
                            CarData[day + ' State of Charge (%)'][y] = (CarData[day + " Battery Capacity"][y]/37)*100
                            
                #if no grid limit threshold exceeded then add an empty dataframe to the dictionary for this count number
                key = count
                new = {key:after_vehicles_charging} #this should still be an empty dataframe
                vehicles_charging_dict.update(new)           

                new = {key:before_vehicles_charging}
                old_vehicles_charging_dict.update(new)

                after_vehicles_charging = [] #reset for the next timestep
                before_vehicles_charging = [] #reset for the next timestep  
                pbar.update(1)

old_charging_dataframe = pd.DataFrame(dict([ (k, pd.Series(v)) for k,v in old_vehicles_charging_dict.items()]))
after_charging_dataframe = pd.DataFrame(dict([ (k, pd.Series(v)) for k,v in vehicles_charging_dict.items()]))

#save the new dataframes
print('Saving Vehicles')
with tqdm(total=1380)  as pbar:
    for car in car_input_dict:
        CarData = car_input_dict[car]
        newpath = r'C:\Users\mckin\Desktop\Demand_Side_Management\DSM Scenario 2 Results\12000 Limit'
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        CarData.to_csv(r'C:\Users\mckin\Desktop\Demand_Side_Management\DSM Scenario 2 Results\12000 Limit\ '+str(car)+ '.csv')
        pbar.update(1)
print('All Vehicles Saved')

newpath = r'C:\Users\mckin\Desktop\Demand_Side_Management\DSM Scenario 2 Results\Vehicles Charging Log'
if not os.path.exists(newpath):
    os.makedirs(newpath)

old_charging_dataframe.to_csv(r'C:\Users\mckin\Desktop\Demand_Side_Management\DSM Scenario 2 Results\Vehicles Charging Log\DSM Scenario 2 - 12000 Limit - original_chargers.csv')
after_charging_dataframe.to_csv(r'C:\Users\mckin\Desktop\Demand_Side_Management\DSM Scenario 2 Results\Vehicles Charging Log\DSM Scenario 2 - 12000 Limit - after_chargers.csv')
print('Saved Vehicle Charging Logs')
print('Completed')