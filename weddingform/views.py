from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse


from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage

from .line import handler, reply_text, get_msg
from .message_queue import MessageQueue
from .order import Order
from pymysql.err import IntegrityError

import sys
import traceback
import requests
import pymysql
import json

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)

CONN_OPTIONS = {
    'host': settings.HOST,
    'user': settings.DBUSER,
    'password': settings.PASSWORD,
    'database': settings.DATABASE,
    'connect_timeout': 30,
}


@csrf_exempt
def callback(request):

    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')
        handler.handle(body, signature)

    return HttpResponse()


@handler.add(MessageEvent, message=TextMessage)
def route(event):
    if MessageQueue.handle(event):
        return

    msg = get_msg(event)
    if msg == '我要參加':
        user_data = get_user(event.source.user_id)
        if user_data:
            reply_text(event, user_data)
        else:
            reply_text(event, settings.ENDPOINT_URL +
                       "/weddingform/form?uuid="+event.source.user_id)


def form(request):
    return render(request, 'form.html')


def get_user(uuid):
    try:
        with pymysql.connect(**CONN_OPTIONS) as conn, conn.cursor() as cursor:
            sql = f'''
                SELECT 
                name, 
                phone, 
                attendees, 
                additionalAttendees, 
                childSeatCount,
                omnivoreCount, 
                vegetarianCount, 
                remark
                FROM {settings.DATABASE}.user WHERE uuid = %s;
            '''
            cursor.execute(sql, (uuid,))
            user_data = dict(
                zip([col[0] for col in cursor.description], cursor.fetchone()))

            result = (
                f"以下為您的報名資訊\n\n"
                f"姓名：{user_data['name']}\n"
                f"聯絡電話：{user_data['phone']}\n"
                f"出席人數：{user_data['attendees']}\n"
                f"陪同參加者：{user_data['additionalAttendees']}\n"
                f"準備兒童座椅：{user_data['childSeatCount']}\n"
                f"葷食：{user_data['omnivoreCount']}\n"
                f"素食：{user_data['vegetarianCount']}\n"
                f"備註：{user_data['remark']}\n\n"
                f"如需修改報名資訊，請聯繫客服"
            )

            return result
    except Exception as e:
        return None
    finally:
        cursor.close()


@csrf_exempt
def create_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            uuid = data.get('uuid')
            name = data.get('name')
            phone = data.get('phone')
            attendees = data.get('attendees')
            additionalAttendeesString = data.get('additionalAttendeesString')
            childSeatCount = data.get('childSeatCount')
            omnivoreCount = data.get('omnivoreCount')
            vegetarianCount = data.get('vegetarianCount')
            with pymysql.connect(**CONN_OPTIONS) as conn:
                cursor = conn.cursor()

                # Check if the UUID already exists in the database
                select_sql = f"SELECT COUNT(*) FROM {settings.DATABASE}.user WHERE uuid = '{uuid}';"
                cursor.execute(select_sql)
                result = cursor.fetchone()
                count = result[0]
                if count > 0:
                    # If the UUID exists, perform an UPDATE operation
                    update_sql = f'''
                            UPDATE {settings.DATABASE}.user
                            SET
                                `name` = '{name}',
                                `phone` = '{phone}',
                                `attendees` = '{attendees}',
                                `additionalAttendees` = '{additionalAttendeesString}',
                                `childSeatCount` = '{childSeatCount}',
                                `omnivoreCount` = '{omnivoreCount}',
                                `vegetarianCount` = '{vegetarianCount}'
                            WHERE `uuid` = '{uuid}';
                        '''
                    cursor.execute(update_sql)
                else:
                    sql = f'''
                        INSERT INTO {settings.DATABASE}.user(
                            `uuid`,
                            `name`,
                            `phone`,
                            `attendees`,
                            `additionalAttendees`,
                            `childSeatCount`,
                            `omnivoreCount`,
                            `vegetarianCount`
                            ) VALUES (
                            '{uuid}',
                            '{name}',
                            '{phone}',
                            '{attendees}',
                            '{additionalAttendeesString}',
                            '{childSeatCount}',
                            '{omnivoreCount}',
                            '{vegetarianCount}'
                            );
                        '''
                    cursor.execute(sql)
                conn.commit()
                return JsonResponse({'message': 'User created successfully.'})
        except IntegrityError as e:
            # Handle unique constraint violation (if UUID already exists)
            parse_exception(e)
            return JsonResponse({'message': 'UUID already exists. Please provide a different UUID.'})
        except Exception as e:
            parse_exception(e)
            return JsonResponse({'message': str(e)})
        finally:
            cursor.close()


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
