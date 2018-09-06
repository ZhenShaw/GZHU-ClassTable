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

    def get_user_info(self):
        user_info_url = "http://jwxt.gzhu.edu.cn/jwglxt/xtgl/index_cxYhxxIndex.html"
        get_response = self.client.get(user_info_url, headers=self.headers)
        selector = html.fromstring(get_response.text)
        self.student_name = selector.xpath('/html/body/div[1]/div/div/h4/text()')[0]
        self.major_info = selector.xpath('/html/body/div[1]/div/div/p/text()')[0]

    def set_log(self):
        if self.login_status:
            with open("login.log", "a") as log:
                login_time = time.strftime(" [%Y-%m-%d %H:%M:%S]")
                log_item = self.student_name + login_time + "\n" + self.major_info + "\n\n"
                log.write(log_item)
        else:
            with open("login_fail.log", "a") as log:
                login_time = time.strftime(" [%Y-%m-%d %H:%M:%S]")
                log_item = self.username + login_time + "\n\n"
                log.write(log_item)

    def login(self):

        # 统一认证转跳教务系统
        login_url = "https://cas.gzhu.edu.cn/cas_server/login?service=" \
                    "http%3A%2F%2Fjwxt.gzhu.edu.cn%2Fjwglxt%2Flyiotlogin"
        # 设置请求头
        self.headers = {
            # "Referer": "https://cas.gzhu.edu.cn/cas_server/login",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"
        }

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
            self.set_log()  # 记录失败记录
            # raise NameError("Login failed")
        else:
            self.login_status = True
            self.get_user_info()
            print("登录状态:登录成功")
            print("姓名：", self.student_name)
            print(self.major_info, "\n")
            self.set_log()      # 记录登录记录
            return self.client, self.login_status

    # 抓取课表并整理数据
    def get_class_table(self, year="2018", semester="3"):
        if self.login_status is not True:
            raise NameError("This is not logged in !")

        kb_url = "http://jwxt.gzhu.edu.cn/jwglxt/kbcx/xskbcx_cxXsKb.html?gnmkdm=N2151"
        kb_data = {
            "xnm": year,         # xnm 学年 取首年
            "xqm": semester,     # xqm 学期  3 是第一学期，12 是第二学期
        }
        kb_response = self.client.post(kb_url, data=kb_data, headers=self.headers)
        kb_json = json.loads(kb_response.text)  # 将str类型的kb_response.text转换成json可识别的对象，对应为dict类型

        # 用jsonpath获取必要内容，类型为list
        name = parse('$.xsxx.XM').find(kb_json)[0].value        # 姓名
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

        student_info = {"name": name, "student_id": student_id}
        class_table = {"student_info": student_info, "course_list": course_list, "sjk_course_list": sjk_course_list}

        return class_table

    # 修改节数和周数数据，以便小程序直接调用
    def modify_data(self, year="2018", semester="3"):
        class_table = self.get_class_table(year, semester)

        set_list = set(())
        for item in class_table['course_list']:
            set_list.add(item["course_id"])     # 生成集合，记录所有不同的课程

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

