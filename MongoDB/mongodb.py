import pymongo
import csv
import os
from uuid import uuid4
import time


class LabDB:
    """
    必须在程序目录下调用该文件，接口目录设置位于上层
    响应代码：
    200-正常响应
    """
    def __init__(self):
        self.client = pymongo.MongoClient()
        self.db = self.client.db
        self.staff = self.db.staff
        self.slaves = self.db.slaves
        self.log = self.db.log

    def close(self):
        self.client.close()

    # del _id in db
    def del_id(self, data):
        for i in data:
            i.pop("_id")

    # 全部依据基础数据重构
    def all_rebuild(self):
        self.client.drop_database(self.db)
        self.staff_rebuild()
        self.slaves_rebuild()
        self.log_rebuild()

    '''staff-----------------------------------------------------------------'''
    def staff_rebuild(self, path=None):
        """
        人员信息重建
        依赖事件：
            path-人员csv文件地址，csv文件必须部署在MongoDB文件夹下，上层输入其
                文件名即可
        """
        if path is None:
            path = "school.csv"
        staff = self.staff
        staff.drop()
        with open("MongoDB\\"+path, encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                staff_id = row[0]
                name = row[1]
                role = row[3]
                if role == "student" or role == "staff":
                    staff.insert_one({"id": staff_id, "password": staff_id, "role": role,
                                      "name": name, "token": uuid4()})
        print("人员数据库初始化为："+str(staff.count()))

    def login_check(self, staff_id, password):
        staff = self.staff
        real_pwd = staff.find_one({"id": staff_id})["password"]
        if real_pwd == password:
            token = uuid4()
            staff.update({"id": staff_id}, {"$set": {"token": token}})
            account_set = staff.find_one({"id": staff_id})
            return account_set.pop("_id").pop("id").pop("password")

    def modify_password(self, staff_id, password):
        staff = self.staff
        staff.update({"id": staff_id}, {"$set": {"password": password}})

    def token_check(self, staff_id, token):
        staff = self.staff
        if token == staff.find_one({"id": staff_id})["token"]:
            return True
        else:
            return False

    '''slaves----------------------------------------------------------------'''

    def slaves_rebuild(self):
        """
        对从机信息的重建
        依赖事件：
            Devices目录下的从机子文件夹
            子文件夹中的实验文件
            此函数下预设的设备ip表
            实验文件地址在server层重构，数据库中不建立文件地址
        """
        # 设备映射表
        ip_dir = {
            # "Arudino":[".??","192.168.1.101"],
            "CC3200": ["out", "192.168.1.102"],
            "RaspberryPi": ["py", "192.168.1.103"],
            # "STM32":["192.168.1.104"]
        }

        # 抛弃数据库中从机表
        slaves = self.slaves
        slaves.drop()

        # 数据建立
        kinds = next(os.walk('Devices'))[1]  # 获取目录中设备种类
        count = 0
        for kind in kinds:
            if kind in ip_dir.keys():  # 设备ip映射表中存在的设备才能继续读取实验文件
                # 构建实验文件列表
                experiment_list = []
                experiments = next(os.walk('Devices\\'+str(kind)))[2]  # 获取实验文件
                for experiment in experiments:
                    name, extension = experiment.split(".")  # 切割实验文件名
                    if ip_dir[kind][0] == extension and name != "test":  # 略过用户测试文件
                        experiment_list.append({"name": name})
                # 加入设备ip
                for ip in ip_dir[kind][1:]:  # 设定id和IP
                    count += 1
                    slaves.insert({"id": count, "ip": ip, "kind": kind,
                                   "experiments": experiment_list, "state": False})
        print("从机数据库初始化为："+str(slaves.count()))

    def slaves_get(self):
        slaves = self.slaves
        data = list(slaves.find())
        self.del_id(data)
        return data

    def slave_state_update(self, slave_id):
        slaves = self.slaves
        slave_state = slaves.find_one({"id": slave_id})["state"]
        slaves.update({"id": slave_id}, {"$set": {"state": not slave_state}})

    '''log-------------------------------------------------------------------'''

    # 抛弃日志表
    def log_rebuild(self):
        log = self.log
        log.drop()
        print("日志数据库初始化为:"+str(log.count()))

    # 日志信息插入
    def log_insert(self, staff_id, slave_id, action, message):
        log = self.log
        log.insert({"staff_id": staff_id, "slave_id": slave_id, "action": action,
                    "message": message, "time": time.time()})

    # 获取指定用户实验操作日志
    def log_get_staff(self, staff_id):
        log = self.log
        data = list(log.find({"staff_id": staff_id}))
        if len(data) == 0:
            return
        else:
            self.del_id(data)
            return data

    # 获取指定设备从机日志
    def log_get_slave(self, slave_id):
        log = self.log
        data = list(log.find({"slave_id": slave_id}))
        if len(data) == 0:
            return
        else:
            self.del_id(data)
            return data

    def log_get_all(self):
        data = list(self.log.find())
        if len(data) == 0:
            return
        else:
            self.del_id(data)
            return data

    # 获取所有日志
    def log_get(self, token, staff_id, slave_id):
        pass
