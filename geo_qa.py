import queue
import time
import sys
import urllib

import requests
import re
import traceback
import lxml.html
import rdflib
from dateutil.parser import parse

### PART 1: Crawler & Extraction from infobox to ontology


start = time.time()
countries = []
visited = set()
g = rdflib.Graph()
url_queue = queue.Queue() # queue of urls: (Type, URL), Type = Country / President / Prime_Minister

wiki_pre = "/wiki/"
prefix = "http://en.wikipedia.org"
ontology_prefix = "http://example.org/"
url_source = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"

data_labels = ["president", "prime_minister", "population", "area", "government", "capital", "Country", "where_born", "when_born"]
g = rdflib.Graph()
count_based_on = 0

def extract_country_from_url(url):
    # This function gets a wikipedia link of a country and returns the name of the country
    return url.split("/")[-1].replace("_", " ")

def data_spaces_to_underlines(question):
    # This function replaces spaces of given string with underlines
    return question.replace(" ", "_")

def data_hyphens_to_underlines(question):
    # This function replaces hyphens of given string with underlines
    return question.replace("-", "_")
def remove_hyphens(question):
    # This function removes hyphens of given string
    return question.replace("-", "")
def remove_underlines(question):
    # This function removes underlines of given string
    return question.replace("_", "")

def add_to_ontology(entity, description, result):
    """
    This function gets a triple of:
    @param entity = country / prime minister / president
    @param description = from data_labels (list)
    @param result data = population, capital, etc

    Result: adds the data to the ontology
    """

    if len(entity) > 0 and len(description) > 0 and len(result) > 0:
        entity = f"{ontology_prefix}{entity}"
        description = f"{ontology_prefix}{description}"
        result = f"{ontology_prefix}{data_spaces_to_underlines(result)}"
        #print(entity, " ", description, " ", str(result))
        g.add((rdflib.URIRef(entity), rdflib.URIRef(description), rdflib.URIRef(result)))

def from_source_url_to_queue():
    """
    This function initialize the url_queue.
    It enters a tuple of: <"Country"> , <Country URL> to queue.
    special array handles special cases of 3 countries that have symbols in their wikipedia link page.
    In addition it initialize countries list from the given page in the task.
    """
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
                wiki = prefix + wiki_pre
                wiki = data_spaces_to_underlines(wiki)
                #print(t)
                url_queue.put((data_labels[6], f"{wiki}{t}"))
            else:
                url_queue.put((data_labels[6], f"{prefix}{t}"))

            if t[6:len(t)] != "o" and t[6:len(t)] != "n":
                countries.append(t[6:len(t)])
                countries.append(remove_underlines(t[6:len(t)]))
    #print(inte)

def add_population(country, doc):
    """
    This function extract the population size of country with XPATH query.
    @param country = given country
    @param doc = country page

    Result: adds the data to the ontology
    """
    population = doc.xpath('//table[contains(@class,"infobox")]/tbody//tr[contains(.//text(),"Population")]/following-sibling::tr/td//text()')
    russia = 'http://en.wikipedia.org/wiki/Russia' #xpath is exception
    if country == "Russia":
        #print('here')
        population = doc.xpath('//table[contains(@class,"infobox")]/tbody//tr[contains(.//text(),"Population")]/following-sibling::tr/td/div/ul/li/text()')
        #print(population)
    if population:
        population = population[0].split("(")[0]
        population = str(population).replace(".", ",").replace(" ", "")
        #print(population)
        add_to_ontology(country, data_labels[2], str(population))

        #print(country)
        #print(population)
        # Russia = //a[text()="Population"]/following::tr[1]/td/div/ul/li/text()
        #print(str(population).replace(",", "_"))

def add_government(country, doc):
    """"
    This function extract the form government of country with XPATH query.
    @param country = given country
    @param doc = country page

    Result: adds the data to the ontology
    """
    government = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Government"]//a/@href')
    government = government[1:]
    val_to_remove = []
    for i in range(len(government)):
        government[i] = government[i][6:]
        government[i] = urllib.parse.unquote(government[i], encoding='utf-8', errors='ignore')
        if ("'" in government[i]):
            government[i] = str(government[i]).replace("'", "")
        if ('[' in government[i] or '#' in government[i] or 'note-' in government[i]):
            val_to_remove.append(government[i])
    for val in val_to_remove:
        government.remove(val)
    government = sorted(government, key=str.lower)
    #print(url)
    if len(government) > 0 :
        #print(government)
        add_to_ontology(country, data_labels[4], str(government))

def add_birth_location(person, url):
    """"
    This function extract the birth location of prime minister / president with XPATH query.
    @param person = prime minister / president
    @param url = prime minister / president wikipedia page

    Result: adds the data to the ontology
    """
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    location_list = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Born"]/td//text()')
    location = ""
    for i in location_list:
        check = data_spaces_to_underlines(i)
        if check in countries:
            location = i
            break
        else:
            # replace chars that can be in string with spaces
            check = i.replace(" ", "").replace(",", "").replace(".", "").replace(")", "").replace("(", "")
            if check in countries:
                location = check
                break
    if location:
        location = data_spaces_to_underlines(location)
        add_to_ontology(person, data_labels[7], location)
    else:
        for country in countries:
            for location_check in location_list:
                if country in location_check:
                    location = country
                    break
        if location:
            location = data_spaces_to_underlines(location)
            add_to_ontology(person, data_labels[7], location)


def add_birthday(person, url):
    """"
    This function extract the birthday of prime minister / president with XPATH query.
    @param person = prime minister / president
    @param url = prime minister / president wikipedia page

    Result: adds the data to the ontology
    """
    #print(person)
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)
    birthday = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Born"]//span[@class="bday"]//text()')
    #print(birthday)
    if birthday:
        birthday = data_hyphens_to_underlines(birthday[0])
        add_to_ontology(person, data_labels[8], birthday)

def add_area(country, doc):
    """"
    This function extract the area size of country with XPATH query.
    @param country = given country
    @param doc = country page

    Result: adds the data to the ontology
    """
    area = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr//td[text()[contains(.,"km")]]//text()')
    if len(area) > 0:
        area = str(area[0].split()[0])
        #print(area)
        add_to_ontology(country, data_labels[3], area)

def add_capital(country, doc):
    """"
    This function extract the capital city of country with XPATH query.
    @param country = given country
    @param doc = country page

    Result: adds the data to the ontology
    """
    capital = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Capital"]//@title')
    if capital:
        capital = data_spaces_to_underlines(capital[0])
        add_to_ontology(country, data_labels[5], capital)
        #print(capital)
    else:
        if country == "Channel_Islands":
            capital = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Capital and largest settlement"]//@title')
            capital = data_spaces_to_underlines(capital[0])
            add_to_ontology(country, data_labels[5], capital)
    ### האם צריך להתייחס למקרים כמו Washington,_D.C.  ###

def add_president_or_prime_minister(country, person, url_person, role):
    """"
    This function extract the form government of country with XPATH query.
    @param country = given country
    @param person = prime minister / president name
    @param url_person = prime minister / president wikipedia page
    @param role = role of entity from data_labels (prime minister / president)

    Result: adds the data to the ontology
    """
    #print(person)
    #print(url_person)
    if url_person:
        url_person = url_person[0]
    #else:
    #    url_person = "error"
    if person:
        person = person[0]
        person = data_spaces_to_underlines(person)
        #print(prime_minister)
        url_person = f"{prefix}{url_person}"
        add_birthday(person, url_person)
        add_birth_location(person, url_person)
        add_to_ontology(country, role, person)
        add_to_ontology(person, role, country)

def get_from_url(job):
    """"
    Main function.
    The function manages every country url it gets from the initialize_crawl function.
    The function sends each request to a small function which extracts all the data
    it needs from country like: area,capital,population etc.

    @param job = tuple of : <"Country"> , <Country URL>.

    Result: manages the build of the ontology
    """
    url = job[1]
    #print(url)
    print(url)
    country = data_spaces_to_underlines(extract_country_from_url(url))
    print(country)
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)

    #### אפשר לשלוח לכל פונקציות הבת שלנו את r ו - doc ###
    president = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="President"]/td//text()')
    url_president = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="President"]/td//a/@href')
    prime_minister = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Prime Minister"]/td//text()')
    url_prime_minister = doc.xpath('//table[contains(@class, "infobox")]/tbody/tr[th//text()="Prime Minister"]/td//a/@href')

    add_capital(country, doc)
    add_area(country, doc)
    add_government(country, doc)
    add_population(country, doc)

    # handle special cases
    if president:
        if president[0] == '\xa0':
            president = ""
    if prime_minister:
        if prime_minister[0].find("TBA") != -1:
            prime_minister = ""
    add_president_or_prime_minister(country, president, url_president, data_labels[0])
    add_president_or_prime_minister(country, prime_minister, url_prime_minister, data_labels[1])

def initialize_crawl():
    """
    This function manages the queue of country links.
    The function sends country link to get_from_url function until the queue is empty
    Creates the ontology
    """
    # queue of urls
    from_source_url_to_queue()
    while not url_queue.empty():
        job = url_queue.get()
        # print(job)
        get_from_url(job)
    g.serialize("ontology.nt", format="nt")

# *** Part 2 - Answer Questions ***

def find_part_for_query(question):
    #question = question[1:-1]
    length_q = len(question)
    question = data_spaces_to_underlines(question)
    print(question)
    part_for_query = ""
    part_for_query2 = ""
    relation = ""
    switch_case = ["1", "area", "find_entity"]

    # question starting with Who
    if question.find("Who") != -1:

        # Who is the president of <country>?
        if question.find("president") != -1:
            part_for_query = question[24:length_q - 1]
            relation = "president"
            case = switch_case[0]

        # Who is the prime minister of <country>?
        elif question.find("prime") != -1:
            part_for_query = question[29:length_q - 1]
            relation = "prime_minister"
            case = switch_case[0]

        # Who is <entity>?
        else:
            part_for_query = question[7:length_q - 1]
            case = switch_case[2]
            #relation = ""

    # question starting with What
    if question.find("What") != -1:
        case = switch_case[0]

        # What is the area of <country>?
        if question.find("area") != -1:
            part_for_query = question[20:length_q - 1]
            relation = "area"
            case = switch_case[1]
        # What is the population of <country>?
        if question.find("population") != -1:
            part_for_query = question[26:length_q - 1]
            relation = "population"

        # What is the capital of <country>?
        if question.find("capital") != -1:
            part_for_query = question[23:length_q - 1]
            relation = "capital"

        # What is the form of government in <country>?
        if question.find("government") != -1:
            part_for_query = question[34:length_q - 1]
            relation = "government"

    # question starting with When
    if question.find("When") != -1:

        # When was the president of <country> born?
        if question.find("president") != -1:
            part_for_query = question[26:length_q - 6]
            relation = "when_born"

        # When was the prime minister of <country> born?
        if question.find("prime") != -1:
            part_for_query = question[31:length_q - 6]
            relation = "when_born"

    # question starting with where
    if question.find("Where") != -1:

        # Where was the president of <country> born?
        if question.find("president") != -1:
            part_for_query = question[27:length_q - 6]
            relation = "where_born"

        # Where was the prime minister of <country> born?
        if question.find("prime") != -1:
            part_for_query = question[32:length_q - 6]
            relation = "where_born"

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


        # Does prime minister born in <country>?
        if question.find("Does") != -1:
            part_for_query = question[28:length_q - 1]



    if case == switch_case[0]  or case == switch_case[1]:
        return "select * where {<http://example.org/" + part_for_query + "> <http://example.org/" + relation + "> ?a.}" , case
    else:
        # <film> <starring> <person>
        return "select * where {<http://example.org/" + part_for_query2 + "> <http://example.org/" + relation + "> <http://example.org/" + part_for_query + ">.}"

    # If the question is general:
    if question.find("How_many_films_are_based_on_books?") != -1:
        return "select (COUNT(*) AS ?count) where {?a <http://example.org/Based_on> <http://example.org/yes>.}"

    if question.find("How_many_films_starring") != -1:
        entity1 = question[24:length_q - 22]
        return "select (COUNT(*) AS ?count) where {?a <http://example.org/Starring> <http://example.org/" + entity1 + ">.}"

    if question.find("are_also") != -1:
        input_question = question[9:length_q - 1]
        occupations = input_question.split("_are_also_")
        #        return "select * where {?a <http://example.org/Occupation> <http://example.org/"+occupations[0]+">. ?a <http://example.org/Occupation> <http://example.org/"+occupations[1]+"> .}"
        return "select (COUNT(?a) AS ?count) where {?a <http://example.org/Occupation> <http://example.org/" + \
               occupations[0] + ">. ?a <http://example.org/Occupation> <http://example.org/" + occupations[1] + "> .}"
    # If the input question do not match any of the above:
    return "ERROR: illegal question format."


def question():
    input_question = sys.argv[2]
    print(input_question)
    input_question = data_spaces_to_underlines(input_question)
    query, case = find_part_for_query(input_question)
    print(query)
    g = rdflib.Graph()
    g.parse("ontology.nt", format="nt")
    query_result = g.query(query)
    #print(list(query_result))

    res_string = ""
    if case == "1" or case == "area":
        for i in range (len(list(query_result))):
            row = list(query_result)[i] # get row i from query list result.
            entity_with_uri = str(row[0])
            entity_with_uri = entity_with_uri.split("/")
            entity_without_uri = entity_with_uri[-1]
            #the next 3 code lines are to strip excessive spaces in the names.
            entity_without_uri = entity_without_uri.replace("_"," ")
            entity_without_uri = entity_without_uri.strip()
            entity_without_uri = entity_without_uri.replace(" ","_")
            res_string += entity_without_uri+" " #get the entity name without the uri.
        names = res_string.split() #split the string to sort the names lexicographically
        names.sort()
        res_string = ""
        for j in range (len(list(names))): #build string of names separated by ', '
            res_string += names[j]+", "
        res_string = res_string[0:len(res_string)-2] #remove the last ', ' in the string
        res_string = res_string.replace("_", " ")
        if case == "area":
            res_string += " km squared"
    print(res_string)
    return res_string

if __name__ == '__main__':
    #question1 = "What is the form of government in Sweden?"
    #question()
    #g = rdflib.Graph()
    #g.parse("ontology.nt", format="nt")
    #length_q = len(question)
    #print(question.find("<"))
    #part_for_query = question[27:length_q - 6]
    #print(question_to_sparql_query(question))

    #from_source_url_to_queue()
    #print(url_to_entity("https://en.wikipedia.org/wiki/Emmanuel_Macron"))
    initialize_crawl()
    #while True:
        #x = (url_queue.get())
        #add_government(x[1], x[1])
    #add_government('Syria', "http://en.wikipedia.org/wiki/Syria")