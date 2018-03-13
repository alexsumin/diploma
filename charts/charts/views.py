import datetime
import sqlite3 as lite

import pandas as pd
import xgboost as xgb
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn import cross_validation
from sklearn.model_selection import GridSearchCV

User = get_user_model()

class HomeView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'charts.html', {"customers": 10})

def get_data(request, *args, **kwargs):
    data = {
        "sales": 100,
        "customers": 10,
    }
    return JsonResponse(data) # http response

class ChartData(APIView):
    authentication_classes = []
    permission_classes = []

    def tsne(self):
        con = lite.connect('test.db', isolation_level='DEFERRED')
        parameters_tech = ['date']
        with con:
            cur = con.cursor()
            list_tech_id = [50, 51, 102, 138, 145, 151, 170, 203, 318];
            questionmarks = '?' * len(list_tech_id);
            query = 'SELECT * FROM PARAMETERS WHERE PARAMETERS.rowid IN ({})'.format(','.join(questionmarks))
            query_args = list_tech_id
            cur.execute(query, query_args)
            rows = cur.fetchall()  # извлечь данные
            for row in rows:
                parameters_tech.append(row[0])
        # print(parameters_tech)

        a = datetime.datetime(2015, 5, 17, 5, 0, 0)
        cur = con.cursor()
        query = ''
        query += 'SELECT date, '
        for row_id in list_tech_id:
            if (list_tech_id[len(list_tech_id) - 1] != row_id):
                query += 'MAX(CASE MEASUREMENTS.parameter_id WHEN ' + str(
                    row_id) + ' THEN MEASUREMENTS.value ELSE NULL END), '
            else:
                query += 'MAX(CASE MEASUREMENTS.parameter_id WHEN ' + str(
                    row_id) + ' THEN MEASUREMENTS.value ELSE NULL END)'
        query += 'FROM measurements WHERE datetime(date) < datetime(?) group by date'
        # print(query)
        cur.execute(query, (a,));
        data = cur.fetchall();  # получаем результаты запроса
        df_query = pd.DataFrame.from_records(data,
                                             columns=parameters_tech)  # перевод в матричный вид для pandas

        df_query.dropna(axis=0, inplace=True)  # для обработки нулевых значений, удаление строк

        dates = df_query['date']
        # print(dates)

        df_data = df_query.drop(['date'], axis=1)  # удаляем столбец с датой

        # print(df_data)
        # по чему будет обучаться
        X = df_query[['Energieverbr._Auftr._Zaehler1', 'Energieverbr._Auftr._Zaehler2', 'ExtB_Ist_Massedruck',
                      'ExtC_Ist_Massedruck', 'ExtC_IST_Temp_Massetemperatur_vor_Sieb', 'ExtC_IST_Temp_Zone4',
                      'IST_Gewicht_Komp3', 'Vorabzug_Zugist']]
        # интересующий параметр
        Y = df_query['Stippe_-3000']

        # здесь разбиваем их на 2 части, первая пара для обучения, вторая - для тестирования
        #0.25 - 1029
        ROCtrainTRN, ROCtestTRN, ROCtrainTRG, ROCtestTRG = cross_validation.train_test_split(X, Y, test_size=0.1)

        gbm = xgb.XGBRegressor()

        # Это вообще нужно или без этого можно обойтись?
        reg_cv = GridSearchCV(gbm, {"colsample_bytree": [1.0], "min_child_weight": [1.0, 1.2]
            , 'max_depth': [3, 4, 6], 'n_estimators': [500, 1000]}, verbose=1)

        # здесь падает с ошибкой
        # ValueError: Found input variables with inconsistent numbers of samples: [1029, 343]
        # reg_cv.fit(ROCtrainTRN, ROCtestTRN)
        # reg_cv.best_params_
        # gbm = xgb.XGBRegressor(**reg_cv.best_params_)

        gbm = xgb.XGBRegressor()

        gbm.fit(ROCtrainTRN, ROCtrainTRG)

        predictions = gbm.predict(ROCtestTRN)
        # должно примерно быть как ROCtestTRG по идее
        # print(predictions)
        #1029
        forX = dates[1234::]
        return forX, ROCtestTRG, predictions

    def classifyQualityValue(self, x):
        if (x > 45):
            return 0
        else:
            return 1

    def get(self, request, format=None):
        ox, realAlg, regrAlg = self.tsne()


        qs_count = User.objects.all().count()

        data = {
                "dates" : ox,
                "reals": realAlg,
                "regress": regrAlg
        }
        return Response(data)