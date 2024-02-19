from omnivoreql import OmnivoreQL
from trilium_py.client import ETAPI
import datetime as DT
import hashlib
import argparse
import sys
import pathlib


def auth_omnivore(key):
    omnivoreql_client = OmnivoreQL(str(key))
    # print (omnivoreql_client)
    return omnivoreql_client

def auth_trilium(key):
    server_url = 'http://localhost:37840'
    ea = ETAPI(server_url, key)
    #print(ea.app_info())
    return ea

def print_profile(omnivoreql_client):
    print(omnivoreql_client.get_profile())

def fetch_articles(omnivoreql_client):
    #articles = omnivoreql_client.get_articles()
    #print(articles["search"])
    article_notes = []
    profile = omnivoreql_client.get_profile()

    #todo: create a query string builder
    today = DT.date.today()
    week_ago = today - DT.timedelta(days=7)
    year = week_ago.year
    month = week_ago.month
    day = week_ago.day
    print ("day of the day " + str(day))
    dateStr = str(year)+"-"+str(month)+"-"+str(day)
    qstr = "in:all AND updated:"+dateStr+".. AND has:highlights"
    articles = omnivoreql_client.get_articles(limit=5, include_content=True, query=qstr)

    username = profile['me']['profile']['username']
    # slug = articles['search']['edges'][0]['node']['slug']
    # count = count(articles['search']['edges'])
    count=0
    for item in articles['search']['edges']:
        slug = item['node']['slug']
        article = omnivoreql_client.get_article(username, slug)
        article_notes.append(note_dict(article))
        #print (count , ": ", articles['article']['article']['highlights'])
        count+=1
    print ("Count == ",count)
    return article_notes

# builds a dictionary object with items neededed for exporting.
def note_dict(article):
    #print(article)
    note = {}
    note["title"] = article['article']['article']['title']
    note["url"] = article['article']['article']['url']
    note["author"] = article['article']['article']['author']
    note["slug"] = article['article']['article']['slug']
    highlights = extract_highlights(article['article']['article']['highlights'])
    note["highlights"] = highlights
    #print (article['article']['article']['labels'])
    note["labels"] = get_labels(article['article']['article']['labels'])
    #print("Extracted highlights:")
    #print(note["highlights"])
    print(note)
    return note

# given an article, it will return a list of highlights/annotations.
def extract_highlights(highlights):
    article_highlights = []
    if highlights:
        #print ( "====================")
        #print (highlights)
        for highlight in highlights:
            #print (highlight)
            #print (highlight["quote"])
            article_highlights.append(highlight["quote"])
            if highlight["annotation"]:
                #to-do: add an option to delilinate between quotes and annotations. 
                # print (highlight["annotation"])
                article_highlights.append(highlight["annotation"])
        #print ( "====================")
        #print (highlight["annotation"])
    #else:
    #    print ("Empty")
    return article_highlights

def get_labels(label_list):
    labels = ["omnivoreHighlight"]
    for label in label_list:
        labels.append(label["name"])
    
    return labels

def createNote(tclient, myNotes):
    # print(tclient.app_info())
    for note in myNotes:
        # print ("SLUG - "+note["slug"])
        slugHash = hashlib.sha256(note["slug"].encode()).hexdigest()
        # print ("SLUG hash - "+slugHash)
        res = tclient.create_note( parentNoteId = "ED7I5lTmim3o",
        title = note["title"],
        type="text",
        content = formatNoteContent(note),
        noteId =  slugHash
        )
        print (res)
        addLabels(tclient, note, slugHash)

def formatNoteContent(note):
    content = ''
    if note["author"]:
        content+="author: "+ note["author"]+'<br><br><br>'
    for highlight in note["highlights"]:
        content+=highlight+'<br><br>'
    content+='<br>'+note["url"]
    return content

# adding labels to a note. at minimal there will be an #omnivoreHighlight label.
def addLabels(tclient, note, noteid):
    for label in note["labels"]:
        print ("*********************"+label)
        res = tclient.create_attribute(
            noteId=noteid,
            attributeId=hashlib.sha256(label.encode()).hexdigest(),
            type='label',
            name=label, #.replace(' ', ''),
            value=None,
            isInheritable=False
            )
        print (res)

# Method loads keys from file. Each key needs the format:
# omnivore:omnivore_key
# trilium:trilium_key
# The method will remove the prefix and return (omnivore_key, trilium_key)
def loadKeys(fileName):
    omnivore_key = None
    trilium_key = None
    if pathlib.Path(fileName).is_file():
        keyFile = open(fileName, 'r')
        lines = keyFile.readlines()

        for line in lines:
            if line.startswith('trilium:'):
                # print ("trilium key - "+line)
                trilium_key = line[8:].strip()
                # print ("t key = " + trilium_key)
            elif line.startswith('omnivore:'):
                # print ("omnivore key - "+line)
                omnivore_key = line[9:].strip()
                # print ("o key - "+ omnivore_key)
    return omnivore_key, trilium_key


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Omnivore2Trilium: Send your Omnivore Highlights to Trilium Notes')
    parser.add_argument('-k', '--keys', type=str, 
                        help='File containing tokens to authenticate to Omnivore and Trilium.')
    args = parser.parse_args()

    okey, tkey = loadKeys(args.keys)
    if okey is None or tkey is None:
        sys.exit("Error: both keys are required.")
    oclient = auth_omnivore(okey)
    tclient = auth_trilium(tkey)
    #print (tclient)
    #print_profile(oclient)
    myNotes = fetch_articles(oclient)
    createNote(tclient, myNotes)