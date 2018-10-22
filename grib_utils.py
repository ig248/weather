import os
import pygrib
import numpy as np
import pandas as pd
from collections import Counter
from datetime import datetime, timedelta


def print_grib_content_report(gribfile):
    """
    Function that describes a grib file as an exhaustive pandas dataframes.
    :param gribfile: String representing a path to grib file or a list of grib messages
    :return:
    """

    if isinstance(gribfile, str):
        grbs = open_grib(gribfile)
    else:
        if isinstance(grbfile,list):
            grbs = gribfile
        else:
            grbs = [gribfile]

            
    df = pd.DataFrame(index=grbs[0].keys())

    for i,grb in enumerate(grbs[:]):
        values = []
        for feature in grb.keys():

            try:
                value = grb[feature]
            except:
                value = None

            if isinstance(value,list) or isinstance(value,np.ndarray):
                #skip np arrays and lists to maintain clarity
                value = None
            values.append(value)

        df[i]=values

    df_same = df[df.apply(pd.Series.nunique, axis=1) == 1]
    df_same = df_same.sort_index()
    df_unique = df[df.apply(pd.Series.nunique, axis=1) > 1].transpose()

    print("GRIB FILE DESCRIPTION:")
    print("***********************************************************")
    print("")
    if isinstance(gribfile,str):
        print("Grib name: {}".format(os.path.abspath(gribfile)))


    if "dataDate" in df.index.tolist() and "dataTime" in df.index.tolist():
        print("Grib date: {} {}".format(grbs[0]["dataDate"],grbs[0]["dataTime"]))

    if "Nx" in df.index.tolist() and "Nx" in df.index.tolist():
        print("Layer size (X x Y): {}x{}".format(grbs[0]["Nx"],grbs[0]["Ny"]))


    print("Number of layers: {}".format(len(grbs)))

    if "name" in df.index.tolist():
        print("Available datasets:")
        for key,value in Counter(df.ix["name",:].values.tolist()).items():
            print("\t{} ({})".format(key,value))
    print("")
    print("")
    print("GENERAL GRIB DATA OVERVIEW:")
    print("")
    print_full_df(df_same.iloc[:, [0]])

    print("")
    print("")
    print("LAYER-SPECIFIC DATA OVERVIEW:")
    print("")
    print_full_df(df_unique)
    print("")
    print("***********************************************************")
    print("")
    print("")

def open_grib(grbs,timestep_interval_mins=60):
    """
    Wrapper function around basic pygrib.open() functionality, patching a GRIB API bug at the time of writing
    this script (early 2017ish), where it seems to lack the decoding ability for stepUnits below 1 hour. At the same time,
    open_grib converts grib object into the list of grib messages on the fly.
    This functions well with a custom filtering (= selecting) function, filter_grib_messages() --> see below
    :param grbs: String pointing to the location of a grib.
    :param timestep_interval_mins: Manual correction attribute for bypassing grib api stepUnits error. Defaults to 60 mins (1H)
    :return:
    """

    if not isinstance(grbs,str):
        raise IOError("Grbs argument has to be a path to the grib file!")

    grbs = pygrib.open(grbs)
    grbs = grbs.select()

    for grb in grbs:
        if timestep_interval_mins < 60:
            grb["stepUnits"]=0

    # If grib file consists of one grib message only, it returns this one, instead of one-element list.
    if isinstance(grbs,list) and len(grbs) == 1:
        grbs = grbs[0]

    return grbs

def filter_grib_layers(grbs,**grib_layer_filters):

    """
    Replacement of pygrib.select() function that filters a list of grib messages, not a grib object itself. This allows
    for multiple consecutive calls of that function since input and output of this function is both a list (except when
    there is only one grib layer left after filtering.
    :param grbs: List of grib messages
    :param grib_layer_filters: pygrib.select()-style kwargs for selecting data e.g. validityDate = 20170104, shortName="tp" ,...
    :return: List of grib messages that satisfy the criteria
    """

    # Returns grib_objects that meet given selection criteria.
    def passes_filters(grb):
        """
        Helper function for filtering a single grib message. True if passes the filter,
        False if it doesnt satisfy anyone of the given.
        :param grb:
        :return:
        """
        for filter in grib_layer_filters:

            if isinstance(grib_layer_filters[filter], list):
                if grb[filter] not in grib_layer_filters[filter]:
                    return False
            else:
                if grb[filter] != grib_layer_filters[filter]:
                    return False

        return True

    #Filter gribs
    ok = [i for i in grbs if passes_filters(i)]

    print("After filterings still {} grib messages left.".format(len(ok)))

    if isinstance(ok,list) and len(ok) == 1:
        ok = ok[0]

    return ok

def get_grib_layer_simulation_datetime(grb):
    # Helper function to quickly get a simulation time of grib message

    dataTime = str(grb["dataTime"]).zfill(4)
    dataDate = str(grb["dataDate"])
    return datetime.strptime(dataDate + dataTime, "%Y%m%d%H%M")

def get_grib_layer_validity_datetime(grb):
    # Helper function to quickly get a validity time of grib message (=simulation_run_date + forecastingTime)

    return get_grib_layer_simulation_datetime(grb) + timedelta(minutes=int(grb["endStep"]))

def grib_message_to_arrays_raster(grb,nodata_buffer=0.001,nodata=0):
    """
    Function for extraction of values, lats and lons from a single grib message
    :param grb: Grib message. Must be one layer only!
    :param nodata_buffer: Values below this treshold will be rounded to nodata.
            Usefull for erasing numerical rounding errors. Defaults to 0.001
    :param nodata: No data value. Defaults to 0
    :return:
    """
    #Converts single grib layer gribfile into ndarrays of values, lats and lons

    if isinstance(grb,list):
        if len(grb) == 1:
            grb = grb[0]
        else:
            raise IOError("You can only pass a one-layered grib list or a grib message. "
                          "You passed a grib with {} layers.".format(len(grb)))

    values = grb.values #read data into np array
    if nodata_buffer:
        values[values<nodata_buffer]=nodata

    lats, lons = grb.latlons() #read coordinates

    return values,lats,lons

def print_full_df(x):
    # Helper function to allow for full display of pandas dataframe

    pd.set_option('display.max_rows', len(x.index))
    pd.set_option('display.max_columns', len(x.columns))
    print(x)
    pd.reset_option('display.max_rows')
    pd.reset_option('display.max_columns')
