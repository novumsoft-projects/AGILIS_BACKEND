#from common.utils import MongoHelper, run_in_background
from common.utils import MongoHelper
from common.utils import RedisKeyBuilderServer,CacheHelper,MongoHelper
from bson import ObjectId
from zipfile import ZipFile
import os
import json
import uuid
import cv2
import datetime
from copy import deepcopy
import xml.etree.cElementTree as ET
from lxml import etree
import csv
from livis.constants import *
import shutil
import imutils
import random
from django.conf import settings
from accounts.utils import get_user_account_util
import tensorflow as tf
#from livis.Monk_Object_Detection.tf_obj_2.lib.models.research.object_detection.webcam import load_model_to_memory,crop_infer
from livis.models.research.object_detection.utils import label_map_util

from livis.celeryy import app
from celery import shared_task
#from livis.common_model import detection_graphm,detection_graphx,sessm,sessx,accuracy_thresholdm,accuracy_thresholdx,category_indexm,category_indexx

import datetime
import base64
import numpy as np
import requests
import cv2
import time
import requests
import cv2
import time
import gc
from billiard import Process

def get_pred_tf_serving(image,port):
    image_expanded = np.expand_dims(image, axis=0)
    accuracy_threshold = 0.9
    gpu_fraction = 0.4


    NUM_CLASSES = 11
    PATH_TO_CKPT = "/critical_data/trained_models/GVM/frozen_inference_graph.pb"
    PATH_TO_LABELS = "/critical_data/trained_models/GVM/labelmap.pbtxt"
    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)


    total_time = time.time()
    
    data = json.dumps({ 
    "instances": image_expanded.tolist()
    })
    SERVER_URL = 'http://localhost:'+str(port)+'/v1/models/saved_model:predict'
    #predict_request = '{"instances" : [{"b64": "%s"}]}' % jpeg_bytes.decode('utf-8')
    response = requests.post(SERVER_URL, data=data)
    response.raise_for_status()
    total_time += response.elapsed.total_seconds()
    prediction = response.json()['predictions'][0]
    #print(prediction.keys())
    #print('Prediction class: {}, avg latency: {} ms'.format(prediction['detection_classes'], (time.time() - total_time)))
    objects = []
    #print(prediction['detection_scores'])
    accuracy = []
    #coordinates = []

    for index, value in enumerate(prediction['detection_classes']):
        if prediction['detection_scores'][index] > accuracy_threshold:
            objects.append((category_index.get(value)).get('name'))
            accuracy.append(prediction['detection_scores'][index])

    ret_obj = {
        "scores": prediction['detection_scores'],
        "boxes": prediction['detection_boxes'],
        "objects": objects,
        "accuracy": accuracy
    }
    return ret_obj

def start_inspection(data):


    try:
        mp = MongoHelper().getCollection(WORKSTATION_COLLECTION)
    except:
        message = "Cannot connect to db"
        status_code = 500
        return message,status_code


    p = [p for p in mp.find()]

    p=p[0]

    workstation_id = p['_id']

    feed_urls = []
    workstation_info = RedisKeyBuilderServer(workstation_id).workstation_info
    #print(workstation_info)
    cam=workstation_info['camera_config']
    #print(cam)
    for camera_info in cam['cameras']:
        url = "http://127.0.0.1:8000/livis/v1/preprocess/stream/{}/{}/".format(workstation_id,camera_info['camera_id'])

        #feed_urls[camera_info['camera_name']] = url
        feed_urls.append(url)


    jig_id = data['jig_id']
    jig_type = data['jig_type']
    barcode_id = data['barcode']

    try:
        mp = MongoHelper().getCollection(JIG_COLLECTION)
    except Exception as e:
        message = "Cannot connect to db"
        status_code = 500
        return message,status_code

    jig_id =  data['jig_id']
    if jig_id is None:
        message = "jig id not provided"
        status_code = 400
        return message,status_code

    try:
        dataset = mp.find_one({'_id' : ObjectId(jig_id)})
        if dataset is None:
            message = "Jig not found in Jig collection"
            status_code = 404
            return message,status_code


    except Exception as e:
        message = "Invalid jigID"
        status_code = 400
        return message,status_code
    

    oem_number = dataset['oem_number']
    jig_type = dataset['jig_type']

    try:
        kanban = dataset['kanban']
    except:
        return "kanban not defined",None
    try:
        vendor_match = dataset['vendor_match']
    except:
        pass
    try:
        full_img = dataset['full_img']
    except:
        return "regions not defined",None
    try:   
        user_id = data['user_id']
    except:
        return "userid not defined",None

    user_details = get_user_account_util(user_id)
    #print("user_details::::",user_details)
    role_name = user_details['role_name']
    #print("role_name::::",role_name,type(role_name))
    user = { "user_id": user_id,
                "role": user_details['role_name'],
                "name": (user_details['first_name']+" "+user_details['last_name'])
            }
    #print("user:::: ",user)
    createdAt = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    mp = MongoHelper().getCollection('INSPECTION')

    #dataset['camera_url'] = feed_urls[0]
    #dataset['jig_id'] = jig_id
    #dataset['user'] = user
    #dataset['status'] = 'started'
    #dataset['createdAt'] = createdAt
    #dataset['is_manual_pass'] = False
    #dataset['is_compleated'] = False


    obj = {
        'jig_details': dataset,
        'camera_url' : feed_urls[0],
        'jig_id' : jig_id,
        'user' : user,
        "status" : 'started',
        'createdAt' : createdAt,
        'is_manual_pass' : False,
        'is_compleated' : False,
        'serial_no' : barcode_id
    }

    _id = mp.insert(obj)

    rch = CacheHelper()

    #rch.set_json({_id:None})

    resp = obj
    if resp:
        return resp,_id
    else:
        return {}




@shared_task
def start_real_inspection(data1,inspection_id):

    frame = None
    crp = None

    #goto workstation and fetch redis keys and camera_name
    #goto jig and pull regions
    #load ssd to memory
    #combine the regions with camera_name
    #iterate through keys,camera_name
        
        #iterate through regions
            #crop send - get back the inference
    


    ############# worstation red key and cam name

    mp = MongoHelper().getCollection(WORKSTATION_COLLECTION)

    p = [p for p in mp.find()]

    workstation_id = p[0]['_id']

    data = RedisKeyBuilderServer(workstation_id).workstation_info

    rch = CacheHelper()

    cam_list = []
    key_list = []

    for cam in data['camera_config']['cameras']:
        camera_index = cam['camera_id']
        camera_name = cam['camera_name']
        key = RedisKeyBuilderServer(workstation_id).get_key(cam['camera_id'],'original-frame') 
        cam_list.append(cam['camera_name'])
        key_list.append(key)



    ########### jig details 

    try:
        mp = MongoHelper().getCollection(JIG_COLLECTION)
    except Exception as e:
        message = "Cannot connect to db"
        status_code = 500
        return message,status_code

    jig_id =  data1['jig_id']
    if jig_id is None:
        message = "jig id not provided"
        status_code = 400
        return message,status_code

    try:
        dataset = mp.find_one({'_id' : ObjectId(jig_id)})
        if dataset is None:
            message = "Jig not found in Jig collection"
            status_code = 404
            return message,status_code

    except Exception as e:
        message = "Invalid jigID"
        status_code = 400
        return message,status_code
    

    oem_number = dataset['oem_number']
    jig_type = dataset['jig_type']
    vendor_match = dataset['vendor_match']


    try:
        kanban = dataset['kanban']
        #print("KANBAN" , kanban )
    except:
        message = "error in kanban/not set"
        status_code = 400
        return message,status_code

    if kanban is None:
        message = "error in kanban/not set"
        status_code = 400
        return message,status_code


    try:
        #var = str(ObjectId(dataset['_id'])) + "_full_img"
        #full_img = rch.get_json(var)
        #print(full_img)
        from os import path
        import json 
        full_img = None
        print("999999999999")
        print(path.exists('/critical_data/regions/'+str(ObjectId(dataset['_id'])) + "_full_img"+".json"))
        if path.exists('/critical_data/regions/'+str(ObjectId(dataset['_id'])) + "_full_img"+".json"):
            f = open ('/critical_data/regions/'+str(ObjectId(dataset['_id'])) + "_full_img"+".json", "r")
            a = json.loads(f.read())
            full_img = a['full_img']
            print("GOTTTTTTTTTTTTTTTTTTT")
            f.close()
        else:
            full_img = None
            
        
    except:
        message = "error in full_img/regions not set"
        status_code = 400
        return message,status_code
    
    if full_img is None:
        message = "error in full_img/regions not set"
        status_code = 400
        return message,status_code



    ########### load the model to the memory 

    """
    base_path =  os.path.join('/critical_data/')
    if oem_number is None:
        this_model_pth = str(jig_type) 
    else:
        this_model_pth = str(jig_type) + str(oem_number) 

    dir_path = os.path.join(base_path,this_model_pth)

    weight_pth = os.path.join(dir_path,'weights')

    inference_grp_pth = os.path.join(weight_pth,'saved_model')
    inference_grp_pth = os.path.join(inference_grp_pth,'saved_model.pb')
    labelmap_pth = os.path.join(weight_pth,'labelmap.txt')

    PATH_TO_CFG = None
    PATH_TO_CKPT = None
    PATH_TO_LABELS = None
    detection_model,category_index = load_model_to_memory(PATH_TO_CFG,PATH_TO_CKPT,PATH_TO_LABELS)
    """

    #if jig_type == "GVM":
    #    detection_graph,sess,accuracy_threshold  = load_gvm_model()
    #else:
    #    detection_graph,sess,accuracy_threshold  = load_gvx_model()

    #####################################

    #final_dct = {}


    def regions_crop_pred(regions,rch,r_key,final_dct,port):
        global frame
        global crp
        t1 = time.time()
        frame  = rch.get_json(r_key)
        t2 = time.time()
        print('time taken to get frame from redis  ::  ::  ::  :: ---------    '+ str(t2-t1))
        

        height,width,c = frame.shape

        #height = height*3
        #width = width*3

        def resize_crop(img):
            scale_percent = 40 # percent of original size
            width = int(img.shape[1] * scale_percent / 100)
            height = int(img.shape[0] * scale_percent / 100)
            dim = (width, height) 
            resized = cv2.resize(img, dim, interpolation = cv2.INTER_LANCZOS64) 
            return resized



        for j in regions:
            #print("checking regions : : : " , j)
            x = float(j["x"])
            y = float(j["y"])
            w = float(j["w"])
            h = float(j["h"])
            #print(x,y,w,h)
            x0 = int(x * width)
            y0 = int(y * height)
            x1 = int(((x+w) * width))
            y1 = int(((y+h) * height))
            #print(x0,y0,x1,y1)
            label = j["cls"]
            cords = [x0,y0,x1,y1]
            import uuid
            unique_id = str(uuid.uuid4())

            #perform crop
            t1 = time.time()
            crp = frame[y0:y1,x0:x1].copy()
            #crp = resize_crop(crp)
            t2 = time.time()
            print('time taken to get crop            ::  ::  ::  :: ---------    '+ str(t2-t1))
            
            
            #cv2.imwrite('/critical_data/tmpcrops/'+unique_id+'.jpg',crp)
            #print('/critical_data/tmpcrops/'+unique_id+'.jpg')

            if jig_type == "GVM":
                print("going into prediction")
                print(crp.shape)
                t1 = time.time()
                ret = get_pred_tf_serving(crp,port)
                scores,boxes,objects,accuracy = ret['scores'], ret['boxes'], ret['objects'], ret['accuracy']
                t2 = time.time()
                print('time taken to predict            ::  ::  ::  :: ---------    '+ str(t2-t1))
                #scores,boxes,objects,accuracy = detect_gvm_frame(crp,detection_graphm,sessm,accuracy_thresholdm,category_indexm)
                #print('done with prediction')
            else:
                pass
                #scores,boxes,objects,accuracy = detect_gvx_frame(crp,detection_graphx,sessx,accuracy_thresholdx,category_indexx)
            #send this crop to inference and get back predicted text detection (region label : predicted label)
            #detections, predictions_dict, shapes = crop_infer(crp)

            #print(scores)
            #print(boxes)
            #print(objects)

            if len(objects) == 0:
                #no predictions
                final_dct[label] = None

            elif len(objects) == 1:
                #one prediction (maybe true or maybe false prediction)
                predicted_obj = str(objects[0])
                if '_' in predicted_obj:
                    predicted_obj = str(predicted_obj.split('_')[0])
                final_dct[label] = predicted_obj

            else:
                #multiple predictions (sort acc to accuracy and take highest acc)
                original_lst = accuracy.copy()
                if len(accuracy) > 0:
                    accuracy.sort(reverse = True)

                first_ele = accuracy[0]

                idx_acc = original_lst.index(first_ele)
                predicted_obj = str(objects[idx_acc])
                if '_' in predicted_obj:
                    predicted_obj = str(predicted_obj.split('_')[0])
                final_dct[label] = predicted_obj

                
                
        return final_dct




    #write a while true loop : if final dict match with kanban  or manual pass by admin using inspection_id
    t_start_inspection = time.time()

    loop_idx_for_del = 0

    def do_del(cl_obj):
        try:
            del cl_obj
        except Exception as e:
            print("del ops")
            print(e)
    retry_list = []
    process_loop_counter = 0
    while(True):
        print("!!!!!!!!!!!!!!!!!!!!!:::: ")
        print(process_loop_counter)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!")

        



        print("Testing here")
        try:
            mp = MongoHelper().getCollection('INSPECTION')
        except Exception as e:
            message = "Cannot connect to db"
            status_code = 500
            return message,status_code


        try:
            dataset = mp.find_one({'_id' : ObjectId(inspection_id)})
            if dataset is None:
                message = "Inspection not found in inspection collection"
                status_code = 404
                return message,status_code

        except Exception as e:
            message = "Invalid inspection ID"
            status_code = 400
            return message,status_code


        is_manual_pass = dataset['is_manual_pass']

        if is_manual_pass is True:
            break
            
        #if process_loop_counter >= 3:
        #    continue

        
        final_dct = {}
        #print(full_img)
        #print(cam_list)
        #print(key_list)

        def get_pred_extreme_left_camera(p1_lst):
            for cam,r_key in zip(cam_list,key_list):
                if cam == "extreme_left_camera":
                    for f in full_img:
                        if f['cam_name'] == 'extreme_left_camera':
                            try:
                                regions = f['regions']
                                if regions != "":
                                    #print('line 399')
                                    print("inside extreme left cam")
                                    p1_lst = regions_crop_pred(regions,rch,r_key,p1_lst,8501)
                                    print("&&&&&&&&&&&&&&&")   
                                    print(p1_lst)
                                    print("&&&&&&&&&&&&&&&")
                                    var = str(inspection_id) + "_cam1"
                                    rch.set_json({var:p1_lst})
                            except Exception as e:
                                print("region not defined in extreme left camera:" + str(e) )
                                pass
                  

        def get_pred_left_camera(p2_lst):
            for cam,r_key in zip(cam_list,key_list):
                if cam == "left_camera":
                    for f in full_img:
                        if f['cam_name'] == 'left_camera':
                            try:
                                regions = f['regions']
                                if regions != "":
                                    print("inside left cam")
                                    p2_lst = regions_crop_pred(regions,rch,r_key,p2_lst,8502)
                                    var = str(inspection_id) + "_cam2"
                                    rch.set_json({var:p2_lst})
                            except Exception as e:
                                print("region not defined in left camera:" + str(e) )
                                pass

        def get_pred_middle_camera(p3_lst):
            for cam,r_key in zip(cam_list,key_list):
                if cam == "middle_camera":
                    for f in full_img:
                        if f['cam_name'] == 'middle_camera':
                            try:
                                regions = f['regions']
                                if regions != "":
                                    print("inside  middle cam")
                                    p3_lst = regions_crop_pred(regions,rch,r_key,p3_lst,8503)
                                    var = str(inspection_id) + "_cam3"
                                    rch.set_json({var:p3_lst})
                            except Exception as e:
                                print("region not defined in middle camera:" + str(e) )
                                pass  

        def get_pred_right_camera(p4_lst):
            for cam,r_key in zip(cam_list,key_list):
                if cam == "right_camera":
                    for f in full_img:
                        if f['cam_name'] == 'right_camera':
                            try:
                                regions = f['regions']
                                if regions != "":
                                    print("inside  right cam")
                                    p4_lst = regions_crop_pred(regions,rch,r_key,p4_lst,8504)
                                    var = str(inspection_id) + "_cam4"
                                    rch.set_json({var:p4_lst})
                            except Exception as e:
                                print("region not defined in right camera:" + str(e) )
                                pass  

        def get_pred_extreme_right_camera(p5_lst):
            for cam,r_key in zip(cam_list,key_list):
                if cam == "extreme_right_camera":
                    for f in full_img:
                        if f['cam_name'] == 'extreme_right_camera':
                            try:
                                regions = f['regions']
                                if regions != "":
                                    print("inside extreme right cam")
                                    p5_lst = regions_crop_pred(regions,rch,r_key,p5_lst,8505)
                                    var = str(inspection_id) + "_cam5"
                                    rch.set_json({var:p5_lst})
                            except Exception as e:
                                print("region not defined in extreme right camera:" + str(e) )
                                pass
        t1 = time.time()
        
        p1_lst = {}
        p2_lst = {}
        p3_lst = {}
        p4_lst = {}
        p5_lst = {}
        
        var = str(inspection_id) + "_cam1"
        rch.set_json({var:p1_lst})
        var = str(inspection_id) + "_cam2"
        rch.set_json({var:p2_lst})
        var = str(inspection_id) + "_cam3"
        rch.set_json({var:p3_lst})
        var = str(inspection_id) + "_cam4"
        rch.set_json({var:p4_lst})
        var = str(inspection_id) + "_cam5"
        rch.set_json({var:p5_lst})
        
        P1 = Process(target=get_pred_extreme_left_camera,args=(p1_lst,))
        P2 = Process(target=get_pred_left_camera,args=(p2_lst,))
        P3 = Process(target=get_pred_middle_camera,args=(p3_lst,))
        P4 = Process(target=get_pred_right_camera,args=(p4_lst,))
        P5 = Process(target=get_pred_extreme_right_camera,args=(p5_lst,))
        
        P1.start()
        P2.start()
        P3.start()
        P4.start()
        P5.start()

        P1.join()
        P2.join()
        P3.join()
        P4.join()
        P5.join()
        
        t2 = time.time()
        print('TIMEEEEEEEEEEEEEEEEEEEEEEEEEEE            ::  ::  ::  :: ---------    '+ str(t2-t1))
        
        var = str(inspection_id) + "_cam1"
        p1_lst = rch.get_json(var)
        var = str(inspection_id) + "_cam2"
        p2_lst = rch.get_json(var)
        var = str(inspection_id) + "_cam3"
        p3_lst = rch.get_json(var)
        var = str(inspection_id) + "_cam4"
        p4_lst = rch.get_json(var)
        var = str(inspection_id) + "_cam5"
        p5_lst = rch.get_json(var)
        
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        print(p1_lst)
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        final_dct = {}
        final_dct.update(p1_lst)
        final_dct.update(p2_lst)
        final_dct.update(p3_lst)
        final_dct.update(p4_lst)
        final_dct.update(p5_lst)

        

        t1 = time.time()
        # compare the final_dct with the actual kanban if all match break else continue  (keep updating the inspection_id key of redis with matched values)
        
        region_pass_fail = []


        def populate_results(pos,k,value):
            
            if k['part_type'] == 'IGBT':

                # if no predictions on region (either he kept part which isnt trained or network hasn't learnt that part well or he hasn't kept anythin at all) if no detections -yellow
                if value is None:
                    region_pass_fail.append( {"position":k['position'],"part_number":k['part_number'],"status":False,"result_part_number":None,"color":"yellow"} )
                else:
                    #if there is a prediction (it can be right or wrong prediction) - 
                    #HAS_PART = True
                    for part in k['part_number']:
                        if str(value) in part: #if model gave right prediction and right part is placed in location - green
                            HAS = False
                            indexx = 0
                            for indivi in region_pass_fail:
                                #print("************************************************************")
                                #print(str(indivi["position"]))
                                #print("\n")
                                #print(str(k['position']))
                                #print('\n')
                                #print(str(indivi["position"]) == str(k['position']))
                                #print("************************************************************")
                                if str(indivi["position"]) == str(k['position']):
                                    HAS = True
                                    break
                                indexx = indexx+1
                            if HAS is True:
                                region_pass_fail[indexx] = {"position":k['position'],"part_number":k['part_number'],"status":True,"result_part_number":str(value),"color":"green"}
                                break
                            else:
                                region_pass_fail.append( {"position":k['position'],"part_number":k['part_number'],"status":True,"result_part_number":str(value),"color":"green"} )
                                break
                        else: #if it cant find in array (operator placed wrong trained part in wrong position or our model gave false prediction) - red
                            #check if already exist - if pos exist in region_pass_fail then dont append else append
                            HAS = False
                            for indivi in region_pass_fail:
                                #print("************************************************************")
                                #print(str(indivi["position"]))
                                #print("\n")
                                #print(str(k['position']))
                                #print('\n')
                                #print(str(indivi["position"]) == str(k['position']))
                                #print("************************************************************")
                                if str(indivi["position"]) == str(k['position']):
                                    HAS = True
                                    break
                            if HAS is True:
                                pass
                            else:
                                region_pass_fail.append( {"position":k['position'],"part_number":k['part_number'],"status":False,"result_part_number":str(value),"color":"red"} )

            elif k['part_type'] == 'THERMOSTAT':
                #thermostat logic

                # if no predictions on region (either he kept part which isnt trained or network hasn't learnt that part well or he hasn't kept anythin at all) if no detections
                if value is None: #yellow
                    region_pass_fail.append( {"position":k['position'],"part_number":k['part_number'],"status":False,"result_part_number":None,"color":"yellow"} )
                else:
                    #if there is a prediction (it can be right or wrong prediction) - 
                    if value == "thermostat":#if model gave right prediction and right part is placed in location - green
                        region_pass_fail.append( {"position":k['position'],"part_number":k['part_number'],"status":True,"result_part_number":str(value),"color":"green"} )

                    else: #if it cant find in array (operator placed wrong trained part in wrong position or our model gave false prediction) - red 
                        region_pass_fail.append( {"position":k['position'],"part_number":k['part_number'],"status":False,"result_part_number":str(value),"color":"red"} )
            else:
                region_pass_fail.append( {"position":k['position'],"part_number":k['part_number'],"status":False,"result_part_number":None,"color":"yellow"} )
        pos_counter = {}
        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
        print(final_dct)
        print("###############################")
        for k in kanban:
         # for each prediction  final_dct = {"region1":"None","region2":"k75t60"}
            #print(key, value)
             # for each actual value
            #    print("kanban_key", k)
            for key,value in final_dct.items():
                #print(k['position'],key, value)
                pos_key = int(key.replace('region',''))
                if k['position'] == pos_key:
                    populate_results(key,k,value)
                    pos_counter[k['position']] = key
                #if k['position'] == 1 and key == "region1":
                #    populate_results(key,k,value)
                #elif k['position'] == 2 and key == "region2":
                #    populate_results(key,k,value)
                #elif k['position'] == 3 and key == "region3":
                #    populate_results(key,k,value)
                #elif k['position'] == 4 and key == "region4":
                #    populate_results(key,k,value)
                #elif k['position'] == 5 and key == "region5":
                #    populate_results(key,k,value)
                #elif k['position'] == 6 and key == "region6":
                #    populate_results(key,k,value)
                #elif k['position'] == 7 and key == "region7":
                #    populate_results(key,k,value)
                #elif k['position'] == 8 and key == "region8":
                #    populate_results(key,k,value)
                #elif k['position'] == 9 and key == "region9":
                #    populate_results(key,k,value)
                #elif k['position'] == 10 and key == "region10":
                #    populate_results(key,k,value)
                #elif k['position'] == 11 and key == "region11":
                #    populate_results(key,k,value)
                #elif k['position'] == 12 and key == "region12":
                #    populate_results(key,k,value)
                #elif k['position'] == 13 and key == "region13":
                #    populate_results(key,k,value)
                #elif k['position'] == 14 and key == "region14":
                #    populate_results(key,k,value)
                #elif k['position'] == 15 and key == "region15":
                #    populate_results(key,k,value)
                #elif k['position'] == 16 and key == "region16":
                #    populate_results(key,k,value)
                #elif k['position'] == 17 and key == "region17":
                #    populate_results(key,k,value)
                #elif k['position'] == 18 and key == "region18":
                #    populate_results(key,k,value)
                #elif k['position'] == 19 and key == "region19":
                #    populate_results(key,k,value)
                #elif k['position'] == 20 and key == "region20":
                #    populate_results(key,k,value)
                else:
                    pass
        for k in kanban:
            if k['position'] not in pos_counter:
                populate_results('region'+str(k['position']),k,None)

        #print(region_pass_fail)
        region_pass_fail = sorted(region_pass_fail, key = lambda i: i['position'])
        
        
        #print(pos_counter)
        #vendor match  - correct the vendors --- [[1,2,5],[3,4],[7,8,9],[10,11,12]] convert to [[p100,p100,p100],[abcd,abcd],[123,123,123],[l,l,l]]
        """
        tmp_vendor = []
        for vendd in vendor_match:
            k = vendd.replace(",","")
            k = int(k)
            tmp_vendor.append([k])

        last = []
        first = []
        for i in tmp_vendor:
            o = 0
            while(o<len(str(i))):
                last.append(int(str(i)[o]))
                o=o+1
            first.append(last)
            last = []

        vendor_match = []
        vendor_match = first.copy()
        """
        e = []
        f=[]
        #print(vendor_match)
        for v in vendor_match:
            
            for h in v.split(','):
                e.append(int(h))
            f.append(e)
            e  = []
                

        vendor_match = e.copy()
        value_region_acc_to_vendors = []
        sub_list = []
        for pos_list in vendor_match:                     
            for pos in pos_list:
                for region_pf in region_pass_fail:
                    if region_pf['status'] == True: #if it passed above checks

                        if region_pf['position'] == region_pf :
                            sub_list.append(str(region_pf['result_part_number']))

            value_region_acc_to_vendors.append(sub_list)

        
        IS_EVEN = True

        if len(value_region_acc_to_vendors) == len(vendor_match):
            i = 0
            while( i<len(value_region_acc_to_vendors)-1 ):

                if len(vendor_match[i]) == len(value_region_acc_to_vendors[i]):
                    pass 
                else:
                    IS_EVEN = False

                i=i+1
        

        if IS_EVEN:

            def chkList(lst): 
                res = False
                if len(lst) < 0 : 
                    res = True
                res = all(ele == lst[0] for ele in lst) 
                
                if(res): 
                    return True
                else: 
                    return False

            
            for ven,vendor_m in zip(value_region_acc_to_vendors,vendor_match):
                is_match = chkList(ven)

                if not is_match:
                    #make all pos red add a msg "vend match failed"
                    for positions in vendor_m:

                        for r_p_f in region_pass_fail:

                            if r_p_f['position'] == positions:

                                #make red in index of that
                                idx = region_pass_fail.index(r_p_f)
                                region_pass_fail[idx] = {"position":r_p_f['position'],"part_number":r_p_f['part_number'],"status":False,"result_part_number":r_p_f['result_part_number'],"color":"red","message":"vendor match failed"}
        
            t2 = time.time()
            #print('time taken to execute comparision logic....            ::  ::  ::  :: ---------    '+ str(t2-t1))


      

            
        #write to redis : key is inspection_id and value is region_pass_fail
        rch.set_json({inspection_id:region_pass_fail})
        var = str(inspection_id) + "_result"
        rch.set_json({var:"fail"})
        
        retry_list.append(region_pass_fail)
        var = str(inspection_id) + "_retry_array"
        rch.set_json({var:retry_list})
        
        
        

        cycle_time_key = str(inspection_id) + "_cycletime"
        rch.set_json({cycle_time_key: time.time() - t_start_inspection })
        #with this pass or fail


        #compare all if all status is true then break
        IS_PROCESS_END = True
        for final_check in region_pass_fail:
            if final_check['status'] is True:
                pass
            else:
                IS_PROCESS_END = False

        if IS_PROCESS_END:
            break

        
        try: do_del(mp)
        except: pass
        try: do_del(message)
        except: pass
        try: do_del(status_code)
        except: pass
        try: do_del(dataset)
        except: pass
        try: do_del(is_manual_pass)
        except: pass
        try: do_del(cam_list)
        except: pass
        try: do_del(key_list)
        except: pass
        try: do_del(region_pass_fail)
        except: pass
        try: do_del(e)
        except: pass
        try: do_del(f)
        except: pass
        try: do_del(final_dct)
        except: pass
        try: do_del(p1_lst)
        except: pass   
        try: do_del(p2_lst)
        except: pass
        try: do_del(p3_lst)
        except: pass
        try: do_del(p4_lst)
        except: pass
        try: do_del(p5_lst)
        except: pass
        try: do_del(pos_counter)
        except: pass
        try: do_del(t1)
        except: pass
        try: do_del(t2)
        except: pass
        try: do_del(P1)
        except: pass
        try: do_del(P2)
        except: pass
        try: do_del(P3)
        except: pass
        try: do_del(P4)
        except: pass
        try: do_del(P5)
        except: pass   
        try: do_del(var)
        except: pass
        try: do_del(key)
        except: pass
        try: do_del(value)
        except: pass
        try: do_del(pos_key)
        except: pass
        try: do_del(pos_list)
        except: pass
        try: do_del(k)
        except: pass
        try: do_del(pos)
        except: pass
        try: do_del(vendor_match)
        except: pass
        try: do_del(vendor_m)
        except: pass
        try: do_del(value_region_acc_to_vendors)
        except: pass
        try: do_del(sub_list)
        except: pass
        try: do_del(r_p_f)
        except: pass   

        try: gc.collect()
        except: pass
        
        #process_loop_counter = process_loop_counter + 1
        
    #outside loop : update inspection id collection with pass and end time.


    var = str(inspection_id) + "_result"
    rch.set_json({var:"pass"})

    try:
        mp = MongoHelper().getCollection('INSPECTION')
    except Exception as e:
        message = "Cannot connect to db"
        status_code = 500
        return message,status_code


    try:
        dataset = mp.find_one({'_id' : ObjectId(inspection_id)})
        if dataset is None:
            message = "Inspection not found in inspection collection"
            status_code = 404
            return message,status_code

    except Exception as e:
        message = "Invalid inspection ID"
        status_code = 400
        return message,status_code

    dataset['completedAt'] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    completedAt = datetime.datetime.strptime(dataset['completedAt'], '%Y-%m-%d %H:%M:%S')
    createdAt = datetime.datetime.strptime(dataset['createdAt'], '%Y-%m-%d %H:%M:%S')
    duration = completedAt - createdAt
    dataset['duration'] = str(duration)
    dataset['status'] = 'completed'
    dataset['is_compleated'] = True
    
    mp.update({'_id' : ObjectId(dataset['_id'])}, {'$set' :  dataset})

    #do gc collect here
    gc.collect()




#get method
def get_current_inspection_details_utils(inspection_id):
    #{eval_data}

    #inspection_id =  data['inspection_id']
    if inspection_id is None:
        message = "inspection_id not provided"
        status_code = 400
        return message,status_code

    try:
        mp = MongoHelper().getCollection('INSPECTION')
    except Exception as e:
        message = "Cannot connect to db"
        status_code = 500
        return message,status_code

    try:
        dataset = mp.find_one({'_id' : ObjectId(inspection_id)})
        if dataset is None:
            message = "Inspection not found in inspection collection"
            status_code = 404
            return message,status_code

    except Exception as e:
        message = "Invalid inspection ID"
        status_code = 400
        return message,status_code
    samp = {}
    if True:
        #samp = {}
        rch = CacheHelper()
        details = rch.get_json(str(inspection_id))
        var = str(inspection_id) + "_result"
        result = rch.get_json(var)
        samp['evaluation_data'] = details
        samp['status'] = result
        var = str(inspection_id) + "_retry_array"
        retry_array = rch.get_json(var)
        samp['retry_array'] = retry_array
        report = {}
        ## cycle time 
        cycle_time_key = str(inspection_id) + "_cycletime"
        curr_cycle_time = rch.get_json(cycle_time_key)
        report['previous_cycle_time'] = str(curr_cycle_time)
        #qty_built : total amt of gvm and gvx built for today 
        Qty_built = 0
        p = [p for p in mp.find()]
        for i in p:
            is_compleated =  i['is_compleated']
            if is_compleated is True:
                Qty_built = Qty_built + 1
        report['total_parts_scanned'] = str(Qty_built)      
        report['previous_barcode_number'] = "  "
        # Previous barcode scanned 
        if len(p) > 1:
            report['previous_barcode_number'] = p[-2]['serial_no']
        ## total 
        total_inspections = len(p) - 1
        pr = [i for i in mp.find({"is_manual_pass" : True})]
        total_manual_pass = len(pr)
        total_auto_pass = str(total_inspections - total_manual_pass)

        fpy = 0.0
        if int(total_inspections) > 0:
            fpy = float(total_auto_pass)  / float(total_inspections)
        report['auto_pass'] = total_auto_pass
        report['manual_pass'] = total_manual_pass
        report['fpy'] = fpy
        samp['reports'] = report
        
        try: del dataset,mp,message,details,var,result,report,p,pr
        except : pass
        
        gc.collect()
        
        #print(samp)
        return samp, 200
    #except:
    #    message = "error fetching inspection_id and status from redis"
    #    status_code = 400
    #    return message,status_code

        
            





#force admin pass    
def force_admin_pass(data):

    inspection_id =  data['inspection_id']
    if inspection_id is None:
        message = "inspection_id not provided"
        status_code = 400
        return message,status_code

    try:
        mp = MongoHelper().getCollection('INSPECTION')
    except Exception as e:
        message = "Cannot connect to db"
        status_code = 500
        return message,status_code


    try:
        dataset = mp.find_one({'_id' : ObjectId(inspection_id)})
        if dataset is None:
            message = "Inspection not found in inspection collection"
            status_code = 404
            return message,status_code

    except Exception as e:
        message = "Invalid inspection ID"
        status_code = 400
        return message,status_code

    
    dataset['is_manual_pass'] = True
    #dataset['is_compleated'] = True

    try:
        mp.update({'_id' : ObjectId(dataset['_id'])}, {'$set' :  dataset})
    except Exception as e:
        message = "error setting ismanualpass"
        status_code = 400
        return message,status_code
    
    message = dataset
    status_code = 200
    return message,status_code




def get_running_process(): #when someone refresh page

    try:
        mp = MongoHelper().getCollection('INSPECTION')
    except Exception as e:
        message = "Cannot connect to db"
        status_code = 500
        return message,status_code

    p = [p for p in mp.find()]

    IS_COMPLEATED = True
    dummy_coll = None

    for i in p:
        is_compleated =  i['is_compleated']

        if is_compleated is False:

            IS_COMPLEATED = False

            dummy_coll = i
            break

    if IS_COMPLEATED is False:
        return dummy_coll,200
    else:
        return {},200
    





