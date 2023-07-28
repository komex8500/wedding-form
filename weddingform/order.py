from .message_queue import MessageQueue, RequestTimeout
from linebot import LineBotApi, WebhookParser
from .line import reply_text, get_room, get_msg
from random import randint
from django.conf import settings

import sys
import traceback
import requests
import pymysql
import uuid
import json
import base64
import datetime

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)

CONN_OPTIONS = {
    'host': settings.HOST,
    'user': settings.DBUSER,
    'password': settings.PASSWORD,
    'database': settings.DATABASE,
    'connect_timeout': 30,
}


class ReOrder(Exception):
    pass


class Order:

    def __init__(self, event):
        self.event = event
        self.userId = event.source.user_id
        self.profile = line_bot_api.get_profile(self.userId)
        self.name = ''
        self.phone = ''
        self.member = 0
        self.child = 0
        self.vegetarian = 0
        self.contract = None
        try:
            self.order()
        except RequestTimeout:
            pass
        except ReOrder:
            Order(self.event)

    def order(self):
        self.ask_name()
        self.ask_phone()
        self.ask_member()
        self.ask_child()
        self.ask_vegetarian()
        self.reply(
            f'報名成功\n以下為您的報名資訊\n\n您的姓名：{self.name}\n您的聯絡電話：{self.phone}\n預計幾位出席：{self.member}\n兒童座椅張數：{self.child}\n素食人數：{self.vegetarian}\n\n如需修改報名資訊，請聯繫客服')

    def ask(self, *msg):
        self.reply(*msg)
        self.event = MessageQueue.request(get_room(self.event))
        return get_msg(self.event)

    def ask_name(self):
        msg = '請輸入您的姓名：'
        while True:
            content = self.ask(msg)
            if content == '我要報名':
                raise ReOrder
            else:
                break
        self.name = content

    def ask_phone(self):
        msg = '請輸入您的聯絡電話：'
        while True:
            content = self.ask(msg)
            if content == '我要報名':
                raise ReOrder
            else:
                break
        self.phone = content

    def ask_member(self):
        msg = '預計幾位出席呢？（含小孩）'
        while True:
            content = self.ask(msg)
            if content == '我要報名':
                raise ReOrder
            if not content.isdigit():
                msg = '請重新輸入數量（請輸入阿拉伯數字）'
            else:
                break
        self.member = int(content)

    def ask_child(self):
        msg = '兒童座椅張數？（不需要請輸入 0 ）'
        while True:
            content = self.ask(msg)
            if content == '我要報名':
                raise ReOrder
            if not content.isdigit():
                msg = '請重新輸入數量（請輸入阿拉伯數字）'
            else:
                break
        self.child = int(content)

    def ask_vegetarian(self):
        msg = '素食人數？（葷食請輸入 0 ）'
        while True:
            content = self.ask(msg)
            if content == '我要報名':
                raise ReOrder
            if not content.isdigit():
                msg = '請重新輸入數量（請輸入阿拉伯數字）'
            else:
                break
        self.vegetarian = int(content)

    def reply(self, *msg):
        reply_text(self.event, *msg)


def parse_exception(e):
    error_class = e.__class__.__name__  # 取得錯誤類型
    detail = e.args[0]  # 取得詳細內容
    cl, exc, tb = sys.exc_info()  # 取得Call Stack
    lastCallStack = traceback.extract_tb(tb)[-1]  # 取得Call Stack的最後一筆資料
    fileName = lastCallStack[0]  # 取得發生的檔案名稱
    lineNum = lastCallStack[1]  # 取得發生的行號
    funcName = lastCallStack[2]  # 取得發生的函數名稱
    errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(
        fileName, lineNum, funcName, error_class, detail)
    print(e, errMsg, flush=True)
