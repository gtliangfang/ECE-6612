from datetime import datetime
from database import Database
from models.post import Post
from models.search import Search
import featureExtraction

import urllib3
from bs4 import BeautifulSoup
import socket
import pandas as pd
import os 
import re
import argparse
import datetime


class Url:
    def __init__(self, id, url):
        """
        This class defines the Url class. Every Url node should have an ipaddress, neigboring links,
        a unique Id assigned on creation of the class instance and a string url
        :param id: A unique Id
        """
        self._root_url = None
        self._parent_url = None
        self._ip_address = None
        self._neighbors = []
        self._id = id
        self._url = url
        self._content = None
        self._visited = 'WHITE'
        self._distance = 0


    def __str__(self):
        return str('id: {}, url: {}, ip_address: {}, root_url: {}, parent_url: {}, distance_from_root: {}, \n'.format(
            self.get_id(), self.get_url(), self.get_ip_address(), self.get_parent_url(), self._root_url, self._distance))

    def __iter__(self):
        yield 'time_stamp',         str(datetime.datetime.now())
        yield 'id',                 self.get_id()
        yield 'url',                self.get_url()
        yield 'ip_address',         self.get_ip_address()
        yield 'root_url',           self.get_root_url()
        yield 'parent_url',         self.get_parent_url()
        yield 'distance_from_root', self.get_distance()
        yield 'url_content',        self.get_content()

    def get_url(self):
        return self._url

    def get_id(self):
        return self._id

    def get_ip_address(self):
        """
        This function returns the IPaddress of a URL
        :return: IPaddress
        """
        return self._ip_address

    def get_neighbors(self):
        """
        :return: links found in this Url
        """
        return self._neighbors

    def get_content(self):
        """
        :return: returns the content of the url
        """
        return self._content

    def get_distance(self):
        """
        :return: return the distance
        """
        return self._distance

    def get_parent_url(self):
        """
        :return: returns the immediate parent url
        """
        return self._parent_url

    def get_root_url(self):
        """
        :return: returns the root url
        """
        return self._root_url

    def get_visited_status(self):
        """
        :return: returns whether a url has been visited or not
        """

        return self._visited

    def set_parent_url(self, parent_url):

        self._parent_url = parent_url

    def set_root_url(self, root_url):
        """
        :param root_url: set the parent url in which this url was found
        :return: nothin
        """
        self._root_url = root_url

    def set_ip_address(self, ip_address):
        """
        :param ip_address: set the ip_address value
        :return: nothing
        """
        self._ip_address = ip_address

    def set_neigbors(self, neighbors):
        """
        :param neighbors: set neighboring links
        :return:
        """
        self._neighbors = neighbors

    def set_content(self, content):
        """
        :param content: sets the content of the url
        :return: nothing
        """
        self._content = content

    def set_visited_status(self, status):
        """
        :param status: sets the visitation status of this URL
        :return: nothing
        """
        self._visited = status

    def set_distance(self, dist):
        """
        :param dist: the distance of this url from the ground truth
        :return: the distance
        """
        self._distance = dist


class Crawl:

    def __init__(self, args):
        self.batch_sz = args.batch_size
        self.start = args.start
        self.id = args.start
        self.args = args

    def extract_batches(pos, batch_sz):

        CSV_PATH = "/Users/kennethyang/Desktop/repo/ECE-6612/data/phishtank_urls.csv"
        df = pd.read_csv(CSV_PATH)
        if pos > df.shape[0]:
            raise (StopIteration('data exceeded!'))
        else:
            return df['url'][pos:pos + batch_sz]

    def crawl(self):
        """
        :param max_iter:
        :return: nothing
        """
        # table_instances = self.init_database()

        for i in range(self.start, self.args.num_urls, self.batch_sz):
            print('batch: {} crawled'.format(i%self.batch_sz))
            url_strings = Crawl.extract_batches(i, self.batch_sz).tolist()
            for j in range(len(url_strings)):
                self.id = self.BFS(self.id, url_strings[j], url_strings[j])

    def BFS(self, id, x, root_url):
        """
        :param id: the index of the url
        :param x: the url string
        :param root_url: the root url
        :return: the current id
        """
        x = UpdateUrl(self.args).create_URL_node(id=id, url_string=x, root_url=root_url)
        queue = []
        x.set_visited_status('GRAY')
        x.set_distance(0)
        queue.append(x)
        while len(queue) > 0:
            current_url = queue.pop(0)
            for url in current_url.get_neighbors():
                id = id + 1
                if type(url) is str:
                    url = UpdateUrl(self.args).create_URL_node(id=id, url_string=url, root_url=root_url)
                url.set_parent_url(current_url)
                if url.get_visited_status() == 'WHITE':
                    url.set_distance(current_url.get_distance() + 1)
                    if url.get_distance() < self.args.crawl_depth:
                        url.set_visited_status('GRAY')
                        url.set_parent_url(current_url)

                        # INITIALIZE DATABASE/COLLECTION
                        Database.initialize('fullstack', 'phishing')

                        # SAVE TO DATA
                        post = Post(str(datetime.datetime.now()),
                                    url.get_id(),
                                    str(url.get_url()),
                                    str(url.get_ip_address()),
                                    str(url.get_root_url()),
                                    str(url.get_parent_url()),
                                    url.get_distance(),
                                    str(url.get_content()))
                        print('status: saved', 'url: ', url)
                        post.save_to_mongo()

                        queue.append(url)

                    else:
                        break
            current_url.set_visited_status('BLACK')
        return id


class UpdateUrl:

    def __init__(self, args):
        """
        TODO: Add some attributes later
        """
        self.args = args

    def open_url(self,  Url):
        """
        The function opens the Url
        :param Url: the Url Class
        :return: a BeautifulSoup object
        """
        timeout = urllib3.Timeout(connect=self.args.http_timeout, read=self.args.socket_timeout)
        client_options = {
            "timeout": timeout,
            "retries": self.args.http_retries
        }

        url = Url.get_url()
        try:
            http = urllib3.PoolManager()
            response = http.request('GET', url)
            soup = BeautifulSoup(response.data, 'html.parser')
            return soup
        except(ConnectionResetError, urllib3.exceptions.MaxRetryError, ConnectionRefusedError,
               ConnectionAbortedError, ConnectionError) as err:
            print('url: {}, error: {}'.format(url, str(err)))


    def extract_links(self, Url):
        """
        the function extracts all the hyperlinks in a webpage
        :param Url:
        :return: a list of hyperlinks
        """
        soup = self.open_url(Url)
        if soup is not None:
            links = []
            for link in soup.find_all('a', href=True):
                temp_link = link.get('href')
                if temp_link.startswith('http'):
                    links.append(temp_link)
            return links
        else:
            return []

    def update_url_neigbors(self, Url):
        """
        This function updates the list of neighbors to a specific Url
        :param Url: the Url class
        :return: nothin
        """
        neighbors = self.extract_links(Url)
        if Url.get_url() in neighbors:
            neighbors.remove(Url.get_url())

        Url.set_neigbors(neighbors[0:args.num_neighbors])

    def update_url_content(self, Url):
        """
        This function updates the Url content of a page
        :param Url: the Url class
        :return: nothing
        """
        soup = self.open_url(Url)
        if soup is not None:
            Url.set_content(soup.contents)

    def update_ip_address(self, Url):
        """
        This function updates the ip_address of a page
        :param Url: the Url class
        :return: nothing
        """
        host = re.match('^([^.]+)\..*$', str(Url.get_url())).group()
        hostname = host.split('.')[-2:]
        if hostname[1] not in ['com', 'edu', 'net',  'org']:
            hostname = host.split('/')[2]
        else:
            hostname = hostname[0]+'.'+hostname[1]
        if hostname.startswith('https'):
            hostname = hostname[8:]
        try:
            ip_address = socket.gethostbyname(hostname)
            Url.set_ip_address(ip_address)
        except(socket.gaierror) as err:
            print(hostname + ': ' + str(err))


    def create_URL_node(self, id, url_string, root_url=None):
        """
        :param id:
        :param url_string:
        :param root_url:
        :return:
        """
        URL = Url(id=id, url=url_string)
        if url_string == root_url:
            URL.set_distance(0)
        self.update_ip_address(URL)
        self.update_url_content(URL)
        self.update_url_neigbors(URL)
        URL.set_root_url(root_url)
        return URL

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Hyperparams')
    parser.add_argument('--num_neighbors', nargs='?', type=int, default=5,
                        help='max number of links to crawl in a new url')
    parser.add_argument('--crawl_depth', nargs='?', type=int, default=3,
                        help='the depth of crawling a url')
    parser.add_argument('--resume', nargs='?', type=str, default=None,
                        help='the url index to resume crawling')
    parser.add_argument('--batch_size', nargs='?', type=int, default=15,
                        help='Batch Size')
    parser.add_argument('--database_name', nargs='?', type=str, default='phisermen_bank',
                        help='the name of the Mongo database we will use')
    parser.add_argument('--url_table_name', nargs='?', type=str, default='url_table',
                        help='the name of the ip_table')
    parser.add_argument('--features_table_name', nargs='?', type=str, default='feature_table',
                        help='the name of the feature_table')
    parser.add_argument('--num_urls', nargs='?', type=int, default=10000,
                        help='total number of urls o list to crawl')
    parser.add_argument('--http_timeout', nargs='?', type=int, default=5,
                        help='timeout for http requests')
    parser.add_argument('--socket_timeout', nargs='?', type=int, default=10,
                        help='timeout for so')
    parser.add_argument('--http_retries', nargs='?', type=int, default=1,
                        help='number of retry counts')
    parser.add_argument('--start', nargs='?', type=int, default=15,
                        help='url index to start from')
    # args = parser.parse_args()
    # crawler = Crawl(args)
    # crawler.crawl()


def main():
    # url = 'https://stackexchange.com'
    # id = 0
    # root_url = 'https://www.people.com'
    # url = UpdateUrl().create_URL_node(id, url, url)
    # crawl = Crawl(args).BFS(id=id, x=url, root_url=url)

    # INITIALIZE DATABASE
    Database.initialize('fullstack', 'phishing')

    # QUERY GENERATED ID
    # generated_id = Search.from_id(24)
    # print(generated_id)

    # QUERY GLOBAL ID
    # global_id = Search.from_global_id("5c85839cbbf8f53182163e4d")
    # print(global_id)

    # QUERY URL
    # url = Search.from_url("https://storkbr.com/")
    # print(url)

    # TOTAL ENTRY COUNT EXAMPLE
    # total_entries = Database.total_entries()
    # print("TOTAL ENTRIES:", total_entries)

    # EXPORT MONGODB COLLECTION
    # os.system("mongoexport -h localhost -d fullstack -c phishing --type=csv --fields _id,url,ip_address,root_url,parent_url,distance_from_root --out phishing.csv")

    # ITERATE AND GET URL_CONTENT
    # example = Search.url_content()
    # print(example)

    # FIND INPUT FIELDS IN HTML/SAVE IN PANDAS DATAFRAME
    # featureExtraction.getInputFields()

if __name__ == '__main__':
    main()
