#!/usr/bin/env python3
from glob import glob

from logging import config
import os 
from datetime import datetime
import pdb 
import sys
import itertools
#from networkx import config
import numpy as np
from multiprocessing import Pool
import argparse
import re 
import pandas as pd 
import matplotlib.pyplot as plt

import subprocess
from datetime import timedelta
import json
import matplotlib.dates as mdates
from contextlib import redirect_stdout
import shutil
import subprocess
try:
    import py_gamma as pg
except ImportError:
    print("py_gamma module not found. Please install it to use this script.")
    sys.exit(1)
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
 
def validate_dates(dateM, date1, date2):
    # Validate dateM: it must be either an 8-digit string or a list of length 1 containing an 8-digit string.
    if isinstance(dateM, list):
        if len(dateM) == 1 and isinstance(dateM[0], str) and len(dateM[0]) == 8 and dateM[0].isdigit():
            dateM = dateM[0]  # Convert list of length 1 to an 8-digit string
        else:
            raise ValueError("dateM must be a list of length 1 containing an 8-digit string or an 8-digit string.")
    elif isinstance(dateM, str):
        if not (len(dateM) == 8 and dateM.isdigit()):
            raise ValueError("dateM must be an 8-digit string.")
    else:
        raise TypeError("dateM must be either a string or a list of length 1.")

    # Validate that date1 and date2 are lists of equal length and each element is an 8-digit string.
    if not (isinstance(date1, list) and isinstance(date2, list)):
        raise TypeError("date1 and date2 must both be lists.")

    if len(date1) != len(date2):
        raise ValueError("date1 and date2 must be of equal length.")

    for d1, d2 in zip(date1, date2):
        if not (isinstance(d1, str) and isinstance(d2, str) and len(d1) == 8 and len(d2) == 8 and d1.isdigit() and d2.isdigit()):
            raise ValueError("Each element of date1 and date2 must be an 8-digit string.")

    # Return the validated and possibly modified dateM
    return dateM



def check_dates(date1_str, date2_str, date_min_str, date_max_str):
    # Define the date format
    date_format = "%Y%m%d"
    
    try:
        # Convert date strings to datetime objects
        date1 = datetime.strptime(date1_str, date_format)
        date2 = datetime.strptime(date2_str, date_format)
        date_min = datetime.strptime(date_min_str, date_format)
        date_max = datetime.strptime(date_max_str, date_format)
        
        # Perform the checks
        is_date1_not_equal_date2 = date1 != date2
        is_date1_before_date2 = date1 < date2
        is_date1_in_range = date_min < date1 < date_max
        is_date2_in_range = date_min < date2 < date_max 
        # Create a dictionary to store the results of the checks
        check_results = {
            "date1": date1_str,
            "date2": date2_str,
            "is_date1_not_equal_date2": is_date1_not_equal_date2,
            "is_date1_before_date2": is_date1_before_date2,
            "is_date1_in_range": is_date1_in_range,
            "is_date2_in_range": is_date2_in_range
        }

        # Write the results to a text file
        with open("date_checks.txt", "a") as file:
            file.write(f"{check_results}\n")
        
        if is_date1_before_date2 and is_date1_in_range and is_date2_in_range and is_date1_not_equal_date2:
            return True
        else:
            return False
            
    except ValueError as e:
        # Handle invalid date formats
        print(f"Error: {e}")
        return False

def construct_date1_date2_combinations(config,n_days,date_min,date_max,step1=False):
    date_list = []
    topdir = config['topdir']
    slc_dir = config['slc_dir']
    min_n_days = config['min_n_days']

    no_important_date = True
    if "important_date" in config:
        important_date = config["important_date"]
        no_important_date = False


    
    print('Using SLCs to find dates')
    search_list = glob(os.path.join(slc_dir,'*'))
    date_list = [os.path.split(file)[-1] for file in search_list]
    date_list = [date for date in date_list if 'M' not in date]

                
    date_array = np.array(date_list)
    # remove repeated dates
    date_array = np.unique(date_array)
    # sort date array min to max
    date_array_sorted = np.sort(date_array)
    date_array_sorted = np.sort(date_array)
    
    

 
    # Check if date_list contains repeats
    # If it does, print a warning and exit the program
    # Otherwise, print the list of dates
    if len(date_list) != len(set(date_list)):
        print(bcolors.WARNING+"Warning: The date list contains repeated dates."+bcolors.ENDC)
        #find repeated dates and print the file path to repeated date 
        for date in set(date_list):
            if date_list.count(date) > 1:
                print(f"Repeated date: {date}")

    else:
        print(bcolors.OKGREEN+"The date list is:"+bcolors.ENDC)
        print(date_list) 
    

    if step1 and len(date_array_sorted) ==1:
        print(bcolors.WARNING+"Warning: Less than 2 unique dates found. Please check your data."+bcolors.ENDC)
        dates1 = list(date_array_sorted)
        dates2 = []
        return dates1,dates2
    #print(date_list)    
    # Initialize lists to store paired dates
    dates1 = []
    dates2 = []
    
    # Use itertools.combinations to generate all possible pairs
    combinations = itertools.combinations(date_array_sorted, 2)
    # Ensure each pair is ordered from earliest to latest
    date_pairs = [(min(date1, date2), max(date1, date2)) for date1, date2 in combinations]
    date_pairs = sorted(date_pairs, key=lambda x: datetime.strptime(x[0], '%Y%m%d'))
    for date1, date2 in date_pairs:
        
        # if no_important_date == false, then check if dates span the important date 
        if no_important_date == False:
         
            important_date_dt = datetime.strptime(important_date, '%Y%m%d')
            date1_dt = datetime.strptime(date1, '%Y%m%d')
            date2_dt = datetime.strptime(date2, '%Y%m%d')
            if not (date1_dt < important_date_dt < date2_dt):
                print(f"Skipping pair {date1} - {date2} as it does not span important date {important_date}")
                continue

        if check_dates(date1, date2, date_min, date_max):
            print(f"Checking  pair {date1} - {date2}")
            date1_dt = datetime.strptime(date1, '%Y%m%d')
            date2_dt = datetime.strptime(date2, '%Y%m%d')
    
            # Calculate the difference in days between the two dates
            delta = abs((date2_dt - date1_dt).days)
            if min_n_days <= delta <= n_days:
                dates1.append(date1)
                dates2.append(date2)

            else:
                print(f"Skipping pair {date1} - {date2}")
        

       
    return dates1,dates2



def proc_master_slc(config):
    
    dateM = config['dateM']
    topdir = config['topdir']
    slc_dir = config['slc_dir'] 
    os.chdir(topdir)

    if not os.path.exists(slc_dir):
        os.makedirs(slc_dir)


    # Create master date folder to be used as non-master date
    pg.multi_look(os.path.join(slc_dir,f'{dateM}/{dateM}.slc'),     #input slc
                 os.path.join(slc_dir,f'{dateM}/{dateM}.slc.par'), #input par
                 os.path.join(slc_dir,f'{dateM}/{dateM}.mli'),     # output mli
                 os.path.join(slc_dir,f'{dateM}/{dateM}.mli.par'), #output par
                 config["rlks"], config["azlks"]) 
    
    # Copy slc_dir/{dateM} directory to slc_dir/{dateM}M  and use as master date
    dateMM = f"{dateM}M"
    src_dir = os.path.join(slc_dir, dateM)
    dst_dir = os.path.join(slc_dir, dateMM)

    if os.path.exists(dst_dir):
        print(bcolors.WARNING + f"Directory {dst_dir} already exists. Skipping copy." + bcolors.ENDC)
    else:
        shutil.copytree(src_dir, dst_dir)
        print(bcolors.OKGREEN + f"Copied {src_dir} to {dst_dir}" + bcolors.ENDC)

    return print(bcolors.OKGREEN + 'Master SLC successfully' + bcolors.ENDC)



def produce_lookvectors(config):

    dateM = config['dateM']
    topdir = config['topdir']
    slc_dir = os.path.join(topdir,'slcs')

    dem_par = pg.ParFile(os.path.join(slc_dir,f'{dateM}M','P.dem_par'))	
    widthdem=int(dem_par.get_value('width'))
    lengthdem = int(dem_par.get_value('nlines'))

    dateM_mli_par = pg.ParFile(os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}.mli.par'))
    lengthmli= int(dateM_mli_par.get_value('azimuth_lines')) 
    widthmli=int(dateM_mli_par.get_value('range_samples'))

    
    dem = config["dem"]
    demlat = config["demlat"]
    demlon = config["demlon"]

    geodir = os.path.join(topdir,'geo')
    # make the geodir
    if not os.path.exists(geodir):
        os.makedirs(geodir)

    slcMdir = os.path.join(topdir,'slcs',f'{dateM}M')
    slcMpar = os.path.join(slcMdir,f'{dateM}'+'.slc.par')

    u = os.path.join(topdir,'geo','u')
    #orientation angle of n 
    v = os.path.join(topdir,'geo','v')
    #local incidence angle
    inc = os.path.join(topdir,'geo','inc')
    #projection angle
    psi = os.path.join(topdir,'geo','psi')
    #pixel area normalization factor
    pix = os.path.join(topdir,'geo','pix')
    #layover and shadow map
    lsmap = os.path.join(topdir,'geo','ls_map')

    pg.gc_map(os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}.mli.par'), #  MLI_par         (input) ISP MLI or SLC image parameter file (slant range geometry)
                '-', 
                os.path.join(f'{topdir}/dem/{dem}.swap.dem_par'), 
                os.path.join(f'{topdir}/dem/{dem}.swap.dem'), 
                os.path.join(topdir,'slcs',f'{dateM}M',f'P.dem_par'), 
                os.path.join(topdir,'slcs',f'{dateM}M',f'P.dem'), 
                os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}M.lt'), 
                demlat, 
                demlon, 
                os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}M.sim_sar'),
                u,
                v,
                inc,
                psi,
                pix,
                lsmap,
                '8',
                '2',
                '')



    [width, length] = [widthmli,lengthmli]
    offpar = '-'

    [demwidth, demlength] =[widthdem,lengthdem]


    dem = os.path.join(slcMdir,'P.dem')
    theta = os.path.join(geodir,'theta')
    phi = os.path.join(geodir,'phi')
    lutfile = os.path.join(slcMdir,f'{dateM}M'+'.lt_fine')
    dempar = os.path.join(slc_dir,f'{dateM}M','P.dem_par')
    dem_par = pg.ParFile(dempar)	
    widthdem=int(dem_par.get_value('width'))
    lengthdem = int(dem_par.get_value('nlines'))



    pg.look_vector(slcMpar,offpar,os.path.join(slc_dir,f'{dateM}M','P.dem_par'),dem,theta,phi)

    pg.geocode(lutfile,theta,demwidth,theta+'.rc',width,length,0,0)

    pg.geocode(lutfile,phi,demwidth,phi+'.rc',width,length,0,0)

    thetarc = np.fromfile(theta+'.rc',dtype=np.float32).byteswap().reshape((int(length),int(width)))
    nanix = thetarc == 0
    thetarc[nanix] = np.nan
    phirc = np.fromfile(phi+'.rc',dtype=np.float32).byteswap().reshape((int(length),int(width)))
    phirc[nanix] = np.nan
    U = np.sin(thetarc)
    E = np.cos(phirc)*np.cos(thetarc)
    N = np.sin(phirc)*np.cos(thetarc)

    U[nanix] = 0
    E[nanix] = 0
    N[nanix] = 0
    U.byteswap().tofile(os.path.join(geodir,'U'))
    E.byteswap().tofile(os.path.join(geodir,'E'))
    N.byteswap().tofile(os.path.join(geodir,'N'))
    os.system('chmod 777 {0}'.format(os.path.join(geodir,'E')))
    os.system('chmod 777 {0}'.format(os.path.join(geodir,'N')))
    os.system('chmod 777 {0}'.format(os.path.join(geodir,'U')))
    os.remove(theta)
    os.remove(theta+'.rc')
    os.remove(phi)
    os.remove(phi+'.rc')


    lat=float(dem_par.get_value('corner_lat')[0])#`awk '$1 == "corner_lat:" {print $2}' ${procdir}/geo/EQA.dem_par`
    lon=float(dem_par.get_value('corner_lon')[0])#`awk '$1 == "corner_lon:" {print $2}' ${procdir}/geo/EQA.dem_par`
    latstep=float(dem_par.get_value('post_lat')[0])#`awk '$1 == "post_lat:" {print $2}' ${procdir}/geo/EQA.dem_par`
    lonstep=float(dem_par.get_value('post_lon')[0])#`awk '$1 == "post_lon:" {print $2}' ${procdir}/geo/EQA.dem_par`
    length_dem=int(dem_par.get_value('nlines')) #`awk '$1 == "nlines:" {print $2}' ${procdir}/geo/EQA.dem_par`
    width_dem=int(dem_par.get_value('width'))#`awk '$1 == "width:" {print $2}' ${procdir}/geo/EQA.dem_par`
    reducfac_dem = max(1, width_dem // 2000)

    lat1 = float(lat) + float(latstep) * (length_dem - 1)  # Subtract one because width starts at zero

    lon1 = float(lon) + float(lonstep) * (width_dem - 1)
    latstep = abs(float(latstep))
    lonstep = abs(float(lonstep))

    # Because no wavelength is reported in master.rmli.par file, we calculated here according to the radar frequency (IN CENTIMETERS)
    # Frequency = (C / Wavelength), Where: Frequency: Frequency of the wave in hertz (hz). C: Speed of light (29,979,245,800 cm/sec (3 x 10^10 approx))
    radar_frequency = float(dateM_mli_par.get_value('radar_frequency')[0])
    wavelength = 29979245800 / radar_frequency


    print("   Geocoding results for lookangles." )
    #psi and incidence

    if os.path.exists(psi):
        pg.geocode_back(psi, width_dem, os.path.join(slcMdir, f'{dateM}M.lt_fine'), os.path.join(geodir, f'{dateM}M.geo.psi'), width_dem, length_dem, 1, 0)
        # pg.data2geotiff(dem_par, os.path.join(geodir, f'{dateM}M.geo.psi'), 2, os.path.join(geodir, f'{dateM}M.geo.psi.tif'), 0.0)

    if os.path.exists(inc):
        pg.geocode_back(inc, width_dem, os.path.join(slcMdir, f'{dateM}M.lt_fine'), os.path.join(geodir, f'{dateM}M.geo.inc'), width_dem, length_dem, 1, 0)
        # pg.data2geotiff(dem_par, os.path.join(geodir, f'{dateM}M.geo.inc'), 2, os.path.join(geodir, f'{dateM}M.geo.inc.tif'), 0.0)

    # E-N-U
    if os.path.exists(os.path.join(geodir, 'E')):
        pg.geocode_back(os.path.join(geodir, 'E'), width, os.path.join(slcMdir, f'{dateM}M.lt_fine'), os.path.join(geodir, f'{dateM}M.geo.E'), width_dem, length_dem, 1, 0)
        pg.data2geotiff(dempar, os.path.join(geodir, f'{dateM}M.geo.E'), 2, os.path.join(geodir, f'{dateM}M.geo.E.tif'), 0.0)

    if os.path.exists(os.path.join(geodir, 'N')):
        pg.geocode_back(os.path.join(geodir, 'N'), width, os.path.join(slcMdir, f'{dateM}M.lt_fine'), os.path.join(geodir, f'{dateM}M.geo.N'), width_dem, length_dem, 1, 0)
        pg.data2geotiff(dempar, os.path.join(geodir, f'{dateM}M.geo.N'), 2, os.path.join(geodir, f'{dateM}M.geo.N.tif'), 0.0)

    if os.path.exists(os.path.join(geodir, 'U')):
        pg.geocode_back(os.path.join(geodir, 'U'), width, os.path.join(slcMdir, f'{dateM}M.lt_fine'), os.path.join(geodir, f'{dateM}M.geo.U'), width_dem, length_dem, 1, 0)
        pg.data2geotiff(dempar, os.path.join(geodir, f'{dateM}M.geo.U'), 2, os.path.join(geodir, f'{dateM}M.geo.U.tif'), 0.0)

    #hgt - not a 'look angle', but useful for LiCSBAS etc
    print('HGT file geocoding')
    if os.path.exists(os.path.join(slcMdir, f'{dateM}M.hgt')):
        print(f"Geocoding {dateM}M.hgt file")
        pg.geocode_back(os.path.join(slcMdir, f'{dateM}M.hgt'), width, os.path.join(slcMdir, f'{dateM}M.lt_fine'), os.path.join(geodir, f'{dateM}M.geo.hgt'), width_dem, length_dem, 1, 0)
        print('Finished geocoding hgt file')
        pg.data2geotiff(dempar, os.path.join(geodir, f'{dateM}M.geo.hgt'), 2, os.path.join(geodir, f'{dateM}M.geo.hgt.tif'), 0.0)
    
    # geocode back mli

    pg.geocode_back(os.path.join(slcMdir,f'{dateM}.mli'),
                        widthmli,
                        os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}M.lt_fine'),
                        os.path.join(slcMdir,f'{dateM}.geo.mli'),
                        widthdem, '-', 2, 0)
    pg.data2geotiff(dempar, os.path.join(slcMdir,f'{dateM}.geo.mli'), 2, os.path.join(slcMdir,f'{dateM}.geo.mli.tif'), 0.0)
    # use pg.SLC_ovr to over sample the rslc
    if os.path.exists(os.path.join(slcMdir, f'{dateM}.hgt')):
        pg.geocode_back(os.path.join(slcMdir, f'{dateM}.hgt'), width, os.path.join(slcMdir, f'{dateM}M.lt_fine'), os.path.join(geodir, f'{dateM}M.geo.hgt'), width_dem, length_dem, 1, 0)
        pg.data2geotiff(dempar, os.path.join(geodir, f'{dateM}M.geo.hgt'), 2, os.path.join(geodir, f'{dateM}M.geo.hgt.tif'), 0.0)

    return



def dem_to_master(config):
    
    # Sort DEM
    #----------------------------------------------------------------------------------#
    print(bcolors.OKBLUE+"Generating DEM files and lookup tables \033[0m"+bcolors.ENDC)
    dateM = config['dateM']
    topdir = config['topdir']
    slc_dir = config['slc_dir'] 
    dim_dir = config['dim_dir'] 
    og_dem_dir = config['og_dem_dir'] 
    dem = config["dem"]
    demlat = config["demlat"]
    demlon = config["demlon"]
    cleanup = config["cleanup"]

    dateM_mli_par = pg.ParFile(os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}.mli.par'))
    lengthmli= int(dateM_mli_par.get_value('azimuth_lines')) 
    widthmli=int(dateM_mli_par.get_value('range_samples'))

    os.chdir(topdir)
    # Assign variables in config to be used in future functions 
    config['lengthmli'] = lengthmli
    config['widthmli'] = widthmli

    dem_dir = os.path.join(topdir, 'dem')
    if not os.path.exists(dem_dir):
        os.mkdir(dem_dir)
    else:
        print(bcolors.WARNING + f"DEM directory already exists at {dem_dir}. Skipping DEM generation." + bcolors.ENDC)
        dem_par = pg.ParFile(os.path.join(slc_dir,f'{dateM}M','P.dem_par'))	
        widthdem=int(dem_par.get_value('width'))

        config['widthdem'] = widthdem
        return config

    os.chdir(dem_dir)

    for file in glob(os.path.join(og_dem_dir,'*',f'{dem}*')):
        if os.path.exists(os.path.join(topdir,'dem',file.split('/')[-1])):
            print(bcolors.WARNING +f'No sym link for {file}, file already exists' +bcolors.ENDC)
        else:
            print(bcolors.OKBLUE +f'sym link for {file}' +bcolors.ENDC)
            os.symlink(file,os.path.join(topdir,'dem',file.split('/')[-1]))

    print(f"Oversampling DEM {dem} by factor of {demlat} in Latitude and {demlon} in Longitude")

    # Get DEM sizes
    dem_ers_dict,[ncells,nlines,xdim,ydim,west,north] = parse_dem_ers_file(f'{topdir}/dem/{dem}.dem.ers')

    print('no. of cells: ',ncells,', nlines: ',nlines,', xdim: ', xdim, 'ydim: ',ydim, ', west: ',west,', North:', north)
    if None in [ncells, nlines, xdim, ydim, west, north]:sys.exit()
    geoid_file = os.path.expandvars("$DIFF_HOME/scripts/egm2008-5.dem")
    geoid_par = os.path.expandvars("$DIFF_HOME/scripts/egm2008-5.dem_par")
    print('find geiod file')
    print(geoid_file,geoid_par)
    # 2022 Update way to import DEM and apply geoid correction so relative to ellipsoid
    dem_import_dict = {'input_dem':os.path.abspath(f'{topdir}/dem/{dem}.tif'),
                'bin_dem':f'{topdir}/dem/{dem}.swap.dem',
                'dem_par':f'{topdir}/dem/{dem}.swap.dem_par',
                'input_type':0, # 0: GeoTIFF / GDAL supported raster format (default)
                'priority':1,
                'geoid': geoid_file,
                'geoid_par': geoid_par,
                'geoid_type':0}

    # 2022 Update way to import DEM and apply geoid correction so relative to ellipsoid
    # dem_import $topdir/dem/$dem.tif $dem.swap.dem $dem.swap.dem_par 0 1 /apps/applications/gamma/$gammaver/2/default/DIFF/scripts/egm2008-5.dem /apps/applications/gamma/$gammaver/2/default/DIFF/scripts/egm2008-5.dem_par 0

    print(bcolors.OKBLUE+'Using py_gamma: pg.dem_import'+ bcolors.ENDC)
    pg.dem_import(dem_import_dict.get('input_dem'),#(input) input DEM in original format
                dem_import_dict.get('bin_dem'),#(output) DEM in binary format (float, enter - for none)
                dem_import_dict.get('dem_par'),#DEM_par     (input/output) DEM parameter file corresponding to output DEM
                dem_import_dict.get('input_type'),
                dem_import_dict.get('priority'),
                dem_import_dict.get('geoid'),
                dem_import_dict.get('geoid_par'),
                dem_import_dict.get('geoid_type'))

     # Look-up table
    print(bcolors.OKBLUE +' pg.gc_map() '+bcolors.ENDC)
    #----------------------------------------------------------------------------------#
    pg.gc_map(os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}.mli.par'), #  MLI_par         (input) ISP MLI or SLC image parameter file (slant range geometry)
              '-', 
              os.path.join(topdir,'dem',dem_import_dict['dem_par']), 
              os.path.join(topdir,'dem',dem_import_dict['bin_dem']), 
              os.path.join(topdir,'slcs',f'{dateM}M',f'P.dem_par'), 
              os.path.join(topdir,'slcs',f'{dateM}M',f'P.dem'), 
              os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}M.lt'), 
              demlat, 
              demlon, 
              os.path.join(topdir,'slcs',f'{dateM}M/{dateM}M.sim_sar'),
              os.path.join(topdir,'slcs',f'{dateM}M','u'),
              os.path.join(topdir,'slcs',f'{dateM}M','v'),
              os.path.join(topdir,'slcs',f'{dateM}M','inc'),
              os.path.join(topdir,'slcs',f'{dateM}M','psi')
              )


    # Open parameter file    
    dem_par = pg.ParFile(os.path.join(slc_dir,f'{dateM}M','P.dem_par'))	
    widthdem=int(dem_par.get_value('width'))

    config['widthdem'] = widthdem
    pg.rasmph(os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}M.sim_sar'),widthdem , '-', '-', '-', '-')

    
    pg.create_diff_par(os.path.join(slc_dir,f'{dateM}M',f'{dateM}.mli.par'),
                       '-', 
                       os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.diff_par'),
                       1,
                       0)
    
    #Geocoding lookup table correction using offset polynomials from the DIFF parameter file
    
    pg.gc_map_fine(os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.lt'), #geocoding lookup table
                   widthdem, #width of lookup table (samples)
                   os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.diff_par'), #DIFF/GEO parameter file containing fine registration polynomial coefficients
                   os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.lt_fine'), # (output) refined geocoding lookup table
                   1) #1: simulated image reference (default)


    
    # Forward transformation with a geocoding look-up table. For each image point defined in 
    # coordinate system A, the lookup table contains the corresponding coordinates in system B. 
    # The program geocode is used to resample the data in coordinate system A into the coordinates of system B.
    print(
        f"DEM width (widthdem): {widthdem}, "
        f"MLI width (widthmli): {widthmli}, "
        f"MLI length (lengthmli): {lengthmli}"
    )
    
    pg.geocode(os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.lt_fine'),  #      lookup_table  (input) lookup table containing pairs of real-valued output data coordinates
               os.path.join(slc_dir,f'{dateM}M','P.dem'),             #   data_in   (input) data file (format as specified by format_flag parameter)
               widthdem,            #   width_in  width of input data file and gc_map lookup table
               os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.hgt'),      #   data_out  (output) output data file
               widthmli,            #   width_out width of output data file
               lengthmli,                 #lengthmli,
               2,                    
               0)                  
    
    pg.geocode(os.path.join(topdir,'slcs',f'{dateM}M/{dateM}M.lt_fine'),  #      lookup_table  (input) lookup table containing pairs of real-valued output data coordinates
               os.path.join(topdir,'slcs',f'{dateM}M/{dateM}M.sim_sar'),             #   data_in   (input) data file (format as specified by format_flag parameter)
               widthdem,            #   width_in  width of input data file and gc_map lookup table
               os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.sim_sar.sar'),      #   data_out  (output) output data file
               widthmli,            #   width_out width of output data file
               lengthmli,                 #lengthmli,
               2,                   
               0)   
    pg.geocode(os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.lt_fine'),  #      lookup_table  (input) lookup table containing pairs of real-valued output data coordinates
               os.path.join(slc_dir,f'{dateM}M','P.dem'),             #   data_in   (input) data file (format as specified by format_flag parameter)
               widthdem,            #   width_in  width of input data file and gc_map lookup table
               os.path.join(slc_dir,f'{dateM}M',f'{dateM}M.hgt_no_ovr'),      #   data_out  (output) output data file
               widthmli,            #   width_out width of output data file
               lengthmli,                 #lengthmli,
               2,                   
               0)      
    produce_geocode_hgt(dateM,os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}.mli.par'),os.path.join(topdir,'slcs',f'{dateM}M',f'P.dem_par'),os.path.join(topdir,'slcs',f'{dateM}M'),os.path.join(topdir,'slcs',f'{dateM}M',f'{dateM}.mli'))
    



    os.chdir(topdir)



    return config
def produce_geocode_hgt(
    master_date,
    mli_par_file,
    dem_par_file,
    slc_directory,
    optional_input_file=None,
    raspixavr=1,
    raspixavaz=1
):
    """
    Python version of produce_geocode_hgt.sh.
    Args:
        master_date (str): e.g. '20150708'
        mli_par_file (str): Path to MLI parameter file
        dem_par_file (str): Path to DEM parameter file
        slc_directory (str): Directory to operate in
        optional_input_file (str, optional): Optional input file
        raspixavr (int, optional): Value for rashgt (default 1)
        raspixavaz (int, optional): Value for rashgt (default 1)
    """
    # Change to SLC directory
    if not os.path.isdir(slc_directory):
        raise FileNotFoundError(f"SLC directory does not exist: {slc_directory}")
    os.chdir(slc_directory)

    dateM = f"{master_date}M"

    # Extract width from DEM parameter file
    widthdem = None
    with open(dem_par_file) as f:
        for line in f:
            if line.startswith("width:"):
                widthdem = int(line.split()[1])
            if line.startswith("width:"):    
                break

    if widthdem is None:
        raise ValueError("Could not find 'width:' in DEM parameter file.")

    # Extract range_samples from MLI parameter file
    widthmli = None
    lengthmli = None
    with open(mli_par_file) as f:
        for line in f:
            if line.startswith("range_samples:"):
                widthmli = int(line.split()[1])

            if line.startswith("azimuth_lines:"):
                lengthmli = int(line.split()[1])
            #if widthmli and lengthmli not eqaul to none then break
            if widthmli is not None and lengthmli is not None:
                break

    if widthmli is None:
        raise ValueError("Could not find 'range_samples:' in MLI parameter file.")

    print(f"DEM width: {widthdem}")
    print(f"MLI width (range samples): {widthmli}")

    # Output TIF of DEM
    # pg.rashgt(f"{dateM}.hgt", "-", widthmli, "-", "-", "-", 1, 1, "-", 1.0, 0.35, "-", f"{dateM}.hgt.tif")

    # Geocode back DEM
    pg.geocode_back(f"{dateM}.hgt", widthmli, f"{dateM}.lt_fine", f"{dateM}.hgt.geo", widthdem, "-", 0, 0)

    # Output TIF of geocoded DEM
    # pg.rashgt(f"{dateM}.hgt.geo", "-", widthdem, "-", "-", "-", raspixavr, raspixavaz, "-", 1.0, 0.35, "-", f"{dateM}.hgt.geo.tif")

    pg.data2geotiff(dem_par_file, f"{dateM}.hgt.geo", 2, f"{dateM}.hgt.geotiff.tif")

    # If optional input file is given, run rashgt again with it
    # if optional_input_file and optional_input_file != slc_directory:
    #     print(f"Running rashgt with optional input file: {optional_input_file}")
    #     pg.rashgt(f"{dateM}.hgt.geo", optional_input_file, widthdem, "-", "-", "-", 1, 1, "-", 1.0, 0.35, "-", f"{dateM}.mli.hgt.geo.tif")


def parse_dem_ers_file(filepath):

    with open(filepath, 'r') as file:
        data = {}
        current_section = data
        section_stack = []
        
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):  # skip empty lines and comments
                continue
            
            if " Begin" in line:
                section_name = line.replace(" Begin", "").strip()
                new_section = {}
                current_section[section_name] = new_section
                section_stack.append(current_section)
                current_section = new_section
            elif " End" in line:
                current_section = section_stack.pop()
            else:
                if "=" in line:
                    key, value = map(str.strip, line.split("=", 1))
                    current_section[key] = value.strip('"')

    dem_ers_dict = data['DatasetHeader']
    ncells = int(dem_ers_dict['RasterInfo']['NrOfCellsPerLine'])#run_command(f"grep NrOfCellsPerLine {topdir}/dem/{dem}.dem.ers | awk '{{print $3}}'").strip()
    nlines = int(dem_ers_dict['RasterInfo']['NrOfLines'])#run_command(f"grep NrOfLines {topdir}/dem/{dem}.dem.ers | awk '{{print $3}}'").strip()
    xdim = float(dem_ers_dict['RasterInfo']['CellInfo']['Xdimension'])#run_command(f"grep Xdimension {topdir}/dem/{dem}.dem.ers | awk '{{printf \"%.11f\\n\", $3}}'").strip()
    ydim = float(dem_ers_dict['RasterInfo']['CellInfo']['Ydimension'])#run_command(f"grep Ydimension {topdir}/dem/{dem}.dem.ers | awk '{{printf \"%.11f\\n\", -$3}}'").strip()
    west = float(dem_ers_dict['RasterInfo']['RegistrationCoord']['Eastings'])#run_command(f"grep Eastings {topdir}/dem/{dem}.dem.ers | awk '{{printf \"%.11f\\n\", $3}}'").strip()
    north = float(dem_ers_dict['RasterInfo']['RegistrationCoord']['Northings'])#run_command(f"grep Northings {topdir}/dem/{dem}.dem.ers | awk '{{print $3}}'").strip()

    output_list = [ncells,nlines,xdim,ydim,west,north]

    return data, output_list


def main():
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="A script to process TSX or TDX slcs to IF.")
    # Add arguments
    parser.add_argument('config_file', type=str, help='config file')
    args = parser.parse_args()
    # Directory organisations 
    topdir = os.getcwd()

    print(f"Processing in {topdir}")
    
    # Load the config file
    with open(args.config_file, 'r') as f:
        config = json.load(f)
        #change directory to:
    os.chdir('/home/users/ee16eme/data/fern_iceye')
    config['topdir'] = topdir
    config['slc_dir'] = os.path.join(topdir, 'slcs')
    config['rslc_dir'] = os.path.join(topdir, 'rslcs')
    config['dim_dir'] = os.path.join(topdir,'*')

    if 'dem_dir' in config:
        config['og_dem_dir'] = os.path.normpath(config['dem_dir'])
    else:
        config['og_dem_dir'] = os.path.join(topdir,'..','dem')

    dateM = config['dateM']
    ndays = config['n_days']
    min_n_days = config['min_n_days']
    date_min = config['dateS']
    date_max = config['dateE']
    cleanup = config['cleanup']
    # Call the function to validate and possibly update dateM
    #try:
    print('Writing to:',os.path.join(topdir, 'log_construct_dates.txt'))
    log_file_path = os.path.join(topdir, 'log_construct_dates.txt')
    sys.stdout = open(log_file_path, 'w')
    sys.stderr = sys.stdout
    try:

        dates1,dates2=construct_date1_date2_combinations(config,ndays,date_min,date_max)
   
        unique_dates = list(set(dates1 + dates2)) # Create a list of unique dates
        if len(unique_dates) == 0:
            print("No unique dates found. Exiting.")
            sys.exit(1)
        dateM = validate_dates(dateM, dates1, dates2)
    except Exception as e:
        print("Error in date construction:", e)
        return
    finally:
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


    print(bcolors.OKCYAN+"Dates provided are in correct format: Validation passed. Updated dateM:", dateM,bcolors.ENDC)
    print(bcolors.WARNING+f'{len(dates1)} Ifgms to be processed'+bcolors.ENDC)
    

    try:
        if not os.path.exists(os.path.join(topdir,'slcs',f'{dateM}M')):
            proc_master_slc(config) # Process master SLC
            config = dem_to_master(config) # Generate look-up tables for DEM 
        
        else:
            config = dem_to_master(config) 
            print(f"Master SLC already exists for {dateM}. Skipping master SLC processing.")
    except Exception as e:
        print("Error in master SLC processing:", e)
        return
 

    produce_lookvectors(config) # Produce look vectors



if __name__ == "__main__":
    main()

