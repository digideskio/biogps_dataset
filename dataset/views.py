#-*-coding: utf-8 -*-
import csv
from django.conf import settings
from django.views.decorators.http import require_http_methods
import models
from django.http.response import HttpResponse
import json
import datetime
from django.db.models.query import QuerySet
from django.core.serializers import serialize, deserialize
from json.encoder import JSONEncoder
from django.db.models.base import Model
import requests

def adopt_dataset():
    try:
        ds_id = settings.DEFAULT_DATASET_ID
        ds = models.BiogpsDataset.objects.get(id=ds_id)
    except Exception, e:
        ds = models.BiogpsDataset.objects.first()
    return ds
   
 #return an array of keys that stand for samples in ds   
def get_ds_factors_keys(ds):
    factors =[]
    for f in ds.metadata['factors']:
        print f
        comment=f[f.keys()[0]]['comment']
        temp=comment.get('Sample_title',None)
        if temp==None:
            temp=comment.get('Sample_title',None)
            if temp == None:
                temp=f.keys()[0]
        factors.append(temp)
    
    return factors
 
#get information about a dataset
@require_http_methods(["GET"])
def dataset_info(request):
    ds = adopt_dataset()
    preset = {'default':True, 'permission_style':'public', 'role_permission': ['biogpsusers'], 'rating_data':{ 'total':5, 'avg_stars':10, 'avg':5 }, 
        'display_params': {'color': ['color_idx'], 'sort': ['order_idx'], 'aggregate': ['title']}
     }
    ret = {'id':ds.id, 'name_wrapped':ds.name, 'name':ds.name, 'owner': ds.ownerprofile_id, 'lastmodified':ds.lastmodified.strftime('%Y-%m-%d %H:%M:%S'), 
           'pubmed_id':ds.metadata['pubmed_id'], 'summary':ds.summary, 'geo_gse_id':ds.geo_gse_id, 'created':ds.created.strftime('%Y-%m-%d %H:%M:%S'),
            'geo_gpl_id':ds.metadata['geo_gpl_id']['accession'], 'species':[ds.species] 
    }
    factors = []
    fa = get_ds_factors_keys(ds)
    for f in fa:
        factors.append({f:{"color_idx":31,  "order_idx":76, "title":f}})
    ret.update(preset)
    ret.update({'factors':factors})
    #print factors
    ret = json.dumps(ret)
    return HttpResponse('{"code":0, "detail":%s}'%ret, content_type="application/json")

def  get_dataset_data(_id):
    ds = adopt_dataset()
    url = 'http://mygene.info/v2/gene/%s/?fields=entrezgene,reporter,refseq.rna'%_id
    res = requests.get(url)
    data_json = res.json()
    reporters = []
    for i in data_json['reporter'].values():
        reporters = reporters+i
    dd = ds.dataset_data.filter(reporter__in = reporters)
    data_list = []
    for d in dd:
        data_list.append({d.reporter:{'values':d.data}})
    return {'id':ds.id, 'name':ds.name, 'data':data_list}

#显示柱状图，但是需要接受id和at参数
def dataset_chart(request):
    _id = request.GET.get('id', None)
    _at= request.GET.get('at', None)
    if _id is None or  _at is None:
        return HttpResponse('{"code":4004, "detail":"argument needed"}', content_type="application/json")
    data_list=get_dataset_data(_id)['data']
    print data_list
    str_list=[]
    for item in data_list:
        if _at  in item:
             str_list=item[_at]["values"]
             break
    
    if  len(str_list)==0:
        return HttpResponse('{"code":4004, "detail":"_at  can not  find"}', content_type="application/json")
    print str_list
    val_list=[]
    for item in str_list:
        temp=float(item)
        val_list.append(temp)
    print val_list
    ds = adopt_dataset()
    name_list=get_ds_factors_keys(ds)
    print name_list
    
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    import matplotlib.pyplot as plt 
    import django
    import numpy as np
    y_pos = [0.0,0.45]
    plt.figure(1,figsize=(160,6)).clear()
    #根据传回的参数获取x轴的范围
    if val_list[0]>val_list[1]:
        x_max=int(val_list[0])
    else:
        x_max=int(val_list[1])
    print "x_max=",x_max
    temp_count=0
    temp_val=0
    while x_max>0:
        temp_count=temp_count+1
        temp_val=x_max%10
        x_max=x_max/10
    x_max=(temp_val+1)*10**(temp_count-1)
    print "=====" ,temp_count,temp_val,x_max
#修改背景色
    fig1 = plt.figure(1)
    rect=fig1.patch
    rect.set_facecolor('white')
#画柱状图    
    xylist=[0, 0, 0, 2.0]  
    xylist[1]=x_max  
    print xylist
    plt.axis(xylist)
    plt.barh(y_pos,val_list,height=0.4,color="m")
#画label    
    plt.text(-2.5*x_max/30,0.2,name_list[0],fontsize=80)
    plt.text(-2.5*x_max/30,0.6,name_list[1],fontsize=80)

#画x坐标    
    x_per=x_max/5
    i=1
    while i<=5:
        x_label=i*x_per
        str_temp='%.2f'%x_label
        plt.text(x_label-0.3*x_max/30,1.3,str_temp,fontsize=80)
        list_temp=[]
        list_temp.append(x_label)
        list_temp.append(x_label)
        plt.plot(list_temp, [1, 0.7],"k",linewidth=4)
        i=i+1
    list_temp=[]
    list_temp.append(0)
    list_temp.append(x_max)
    plt.plot(list_temp, [1, 1],"k",linewidth=4)
    canvas = FigureCanvas(plt.figure(1))
    response=django.http.HttpResponse(content_type='image/png')
    canvas.print_png(response) 
    return response

def get_cvs(request):
     _id = request.GET.get('id', None)
     if _id is None:
         return HttpResponse('{"code":4004, "detail":"argument needed"}', content_type="application/json")
     data_list=get_dataset_data(_id)['data']
     row_list=['Tissue']
     val_list=[]
     for item in data_list:
         key_list=item.keys()
         for key_item in key_list:
             row_list.append(key_item)
             val_list.append(item[key_item]['values'])
     length=len(val_list[0])       
     ds = adopt_dataset()
     name_list=get_ds_factors_keys(ds)
     response = HttpResponse(mimetype='text/csv')
     response['Content-Disposition'] = 'attachment; filename=asd.csv'
     writer = csv.writer(response)
     writer.writerow(row_list)
     i=0
     while(i<length):
         temp_list=[]
         temp_list.append(name_list[i])
         for item in val_list:
             temp_list.append(item[i])
         writer.writerow(temp_list)
         i=i+1   
     return response
    
    
    
#get information about a dataset
@require_http_methods(["GET"])
def dataset_data(request):
    _id = request.GET.get('id', None)
    if _id is None :
        return HttpResponse('{"code":4004, "detail":"argument needed"}', content_type="application/json")
    ret = get_dataset_data(_id)
    print ret
    ret['probeset_list'] = ret['data']
    del ret['data']
    return HttpResponse('{"code":0, "detail":%s}'%json.dumps(ret), content_type="application/json")
    
    
class ComplexEncoder(JSONEncoder):
    def default(self, obj):
        print type(obj)
        if isinstance(obj, Model):
            return json.loads(serialize('json', [obj])[1:-1])['fields']
        if isinstance(obj, QuerySet):
            obj = obj.values()
            obj = list(obj)
            return json.loads(json.dumps(obj, cls=ComplexEncoder))
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M')
        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

    def jsonBack(self, json):
        if json[0] == '[':
            return deserialize('json', json)
        else:
            return deserialize('json', '[' + json + ']')
