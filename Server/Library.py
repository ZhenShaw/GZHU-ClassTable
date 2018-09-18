# coding=utf-8
from lxml import html
import requests
import re
import time
import json


class Library(object):
    def __init__(self):
        self.library_visit = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_0) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"
        }

    # 爬取进馆统计页面
    def get_visit(self):
        login_url = "http://lib.gzhu.edu.cn:8080/bookle/goLibTotal/index"
        view_response = requests.get(login_url, headers=self.headers)
        html_text = html.fromstring(view_response.text)
        total_view = html_text.xpath('//*[@id="total"]')[0].text

        total = re.findall("\d+", total_view)[0]

        college = html_text.xpath('//*[@id="view"]/table/tr/td[1]')
        amount = html_text.xpath('//*[@id="view"]/table/tr/td[2]')
        visit = html_text.xpath('//*[@id="view"]/table/tr/td[3]')
        average = html_text.xpath('//*[@id="view"]/table/tr/td[4]')

        college_list = []
        for i, item in enumerate(college):
            temp = []
            temp.append(college[i].text)
            temp.append(amount[i].text)
            temp.append(visit[i].text)
            temp.append(average[i].text)

            college_list.append(temp)

        self.library_visit = {"total": total, "update_time": time.strftime("%Y-%m-%d %H:%M:%S"), "college_list": college_list}

        # 存入本地文件
        with open("record_file/visit_data.json", "w") as visit:
            json.dump(self.library_visit, visit)

    # 设置定时器，15min更新一次
    def timer(self):
        print("启动定时任务")
        hour = int(time.strftime("%H"))
        self.get_visit()

        while 1:
            if 0 <= hour < 6:
                time.sleep(3600)
            else:
                while hour >= 6:
                    time.sleep(900)      # 15min执行一次
                    self.get_visit()
                    print(time.strftime("%Y-%m-%d %H:%M:%S"))


# if __name__ == "__main__":
print("启动")
run = Library()
run.timer()

