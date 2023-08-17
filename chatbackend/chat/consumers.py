# chat/consumers.py
import datetime
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from .models import Message
from pymongo import MongoClient
from bson import json_util
from bson.json_util import dumps,ObjectId
import pandas as pd
from channels.db import database_sync_to_async
client = MongoClient('localhost',27017)
print("connection success",client)
db = client.mongodbSchema

class ChatConsumer(WebsocketConsumer):

    # def get_name(self):
    #     return User.objects.all()[0].name

    def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = 'chat_%s' % self.user_id
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()
        messages = self.retrieve_messages()
        js = json.dumps(messages, default=json_util.default)
        self.send(text_data=js)

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )
        print("disconnected")

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)


        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'content':text_data_json["message"],
                 'user':text_data_json['name'],
                 'usertoken':text_data_json['user'],
                 'timestamp':datetime.datetime.utcnow()
            }
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event['content']
        name = event['user']
        user = event['usertoken']
        # Send message to WebSocket
        data = {
            'content': message,
            'user':name,
            'usertoken':user,
            'timestamp': datetime.datetime.utcnow()
        }
        js = json.dumps(data, default=json_util.default)
        self.send(text_data=js)

    def retrieve_messages(self):
        try:
            messages = list(db.chat_message.find({"room":self.room_name},{"room":0,"_id":0,}))
        except:
            messages  =[]
        return messages



class ChatMessage(WebsocketConsumer):

    # def get_name(self):
    #     return User.objects.all()[0].name

    def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.user = self.scope['url_route']['kwargs']['user']
        self.room_group_name = 'chat_%s' % self.room_id

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()
        users = db.users_online.insert_one({"user":str(self.user)})
        dele = db.notification.delete_many({"receiver": str(self.user), "varient": self.room_id,"type":"chat"})
        messages = self.retrieve_messages()
        js = json.dumps(messages, default=json_util.default)
        self.send(text_data=js)

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )
        users = db.users_online.delete_many({"user": self.user})

    # Receive message from WebSocket
    def receive(self, text_data):
        user_group = ''
        text_data_json = json.loads(text_data)
        message_store = Message.objects.create( room_id=self.room_id,
                                                sender=int(self.user)
                                               ,message=text_data_json['message'],
                                                receiver=int(text_data_json['receiver']),
                                                name=text_data_json['name']
                                                )
        if db.users_online.find({"user":str(text_data_json['receiver'])}).count() <= 0:
            dele = db.notification.delete_many({"receiver":str(text_data_json['receiver']),"varient":self.room_id})
            data = db.notification.insert_one({"sender":str(self.user),"receiver":str(text_data_json['receiver']),"varient":self.room_id,
                                               "date": datetime.datetime.now(), "type": 'chat'})
            try:
                user = list(db.myapp_customuser.find({"id": text_data_json['receiver']}))
                user_group = user[0]['user_group']
            except:
                user_group=''
            try:
                noti = db.notificationCount.update({"usergroup":user_group}, {"$inc": {"count": 1}})
                if noti.nMatched == 0:
                    noti = db.notificationCount.insert({"usergroup":user_group , "count": 1})
            except:
                noti = db.notificationCount.insert({"usergroup":user_group, "count": 1})
        else:
            pass
        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {    'type': 'chat_message',
                 'sender':int(self.user),
                 'message':text_data_json['message'],
                 'name':text_data_json['name'],
                 'receiver':int(text_data_json['receiver']),
                 'timestamp':datetime.datetime.utcnow()
            }
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']
        sender = event['sender']
        name = event['name']
        receiver = event['receiver']

        # Send message to WebSocket
        data = {
            'sender':int(sender),
            'message':message,
            'name':name,
            'receiver':int(receiver),
            'timestamp': datetime.datetime.utcnow()
        }
        messages = self.retrieve_messages()
        js = json.dumps(messages, default=json_util.default)
        self.send(text_data=js)

    def retrieve_messages(self):
        try:
            users = []
            user_list = []
            messages = list(db.chat_message.find({"room_id":self.room_id,'$or':[{"sender":int(self.user)},
                                {"receiver":int(self.user)}]},{"room_id":0,"_id":0,"id":0}).sort("timestamp",-1))
            message = list(db.chat_message.find({"room_id": self.room_id, '$or': [{"sender": int(self.user)},
                                                                                   {"receiver": int(self.user)}]},
                                                 {"room_id": 0, "_id": 0, "id": 0}))
            for i in messages:
                if i['sender'] == int(self.user) and int(i['receiver']) not in users:
                    users.append(int(i['receiver']))
                    if db.myapp_customuser.find({"id":int(i['receiver'])}).count() >0:
                        user = list(db.myapp_customuser.find({"id":int(i['receiver'])}))
                        print(users)
                        name = user[0]['first_name'] + " " +user[0]['last_name']
                        avatar =user[0]['first_name'][0] + user[0]['last_name'][0]
                        user_list.append({"user":name,"id":int(i['receiver']),"avatar":avatar,"message":"you:"+i['message'],"timestamp":i['timestamp']})
                elif i['receiver'] == int(self.user) and int(i['sender']) not in users:
                    users.append(int(i['sender']))
                    if db.myapp_customuser.find({"id":int(i['sender'])}).count() >0:
                        user = list(db.myapp_customuser.find({"id":int(i['sender'])}))
                        name = user[0]['first_name'] + " " +user[0]['last_name']
                        avatar =user[0]['first_name'][0] + user[0]['last_name'][0]
                        user_list.append({"user":name,"id":int(i['sender']),"avatar":avatar,"message":i['message'],"timestamp":i['timestamp']})
        except:
            user_list  =[]
            message = []
        return {"user_list":user_list,"message":message}