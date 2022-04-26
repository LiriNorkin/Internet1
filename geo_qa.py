import queue
import time
import sys
import requests
import re
import traceback
import lxml.html
import rdflib

### PART 1: Crawler & Extraction from infobox to ontology


start = time.time()

visited = set()
g = rdflib.Graph()
url_queue = queue.Queue() # queue of urls: (Type, URL), Type = Country / President / Prime_Minister

### added /wiki to prefix
prefix = "http://en.wikipedia.org"
ontology_prefix = "http://example.org/"
url_source = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"

data_labels = ["president of", "prime minister of", "population of", "area of", "government", "capital of"]
g = rdflib.Graph()
count_based_on = 0

def url_to_entity(url):
    return url.split("/")[-1].replace("_"," ")

def question_spaces_to_bottom_line(question):
    return question.replace(" ", "_")

def replace_hyphens_to_bottom_line(question):
    return question.replace("-", "_")

def add_to_ontology(entity, description, result):
    entity = f"{ontology_prefix}{entity}"
    description = f"{ontology_prefix}{description}"
    result = f"{ontology_prefix}{question_spaces_to_bottom_line(result)}"
    #print(entity, " ", description, " ", result)
    g.add((rdflib.URIRef(entity), rdflib.URIRef(description), rdflib.URIRef(result)))

def from_source_url_to_queue():
    r = requests.get(url_source)
    doc = lxml.html.fromstring(r.content)
    special = [163, 196, 203]
    count = 0
    inte = 0
    for t in doc.xpath('//*[@id="mw-content-text"]/div[1]/table/tbody//tr/td[1]//a[@title]/@href'):
        if t not in visited:
            inte = inte + 1
            #print(t)
            visited.add(t)
            #print(("Country", f"{prefix}{t}"))
            if "%" in t:
                t = doc.xpath('//*[@id="mw-content-text"]/div[1]/table/tbody//tr/td[1]//a[@title]/@title')
                t = t[special[count]]
                count = count + 1
                wiki = prefix + "/wiki/"
                wiki = question_spaces_to_bottom_line(wiki)
                #print(t)
                url_queue.put(("Country", f"{wiki}{t}"))
            else:
                url_queue.put(("Country", f"{prefix}{t}"))
            #countries.append(t[6:len(t)])
    #print(inte)

def add_population(country, url):
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    population = doc.xpath('//a[text()="Population"]/following::tr[1]/td/text()')
    if len(population) > 0:
        population = population[0].split("(")[0]
    #print(country)
    print(population)
    # Russia = //a[text()="Population"]/following::tr[1]/td/div/ul/li/text()
    #add_to_ontology(country, data_labels[2], population)

def add_government(country, url):
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    government = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Government"]//a/text()')
    government = government[1:]
    val_to_remove = []
    #print(government)
    for i in range(len(government)):
        if ('[' in government[i]):
            val_to_remove.append(government[i])
    for val in val_to_remove:
        government.remove(val)
    government = sorted(government, key=str.lower)
    #print(url)
    #print(government)

    add_to_ontology(country, data_labels[4], str(government))

def add_birth_location(person, url):
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    city = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Born"]//@title')
    location = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Born"]/td//text()')
    #print(city)
    for i in location:
        if i == city:
            location = i+1
            #print(location)
            break

    if location:
        location = question_spaces_to_bottom_line(location[0])
        add_to_ontology(person, "where_born", location)

def add_birthday(person, url):
    #### שווה בדיקה אם יש תאריכים שהתפספסו ##

    test = ""
    #print(person)
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    birthday = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Born"]//span[@class="bday"]//text()')
    text_date = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Born"]//td//text()')
    if text_date:
        for i in text_date:
            #print(i)
            if "19" in i:
                test = i
                break
        if test and len(test) == 10:
            test = replace_hyphens_to_bottom_line(test)
            add_to_ontology(person, "when_born", test)
    #else:
        #print(person)
    #if birthday:
    #    birthday = replace_hyphens_to_bottom_line(birthday[0])
    #    add_to_ontology(person, "when_born", birthday)
    #else:
        #print(person)


def add_area(country, url):

    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    area = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr//td[text()[contains(.,"km")]]//text()')
    if len(area) > 0:
        area = area[0].split()[0]
    add_to_ontology(country, "area_of", str(area))

def get_from_url(job):
    dict = {}
    url = job[1]
    #print(url)
    print(url)
    country = url_to_entity(url)
    country = question_spaces_to_bottom_line(country)
    print(country)
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    president = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="President"]/td//text()')
    url_president = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="President"]/td//a/@href')
    prime_minister = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Prime Minister"]/td//text()')
    url_prime_minister = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Prime Minister"]/td//a/@href')
    capital = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Capital"]//@title')
    if capital:
        capital = question_spaces_to_bottom_line(capital[0])
        add_to_ontology(country, "capital_of", capital)
        #print(capital)
    else:
        if country == "Channel_Islands":
            capital = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Capital and largest settlement"]//@title')
            capital = question_spaces_to_bottom_line(capital[0])
            add_to_ontology(country, "capital_of", capital)
    add_area(country, url)

    #government =
    add_government(country, url)

    #population =
    add_population(country, url)

    if url_president:
        url_president = url_president[0]
    else:
        url_president = "error"
    if url_prime_minister:
        url_prime_minister = url_prime_minister[0]
    else:
        url_prime_minister = "error"
    if prime_minister:
        prime_minister = prime_minister[0]
        prime_minister = question_spaces_to_bottom_line(prime_minister)
        #print(prime_minister)
        url_prime_minister = f"{prefix}{url_prime_minister}"
        add_birthday(prime_minister, url_prime_minister)
        #add_birth_location(prime_minister, url_prime_minister)
        add_to_ontology(country, "prime_minister_of", prime_minister)
        add_to_ontology(prime_minister, "prime_minister_of", country)

    if president:
        president = president[0]
        president = question_spaces_to_bottom_line(president)
        url_president = f"{prefix}{url_president}"
        add_birthday(president, url_president)
        #add_birth_location(president, url_president)
        add_to_ontology(country, "president_of", president)
        add_to_ontology(president, "president_of", country)


def initialize_crawl():
    # queue of urls
    dict = {}
    from_source_url_to_queue()
    while not url_queue.empty():
        job = url_queue.get()
        # print(job)
        get_from_url(job)
        #print(dict)
        #print(dict['Xi Jinping'])
    #print(dict.keys())
    g.serialize("ontology.nt", format="nt")





# *** Part 2 - Answer Questions ***
def question_to_sparql_query(question):
    length_q = len(question)
    question = question_spaces_to_bottom_line(question)
    part_for_query = ""
    part_for_query2 = ""
    # question starting with Who
    if question.find("Who") != -1:
        # Who is the president of <country>?
        if question.find("president") != -1:
            part_for_query = question[24:length_q - 1]

            # query place

        # Who is the prime minister of <country>?
        if question.find("prime") != -1:
            part_for_query = question[29:length_q - 1]

            # query place

        # Who is <entity>?
        else:
            part_for_query = question[7:length_q - 1]

            # query place

    # question starting with What
    if question.find("What") != -1:
        # What is the area of <country>?
        if question.find("area") != -1:
            part_for_query = question[20:length_q - 1]

            # query place

        # What is the population of <country>?
        if question.find("population") != -1:
            part_for_query = question[26:length_q - 1]

             # query place

        # What is the capital of <country>?
        if question.find("capital") != -1:
            part_for_query = question[23:length_q - 1]

            # query place

        # What is the form of government in <country>?
        if question.find("government") != -1:
            part_for_query = question[34:length_q - 1]
            q = "select * where {<http://example.org/"+part_for_query+"> <http://example.org/government> ?x.}"
            ans = list(g.query(q))
            print("Answer is: ", ans)

            # query place

    # question starting with When
    if question.find("When") != -1:
        # When was the president of <country> born?
        if question.find("president") != -1:
            part_for_query = question[26:length_q - 6]

            # query place

        # When was the prime minister of <country> born?
        if question.find("prime") != -1:
            part_for_query = question[31:length_q - 6]

            # query place

    # question starting with where
    if question.find("Where") != -1:
        # Where was the president of <country> born?
        if question.find("president") != -1:
            part_for_query = question[27:length_q - 6]

            # query place

        # Where was the prime minister of <country> born?
        if question.find("prime") != -1:
            part_for_query = question[32:length_q - 6]

            # query place

    # How many presidents were born in <country>?
    if question.find("were_born_in") != -1:
        part_for_query = question[33:length_q-1]

        # query place

    # List all countries whose capital name contains the string <str>
    if question.find("List_all") != -1:
        part_for_query = question[58:length_q]

        # query place

    # How many <government_form1> are also <government_form2>?
    if question.find("are_also") != -1:
        # government form1
        part_for_query = question[9:length_q - 23]
        # government form2
        part_for_query2 = question[31:length_q - 1]

        # query place
    return(part_for_query, part_for_query2)

if __name__ == '__main__':
    question = "What is the form of government in Sweden?"
    g = rdflib.Graph()
    g.parse("ontology.nt", format="nt")
    #length_q = len(question)
    #print(question.find("<"))
    #part_for_query = question[27:length_q - 6]
    print(question_to_sparql_query(question))

    #from_source_url_to_queue()
    #print(url_to_entity("https://en.wikipedia.org/wiki/Emmanuel_Macron"))
    #initialize_crawl()
    #while True:
    #    x = (url_queue.get())
    #    add_area(x[1], x[1])
    #add_population('Frace', "https://en.wikipedia.org/wiki/France")