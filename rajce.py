import argparse
import re
import sys
import logging
import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from multiprocessing.dummy import Pool
from time import gmtime, strftime


class Rajce:
    urls = None
    path = None
    useHistory = False
    useBruteForce = False

    history = []
    videoStorage = None
    securityCode = None
    storage = None
    filePath = None
    links = {}
    root = Path(__file__).resolve().parent

    THREADS_COUNT = 10

    def __init__(self, urls, path=None, archive=None, bruteForce=None):
        self.setLogger()

        self.urls = urls
        self.path = Path(path) if path else self.root
        self.useBruteForce = bruteForce
        if archive:
            self.useHistory = True
            self.history = self.getHistory()

    def getHistory(self) -> list:
        list = []
        try:
            with open(self.root.joinpath('history'), 'r+') as f:
                for line in f:
                    currentPlace = line[:-1]
                    list.append(currentPlace)
        except:
            return []

        return list

    def setLogger(self):
        logging.basicConfig(
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='[%Y-%m-%d %H:%M:%S] :',
            filename=self.root.joinpath('errors.log'),
            filemode='a+',
            level=logging.INFO
        )

        formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='[%Y-%m-%d %H:%M:%S] ')
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)

        self.logger = logging.getLogger()
        self.logger.addHandler(console)

    def isAlbum(self, url):
        return len(urllib.parse.urlparse(url).path.strip('/')) > 0

    def getBruteForceList(self, url) -> list:
        urlList = []

        try:
            url = urllib.request.urlopen(url).geturl()
        except urllib.error.URLError as e:
            self.logger.error(f'Error while getting brute force list: "{e.reason}" for url : {url}')
            return []

        url = url.split('?')[0].strip('/')

        nameList = [
            urllib.parse.urlsplit(url).netloc.split('.')[0],
            urllib.parse.urlsplit(url).path.strip('/'),
        ]
        # nameList += urllib.parse.urlsplit(url).path.strip('/').split('_')
        # nameList += [x.lower() for x in urllib.parse.urlsplit(url).path.strip('/').split('_')]

        pwrdList = nameList = list(set(nameList))

        for login in nameList:
            for password in pwrdList:
                urlList.append(url + f'/?login={login}&password={password}')

        return urlList

    def getConfig(self, url, bruteForce=False) -> dict:
        config = {}

        try:
            data = dict(
                urllib.parse.parse_qsl(
                    urllib.parse.urlsplit(url).query
                )
            )
            data = urllib.parse.urlencode(data).encode()
            request = urllib.request.Request(url, data=data)
            response = urllib.request.urlopen(request)
        except urllib.error.URLError as e:
            self.logger.error(f'Error : "{e.reason}" for url : {url}')
            return {}

        for line in response.readlines():
            m = re.search('var (.+?) = (.+?);$', line.decode('utf-8').strip('\n\t\r '))
            if not m or m.group(1) in config: continue
            config[m.group(1)] = m.group(2)

        for key in ['photos', 'albumName', 'storage', 'settings', 'albumRating']:
            if key in config: config[key] = json.loads(config[key])

        for key in config:
            if isinstance(config[key], str):
                config[key] = config[key].strip('"')

        if 'photos' not in config and bruteForce:
            self.logger.info(f'Trying to bruteforce "{url}"')
            urls = self.getBruteForceList(url)
            for url in urls:
                config = self.getConfig(url, False)
                if 'photos' in config: break

        return config

    def getUrl(self, url) -> str:
        data = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        data = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(url, data=data)

        return urllib.request.urlopen(request).read().decode('utf-8')

    def getMediaList(self, config) -> list:
        if 'photos' not in config:
            self.logger.error(f'Error : Album is empty or password protected')
            return []

        # Parse user, album, storage
        if not all(k in config for k in ('albumUserName', 'albumServerDir', 'storage')):
            self.logger.error(f'Error : Config keys not found')
            return []

        photos = config['photos']

        for elem in photos:
            elem['albumUserName'] = config['albumUserName'].strip('"')
            elem['albumServerDir'] = config['albumServerDir'].strip('"')
            elem['storage'] = config['storage']

        return photos

    def getAlbumsList(self, url) -> list:
        url = urllib.parse.urljoin(url, 'services/web/get-albums.json')
        offset = 1
        limit = 50
        albums = []

        while True:
            data = {'offset': offset - 1, 'limit': limit}

            data = urllib.parse.urlencode(data).encode()
            request = urllib.request.Request(url, data=data)
            try:
                content = urllib.request.urlopen(request).read().decode('utf-8')
            except urllib.error.URLError as e:
                self.logger.error(f'Error : "{e.reason}" for url : {url}')
                break

            content = json.loads(content)

            if len(content['result']['data']) == 0:
                break

            albums += [x['permalink'] for x in content['result']['data']]

            offset += limit

        return albums

    def downloadFile(self, media):
        if media['videoStructure']:
            url = media['videoStructure']['items'][1]['video'][0]['file']
        else:
            url = media['storage'] + 'images/' + media['fileName']

        file = self.path.joinpath(media['albumUserName'], media['albumServerDir'], media['info'].split(' | ')[0])

        try:
            urllib.request.urlretrieve(url, file)
        except urllib.error.HTTPError as e:
            self.logger.error(f'HTTPError : "{e.reason}" for url : {url}')
            return False
        except urllib.error.ContentTooShortError as e:
            self.logger.error(f'ContentTooShortError : "{e.reason}" for url : {url}')
            return False
        except urllib.error.URLError as e:
            self.logger.error(f'URLError : "{e.reason}" for url : {url}')
            return False

        return media['photoID']

    def downloadAlbum(self, url):
        config = self.getConfig(url, self.useBruteForce)
        links = self.getMediaList(config)

        user, album = config['albumUserName'], config['albumServerDir']
        self.logger.info(f'Checking {user}\'s album "{album}"')

        if len(links) == 0:
            self.logger.info(f'No photos found')
            return

        fileList = [x for x in links if x['photoID'] not in self.history] if self.useHistory else links

        if len(fileList) == 0:
            self.logger.info(f'No new photos found')
            return

        self.logger.info(f'{len(fileList)} new photo{("s" if len(fileList) > 1 else "")} found')
        try:
            self.path.joinpath(user, album).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f'Error "{e}" when mkdir "{user}/{album}"')
            return

        ttl = len(fileList)
        dld = 0
        barLen = 50
        timestamp = strftime("%Y-%m-%d %H:%M:%S", gmtime())

        p = Pool(self.THREADS_COUNT)
        with open(self.root.joinpath('history'), 'a+') as f:
            for photoId in p.imap(self.downloadFile, fileList):
                if photoId:
                    dld += 1
                    block = int(barLen * dld / ttl)
                    sys.stdout.write(f"\r[{timestamp}] [{dld}/{ttl}] [{'#' * block}{'-' * (barLen - block)}]")
                    sys.stdout.flush()
                if self.useHistory and photoId:
                    f.write(f"{photoId}\n")
        print("\r")

    def download(self):
        urls = []

        for url in self.urls:
            urls += [url] if self.isAlbum(url) else self.getAlbumsList(url)

        for url in urls:
            self.downloadAlbum(url)

        self.logger.info('Done!')

    def analyze(self, albumCount=10, mediaCount=50):
        albums = []
        media = []
        urls = []

        for url in self.urls:
            urls += [url] if self.isAlbum(url) else self.getAlbumsList(url)

        for url in urls:
            config = self.getConfig(url, self.useBruteForce)
            links = self.getMediaList(config)

            user, album = config['albumUserName'], config['albumServerDir']
            self.logger.info(f'Analyze {user}\'s album "{album}"')

            albums += [config]
            media += links

        albums = [x for x in albums if 'albumRating' in x]

        print(f'Album\'s top {albumCount}')
        for elem in sorted(albums, reverse=True, key=lambda item: item['albumRating'])[:albumCount]:
            album = 'https://' + elem['albumUserName'] + '.rajce.idnes.cz/' + elem['albumServerDir']
            print(elem['albumRating'], album)

        print(f'Photos top {mediaCount}')
        for elem in sorted(media, reverse=True, key=lambda item: item['rating'])[:mediaCount]:
            album = 'https://' + elem['albumUserName'] + '.rajce.idnes.cz/' + elem['albumServerDir']
            print(elem['rating'], album + '/' + elem['photoID'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help="List of URLs", nargs='+', required=True)
    parser.add_argument('-p', '--path', help="Destination folder")
    parser.add_argument('-ht', '--history', help="Downloaded URLs log", action='store_true')
    parser.add_argument('-b', '--bruteforce', help="Use bruteForce", action='store_true')
    parser.add_argument('-a', '--analyze', help="Analyze URL", action='store_true')
    args = parser.parse_args()

    rajce = Rajce(args.url, args.path, args.history, args.bruteforce)
    if args.analyze:
        rajce.analyze(10, 50)
    else:
        rajce.download()
