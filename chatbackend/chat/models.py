from django.db import models




class Message(models.Model):
    room_id = models.CharField(max_length=200)
    sender = models.IntegerField()
    receiver = models.IntegerField()
    name = models.CharField(max_length=200)
    message = models.CharField(max_length=1000)
    timestamp = models.DateTimeField(auto_now_add=True)

