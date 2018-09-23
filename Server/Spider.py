from lxml import html
from jsonpath_rw import parse
import requests
import json
import re
import time


class Spider(object):
    def __init__(self, username="", password=""):
        self.username = username
        self.password = password
        self.client = requests.session()
        self.login_status = False
        self.headers = {    # 设置请求头
            # "Referer": "https://cas.gzhu.edu.cn/cas_server/login",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36" }

    def get_user_info(self):
        user_info_url = "http://jwxt.gzhu.edu.cn/jwglxt/xtgl/index_cxYhxxIndex.html"
        get_response = self.client.get(user_info_url, headers=self.headers)
        selector = html.fromstring(get_response.text)
        self.student_name = selector.xpath('/html/body/div[1]/div/div/h4/text()')[0]
        self.major_info = selector.xpath('/html/body/div[1]/div/div/p/text()')[0]

    def set_log(self, api_type="All"):
        if self.login_status:
            with open("record_file/login.log", "a") as log:
                login_time = time.strftime(" [%Y-%m-%d %H:%M:%S]\n")
                log_item = self.student_name + " " + self.username + login_time + self.major_info + " " + api_type + "\n\n"
                log.write(log_item)
        else:
            with open("record_file/login_fail.log", "a") as log:
                login_time = time.strftime(" [%Y-%m-%d %H:%M:%S]")
                log_item = self.username + login_time + "\n\n"
                log.write(log_item)

    def login(self):

        # 统一认证转跳教务系统
        login_url = "https://cas.gzhu.edu.cn/cas_server/login?service=" \
                    "http%3A%2F%2Fjwxt.gzhu.edu.cn%2Fjwglxt%2Flyiotlogin"

        get_response = self.client.get(login_url, headers=self.headers)
        html_text = get_response.text               # 获取登陆页面代码
        # cookie = get_response.cookies             # 获取cookies，使用session自动处理cookie
        selector = html.fromstring(html_text)       # 将html文件转换为xpath可以识别的结构
        target = selector.xpath('//div[@class="row btn-row"]/input/@value')     # 使用xpath从登陆页面获取提交表单所必要的字段
        lt = target[0]
        execution = target[1]

        # 构建post字典表单数据，用于提交
        form_data = {
            "username": self.username,
            "password": self.password,
            "captcha": "",
            "warn": "true",
            "lt": lt,
            "execution": execution,
            "_eventId": "submit",
            "submit": "登录"
        }

        post_response = self.client.post(login_url, data=form_data, headers=self.headers)
        if "账号或密码错误" in post_response.text:
            print("登录状态:登录失败")
            self.set_log("Fail")  # 记录失败记录
            # raise NameError("Login failed")
        else:
            self.login_status = True
            self.get_user_info()
            print("登录状态:登录成功")
            print("姓名：", self.student_name)
            print(self.major_info, "\n")
            return self.client, self.login_status

    # 抓取课表并整理数据
    def get_class_table(self, year="2018", semester="3"):
        if self.login_status is not True:
            raise NameError("This is not logged in !")
        self.set_log("获取课表")  # 写入记录

        kb_url = "http://jwxt.gzhu.edu.cn/jwglxt/kbcx/xskbcx_cxXsKb.html?gnmkdm=N2151"
        kb_data = {
            "xnm": year,         # xnm 学年 取首年
            "xqm": semester,     # xqm 学期  3 是第一学期，12 是第二学期
        }
        kb_response = self.client.post(kb_url, data=kb_data, headers=self.headers)
        kb_json = json.loads(kb_response.text)  # 将str类型的kb_response.text转换成json可识别的对象，对应为dict类型

        # 用jsonpath获取必要内容，类型为list
        name = parse('$.xsxx.XM').find(kb_json)[0].value         # 姓名
        student_id = parse('$.xsxx.XH').find(kb_json)[0].value   # 学号

        course_id = parse('$.kbList[*].kch_id').find(kb_json)    # 课程ID
        course_name = parse('$.kbList[*].kcmc').find(kb_json)    # 课程名称
        class_place = parse('$.kbList[*].cdmc').find(kb_json)    # 上课地点
        which_day = parse('$.kbList[*].xqjmc').find(kb_json)     # 星期几
        class_time = parse('$.kbList[*].jc').find(kb_json)       # 上课时间（节数）
        weeks = parse('$.kbList[*].zcd').find(kb_json)           # 周数
        teacher = parse('$.kbList[*].xm').find(kb_json)          # 教师姓名
        check_type = parse('$.kbList[*].khfsmc').find(kb_json)   # 考核类型
        # 实践课程，课表底部，单独处理
        sjk_course_name = parse('$.sjkList[*].kcmc').find(kb_json)  # 课程名称
        sjk_weeks = parse('$.sjkList[*].qsjsz').find(kb_json)       # 周数
        sjk_teacher = parse('$.sjkList[*].xm').find(kb_json)        # 教师姓名

        course_list = []
        for idx, item in enumerate(course_id):
            course = {}
            course["course_id"] = course_id[idx].value
            course["course_name"] = course_name[idx].value
            course["class_place"] = class_place[idx].value
            course["which_day"] = which_day[idx].value
            course["class_time"] = class_time[idx].value
            course["weeks"] = weeks[idx].value
            course["teacher"] = teacher[idx].value
            course["check_type"] = check_type[idx].value
            course_list.append(course)

        sjk_course_list = []
        for idx, item in enumerate(sjk_course_name):
            course = {}
            course["sjk_course_name"] = sjk_course_name[idx].value
            course["sjk_weeks"] = sjk_weeks[idx].value
            course["sjk_teacher"] = sjk_teacher[idx].value
            sjk_course_list.append(course)

        self.modify_info(self.major_info)

        student_info = {"name": name, "student_id": student_id, "college": self.college, "class": self.class_info}
        class_table = {"student_info": student_info, "course_list": course_list, "sjk_course_list": sjk_course_list}

        return class_table

    # 修改节数和周数数据，以便小程序直接调用
    def modify_data(self, year="2018", semester="3"):
        class_table = self.get_class_table(year, semester)

        set_list = set(())  # 定义空集合，记录所有不同的课程
        for item in class_table['course_list']:
            set_list.add(item["course_id"])     # 生成集合

            class_time = item['class_time']

            reg = "\d+"
            class_res = re.findall(reg, class_time)

            # 生成开始节和持续节数
            if len(class_res) == 2:
                item['class_start'] = int(class_res[0])
                item['class_last'] = int(class_res[1]) - int(class_res[0]) + 1
            else:
                item['class_start'] = int(class_res[0])
                item['class_last'] = 1

            # 转换星期几至数字
            switcher = {
                "星期一": 1,
                "星期二": 2,
                "星期三": 3,
                "星期四": 4,
                "星期五": 5,
                "星期六": 6,
                "星期日": 7,
                "星期天": 7,
            }
            item['weekday'] = switcher.get(item['which_day'], "未安排")

        # 给每种不同的课程标号，相同课程标号相同
        for item1 in class_table['course_list']:
            for item2 in set_list:
                if item1["course_id"] == item2:
                    item1["color"] = list(set_list).index(item2)

        return class_table

    # 处理学院专业班级信息
    def modify_info(self, major):
        info = major.split(" ")
        self.class_info = info[1]
        if "(" in info[0]:
            reg = "(.+)\("
            self.college = re.findall(reg, info[0])[0]
        else:
            self.college = info[0]

    # 从文件读取图书馆进馆人数
    def read_library(self):

        with open("record_file/visit_data.json", "r") as f:
            visit = json.load(f)
        return visit

    # 获取成绩数据
    def get_grage(self):
        self.set_log("获取成绩")  # 写入记录

        if self.login_status is not True:
            self.login()
            self.get_grage()
        else:
            t = time.time()
            nd = int(round(t*1000))
            grade_url = "http://jwxt.gzhu.edu.cn/jwglxt/cjcx/cjcx_cxDgXscj.html?doType=query&gnmkdm=N100801"
            data = {
                "xh_id": self.username,
                "xnm": "",
                "xqm": "",
                "_search": "false",
                "nd": nd,
                "queryModel.showCount": 100,
                "queryModel.currentPage": 1,
                "queryModel.sortName": "",
                "queryModel.sortOrder": "asc",
                "time": 0,
            }
            grade_response = self.client.post(grade_url, data=data, headers=self.headers)
            grade_json = json.loads(grade_response.text)  # 转换成json,dict类型
            # 筛选数据
            year = parse('$.items[*].xnmmc').find(grade_json)  # 学年 2017~2018
            semester = parse('$.items[*].xqmmc').find(grade_json)  # 学期 1/2
            course_id = parse('$.items[*].kch_id').find(grade_json)  # 课程代码
            course_name = parse('$.items[*].kcmc').find(grade_json)  # 课程名称
            credit = parse('$.items[*].xf').find(grade_json)  # 学分
            grade_value = parse('$.items[*].bfzcj').find(grade_json)  # 成绩分数
            grade = parse('$.items[*].cj').find(grade_json)  # 成绩
            course_gpa = parse('$.items[*].jd').find(grade_json)  # 绩点
            course_type = parse('$.items[*].kcxzmc').find(grade_json)  # 课程性质
            exam_type = parse('$.items[*].ksxz').find(grade_json)  # 考试性质 正常/补考/重修

            self.totalCount = parse('$.totalCount').find(grade_json)[0].value  # 成绩总条数

            self.grade_list = []
            for idx, item in enumerate(course_id):
                temp = {}
                temp["year"] = year[idx].value
                temp["semester"] = semester[idx].value
                temp["course_id"] = course_id[idx].value
                temp["course_name"] = course_name[idx].value
                temp["credit"] = credit[idx].value
                temp["grade_value"] = grade_value[idx].value
                temp["grade"] = grade[idx].value
                temp["course_gpa"] = course_gpa[idx].value
                temp["course_type"] = course_type[idx].value
                temp["exam_type"] = exam_type[idx].value
                self.grade_list.append(temp)
        return self.grade_list

    # 处理成绩数据
    def modify_grade(self):
        grade_list = self.get_grage()

        if self.totalCount == 0:
            grade = {"update_time": time.strftime("%Y-%m-%d %H:%M:%S"), "totalCount": self.totalCount}
            return grade
        else:
            jd_xf, xf = 0, 0

            list_year = []  # 定义空列表，有序记录所有不同的学年
            list_sem = []  # 有序记录所有不同的学年-学期

            for item in grade_list:
                if item["year"] not in list_year:
                    list_year.append(item["year"])

                xf = xf + float(item["credit"])  # 总学分，分母
                jd_xf = jd_xf + float(item["course_gpa"]) * float(item["credit"])

            GPA = round(jd_xf / xf, 2)  # 大学总绩点
            grade = {"GPA": GPA, "total_credit": xf, "update_time": time.strftime("%Y-%m-%d %H:%M:%S"), "totalCount": self.totalCount}

            # 添加 学年-学期  如2017-2018-2
            for set_item in list_year:
                for item in grade_list:
                    if item["year"] == set_item:
                        if item["semester"] == "1":
                            item["year_sem"] = item["year"] + "-1"
                            if item["year_sem"] not in list_sem:
                                list_sem.append(item["year_sem"])
                        else:
                            item["year_sem"] = item["year"] + "-2"
                            if item["year_sem"] not in list_sem:
                                list_sem.append(item["year_sem"])

            temp_sem_list = []     # 所有学期的成绩存放于一个列表
            for set_item in list_sem:
                jd_xf, xf = 0, 0

                temp_sem = {}   # 每个学期的成绩存放于一个字典
                for item in grade_list:
                    if item["year_sem"] == set_item:
                        temp_sem["year_sem"] = item["year_sem"]
                        temp_sem["year"] = item["year"]
                        temp_sem["semester"] = item["semester"]

                        xf = xf + float(item["credit"])  # 总学分，分母
                        jd_xf = jd_xf + float(item["course_gpa"]) * float(item["credit"])

                sem_gpa = round(jd_xf / xf, 2)
                temp_sem["sem_credit"] = xf  # 学期总学分
                temp_sem["sem_gpa"] = sem_gpa  # 学期绩点
                temp_sem_list.append(temp_sem)

            for sem_item in temp_sem_list:
                temp = []
                for item in grade_list:
                    if item["year_sem"] == sem_item["year_sem"]:
                        temp.append(item)
                    sem_item["grade_list"] = temp

            grade["sem_list"] = temp_sem_list
            grade["student_id"] = self.username
            grade["name"] = self.student_name
            grade["major"] = self.major_info

            return grade
