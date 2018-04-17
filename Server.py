#!/usr/bin/env python
#coding:utf-8

import asyncio
import websockets
import pymongo
import time
import modbushandle
import Raspi
from bson import json_util as jsonb

'''登录操作'''
def check_account(message):
    id=message["id"]
    password=message["password"]
    account_set=account.find({"id":id})
    if account_set==None:
        data={"code":"101","mes":"账户登录：错误，不存在账户","data":None}
    else:
        if account_set["password"]!=password:
            data={"code":"102","mes":"账户登录：错误，密码与账号不符","data":None}
        else:
            data={"code":"100","mes":"账户登录：成功","data":account_set}
    print("message:"+message+"data:"+str(data))
    return data

'''改密操作'''
def modify_password(message):
    id=message["id"]
    password=message["password"]
    account.update({"id":id},{"$set":{"password":password}})
    data={"code":"200","mes":"密码修改：成功","data":None}
    print("message:" + message + "data:" + str(data))
    return data

'''获取信息'''
def get_info(message):
    flag=message["flag"]
    if flag=="slaves":
        data={"code":"300","mes":"获取信息：slaves，成功","data":db.slaves.find()}
    elif flag=="log":
        id=message["id"]
        data={"code":"301","mes":"获取信息：log，成功","data":db[id].log.find().sort("time",pymongo.DESCENDING).limit(10)}
    else:
        data={"code":"302","mes":"获取信息：标识错误！","data":None}
    print("message:" + message + "data:" + str(data))
    return data

def save_file(file):
    bin_file=open(file["name"],"wb")
    bin_file.write(file["file"])
    bin_file.close()

'''操作记录日志'''
def db_log(id, data):
    db[id]["log"].insert_one({"time":time.time(),"data":data})

'''设备操作：对于设备相关，需要在此修改'''
def operate(message):
    id=message["id"]
    slave = message["slave"]
    flag=message["flag"]
    if flag=="upload":
        save_file(message["file"])
        db.slaves.update({"name":slave["name"]},{"$set":{"user_experiment":message["file"]["name"]}})
        data = {"code": "400", "mes":"上传文件：成功","data": db.slaves.find()}
        db_log(id,data["mes"])
    if flag=="start":
        experiment=message["experiment"]
        slave_kind=message["slave"]["kind"]
        slave_name=message["slave"]["name"]
        if slave_kind=="RaspberryPi":
            data={"code":"401","mes":slave_name+"从机运行程序："+str(Raspi.transport()),"data":None}
        elif slave_kind=="CC3200":
            data={"code":"402","mes":slave_name+"从机运行程序：","data":None}
        elif slave_kind=="Arduino":
            data = {"code": "403", "mes":slave_name+ "从机运行程序：", "data": None}
        elif slave_kind=="STM32":
            data = {"code": "404", "mes": slave_name+"CC3200从机运行程序：", "data": None}
    if flag=="modbus":
        modbus_res=modbushandle.Master(device, modbus["function_id"], modbus["starting_address"], modbus["quantity_x"], modbus["output_value"])
        data={"code":100,"mes":{"modbus_res":modbus_res}}
        db_log(log_id, {"mode":mode, "modbus":modbus, "modbus_res":modbus_res})
    print("message:" + message + "data:" + str(data))
    return data

async def Server(websocket, path):
    mode=(path.split("="))[1]
    if mode=="login":
        data=check_account(jsonb.loads(await websocket.recv()))
    elif mode=="modify":
        data=modify_password(jsonb.loads(await websocket.recv()))
    elif mode=="info":
        data = get_info(jsonb.loads(await websocket.recv()))
    elif mode=="operate":
        data=operate(jsonb.loads(await websocket.recv()))
    else:
        data={"code":"001","mes":"路径错误","data":None}
    await websocket.send(jsonb.dumps(data, ensure_ascii=False))

if  __name__=="__main__":

    client = pymongo.MongoClient()
    db = client.hducloud
    account = db.account

    wsServer = websockets.serve(Server, 'localhost', 80)
    asyncio.get_event_loop().run_until_complete(wsServer)
    asyncio.get_event_loop().run_forever()