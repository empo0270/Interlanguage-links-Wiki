
# coding: utf-8

# # Lab 2 - Hyperlink Networks

# **Professor [Brian Keegan](https://www.brianckeegan.com)**  
# **[Department of Information Science, CU Boulder](www.colorado.edu/cmci/academics/information-science)**  
# This notebook is copyright and made available under the [Apache License v2.0](https://creativecommons.org/licenses/by-sa/4.0/) license.
# 
# This is the second of five lab notebooks that will explore how to do some introductory data extraction and analysis from Wikipedia data. This lab will extend the methods in the prior lab about analyzing a single article's revision histories and use network science methods to analyze the networks of hyperlinks around a single article. You do not need to be fluent in either to complete the lab, but there are many options for extending the analyses we do here by using more advanced queries and scripting methods.
# 
# **Acknowledgements**  
# I'd like to thank the Wikimedia Foundation for the [PAWS system](https://wikitech.wikimedia.org/wiki/PAWS) and [related Wikitech infrastructure](https://wikitech.wikimedia.org/wiki/Main_Page) that this workbook runs within. Yuvi Panda, Aaron Halfaker, Jonathan Morgan, and Dario Taraborelli have all provided crucial support and feedback.

# ## Confirm that basic Python commands work

# In[1]:

a = 3
b = 4
a**b


# ## Import modules and setup environment

# Load up all the libraries we'll need to connect to the database, retreive information for analysis, and visualize results.

# In[2]:

# Makes the plots appear within the notebook
get_ipython().magic('matplotlib inline')

# Two fundamental packages for doing data manipulation
import numpy as np                   # http://www.numpy.org/
import pandas as pd                  # http://pandas.pydata.org/

# Two related packages for plotting data
import matplotlib.pyplot as plt      # http://matplotlib.org/
import seaborn as sb                 # https://stanford.edu/~mwaskom/software/seaborn/

# Package for requesting data via the web and parsing resulting JSON
import requests
import json
from bs4 import BeautifulSoup

# Two packages for accessing the MySQL server
import pymysql                       # http://pymysql.readthedocs.io/en/latest/
import os                            # https://docs.python.org/3.4/library/os.html

# Packages for analyzing complex networks
import networkx as nx                # https://networkx.github.io/
import igraph as ig

# Setup the code environment to use plots with a white background and DataFrames show more columns and rows
sb.set_style('whitegrid')
pd.options.display.max_columns = 100
pd.options.display.max_rows = 110


# Define the name of the article you want to use for the rest of the lab.

# In[3]:

page_title = "2013 Egyptian coup d'état"




# In[7]:

#make a dictionary of links for each language 
_langlink_dict=dict()

for d in _langlink_list:
    _lang=d['lang']
    _title=d['*']
    _langlink_dict[_lang]=_title


# In[8]:

#dictionary list of all languages and their abbreviations
_langAbrev_dict=dict()

for d in _langlink_list:
    _lang=d['lang']
    _langname=d['langname']
    _langAbrev_dict[_lang]=_langname


# In[9]:

_langAbrev_dict


# In[10]:

#combine all the steps above into one function, every page in another language will be listed and written in that particular language
def link_getter(page_title):
    
    _S="https://en.wikipedia.org/w/api.php?action=query&format=json&prop=langlinks&titles={0}&llprop=autonym|langname&lllimit=500".format(page_title)
    
    req = requests.get(_S)

    json_string = json.loads(req.text)
    
    _pageID=list(json_string['query']['pages'].keys())[0]

    _langlink_list=json_string['query']['pages'][_pageID]['langlinks']
    
    _langlink_dict=dict()

    for d in _langlink_list:
        _lang=d['lang']
        _title=d['*']
        _langlink_dict[_lang]=_title
        
    
    return _langlink_dict


# In[11]:

#returns list of pages in each lang it is published in 
link_getter(page_title)


# ### Retrieve the content of the page via API

# Write a function that takes an article title and returns the list of links in the body of the article. Note that the reason we don't use the "pagelinks" table in MySQL or the "links" parameter in the API is that this includes links within templates. Articles with templates link to each other forming over-dense clusters in the resulting networks. We only want the links appearing in the body of the text.
# 
# We pass a request to the API, which returns a JSON-formatted string containing the HTML of the page. We use BeautifulSoup to parse through the HTML tree and extract the non-template links and return them as a list.

# In[12]:

def get_page_outlinks(page_title,lang='en',redirects=1):
    # Replace spaces with underscores
    page_title = page_title.replace(' ','_')
    
    bad_titles = ['Special:','Wikipedia:','Help:','Template:','Category:','International Standard','Portal:','s:','File:']
    
    # Get the response from the API for a query
    # After passing a page title, the API returns the HTML markup of the current article version within a JSON payload
    req = requests.get('https://{2}.wikipedia.org/w/api.php?action=parse&format=json&page={0}&redirects={1}&prop=text&disableeditsection=1&disabletoc=1'.format(page_title,redirects,lang))
    
    # Read the response into JSON to parse and extract the HTML
    json_string = json.loads(req.text)
    
    # Initialize an empty list to store the links
    outlinks_list = [] 
    
    if 'parse' in json_string.keys():
        page_html = json_string['parse']['text']['*']

        # Parse the HTML into Beautiful Soup
        soup = BeautifulSoup(page_html,'lxml')

        # Delete tags associated with templates
        for tag in soup.find_all('tr'):
            tag.replace_with('')

        # For each paragraph tag, extract the titles within the links
        for para in soup.find_all('p'):
            for link in para.find_all('a'):
                if link.has_attr('title'):
                    title = link['title']
                    # Ignore links that aren't interesting
                    if all(bad not in title for bad in bad_titles):
                        outlinks_list.append(title)

        # For each unordered list, extract the titles within the child links
        for unordered_list in soup.find_all('ul'):
            for item in unordered_list.find_all('li'):
                for link in item.find_all('a'):
                    if link.has_attr('title'):
                        title = link['title']
                        # Ignore links that aren't interesting
                        if all(bad not in title for bad in bad_titles):
                            outlinks_list.append(title)

    return outlinks_list


# In[19]:

#test of outlinks grabbed for german page specifically named here, naming the page and the language
german_outlinks=get_page_outlinks('Militärputsch in Ägypten 2013',lang='de')


# In[20]:

#chunk/batch getter format 
#link_getter('|'.join(german_outlinks[:5]))


# In[36]:


#combine all the steps above into one function, every page in another language will be listed and written in that particular language
_page_title='|'.join(german_outlinks[:10])

_S="https://de.wikipedia.org/w/api.php?action=query&format=json&prop=langlinks&titles={0}&redirects=1&llprop=autonym|langname&lllimit=500".format(_page_title)

req = requests.get(_S)

json_string = json.loads(req.text)

_pageID_list=list(json_string['query']['pages'].keys())

#_langlink_list=json_string['query']['pages'][_pageID]['langlinks']

#_langlink_dict=dict()

#for d in _langlink_list:
#    _lang=d['lang']
#    _title=d['*']
#    _langlink_dict[_lang]=_title

translation_dict=dict()


for _pageID in _pageID_list:
    try:
        _langlink_list=json_string['query']['pages'][_pageID]['langlinks']
        _title=json_string['query']['pages'][_pageID]['title']
        for d in _langlink_list:
            if d['lang']=='en':
                translation_dict[_title]=d['*']
    except KeyError:
        _title=json_string['query']['pages'][_pageID]['title']
        translation_dict[_title]=None



# In[37]:

translation_dict


# In[ ]:

#page keys 
json_string['query']['pages']['17531']['title']


# In[ ]:

german_outlinks[:5]


