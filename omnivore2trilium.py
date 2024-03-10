from omnivoreql import OmnivoreQL
from trilium_py.client import ETAPI
import datetime as DT
import hashlib
import argparse
import sys
import pathlib


def authOmnivore(key):
    omnivoreql_client = OmnivoreQL(str(key))
    # print (omnivoreql_client)
    return omnivoreql_client

def authTrilium(key):
    server_url = 'http://localhost:37840'
    ea = ETAPI(server_url, key)
    # print(ea.app_info())
    return ea

def printOmnivoreProfile(omnivoreql_client):
    print(omnivoreql_client.get_profile())

# Query the Omnivore API for and return article highlights.
def fetchArticles(omnivoreql_client, queryString, articleLimit):
    article_notes = []
    profile = omnivoreql_client.get_profile()

    articles = omnivoreql_client.get_articles(limit=articleLimit, include_content=True, query=queryString)

    username = profile['me']['profile']['username']
    # slug = articles['search']['edges'][0]['node']['slug']
    # count = count(articles['search']['edges'])
    count=0
    for item in articles['search']['edges']:
        slug = item['node']['slug']
        article = omnivoreql_client.get_article(username, slug)
        article_notes.append(buildNoteDictionary(article))
        # print (count , ": ", articles['article']['article']['highlights'])
        count+=1
    # print ("Count == ",count)
    return article_notes

# builds a dictionary object with items neededed for exporting.
def buildNoteDictionary(article):
    note = {}
    note["title"] = article['article']['article']['title']
    note["url"] = article['article']['article']['url']
    note["author"] = article['article']['article']['author']
    note["published"] = article['article']['article']['publishedAt']
    note["saved"] = article['article']['article']['savedAt']
    note["slug"] = article['article']['article']['slug']
    highlights = extractHighlights(article['article']['article']['highlights'])
    note["highlights"] = highlights
    # print (article['article']['article']['labels'])
    note["labels"] = getLabels(article['article']['article']['labels'])
    return note

# given an article, it will return a list of highlights/annotations.
def extractHighlights(highlights):
    article_highlights = []
    if highlights:
        #print ( "====================")
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
    return article_highlights

# get the article's labels
def getLabels(label_list):
    labels = ["omnivoreHighlight"]
    for label in label_list:
        labels.append(label["name"])
    return labels

def createNote(tclient, myNotes, args):
    articles_received = 0
    articles_injested = 0
    for note in myNotes:
        articles_received+=1
        slugHash = hashlib.sha256(note["slug"].encode()).hexdigest()
        note_meta = tclient.get_note(slugHash)
        if (note_meta.get("code") or args.overwrite): # code is 'none' if the note exists
            res = tclient.create_note( parentNoteId =  args.parentNoteId,
            title = note["title"],
            type="text",
            content = formatNoteContent(note),
            noteId =  slugHash
            )
            # print (res)
            addLabels(tclient, note, slugHash)
            articles_injested+=1
    return articles_received, articles_injested

# Format the content before adding it Trilium.
def formatNoteContent(note):
    content = ''
    if note["author"]:
        content+="Author: "+ note["author"]+'<br>'
    if note["published"]:
        content+="Published: "+ note["published"]+'<br>'
    content+="Saved on: "+ note["saved"]+'<br><br><br>'
    for highlight in note["highlights"]:
        content+=highlight+'<br><br>'
    content+='<br>'+note["url"]
    return content

# adding labels to a note. at minimal there will be an #omnivoreHighlight label.
def addLabels(tclient, note, noteid):
    for label in note["labels"]:
        # print ("*********************"+label)
        res = tclient.create_attribute(
            noteId=noteid,
            attributeId=hashlib.sha256(label.encode()).hexdigest(),
            type='label',
            name=label,
            value=None,
            isInheritable=False
            )
        # print (res)

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
                trilium_key = line[8:].strip()
                # print ("t key = " + trilium_key)
            elif line.startswith('omnivore:'):
                omnivore_key = line[9:].strip()
                # print ("o key - "+ omnivore_key)
    return omnivore_key, trilium_key

# builds the query string for the Omnivore Query engine. 
def queryStringBuilder(args):
    # base query string
    queryStr = "has:highlights" # "in:all AND updated:"+dateStr+".. AND has:highlights"
    # in:inbox  in:all  in:archive
    queryStr+= f" AND in:{args.archive}"
    # add date string
    if args.days:
        today = DT.date.today()
        past_date = today - DT.timedelta(days=args.days)
        queryStr+= f" AND updated:{past_date.year}-{past_date.month}-{past_date.day}.."
    
    # print ("queryStr = "+ queryStr)
    return queryStr

if __name__ == "__main__":
    list_of_choices = ["inbox", "archive", "all"]
    parser = argparse.ArgumentParser(description = 'Omnivore2Trilium: Send your Omnivore Highlights to Trilium Notes')
    parser.add_argument('-k', '--keys', type=str, 
                        help='File containing tokens to authenticate to Omnivore and Trilium.')
    parser.add_argument('-a', '--archive', type=str, choices=list_of_choices, default="all",
                        help="Extract highlights from the inbox, archive, or all. (default is all)")
    parser.add_argument('-p', '--parentNoteId', type=str, default="root",
                        help="Note ID of the parent Trilium Note. (defaults to root)")
    parser.add_argument('-d', "--days", type=int, default=0,
                        help="Number of days ago the the articles were highlighted.")
    parser.add_argument('-o', '--overwrite', action='store_true',
                        help="Overwrite content of existing note. (Erases any changes in Trilium)")
    parser.add_argument('-l', "--limit", type=int, default=10,
                        help="Limit number of articles returned by Omnivore (limit 100)")
    args = parser.parse_args()

    okey, tkey = loadKeys(args.keys)
    if okey is None or tkey is None:
        sys.exit("Error: both keys are required.")
    oclient = authOmnivore(okey)
    tclient = authTrilium(tkey)
    queryString = queryStringBuilder(args)

    myNotes = fetchArticles(oclient, queryString, args.limit)
    received, injested = createNote(tclient, myNotes, args)
    print(f'Received {received} articles from Omnivore')
    print(f'Transfered {injested} articles into Trilium')