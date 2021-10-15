# -*- coding: utf-8 -*-
"""
Created on Fri Oct 15 17:14:14 2021

@author: quincy408
"""

import pandas as pd
import shioaji as sj
import datetime
import mplfinance as mpf
import requests
import talib

api = sj.Shioaji()

UID = "B123324265"
PWD = "Kobe8922"
api.login(UID, PWD)

def LineNotifyPush(msg, image_path, Token):
    headers = {
        "Authorization":"Bearer " + Token
        }
    payload = {'message':msg}
    files = {'imageFile':open(image_path,'rb')}
    r = requests.post('https://notify-api.line.me/api/notify',
                headers = headers, params = payload, files = files)
    if r.status_code == 200:
        print('推播完成')
    else:
        print(r.status_code)

def Work():
    Work_Datetime = str((datetime.datetime.now() + datetime.timedelta(days=0)).strftime("%Y-%m-%d %H:%M:%S"))
    EndDate = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime("%Y-%m-%d")
    StartDate = (datetime.datetime.now() + datetime.timedelta(days=-120)).strftime("%Y-%m-%d")
    
    StockID = {'TAIWAN SE WEIGHTED INDEX':'台股指數','2330':'台積電','2376':'技嘉'}
    for StockKey, StockNamee in StockID.items():
        if StockKey == 'TAIWAN SE WEIGHTED INDEX':
            StockContract = api.Contracts.Indexs.TSE.TSE001
        else:
            StockContract = api.Contracts.Stocks[StockKey]
        kbars = api.kbars(StockContract, start = StartDate, end = EndDate)
        kbarsDF = pd.DataFrame({**kbars})
        kbarsDF.ts = pd.to_datetime(kbarsDF.ts)
        kbarsDF['ts'] = (kbarsDF['ts'] - pd.DateOffset(hours=14)).dt.date
        kbarsDF.rename(columns={'ts': 'Date'}, inplace=True)
        kbarsDF.head()
        kbarsDF = kbarsDF.groupby('Date').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last','Volume':'sum'})
        kbarsDF=kbarsDF.iloc[2: , :]
    
        KD_DF = kbarsDF.copy()
        KD_DF['Min'] = KD_DF['Low'].rolling(9).min()
        KD_DF['Max'] = KD_DF['High'].rolling(9).max()
        KD_DF['RSV'] = ((KD_DF['Close'] - KD_DF['Min']) / (KD_DF['Max'] - KD_DF['Min']))*100
        KD_DF = KD_DF.dropna()
        K_list = [50]
        for index,rsv in enumerate(list(KD_DF['RSV'])):
            K_yestarday = K_list[index]
            K_today = 2/3 * K_yestarday + 1/3 * rsv
            K_list.append(K_today)
        KD_DF['K'] = K_list[1:]
        D_list = [50]
        for index,K in enumerate(list(KD_DF['K'])):
            D_yestarday = D_list[index]
            D_today = 2/3 * D_yestarday + 1/3 * K
            D_list.append(D_today)
        KD_DF['D'] = D_list[1:]
        kbarsDF = pd.merge(kbarsDF,KD_DF[['K','D']],left_index = True,right_index = True,how = 'left')
    
        
        # RSI 指標計算
        RSI_DF = kbarsDF.copy()
        RSI_DF['RSI6'] = talib.RSI(RSI_DF['Close'], timeperiod = 6)
        RSI_DF['RSI12'] = talib.RSI(RSI_DF['Close'], timeperiod = 12)
        kbarsDF = pd.merge(kbarsDF,RSI_DF[['RSI6','RSI12']],left_index = True,right_index = True,how = 'left')
        
        #　MA 指標計算
        MA_DF = kbarsDF.copy()
        MA_DF['MA10'] = talib.SMA(MA_DF['Close'], 10)
        MA_DF['MA20'] = talib.SMA(MA_DF['Close'], 20)
        kbarsDF = pd.merge(kbarsDF,MA_DF[['MA10','MA20']],left_index = True,right_index = True,how = 'left')
        
        # MACD 指標計算
        MACD_DF = kbarsDF.copy()
        MACD_DF['MACD_DIF'],  MACD_DF['MACD'], MACD_DF['MACD_HIST']  = talib.MACD(MACD_DF['Close'], fastperiod = 12, slowperiod = 26, signalperiod = 9)
        kbarsDF = pd.merge(kbarsDF,MACD_DF[['MACD','MACD_DIF','MACD_HIST']],left_index = True,right_index = True,how = 'left')
        
        # 乖離率 
        BIAS_DF = kbarsDF.copy()
        BIAS_DF['MA12']=BIAS_DF['Close'].rolling(12).mean()
        BIAS_DF['BIAS12']=BIAS_DF['Close']/BIAS_DF['MA12']-1
        kbarsDF = pd.merge(kbarsDF,BIAS_DF["BIAS12"],left_index = True,right_index = True,how = 'left')
        
        # 布林通道
        BBANDS_DF = kbarsDF.copy()
        BBANDS_DF['BBup'], BBANDS_DF['BBmid'], BBANDS_DF['BBlow'] = talib.BBANDS(BBANDS_DF['Close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        kbarsDF = pd.merge(kbarsDF,BBANDS_DF[['BBup','BBmid','BBlow']],left_index = True,right_index = True,how = 'left')
        
        # 威廉指標
        WILLR_DF = kbarsDF.copy()
        WILLR_DF['WILLR'] = talib.WILLR(WILLR_DF['High'], WILLR_DF['Low'], WILLR_DF['Close'], timeperiod = 14)
        kbarsDF = pd.merge(kbarsDF,WILLR_DF['WILLR'],left_index = True,right_index = True,how = 'left')
        kbarsDF = kbarsDF.dropna()
        
        if kbarsDF['MACD_DIF'].max() > 10 or kbarsDF['MACD_DIF'].min() < -10:
            MACD_MAX = kbarsDF['MACD_DIF'].max() + 5
            MACD_MIN = kbarsDF['MACD_DIF'].min() - 5
        else:
            MACD_MAX = 15
            MACD_MIN = -15
    
        MPF_DF =  kbarsDF.copy()
        MPF_DF = MPF_DF.reset_index()
        MPF_DF.index = pd.DatetimeIndex(MPF_DF['Date'])
        mc = mpf.make_marketcolors(up='r',down='g',edge='', wick='inherit',volume='inherit')
        s = mpf.make_mpf_style(base_mpf_style='yahoo', marketcolors=mc)
        ADD_Plot = [mpf.make_addplot(MPF_DF['BBup'].values,panel= 0,linestyle='dashdot'), mpf.make_addplot(MPF_DF['BBmid'].values,panel= 0,color="y",linestyle='dotted'),
                    mpf.make_addplot(MPF_DF['BBlow'].values,panel= 0,linestyle='dashdot'),
                    mpf.make_addplot(MPF_DF['K'].values,panel= 2,color="b"), mpf.make_addplot(MPF_DF['D'].values,panel= 2,color="r",ylabel='KD'), 
                    mpf.make_addplot(MPF_DF['MACD'].values,panel= 3,color="r",ylim=(MACD_MIN,MACD_MAX),secondary_y = False,y_on_right=False), mpf.make_addplot(MPF_DF['MACD_DIF'].values,panel= 3,color="b",ylabel='MACD'),
                    mpf.make_addplot(MPF_DF['RSI6'].values,panel= 4,color="b"), mpf.make_addplot(MPF_DF['RSI12'].values,panel= 4,color="r",ylabel='RSI'),
                    mpf.make_addplot(MPF_DF['MA10'].values,panel= 5,color="b",secondary_y = False,y_on_right=False), mpf.make_addplot(MPF_DF['MA20'].values,panel= 5,color="r",ylabel='MA'),
                    mpf.make_addplot(MPF_DF['BIAS12'].values,panel= 6,color="b",ylabel='BIAS',ylim=(MPF_DF["BIAS12"].min(),MPF_DF["BIAS12"].max())),
                    mpf.make_addplot(MPF_DF['WILLR'].values,panel= 7,color="b",ylabel='WILLR',ylim=(-102,2),secondary_y = False,y_on_right=False)]
        MPF_DF_MAX_Limit = MPF_DF["BBup"].max() + 2
        MPF_DF_Min_Limit = MPF_DF["BBlow"].min() - 2
        mpf.plot(MPF_DF,type='candle',style=s,volume=True,addplot = ADD_Plot,ylabel='',title = StockKey, tight_layout=True,ylim=(MPF_DF_Min_Limit,MPF_DF_MAX_Limit),savefig= 'TW.png')
        
        PlusFall = int(kbarsDF.Close.iat[-1]) - int(kbarsDF.Close.iat[-2])
        msg = StockID[StockKey] + '\n時間:' + str(EndDate) + '\n漲跌:' + str(PlusFall) + \
            '   漲跌幅(%):' + str(round((PlusFall / kbarsDF.Close.iat[-1])*100,2)) + '%\n最高點:' + str(round(kbarsDF.High.iat[-1],2)) + '   最低點:' + str(round(kbarsDF.Low.iat[-1],2)) + '\n收:' + str(round(kbarsDF.Close.iat[-1],2)) + '   量:' + str(round(kbarsDF.Volume.iat[-1],2))
        TodayDate = pd.Timestamp.now()
        if TodayDate.dayofweek != 0 and TodayDate.dayofweek != 6:
            Token = ['OafiwKhZtfKocPZ6aHRJ47PquRYoZdSwfDuI1BfQu8j']
            for Token in Token:
                LineNotifyPush(msg,'TW.png', Token)
        else:
            print('今日台股為假日')
    print(Work_Datetime + '完成推播')
  

if __name__ == '__main__':
    TodayDate = pd.Timestamp.now()
    if TodayDate.dayofweek != 5 and TodayDate.dayofweek != 6:
        Work()
