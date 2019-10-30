#!/usr/bin/env python
__author__ = 'cloud'
#for mapathon
import urllib2, datetime, time, socket, logging,os
from bs4 import BeautifulSoup
from retry import retry
import smtplib
from email.mime.text import MIMEText
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import pandas as pd
from multiprocessing import Pool

BASE_URL = "http://www.openstreetmap.org"
REQUEST_RANGE = "/api/0.6/changesets?display_name={0}&time={1},{2}"
REQUEST = "/api/0.6/changesets?display_name={0}"
# users = []
DATE = "{year}-{month}-{day}T00:00:00+8"
#end_date_string = "2016-05-17T23:59:59+8"
# COMMENT_TAGS = ['newbie']
REQUEST_CHANGESET = "/api/0.6/changeset/{0}/download"
yesterday = datetime.datetime.now() - datetime.timedelta(1)
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
OUTNAME = ""
daterange = None



class User:
    username = ""
    def __init__(self,username):
        self.username = username
        self.changesets_id = []
        self.created = 0
        self.modified = 0
    def __str__(self):
        return self.username

    def get_all_changes(self):
        for changeset_id in self.changesets_id:
            print changeset_id
            print "checking " + changeset_id + "..."
            req = BASE_URL + REQUEST_CHANGESET.format(changeset_id)
            response = urlopen_with_retry2(req)
            try:
                raw_xml = response.read()
                parsed_xml = BeautifulSoup(raw_xml,'html.parser')
            except:
                parsed_xml = BeautifulSoup()
            created = parsed_xml.find_all("create")
            modified = parsed_xml.find_all("modify")

            self.node_in_way = list() # collate all created node in a list

            # get all nodes associated with a way and add to list
            for create in created:
                if len(create.find_all("way")) != 0:
                    nodes = create.find_all("nd")
                    for node in nodes:
                        self.node_in_way.append(node['ref'])

            # get all nodes not in a way and count them individually
            self.count_nodes = 0
            self.count_ways = 0
            for create in created:
                # Ill just use try
                if create.find("node"):
                    # print create.node["id"]
                    if not create.node["id"] in self.node_in_way:
                        print create.node["id"]
                        self.count_nodes += 1
                elif create.find("way"):
                    self.count_ways += 1


            total_created = self.count_ways + self.count_nodes
            print "created: {}".format(total_created)
            print "modified: {}".format(len(modified))
            print "\n"
            self.created += total_created
            self.modified += len(modified)

            #   if len(tags) >= 2:
            #       # print "MULTIPLE TAGS"
            #       if tags[-2]['k'] == "addr:province" and tags[-1]['k'] == "building":
            #           area = tags[-2]['v']
            #           print 'area: ' + area

            #           # print 'prov: ' + prov
            #           if area == prov or area == prov.lower():
            #               try:
            #                   self.buildings.append(create.way['id'])
            #                   print "[created]Success getting " + create.way['id']
            #               except TypeError, e:
            #                   print "Type Error, no 'way' tag"
            # for modified_building in modified_buildings:
            #   tags = modified_building.find_all('tag')
            #   for tag in tags:
            #       if tag['k'] == 'building':
            #           try:
            #               self.modified_buildings.append(modified_building.way['id'])
            #               print "[modified]Success getting " + modified_building.way['id']
            #           except TypeError:
            #               print "TypeError"

            print "done at " + changeset_id
        # print self.buildings

    def get_number_of_created(self):
        return self.created
    def get_number_of_modified(self):
        return self.modified

@retry(Exception, tries=4, delay=3, backoff=2)
def urlopen_with_retry(url):
    return urllib2.urlopen(url)

@retry(Exception, tries=5, delay=3, backoff=2)
def urlopen_with_retry2(url):
    return urllib2.urlopen(url)

#returns XML of the request between the time_range
def osm_query_range(user,start=None,end=None):
    if start != None:
        req = REQUEST_RANGE.format(user,start,end)
        print "TRYING " + req
        response = urlopen_with_retry(BASE_URL + req)
        raw_xml = response.read()
        parsed_xml = BeautifulSoup(raw_xml, 'html.parser')
        print "SUCCESS " + req
        return parsed_xml


    else:
        pass

def string_to_date(datestring):
    #in this format "2016-03-14T00:00:00Z"
    year = int(datestring[0:4])
    month = int(datestring[5:7])
    day = int(datestring[8:10])
    hour = int(datestring[11:13])
    minute = int(datestring[14:16])
    secs = int(datestring[17:19])
    #print year, month, day, hour, minute, secs
    return datetime.datetime(year=year,month=month,day=day,hour=hour,minute=minute,second=secs)

#get all changesets and store them into user.changesets_id
def get_all_changesets(user,daterange):
    yesterday = datetime.datetime.now() - datetime.timedelta(1)
    day, month, year = yesterday.day, yesterday.month, yesterday.year
    if datetime.datetime.now().weekday() == 0:
        start_date = datetime.datetime.now() - datetime.timedelta(3)
        s_day, s_month, s_year = start_date.day, start_date.month, start_date.year
        #START_DATE = DATE.format(year=s_year,month="%02d"%s_month,day="%02d"%s_day)
    else:
        s_day, s_month, s_year = yesterday.day, yesterday.month, yesterday.year

    daily = False
    if daily:
        today = datetime.datetime.now()
        day, month, year = today.day, today.month, today.year
        START_DATE = DATE.format(year=year,month="%02d"%month,day="%02d"%day) #for everyday running
        end_date_string = "{year}-{month}-{day}T23:59:59+8".format(year=year,month="%02d"%month,day="%02d"%day)

    else:
        start = daterange[0].strip().split('/')
        end = daterange[1].strip().split('/')

        START_DATE = DATE.format(year=start[2],month=start[0],day=start[1])
        end_date_string = DATE.format(year=end[2],month=end[0],day=end[1])

    original_start = string_to_date(START_DATE)
    # end_date = string_to_date(end_date_string)
    end_date = end_date_string
    print end_date

    #while the first date is not yet equal to specified start
    while True:
        xml_result = osm_query_range(user,START_DATE,end_date_string)
        changesets = xml_result.find_all('changeset')

        #if no more results between the end and start
        if len(changesets) == 0 or end_date_string == changesets[-1]["closed_at"]:
            break

        else:
            end_date_string = changesets[-1]["closed_at"]
            end_date = string_to_date(end_date_string)
            #print end_date_string
            if original_start >= end_date:
                break
            for changeset in changesets:
                user.changesets_id.append(changeset["id"])
                #to catch empty comments
                # try:
                #   comment = get_comment(changeset)
                #   if any (tag in comment for tag in COMMENT_TAGS):
                #       user.changesets_id.append(changeset["id"])
                # except TypeError:
                #   print "Empty comment at id="+changeset["id"]

#get comment of the changeset
def get_comment(changeset):
    tags = changeset.find_all('tag')
    for tag in tags:
        if tag['k'] == 'comment':
            return tag['v']

def output(users,email):
    if datetime.datetime.now().weekday() == 0:
        friday = yesterday - datetime.timedelta(2)
        yesterday_string = friday.strftime("%Y-%m-%d") + " to " + yesterday.strftime("%Y-%m-%d")
    else:
        yesterday_string = yesterday.strftime("%Y-%m-%d")
    output_filename = "results_mapathon.txt"
    results_dir = os.path.join(DIR_PATH,"results_mapathon")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    output_file = os.path.join(results_dir,output_filename)
    csvpath = os.path.join(results_dir,'results.csv')

    # Write a nicely formatted output
    dics = []
    for user in users:
        dic = {}
        dic['name'] = user.username
        dic['created'] = user.get_number_of_created()
        dic['modified'] = user.get_number_of_modified()
        dics.append(dic)
    df = pd.DataFrame(dics)
    df.to_csv(csvpath,index=False)

    with open(output_file,"w") as f:
        for user in users:
            f.write(user.username + ",created:" + str(user.get_number_of_created()) +",modified:"+str(user.get_number_of_modified())+"\n")
    send_mail(csvpath,email)

def send_mail(output_file,email):
    msg = MIMEMultipart()

    # to = "feye@noah.dost.gov.ph"  #email address to send to.
    to = email
    msg['Subject'] = "Mapathon Results"
    # msg['Subject'] = 'Running Total {}'.format(datetime.datetime.now().strftime("%Y-%m-%d"))
    msg['From'] = "noahdev@up.edu.ph"
    msg['To'] = to
    body = "This is an autogenerated email. Do not reply."

    # Add body to email
    msg.attach(MIMEText(body, "plain"))

    # Adding attachment
    # Open file in binary mode
    with open(output_file, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email    
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    filename = output_file.split('/')[-1]
    part.add_header(
        "Content-Disposition",
        "attachment; filename= {}".format(filename),
    )

    # Add attachment to message and convert message to string
    msg.attach(part)
    text = msg.as_string()

    s = smtplib.SMTP('smtp.gmail.com',587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login("devnoah123@gmail.com","noah12345")
    s.sendmail("devnoah123@gmail.com",to,text)
    # s.sendmail("devnoah123@gmail.com",to2,msg.as_string())

    #s.sendmail("devnoah123@gmail.com","ebmalicdem@cxsmedia.com",msg.as_string())
    s.quit()

def csv_to_list(csvpath):
    print(csvpath)
    with open(csvpath,'rb') as f:
        print(f.readline())
        return f.readlines()

def mp_get(user):
    print user
    user = user.replace(" ", "%20")
    new_user = User(user)
    # users.append(new_user)

    try:
        get_all_changesets(new_user,daterange)
        new_user.changesets_id = list(set(new_user.changesets_id))
        new_user.get_all_changes()
    except Exception as e:
        print(e)
        new_user.created = "error"
        new_user.modified = "error"
    else:
        print "total created: {}".format(new_user.get_number_of_created())
        print "total modified: {}".format(new_user.get_number_of_modified())
    return new_user


def main2(usernames,drange,email):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    fname = os.path.join(DIR_PATH,"logs/count.log")
    handler = logging.FileHandler(fname)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    logger.info("STARTED:"+datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+8"))
    

    # Update global
    global daterange
    daterange = drange

    pool = Pool(4)
    users = []
    print(usernames)
    for i in pool.imap(mp_get,usernames):
        users.append(i)

    # for user in usernames:
        # print user
        # user = user.replace(" ", "%20")
        # new_user = User(user)
        # users.append(new_user)

        # try:
        #     get_all_changesets(new_user,daterange)
        #     new_user.changesets_id = list(set(new_user.changesets_id))
        #     new_user.get_all_changes()
        # except Exception as e:
        #     print(e)
        #     new_user.created = "error"
        #     new_user.modified = "error"
        # else:
        #     print "total created: {}".format(new_user.get_number_of_created())
        #     print "total modified: {}".format(new_user.get_number_of_modified())
        # print len(new_user.changesets_id)
        # finally:
    output(users,email)


    logger.info("ENDED :"+datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+8"))

if __name__ == "__main__":
    usernames = ["arnalielsewhere","cloud5" ]#"larissealmi", "ChrisChubs", "Thenahs75", "RSCOpenMaps", "BGMH", "jhansel_feutech", "Kendel", "sgmtesalona", "Densho123", "affenhaus", "mpsapuay", "rehama", "nastan03", "dbcristobal", "Snibb", "tencurse", "htarriola", "jvmanikan", "neilrg", "jocontreras77", "hjtejuco", "kimdiwa", "DaleDP"]
    with open('users.csv','r') as f:
        usernames = f.read().split('\n')
    daterange = ['08/12/2019','09/15/2019']
    email = "monica.mendoza@younggeographers.org"
    # email = "nhett258@gmail.com"
    start = datetime.datetime.now()
    main2(usernames,daterange,email)
    end = datetime.datetime.now()
    print str(end-start)
