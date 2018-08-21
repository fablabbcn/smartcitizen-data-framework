import matplotlib
import matplotlib.pyplot as plt                  # plots
import seaborn as sns                            # more plots
sns.set(color_codes=True)
matplotlib.style.use('seaborn-whitegrid')

import plotly as ply                             # even more plots
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
from plotly.graph_objs import Scatter, Layout
import plotly.tools as tls

import pandas as pd
import numpy as np

import datetime
from scipy.stats.stats import linregress   
import warnings                                  # `do not disturbe` mode
warnings.filterwarnings('ignore')
from dateutil import relativedelta
from scipy.optimize import curve_fit

from calData_utils import getCalData
from test_utils import *

alpha_calData = getCalData('alphasense')
mics_calData = getCalData('mics')

# AlphaDelta PCB factor
factorPCB = 6.36

# Background Concentration (model assumption) - (from Modelling atmospheric composition in urban street canyons - Vivien Bright, William Bloss and Xiaoming Cai)
backgroundConc_CO = 0.2 # ppm
backgroundConc_NO2 = 8 # ppb
backgroundConc_OX = 40 # ppb

# Overlap in hours for each day (index = [day(i)-overlapHours, day(i+1)+overlapHours])
overlapHours = 2 

# Filter Smoothing 
filterExpSmoothing = 0.2

# Range of deltas
deltas = np.arange(1,20,1)
deltasMICS = np.arange(1,200,1)

# Units Look Up Table - ['Pollutant', unit factor from ppm to target 1, unit factor from ppm to target 2]
alphaUnitsFactorsLUT = (['CO', 1, 0],
                        ['NO2', 1000, 0],
                        ['O3', 1000, 1000])

micsUnitsFactorsLUT = (['CO', 1],
                        ['NO2', 1000])

def ExtractBaseline(_data, _delta):
    '''
        Input:
            _data: dataframe containing signal to be baselined and index
            _delta : float for delta time (N periods)
        Output:
            result: vector containing baselined values
    ''' 
    
    result = np.zeros(len(_data))
    name = []
    for n in range(0, len(_data)):
        minIndex = max(n-_delta,0)
        maxIndex = min(n+_delta, len(_data))
        
        chunk = _data.values[minIndex:maxIndex]
        result[n] = min(chunk)

    return result

def findMax(_listF):
    '''
        Input: list to obtain maximum value
        Output: value and index of maximum in the list
    '''
    
    valMax=max(_listF)
    indexMax = _listF.index(max(_listF))
    # print 'Max Value found at index: {}, with value: {}'.format(indexMax, valMax)
    
    return valMax, indexMax

def exponential_smoothing(series, alpha):
    '''
        Input:
            series - dataset with timestamps
            alpha - float [0.0, 1.0], smoothing parameter
        Output: 
            smoothed series
    '''
    result = [series[0]] # first value is same as series
    for n in range(1, len(series)):
        result.append(alpha * series[n] + (1 - alpha) * result[n-1])
    return result

def exponential_func(x, a, b, c):
     return a * np.exp(b * x) + c

def createBaselines(_dataBaseline, _dataCorr, _numberDeltas, _type_regress = 'linear', _plots = False, _verbose = False):
    '''
        Input:
            _dataBaseline: dataframe containing signal and index to be baselined
            _dataCorr: baseline data for regression
            _type_regress= 'linear', 'exponential', 'best' (based on p_value of both)
            _numberDeltas : vector of floats for deltas (N periods)
            _plots:  display plots or not
            _verbose: print info or not
            _type_regress: regression type (linear, exp, ... )
        Output:
            baseline: pandas dataframe baseline
        TODO:
            implement other types of regression
    '''
    
    resultData = _dataBaseline.copy()
    vectorCorr = _dataCorr.values

    name = resultData.name
    pearsons =[]
    
    for delta in _numberDeltas:
        resultData[(name +'_' +str(delta))] = ExtractBaseline(_dataBaseline, delta)
        slope, intercept, r_value, p_value, std_err = linregress(np.transpose(resultData[(name +'_' +str(delta))]), np.transpose(vectorCorr))
        pearsons.append(r_value)
    
    ## Find Max in the pearsons
    valMax, indexMax = findMax(pearsons)
        
    ## Find regression between _dataCorr
    baseline = pd.DataFrame(index = _dataBaseline.index)
    if _type_regress == 'linear':
        ## Fit with y = A + Bx
        slope, intercept, r_value, p_value, std_err = linregress(np.transpose(vectorCorr),resultData[(name + '_'+str(_numberDeltas[indexMax]))])
        baseline[(name + '_' + 'baseline_' +  _type_regress)] = intercept + slope*vectorCorr
    elif _type_regress == 'exponential':
        ## Fit with y = Ae^(Bx) -> logy = logA + Bx
        logy = np.log(resultData[(name + '_'+str(_numberDeltas[indexMax]))])
        slope, intercept, r_value, p_value, std_err = linregress(np.transpose(vectorCorr), logy)
        baseline[(name + '_' + 'baseline_' +  _type_regress)] = exponential_func(np.transpose(vectorCorr), np.exp(intercept), slope, 0)
    elif _type_regress == 'best':
        ## Find linear r_value
        slope_lin, intercept_lin, r_value_lin, p_value_lin, std_err_lin = linregress(np.transpose(vectorCorr),resultData[(name + '_'+str(_numberDeltas[indexMax]))])
        
        ## Find Exponential r_value
        logy = np.log(resultData[(name + '_'+str(_numberDeltas[indexMax]))])
        slope_exp, intercept_exp, r_value_exp, p_value_exp, std_err_exp = linregress(np.transpose(vectorCorr), logy)
        
        ## Pick which one is best
        if r_value_lin > r_value_exp:
            if _verbose:
                print 'Using linear regression'
            baseline[(name + '_' + 'baseline_' +  _type_regress)] = intercept_lin + slope_lin*vectorCorr
        else:
            if _verbose:
                print 'Using exponential regression'
            baseline[(name + '_' + 'baseline_' +  _type_regress)] = exponential_func(np.transpose(vectorCorr), np.exp(intercept_exp), slope_exp, 0)
            
    if _plots == True:
        with plt.style.context('seaborn-white'):
            fig1, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(20,8))
            
            ax1.plot(_dataCorr.values, resultData[(name + '_'+str(_numberDeltas[indexMax]))], label = 'Baseline', linestyle='-', linewidth=0, marker='o')
            ax1.plot(_dataCorr.values, baseline[(name + '_' + 'baseline_' +  _type_regress)] , label = 'Regressed value', linestyle='-', linewidth=1, marker=None)
            legend = ax1.legend(loc='best')
            ax1.set_xlabel(_dataCorr.name)
            ax1.set_ylabel('Regression values')
            ax1.grid(True)
            
            ax2.plot(_dataBaseline.index, _dataBaseline.values, label = "Actual", linestyle=':', linewidth=1, marker=None)
            #[ax2.plot(resultData.index, resultData[(name +'_' +str(delta))].values, label="Delta {}".format(delta), marker=None,  linestyle='-', linewidth=1) for delta in _numberDeltas]
            ax2.plot(baseline.index, baseline.values, label='Baseline', marker = None)

            ax2.axis('tight')
            ax2.legend(loc='best')
            ax2.set_title("Baseline Extraction")
            ax2.grid(True)
            
            ax22 = ax2.twinx()
            ax22.plot(_dataCorr.index, _dataCorr.values, color = 'red', label = _dataCorr.name, linestyle='-', linewidth=1, marker=None)
            ax22.set_ylabel(_dataCorr.name, color = 'red')
            ax22.tick_params(axis='y', labelcolor='red')
            
            fig2, ax3 = plt.subplots(figsize=(20,8)) # two axes on figure
            ax3.plot(_numberDeltas, pearsons)
            ax3.axis('tight')
            ax3.set_title("R2 vs. Delta")
            ax3.set_xlabel('Delta')
            ax3.set_ylabel('R2')
            ax3.grid(True)

    return baseline, indexMax

def decompose(_data, plots = False):
    '''
            Function to decompose a signal into it's trend and normal variation
            Input:
                _data: signal to decompose
                plots: print plots or not (default False)
            Output:
                DataDecomp = _data - slope*_data.index
                slope, intercept = linear regression coefficients
    '''
    indexDecomp = np.arange(len(_data))

    slope, intercept, r_value, p_value, std_err = linregress(indexDecomp, np.transpose(_data.values))
    dataDecomp=pd.DataFrame(index = _data.index)
    name = _data.name
    result = []
    
    for n in range(len(_data)):
        result.append(float(_data.values[n]-slope*n))
    dataDecomp[(name + '_' + '_flat')] = result
    
    trend = slope*indexDecomp + intercept
    if plots == True:
        
        with plt.style.context('seaborn-white'):
            fig, ax = plt.subplots(figsize=(20,10))
            ax.plot(_data.index, _data.values, label = "Actual", marker = None)
            ax.plot(_data.index, dataDecomp[(name + '_' +'_flat')], marker = None, label = 'Flattened')
            ax.plot(_data.index, trend, label = 'Trend')
            ax.legend(loc="best")
            ax.axis('tight')
            ax.set_title("Signal Decomposition - "+ name)
            ax.set_xlabel('Index')
            ax.set_ylabel('Signal')
            ax.grid(True)
            
    return dataDecomp, slope, intercept

def calculateBaselineDay(_dataFrame, _typeSensor, _listNames, _baselined, _baseliner, _deltas, _type_regress, _trydecomp = False, _plots = False, _verbose = True):
    '''
        Function to calculate day-based baseline corrections
        Input:
            _dataFrame: pandas dataframe with datetime index containing 1 day of measurements + overlap
            _listNames: list containing column names of /WE / AE / TEMP / HUM) or (MICS / TEMP / HUM)
            _baselined: channel to calculate the baseline of
            _baseliner: channel to use as input for the baselined (baselined = f(baseliner)) 
            _type_regress: type of regression to perform (linear, exponential, best)
            // NOT USED - _trydecomp: try trend decomposition (not needed . remove it)
            _plot: plot analytics or not
            _verbose: print analytics or not
        Output:
            _data_baseline: dataframe with baseline
            _baseline_corr: metadata containing analytics for long term analysis
    '''

    # def decomposeData(_dataframe, _listNames):
    #     dataDecomp = pd.DataFrame(index = _dataframe.index)
    #     slopeList = list()
    #     interceptList = list()
    #     # Decompose Trend - Check if decomposition helps at all
    #     for name in _listNames:
    #         dataDecomp[name], slope, intercept = decompose(_dataframe[name], _plots)
    #         slopeList.append(slope)
    #         interceptList.append(intercept)

    #     return dataDecomp, slopeList, interceptList
    
    ## Create Baselines
    data_baseline, indexMax = createBaselines(_dataFrame[_baselined], _dataFrame[_baseliner], _deltas, _type_regress, _plots, _verbose)

    ## Verify anticorrelation between temperature and humidity
    if _plots == True:
        with plt.style.context('seaborn-white'):
            fig2, (ax3, ax4) = plt.subplots(nrows = 2, ncols = 1,figsize=(20,10))
            ax3.scatter(_dataFrame[hum], _dataFrame[temp], marker = 'o', linewidth = 0)
            ax3.set_xlabel(_dataFrame[hum].name)
            ax3.set_ylabel(_dataFrame[temp].name)
            ax3.grid(True)
            
            colorH = 'red'
            colorT = 'blue'
            ax4.plot(_dataFrame.index, _dataFrame[hum], c = colorH, label = _dataFrame[hum].name, marker = None)
            ax5 = ax4.twinx()
            ax5.plot(_dataFrame.index, _dataFrame[temp], c = colorT, label = _dataFrame[temp].name, marker = None)
            ax4.tick_params(axis='y', labelcolor=colorH)
            ax5.tick_params(axis='y', labelcolor=colorT)
            ax4.set_xlabel('Time')
            ax4.set_ylabel(_dataFrame[temp].name, color = colorH)
            ax5.set_ylabel(_dataFrame[hum].name, color = colorT)
            ax4.grid(True)

    if _typeSensor == 'alphasense': 

        ## Un-pack list names
        alphaW, alphaA, temp, hum = _listNames

        ## Correlation between Baseline and original auxiliary
        slopeBA, interceptBA, r_valueBA, p_valueBA, std_errBA = linregress(np.transpose(data_baseline.values), np.transpose(_dataFrame[alphaA].values))

        # Add metadata for further research
        deltaAuxBas = data_baseline.values-_dataFrame[alphaA].values
        ratioAuxBas = data_baseline.values/_dataFrame[alphaA].values
       
        deltaAuxBas_avg = np.mean(deltaAuxBas)
        ratioAuxBas_avg = np.mean(ratioAuxBas)
       
        # Pre filter based on the metadata itself
        if slopeBA > 0 and r_valueBA > 0.3:
            valid = True
        else:
            valid = False
       
        baselineCorr = (slopeBA, interceptBA, r_valueBA, p_valueBA, std_errBA, deltaAuxBas_avg, ratioAuxBas_avg, indexMax, valid)
    
        if _verbose == True:
            
            print '-------------------'
            print 'Auxiliary Electrode'
            print '-------------------'
            print 'Correlation coefficient of Baseline and Original auxiliary: {}'.format(r_valueBA)
            print 'Baseline Correlation Slope: {} \t Intercept: {}'.format(slopeBA, interceptBA)
            
            print 'Average Delta: {} \t Average Ratio: {}'.format(deltaAuxBas_avg, ratioAuxBas_avg)

        if _plots == True:
            with plt.style.context('seaborn-white'):
                
                fig2, ax3 = plt.subplots(figsize=(20,8))

                # if _trydecomp == False:
                #     fig2, ax3 = plt.subplots(figsize=(20,8))
                # else: 
                #     fig2, (ax3, ax4) = plt.subplots(nrows = 1, ncols = 2, figsize=(20,8))
                #     ax4.plot(data_baselineDecomp.index, data_baselineDecomp.values, label='Baseline', marker = None)
                #     ax4.plot(dataDecomp.index, dataDecomp[alphaW], label = 'Working Decomp', marker = None)
                #     ax4.plot(dataDecomp.index, dataDecomp[alphaA], label = 'Auxiliary Decomp', marker = None)
                #     ax4.legend(loc="best")
                #     ax4.axis('tight')
                #     ax4.set_title("Baseline Compensated")
                #     ax4.set(xlabel='Time', ylabel='Ouput-mV')
                #     ax4.grid(True)
                #     ax4.set_ylim(min(min(dataDecomp[temp]),min(data_baselineDecomp.values)) -5,max(max(dataDecomp[temp]),max(data_baselineDecomp.values))+5)
                    
                #     ax6 = ax4.twinx()
                #     ax6.plot(dataDecomp.index, dataDecomp[temp], label='Temperature Decomp', c = 'red', marker = None)
                #     ax6.tick_params(axis='y', labelcolor ='red')
                #     ax6.set_ylabel('Temperature (degC)', color = 'red')
                #     ax6.set_ylim(min(min(dataDecomp[temp]),min(data_baselineDecomp.values)) -5,max(max(dataDecomp[temp]),max(data_baselineDecomp.values))+5)
                
                ax3.plot(data_baseline.index, data_baseline.values, label='Baseline', marker = None)
                ax3.plot(_dataFrame.index, _dataFrame[alphaW], label='Original Working', marker = None)
                ax3.plot(_dataFrame.index, _dataFrame[alphaA], label='Original Auxiliary', marker = None)

                ax3.legend(loc="best")
                ax3.axis('tight')
                ax3.set_title("Baseline Not Compensated")
                ax3.set(xlabel='Time', ylabel='Ouput-mV')
                ax3.grid(True)
                ax3.set_ylim(min(min(_dataFrame[temp]),min(data_baseline.values)) -5,max(max(_dataFrame[temp]),max(data_baseline.values))+5)
                
                # if _trydecomp == True:
                #     ax5 = ax3.twinx()
                #     ax5.plot(dataDecomp.index, dataDecomp[temp], label='Temperature Decomp', c = 'red', marker = None)
                #     ax5.tick_params(axis='y', labelcolor ='red')
                #     ax5.set_ylabel(dataDecomp[temp].name, color = 'red')
                #     ax5.set_ylim(min(min(dataDecomp[temp]),min(data_baselineDecomp.values)) -5,max(max(dataDecomp[temp]),max(data_baselineDecomp.values))+5)
                    
                fig3, ax7 = plt.subplots(figsize=(20,8))
                
                ax7.plot(_dataFrame[temp], _dataFrame[alphaW], label='W - Raw', marker='o',  linestyle=None, linewidth = 0)
                ax7.plot(_dataFrame[temp], _dataFrame[alphaA], label ='A - Raw', marker='v', linewidth=0)
                
                # if _trydecomp == True:
                #     ax7.plot(dataDecomp[temp], dataDecomp[alphaA], label ='A - Trend Decomposed', marker='v', linewidth=0)
                #     ax7.plot(dataDecomp[temp], dataDecomp[alphaW], label = 'W - Trend Decomposed',marker='o', linestyle=None, linewidth = 0)
                
                ax7.legend(loc="best")
                ax7.axis('tight')
                ax7.set_title("Output vs. Temperature")
                ax7.set(xlabel='Temperature', ylabel='Ouput-mV')
                ax7.grid(True)

    elif _typeSensor == 'mics':
        ## Un-pack list names
        mics_resist, temp, hum = _listNames

        baselineCorr = list()
        baselineCorr.append(indexMax)


    return data_baseline, baselineCorr

def findDates(_dataframe):
    '''
        Find minimum, maximum dates in the dataframe and the amount of days in between
        Input: 
            _dataframe: pandas dataframe with datetime index
        Output: 
            rounded up min day, floor max day and number of days between the min and max dates
    '''
    range_days = (_dataframe.index.max()-_dataframe.index.min()).days
    min_date_df = _dataframe.index.min().ceil('D')
    max_date_df = _dataframe.index.max().floor('D')
    
    return min_date_df, max_date_df, range_days

from formula_utils import maxer, miner

def calculatePollutantsAlpha(_dataframe, _pollutantTuples, _append, _refAvail, _dataframeRef, _deltas, _overlapHours = 0, _type_regress = 'best', _filterExpSmoothing = 0.2, _trydecomp = False, _plotsInter = False, _plotResult = True, _verbose = False, _printStats = False):
    '''
        Function to calculate alphasense pollutants with baseline technique
        Input:
            _dataframe: pandas dataframe from
            _pollutantTuples: list of tuples containing: 
                '[(_pollutant, 
                _sensorID, 
                calibration_method: 
                    'classic'
                    'baseline', 
                baseline_type: 'baseline using auxiliary, temperature or humidity'
                    ''
                    'single_aux'
                    'single_temp'
                    'single_hum'
                sensor_slot), 
                ...]'
            _append: suffix to the new channel name (pollutant + append)
            _refAvail: True or False if there is a reference available
            _dataframeRef: reference dataframe if available
            _deltas: for baseline correction method
            _overlapHours: number of hours to overlap over the day -> -_overlapHours+day:day+1+_overlapHours
            _type_regress = type of regression for baseline (best, exponential or linear)
            _filterExpSmoothing = alpha parameter for exponential filter smoothing
            _trydecomp = try to decompose with temperature trend or not
            _plotsInter = warning - many plots (True, False) plot intermediate analysis, 
            _plotResult = (True, False) plot final result, 
            _verbose = warning - many things (True, False), 
            _printStats = (True, False) print final statistics) 

        Output:
            _dataframe with pollutants added
            _metadata with statistics analysis
    '''
    
    dataframeResult = _dataframe.copy()
    numberSensors = len(_pollutantTuples)
    CorrParamsDict = dict()
    
    for sensor in range(numberSensors):
        
        # Get Sensor 
        pollutant = _pollutantTuples[sensor][0]
        sensorID = _pollutantTuples[sensor][1]
        method = _pollutantTuples[sensor][2]
        if method == 'baseline':
            baselineType = _pollutantTuples[sensor][3]
        slot = _pollutantTuples[sensor][4]
        
        # Get Sensor data
        Sensitivity_1 = alpha_calData.loc[sensorID,'Sensitivity 1']
        Sensitivity_2 = alpha_calData.loc[sensorID,'Sensitivity 2']
        Target_1 = alpha_calData.loc[sensorID,'Target 1']
        Target_2 = alpha_calData.loc[sensorID,'Target 2']
        nWA = alpha_calData.loc[sensorID,'Zero Current']/alpha_calData.loc[sensorID,'Aux Zero Current']

        if not Target_1 == pollutant:
            print 'Sensor ID ({}) and pollutant type ({}) not matching'.format(Target_1, pollutant)
            return

        alphaW = CHANNEL_NAME(currentSensorNames, 'GASES', slot, 'W', 'BOARD_AUX', '')
        alphaA = CHANNEL_NAME(currentSensorNames, 'GASES', slot, 'A', 'BOARD_AUX', '')
        temp = CHANNEL_NAME(currentSensorNames, 'TEMPERATURE', 0, '?ONE', 'BOARD_AUX', 'C')
        hum = CHANNEL_NAME(currentSensorNames, 'HUMIDITY', 0, '?ONE', 'BOARD_AUX', '%')
        
        _listNames = (alphaW, alphaA, temp, hum)

        if pollutant == 'O3':
            # Check if NO2 is already present in the dataset
            if ('NO2'+ '_' + _append) in dataframeResult.columns:
                pollutant_column_2 = ('NO2' + '_' + _append)
            else:
                print 'Change tuple order to [(CO,sensorID_CO, ...), (NO2, sensorID_NO2, ...), (O3, sensorID_O3, ...)]'
                return
        
        # Get units for the pollutant in questions
        for pollutantItem in alphaUnitsFactorsLUT:
            
            if pollutant == pollutantItem[0]:
                factor_unit_1 = pollutantItem[1]
                factor_unit_2 = pollutantItem[2]

        ## Find min, max and range of days
        min_date_df, max_date_df, range_days = findDates(_dataframe)
        print '------------------------------------------------------------------'
        print ('Calculation of ' + '\033[1m{:10s}\033[0m'.format(pollutant))
        print 'Data Range from {} to {} with {} days'.format(min_date_df, max_date_df, range_days)
        print '------------------------------------------------------------------'
        
        # Give name to pollutant column
        pollutant_column = (pollutant + '_' + _append) 
        
        if method == 'baseline':
            # Select baselined - baseliner depending on the baseline type
            if baselineType == 'single_temp':
                baseliner = temp
            elif baselineType == 'single_hum':
                baseliner = hum
            elif baselineType == 'single_aux':
                baseliner = alphaA
            baselined = alphaW
            
            # Iterate over days
            for day in range(range_days):
            
                # Calculate overlap dates for that day
                min_date_ovl = max(_dataframe.index.min(), (min_date_df + pd.DateOffset(days=day) - pd.DateOffset(hours = _overlapHours)))
                max_date_ovl = min(_dataframe.index.max(), (min_date_ovl + pd.DateOffset(days=1) + pd.DateOffset(hours = _overlapHours + relativedelta.relativedelta(min_date_df + pd.DateOffset(days=day),min_date_ovl).hours)))
                
                # Calculate non overlap dates for that day
                min_date_novl = max(min_date_df, (min_date_df + pd.DateOffset(days=day)))
                max_date_novl = min(max_date_df, (min_date_novl + pd.DateOffset(days=1)))
            
                if _verbose:
                    print '------------------------------------------------------------------'
                    print 'Calculating day {}, with range: {} \t to {}'.format(day, min_date_ovl, max_date_ovl)
                    print '------------------------------------------------------------------'
                
                ## Trim dataframe to overlap dates
                dataframeTrim = dataframeResult[dataframeResult.index > min_date_ovl]
                dataframeTrim = dataframeTrim[dataframeTrim.index <= max_date_ovl]
                
                # Init stuff
                if day == 0:
                    # Init list for CorrParams
                    CorrParams = list()
                 
                if dataframeTrim.empty:
                    if _verbose:
                        print 'No data between these dates'
                    
                    # Fill with nan if no data available (to avoid messing up the stats)
                    nanV =np.ones(10)
                    nanV.fill(np.nan)

                    CorrParams.append(tuple(nanV))
                    
                else:
                    
                    # CALCULATE THE BASELINE PER DAY
                    dataframeTrim[alphaW + '_baseline'], CorrParamsTrim = calculateBaselineDay(dataframeTrim, 'alphasense', _listNames, baselined, baseliner, _deltas, _type_regress, _trydecomp, _plotsInter, _verbose)
                    
                    # TRIM IT BACK TO NO-OVERLAP
                    dataframeTrim = dataframeTrim[dataframeTrim.index > min_date_novl].fillna(0)
                    dataframeTrim = dataframeTrim[dataframeTrim.index <= max_date_novl].fillna(0)
                    
                    # CALCULATE ACTUAL POLLUTANT CONCENTRATION
                    if pollutant == 'CO': 
                        # Not recommended for CO
                        dataframeTrim[pollutant_column] = backgroundConc_CO + factor_unit_1*factorPCB*(dataframeTrim[alphaW] - dataframeTrim[alphaW + '_baseline'])/abs(Sensitivity_1)
                    elif pollutant == 'NO2':
                        dataframeTrim[pollutant_column] = backgroundConc_NO2 + factor_unit_1*factorPCB*(dataframeTrim[alphaW] - dataframeTrim[alphaW + '_baseline'])/abs(Sensitivity_1)
                    elif pollutant == 'O3':
                        dataframeTrim[pollutant_column] = backgroundConc_OX + factor_unit_1*(factorPCB*(dataframeTrim[alphaW] - dataframeTrim[alphaW + '_baseline']) - (dataframeTrim[pollutant_column_2])/factor_unit_2*abs(Sensitivity_2))/abs(Sensitivity_1)
                    
                    # ADD IT TO THE DATAFRAME
                    dataframeResult = dataframeResult.combine_first(dataframeTrim)
                    
                    if _refAvail:
                        ## Trim ref dataframe to no-overlap dates
                        dataframeTrimRef = _dataframeRef[_dataframeRef.index >= dataframeTrim.index.min()].fillna(0)
                        dataframeTrimRef = dataframeTrimRef[dataframeTrimRef.index <= dataframeTrim.index.max()].fillna(0)
                        
                        # Adapt dataframeTrim to be able to perform correlation
                        if dataframeTrimRef.index.min() > dataframeTrim.index.min():
                            dataframeTrim = dataframeTrim[dataframeTrim.index >= dataframeTrimRef.index.min()]
                        if dataframeTrimRef.index.max() < dataframeTrim.index.max():
                            dataframeTrim = dataframeTrim[dataframeTrim.index <= dataframeTrimRef.index.max()]
                        pollutant_ref = (pollutant + '_' + ref_append)
                        if pollutant_ref in dataframeTrimRef.columns and not dataframeTrimRef.empty:
                            slopeRef, interceptRef, r_valueRef, p_valueRef, std_errRef = linregress(np.transpose(dataframeTrim[pollutant_column]), np.transpose(dataframeTrimRef[pollutant_ref]))
                        else:
                            r_valueRef = np.nan
                    else:
                        r_valueRef = np.nan
                        print 'No Ref available'
                    
                    ## Get some metrics
                    temp_avg = dataframeTrim[temp].mean(skipna = True)
                    temp_stderr = dataframeTrim[temp].std(skipna = True)
                    hum_avg = dataframeTrim[hum].mean(skipna = True)
                    hum_stderr = dataframeTrim[hum].std(skipna = True)
                    pollutant_avg = dataframeTrim[pollutant_column].mean(skipna = True)
                    
                    tempCorrParams = list(CorrParamsTrim)
                    tempCorrParams.insert(0,r_valueRef**2)
                    tempCorrParams.insert(1,pollutant_avg)
                    tempCorrParams.insert(1,hum_stderr)
                    tempCorrParams.insert(1,hum_avg)
                    tempCorrParams.insert(1,temp_stderr)
                    tempCorrParams.insert(1,temp_avg)                    
                    CorrParamsTrim = tuple(tempCorrParams)
                    CorrParams.append(CorrParamsTrim)
            
            ## Add relevant metadata for this method
            labelsCP = ['r_valueRef',
                        'avg_temp',
                        'stderr_temp',
                        'avg_hum',
                        'stderr_hum',
                        'avg_pollutant',
                        'slopeBA', 
                        'interceptBA', 
                        'r_valueBA', 
                        'p_valueBA', 
                        'std_errBA', 
                        'deltaAuxBas_avg', 
                        'ratioAuxBas_avg', 
                        'indexMax', 
                        'valid']
            
            CorrParamsDF = pd.DataFrame(CorrParams, columns = labelsCP, index = [(min_date_df+ pd.DateOffset(days=days)).strftime('%Y-%m-%d') for days in range(range_days)])
            
            ## Find average ratio for hole dataset
            deltaAuxBas_avg = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'deltaAuxBas_avg'].mean(skipna = True)
            deltaAuxBas_std = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'deltaAuxBas_avg'].std(skipna = True)
            ratioAuxBas_avg = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'ratioAuxBas_avg'].mean(skipna = True)
            ratioAuxBas_std = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'ratioAuxBas_avg'].std(skipna = True)
                    
            # SHOW SOME METADATA FOR THE BASELINES FOUND
            if _printStats:
                        
                print '------------------------'
                print ' Meta Data'
                print '------------------------'
                display(CorrParamsDF)
                        
                print '------------------------'
                print 'Average Delta between baseline and auxiliary electrode: {}, and ratio {}:'.format(deltaAuxBas_avg, ratioAuxBas_avg)
                print 'Std Dev of Delta between baseline and auxiliary electrode: {}, and ratio {}:'.format(deltaAuxBas_std, ratioAuxBas_std)
                print '------------------------'
                    
        elif method == 'classic':
            
            ## CorrParams
            CorrParamsTrim = list()
            
            if pollutant == 'CO': 
                dataframeResult[pollutant_column] = factor_unit_1*factorPCB*(dataframeResult[alphaW] - nWA*dataframeResult[alphaA])/abs(Sensitivity_1)+backgroundConc_CO
            elif pollutant == 'NO2':
                dataframeResult[pollutant_column] = factor_unit_1*factorPCB*(dataframeResult[alphaW] - nWA*dataframeResult[alphaA])/abs(Sensitivity_1)+backgroundConc_NO2
            elif pollutant == 'O3':
                dataframeResult[pollutant_column] = factor_unit_1*(factorPCB*(dataframeResult[alphaW] - nWA*dataframeResult[alphaA]) - (dataframeResult[pollutant_column_2])/factor_unit_2*abs(Sensitivity_2))/abs(Sensitivity_1) + backgroundConc_OX
            
            ## Calculate stats day by day to avoid stationarity
            min_date_df, max_date_df, range_days = findDates(dataframeResult)
            print 'Data Range from {} to {} with {} days'.format(min_date_df, max_date_df, range_days)
            
            for day in range(range_days):
                ## CorrParams
                CorrParamsTrim = list()
                
                # Calculate non overlap dates for that day
                min_date_novl = max(min_date_df, (min_date_df + pd.DateOffset(days=day)))
                max_date_novl = min(max_date_df, (min_date_novl + pd.DateOffset(days=1)))
                
                ## Trim dataframe to no-overlap dates
                dataframeTrim = dataframeResult[dataframeResult.index > min_date_novl].fillna(0)
                dataframeTrim = dataframeTrim[dataframeTrim.index <= max_date_novl].fillna(0)
                
                if _refAvail:
                    ## Trim ref dataframe to no-overlap dates
                    dataframeTrimRef = _dataframeRef[_dataframeRef.index >= dataframeTrim.index.min()].fillna(0)
                    dataframeTrimRef = dataframeTrimRef[dataframeTrimRef.index <= dataframeTrim.index.max()].fillna(0)
                    
                    # Adapt dataframeTrim to be able to perform correlation
                    if dataframeTrimRef.index.min() > dataframeTrim.index.min():
                        dataframeTrim = dataframeTrim[dataframeTrim.index >= dataframeTrimRef.index.min()]
                    if dataframeTrimRef.index.max() < dataframeTrim.index.max():
                        dataframeTrim = dataframeTrim[dataframeTrim.index <= dataframeTrimRef.index.max()]                    
                    pollutant_ref = pollutant + '_' + ref_append
                    if pollutant_ref in dataframeTrimRef.columns and not dataframeTrimRef.empty:
                        slopeRef, interceptRef, r_valueRef, p_valueRef, std_errRef = linregress(np.transpose(dataframeTrimRef[pollutant_ref]),np.transpose(dataframeTrim[pollutant_column]))
                        CorrParamsTrim.append(r_valueRef**2)
                    else:
                        CorrParamsTrim.append(np.nan)
                else:
                    CorrParamsTrim.append(np.nan)
                    print 'No ref Available'
                
                ## Get some metrics
                CorrParamsTrim.append(dataframeTrim[temp].mean(skipna = True))
                CorrParamsTrim.append(dataframeTrim[temp].std(skipna = True))
                CorrParamsTrim.append(dataframeTrim[hum].mean(skipna = True))
                CorrParamsTrim.append(dataframeTrim[hum].std(skipna = True))
                CorrParamsTrim.append(dataframeTrim[pollutant_column].mean(skipna = True))
                
                if day == 0:
                    CorrParams = list()
                
                CorrParams.append(CorrParamsTrim)
            
            ## TODO: Add relevant metadata for this method
            labelsCP = ['r_valueRef',
                        'avg_temp',
                        'stderr_temp',
                        'avg_hum',
                        'stderr_hum',
                        'avg_pollutant']
            
            CorrParamsDF = pd.DataFrame(CorrParams, columns = labelsCP, index = [(min_date_df+ pd.DateOffset(days=days)).strftime('%Y-%m-%d') for days in range(range_days)])
            
            # SHOW SOME METADATA FOR THE BASELINES FOUND
            if _printStats:
            
                print '------------------------'
                print ' Meta Data'
                print '------------------------'
                display(CorrParamsDF)
        
        # FILTER IT
        dataframeResult[pollutant_column + '_filter'] = exponential_smoothing(dataframeResult[pollutant_column].fillna(0), filterExpSmoothing)
        
        ## RETRIEVE METADATA
        CorrParamsDict[pollutant] = CorrParamsDF
        
        ## TODO - Make the check for outliers and mark them out
        # CorrParamsDF['valid'] = deltaAuxBas_avg-deltaAuxBas_std <= CorrParamsDF['deltaAuxBas_avg'] <= deltaAuxBas_avg-deltaAuxBas_std
        # CorrParamsDF['valid'] = ratioAuxBas_avg-ratioAuxBas_std <= CorrParamsDF['ratioAuxBas_avg'] <= ratioAuxBas_avg-ratioAuxBas_std
        # 
        # print CorrParamsDF
        # 
        # deltaAuxBas_avg = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'deltaAuxBas_avg'].mean(skipna = True)
        # deltaAuxBas_std = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'deltaAuxBas_avg'].std(skipna = True)
        # ratioAuxBas_avg = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'ratioAuxBas_avg'].mean(skipna = True)
        # ratioAuxBas_std = CorrParamsDF.loc[CorrParamsDF['valid'].fillna(False), 'ratioAuxBas_avg'].std(skipna = True)
        
        # PLOT THINGS IF REQUESTED
        if _plotResult:

            fig1 = tls.make_subplots(rows=4, cols=1, shared_xaxes=True, print_grid=False)
            
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[alphaW], 'type': 'scatter', 'line': dict(width = 2), 'name': dataframeResult[alphaW].name}, 1, 1)
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[alphaA], 'type': 'scatter', 'line': dict(width = 2), 'name': dataframeResult[alphaA].name}, 1, 1)
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[alphaA] * nWA, 'type': 'scatter', 'line': dict(width = 1, dash = 'dot'), 'name': 'AuxCor Alphasense'}, 1, 1)
            if method == 'baseline':
                fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[alphaW + '_baseline'], 'type': 'scatter', 'line': dict(width = 2), 'name': 'Baseline'}, 1, 1)
            
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[pollutant_column], 'type': 'scatter', 'line': dict(width = 1, dash = 'dot'), 'name': dataframeResult[pollutant_column].name}, 2, 1)
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[pollutant_column + '_filter'], 'type': 'scatter', 'name': (dataframeResult[pollutant_column + '_filter'].name)}, 2, 1)
            
            if _refAvail:
                # take the reference and check if it's available
                pollutant_ref = pollutant + '_' + ref_append
                if pollutant_ref in _dataframeRef.columns:
                    # If all good, plot it
                    fig1.append_trace({'x': _dataframeRef.index, 'y': _dataframeRef[pollutant_ref], 'type': 'scatter', 'name': _dataframeRef[pollutant_ref].name}, 2, 1)
                
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[temp], 'type': 'scatter', 'line': dict(width = 1, dash = 'dot'), 'name': dataframeResult[temp].name}, 3, 1)
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[hum], 'type': 'scatter', 'name': (dataframeResult[hum].name)}, 4, 1)
            
            fig1['layout'].update(height = 1500, 
                                  legend=dict(x=-.1, y=0.9), 
                                  xaxis=dict(title='Time'), 
                                  title = 'Baseline Correction for {}'.format(pollutant),
                                  yaxis1 = dict(title='Sensor Output - mV'), 
                                  yaxis2 = dict(title='Pollutant - ppm'),
                                  yaxis3 = dict(title='Temperature - degC'),
                                  yaxis4 = dict(title='Humidity - %'),
                                 )
                                   
            ply.offline.iplot(fig1)

    return dataframeResult, CorrParamsDict

def calculatePollutantsMICS(_dataframe, _pollutantTuples, _append, _refAvail, _dataframeRef, _deltas, _overlapHours = 0, _type_regress = 'best', _filterExpSmoothing = 0.2, _trydecomp = False, _plotsInter = False, _plotResult = True, _verbose = False, _printStats = False):
    '''
        Function to calculate mics pollutants with baseline technique
        Input:
            _dataframe: pandas dataframe from
            _pollutantTuples: list of tuples containing: 
                '[(_pollutant,
                    _sensorSN, 
                    calibration_method:
                        'baseline', 
                    baseline_type: 'baseline using temperature or humidity'
                        'single_temp'
                        'single_hum', 
                ...]'
            _append: suffix to the new channel name (pollutant + append)
            _refAvail: True or False if there is a reference available
            _dataframeRef: reference dataframe if available
            _deltas: for baseline correction method
            _overlapHours: number of hours to overlap over the day -> -_overlapHours+day:day+1+_overlapHours
            _type_regress = type of regression for baseline (best, exponential or linear)
            _filterExpSmoothing = alpha parameter for exponential filter smoothing
            _trydecomp = try to decompose with temperature trend or not
            _plotsInter = warning - many plots (True, False) plot intermediate analysis, 
            _plotResult = (True, False) plot final result, 
            _verbose = warning - many things (True, False), 
            _printStats = (True, False) print final statistics) 

        Output:
            _dataframe with pollutants added
            _metadata with statistics analysis
    '''
    
    dataframeResult = _dataframe.copy()
    numberSensors = len(_pollutantTuples)
    CorrParamsDict = dict()
    
    for sensor in range(numberSensors):
        
        # Get Sensor 
        pollutant = _pollutantTuples[sensor][0]
        sensorSN = _pollutantTuples[sensor][1]
        method = _pollutantTuples[sensor][2]
        
        if method == 'baseline':
            baselineType = _pollutantTuples[sensor][3]
        
        # Get Sensor data
        if pollutant == 'CO':
            indexPollutant = 1
        elif pollutant == 'NO2':
            indexPollutant = 2

        Sensitivity = mics_calData.loc[sensorSN,'Sensitivity ' +str(indexPollutant)]
        Target = mics_calData.loc[sensorSN,'Target ' + str(indexPollutant)]
        Zero_Air_Resistance = mics_calData.loc[sensorSN,'Zero Air Resistance ' + str(indexPollutant)]

        if not Target == pollutant:
            print 'Sensor ID ({}) and pollutant type ({}) not matching'.format(Target, pollutant)
            return

        mics_resist = CHANNEL_NAME(currentSensorNames, 'SENSOR_' + pollutant, '', '', 'BOARD_URBAN','kOhm')
        temp = CHANNEL_NAME(currentSensorNames, 'TEMPERATURE', '', '', 'BOARD_URBAN','C')
        hum = CHANNEL_NAME(currentSensorNames, 'HUMIDITY', '', '', 'BOARD_URBAN','%')
        
        _listNames = (mics_resist, temp, hum)
        
        # Get units for the pollutant in questions
        for pollutantItem in micsUnitsFactorsLUT:
            if pollutant == pollutantItem[0]:
                factor_unit = pollutantItem[1]

        ## Find min, max and range of days
        min_date_df, max_date_df, range_days = findDates(_dataframe)
        print '------------------------------------------------------------------'
        print ('Calculation of ' + '\033[1m{:10s}\033[0m'.format(pollutant))
        print 'Data Range from {} to {} with {} days'.format(min_date_df, max_date_df, range_days)
        print '------------------------------------------------------------------'
        
        # Give name to pollutant column
        pollutant_column = (pollutant + '_' + _append) 
        
        if method == 'baseline':

            # Select baselined - baseliner depending on the baseline type
            if baselineType == 'single_temp':
                baseliner = temp
            elif baselineType == 'single_rel_hum':
                baseliner = hum

            baselined = mics_resist
            
            # Iterate over days
            for day in range(range_days):
            
                # Calculate overlap dates for that day
                min_date_ovl = max(_dataframe.index.min(), (min_date_df + pd.DateOffset(days=day) - pd.DateOffset(hours = _overlapHours)))
                max_date_ovl = min(_dataframe.index.max(), (min_date_ovl + pd.DateOffset(days=1) + pd.DateOffset(hours = _overlapHours + relativedelta.relativedelta(min_date_df + pd.DateOffset(days=day),min_date_ovl).hours)))
                
                # Calculate non overlap dates for that day
                min_date_novl = max(min_date_df, (min_date_df + pd.DateOffset(days=day)))
                max_date_novl = min(max_date_df, (min_date_novl + pd.DateOffset(days=1)))
            
                if _verbose:
                    print '------------------------------------------------------------------'
                    print 'Calculating day {}, with range: {} \t to {}'.format(day, min_date_ovl, max_date_ovl)
                    print '------------------------------------------------------------------'
                
                ## Trim dataframe to overlap dates
                dataframeTrim = dataframeResult[dataframeResult.index > min_date_ovl]
                dataframeTrim = dataframeTrim[dataframeTrim.index <= max_date_ovl]
                
                # Init stuff
                if day == 0:
                    # Init list for CorrParams
                    CorrParams = list()
                 
                if dataframeTrim.empty:
                    if _verbose:
                        print 'No data between these dates'
                    
                    # Fill with nan if no data available (to avoid messing up the stats)
                    nanV =np.ones(10)
                    nanV.fill(np.nan)

                    CorrParams.append(tuple(nanV))
                    
                else:
                    
                    # CALCULATE THE BASELINE PER DAY
                    dataframeTrim[mics_resist + '_baseline'], CorrParamsTrim = calculateBaselineDay(dataframeTrim, 'mics', _listNames, baselined, baseliner, _deltas, _type_regress, _trydecomp, _plotsInter, _verbose)
                    
                    # TRIM IT BACK TO NO-OVERLAP
                    dataframeTrim = dataframeTrim[dataframeTrim.index > min_date_novl].fillna(0)
                    dataframeTrim = dataframeTrim[dataframeTrim.index <= max_date_novl].fillna(0)
                    
                    # CALCULATE ACTUAL POLLUTANT CONCENTRATION
                    pollutant_wo_background = factor_unit*(dataframeTrim[mics_resist] - dataframeTrim[mics_resist + '_baseline'] - Zero_Air_Resistance)/Sensitivity
                    
                    if pollutant == 'CO': 
                        dataframeTrim[pollutant_column] = backgroundConc_CO + pollutant_wo_background
                    elif pollutant == 'NO2':
                        dataframeTrim[pollutant_column] = backgroundConc_NO2 + pollutant_wo_background

                    # ADD IT TO THE DATAFRAME
                    dataframeResult = dataframeResult.combine_first(dataframeTrim)
                    
                    if _refAvail:
                        pollutant_ref = pollutant + '_' + ref_append
                        ## Trim ref dataframe to no-overlap dates
                        dataframeTrimRef = _dataframeRef[_dataframeRef.index >= dataframeTrim.index.min()].fillna(0)
                        dataframeTrimRef = dataframeTrimRef[dataframeTrimRef.index <= dataframeTrim.index.max()].fillna(0)
                        
                        # Adapt dataframeTrim to be able to perform correlation
                        if dataframeTrimRef.index.min() > dataframeTrim.index.min():
                            dataframeTrim = dataframeTrim[dataframeTrim.index >= dataframeTrimRef.index.min()]
                        if dataframeTrimRef.index.max() < dataframeTrim.index.max():
                            dataframeTrim = dataframeTrim[dataframeTrim.index <= dataframeTrimRef.index.max()]
                        
                        if pollutant_ref in dataframeTrimRef.columns and not dataframeTrimRef.empty:
                            slopeRef, interceptRef, r_valueRef, p_valueRef, std_errRef = linregress(np.transpose(dataframeTrim[pollutant_column]), np.transpose(dataframeTrimRef[pollutant_ref]))
                        else:
                            r_valueRef = np.nan
                    else:
                        r_valueRef = np.nan
                        print 'No Ref available'
                    
                    ## Get some metrics
                    temp_avg = dataframeTrim[temp].mean(skipna = True)
                    temp_stderr = dataframeTrim[temp].std(skipna = True)
                    hum_avg = dataframeTrim[hum].mean(skipna = True)
                    hum_stderr = dataframeTrim[hum].std(skipna = True)
                    pollutant_avg = dataframeTrim[pollutant_column].mean(skipna = True)
                    
                    tempCorrParams = list(CorrParamsTrim)
                    tempCorrParams.insert(0,r_valueRef**2)
                    tempCorrParams.insert(1,pollutant_avg)
                    tempCorrParams.insert(1,hum_stderr)
                    tempCorrParams.insert(1,hum_avg)
                    tempCorrParams.insert(1,temp_stderr)
                    tempCorrParams.insert(1,temp_avg)                    
                    CorrParamsTrim = tuple(tempCorrParams)
                    CorrParams.append(CorrParamsTrim)
            
            ## Add relevant metadata for this method
            labelsCP = ['r_valueRef',
                        'avg_temp',
                        'stderr_temp',
                        'avg_hum',
                        'stderr_hum',
                        'avg_pollutant',
                        'indexMax']
            
            CorrParamsDF = pd.DataFrame(CorrParams, columns = labelsCP, index = [(min_date_df+ pd.DateOffset(days=days)).strftime('%Y-%m-%d') for days in range(range_days)])
                   
            # SHOW SOME METADATA FOR THE BASELINES FOUND
            if _printStats:
                        
                print '------------------------'
                print ' Meta Data'
                print '------------------------'
                display(CorrParamsDF)
                        
        elif method == 'classic':
            print('Nothing to see here')
            # Nothing
        
        # FILTER IT
        dataframeResult[pollutant_column + '_filter'] = exponential_smoothing(dataframeResult[pollutant_column].fillna(0), filterExpSmoothing)
        
        ## RETRIEVE METADATA
        CorrParamsDict[pollutant] = CorrParamsDF
        
        # PLOT THINGS IF REQUESTED
        if _plotResult:
            
            fig1 = tls.make_subplots(rows=4, cols=1, shared_xaxes=True, print_grid=False)
            
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[mics_resist], 'type': 'scatter', 'line': dict(width = 2), 'name': dataframeResult[mics_resist].name}, 1, 1)
            if method == 'baseline':
                fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[mics_resist + '_baseline'], 'type': 'scatter', 'line': dict(width = 2), 'name': 'Baseline'}, 1, 1)
            
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[pollutant_column], 'type': 'scatter', 'line': dict(width = 1, dash = 'dot'), 'name': dataframeResult[pollutant_column].name}, 2, 1)
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[pollutant_column + '_filter'], 'type': 'scatter', 'name': (dataframeResult[pollutant_column + '_filter'].name)}, 2, 1)
            
            if _refAvail:
                # take the reference and check if it's available
                if pollutant_ref in _dataframeRef.columns:
                    # If all good, plot it
                    fig1.append_trace({'x': _dataframeRef.index, 'y': _dataframeRef[pollutant_ref], 'type': 'scatter', 'name': _dataframeRef[pollutant_ref].name}, 2, 1)
                
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[temp], 'type': 'scatter', 'line': dict(width = 1, dash = 'dot'), 'name': dataframeResult[temp].name}, 3, 1)
            fig1.append_trace({'x': dataframeResult.index, 'y': dataframeResult[hum], 'type': 'scatter', 'name': (dataframeResult[hum].name)}, 4, 1)
            
            fig1['layout'].update(height = 1500, 
                                  legend=dict(x=-.1, y=0.9), 
                                  xaxis=dict(title='Time'), 
                                  title = 'Baseline Correction for {}'.format(pollutant),
                                  yaxis1 = dict(title='Sensor Output - mV'), 
                                  yaxis2 = dict(title='Pollutant - ppm'),
                                  yaxis3 = dict(title='Temperature - degC'),
                                  yaxis4 = dict(title='Humidity - %'),
                                 )
                                   
            ply.offline.iplot(fig1)

    return dataframeResult, CorrParamsDict
