#!/bin/python
import calendar
import os
import csv
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta

LOCAL_EXPORT_PATH = '/tmp/es_export'
ES_HOSTS = ['localhost:9200']
INDEX_NAME = 'es_index'
INDEX_MAPPING_NAME = 'index_map_to_export'
TIME_FIELD = "time_created"


def dt_to_timestamp(dt):
    return str(calendar.timegm(dt.timetuple()) * 1000)


def create_directory(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def get_fields(es):
    fields = []
    index_info = es.indices.get(INDEX_NAME)
    for field_name, field_info in index_info[INDEX_NAME]['mappings'][INDEX_MAPPING_NAME]['properties'].iteritems():
        fields.append({
            'name': field_name,
            'type': field_info['type']
        })
    return fields


def add_headers(fields, filename):
    with open(filename, 'w+') as csvfile:
        data_csv = csv.writer(csvfile, delimiter=',', lineterminator='\n', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        rowData = []
        for field in fields:
            rowData.append(field['name'])
        data_csv.writerow(rowData)


def add_rows(rows, filename):
    with open(filename, 'a') as csvfile:
        data_csv = csv.writer(csvfile, delimiter=',', lineterminator='\n', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        data_csv.writerows(rows)


def scroll_timeframe(gte_timestamp, lte_timestamp):
    es = Elasticsearch(ES_HOSTS)

    fields = get_fields(es)

    gte_scroll_date_epoch = dt_to_timestamp(gte_timestamp)
    lte_scroll_date_epoch = dt_to_timestamp(lte_timestamp)

    # Initialize the scroll
    page = es.search(
        index=INDEX_NAME,
        scroll='60m',
        search_type='scan',
        size=1000,
        body={
            "query": {
                "range": {
                    TIME_FIELD: {
                        "gte": gte_scroll_date_epoch,
                        "lte": lte_scroll_date_epoch,
                        "format": "epoch_millis"
                    }
                }
            }
        }
    )
    sid = page['_scroll_id']
    total_hits = page['hits']['total']

    full_filename = LOCAL_EXPORT_PATH + "/{0}_{1}.csv".format(INDEX_MAPPING_NAME, gte_timestamp.strftime('%Y-%m-%d'))
    add_headers(fields, full_filename)

    # Start scrolling
    while (total_hits > 0):
        print("scroll {0}: total_hits: {1}".format(gte_timestamp.strftime('%Y-%m-%d'), total_hits))
        page = es.scroll(scroll_id=sid, scroll='60m')
        sid = page['_scroll_id']
        data = page['hits']['hits']
        rows = []
        for datumn in data:
            row = []
            for field in fields:
                row.append(datumn["_source"].get(field['name']))
            rows.append(row)
        add_rows(rows, full_filename)
        print("length: {}".format(len(data)))
        total_hits -= len(data)
    print("Finished scroll {0}:".format(gte_timestamp.strftime('%Y-%m-%d')))


def export():
    dateList = [datetime.now() - timedelta(days=1)]

    create_directory(LOCAL_EXPORT_PATH)

    scroll_dates = []
    for day in dateList:
        scroll_dates.append({"gte": datetime(day.year, day.month, day.day, 0, 0, 0), "lte": datetime(day.year, day.month, day.day, 23, 59, 59)})
    for scroll_date in scroll_dates:
        scroll_timeframe(scroll_date["gte"], scroll_date["lte"])

if __name__ == '__main__':
    export()
