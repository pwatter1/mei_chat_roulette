import datetime
import string
import time
from django.db.models import Q
from datetime import timedelta
from django.db import connection
from sms_analyzer import models
from pymessenger.bot import Bot
from flask import Flask, request

app = Flask(__name__)
ACCESS_TOKEN = 'EAAeLx5kmojgBADM8vq0EULfJZBGPkdXhWwy4Usl3a893GmC1YH4GSZA25R6zhyocJra8LMc0HCjSc6XKatKECjMsxM2PRnJGcQ1QLtXcht43l6DRLWuZChej6Sdu7TPDARIcNjfpjpPIStLBB06I5Ssk5MvyuyYx3DMFT09cgZDZD'
VERIFY_TOKEN = 'MEITOKEN'
bot = Bot(ACCESS_TOKEN)

@app.route('/', methods=['GET', 'POST'])
def receive_message():
    if request.method == 'GET':
        # Before allowing people to message your bot, Facebook has implemented a verify token
        # that confirms all requests that your bot receives came from Facebook. 
        token_sent = request.args.get("hub.verify_token")
        return verify_fb_token(token_sent)
    else:
    # get whatever message a user sent the bot
        output = request.get_json()
        for event in output['entry']:
            messaging = event['messaging']
            for message in messaging:
                if message.get('message'):
                    #Facebook Messenger ID for user so we know where to send response back to
                    recipient_id = message['sender']['id']
                    if message['message'].get('text'):
                        response_sent_text = get_cr_response(message['message'].get('text'))
                        send_message(recipient_id, response_sent_text)
                    #if user sends us a GIF, photo,video, or any other non-text item
                    elif message['message'].get('attachments'):
                        response_sent_nontext = "Chat Roulette can't handle attachments at this time!"
                        send_message(recipient_id, response_sent_nontext)
                    else:
                        send_message(recipient_id, "Msg error!")  

    return "Message Processed" 


def send_message(recipient_id, response):
    #sends user the text message provided via input response parameter
    bot.send_text_message(recipient_id, response)
    return "success"


def verify_fb_token(token_sent):
    #take token sent by facebook and verify it matches the verify token you sent
    #if they match, allow the request, else return an error 
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


def get_cr_response(phrase):
    start = time.time()
    userstats = models.UserStatsRecord.objects.filter(user__language='en',text_messages_count__gte=10).order_by('?')[:20000]
    traversed = 0
    limit = 180

    for userstat in userstats:
        traversed += 1
       	user = models.User.objects.get(id=userstat.user_id)
        sms_logs = models.SMSLog.objects.filter(user_id=user.id, encryption_version__gt=0).order_by('datetime')
        msg_lst = []

        for log in sms_logs:
            try:
                body = log.get_decrypted_body()
                if len(body) != 0:
                    msg_lst.append([log.datetime, body, log.type])
            except Exception:
    

        response = search(phrase, msg_lst)
        if response:
            end = time.time()
            total = end - start
            retVal = "RESPONSE: "+response+"\nUSERS TRAVERSED: "+str(traversed)+"\nTIME ELAPSED /secs: "+str(total) 
            return retVal
        else:
            if traversed < limit:
                continue
            else:
                break

    # broke from loop, traversed all users
    retVal = "RESPONSE: CR could not find a match before dev's limit!\nUSERS TRAVERSED: " + str(traversed)
    return retVal

    
def search(phrase, message_list):

    num_msgs = len(message_list)

    for i in xrange(num_msgs-1):

        msg_type = message_list[i][2]
        msg_body = message_list[i][1]
        msg_time = message_list[i][0]
        
        # lose useless punctuation
        phrase = phrase.lstrip(string.punctuation)
        phrase = phrase.rstrip(string.punctuation)
        msg_body = msg_body.lstrip(string.punctuation)
        msg_body = msg_body.rstrip(string.punctuation)
        # same case and lose trailing/leading whitespace
        phrase = phrase.lower().strip()
        msg_body = msg_body.lower().strip()

        if phrase == msg_body: 
            if (msg_type == "Sent" and message_list[i+1][2] == "Inbox"):
                # reply within a day
                if (msg_time - message_list[i+1][0] < timedelta(1)):
                    return message_list[i+1][1]
            elif (msg_type == "Outgoing" and message_list[i+1][2] == "Incoming"):
                # reply within a day
                if (msg_time - message_list[i+1][0] < timedelta(1)):
                    return message_list[i+1][1]
            #elif phrase.lower() in msg_body.lower():
                    #print "DEBUG - NON EXACT: " + msg_body
                        #pass
    return None

def main():
    app.run(port=5000,threaded=True)

if __name__ == '__main__':
    app.run(port=5000,threaded=True)   



