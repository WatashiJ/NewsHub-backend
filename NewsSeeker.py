import urllib.request
from bs4 import BeautifulSoup
from News import News
import re
from NewsContentCrawler import NewsContentCrawler

class NewsSeeker:

	headlinePatterns = {'metro': '<div class="top-story"(.*?|\s)*?<\/div>',
						'chronicle': '<div class="text">(\s|.)*?<h2>.*?<\/h2>'}
	normalPatterns = {'metro': '(\s<li( class="((top\-story )?float\-clear)")?( data-thumbnail=.*?)?>(.|\s)*?(<\/p>)(.|\s)*?<\/li>)|<li class="no-thumb".*\s*?<a.*\s*?<\/li>', 
						'chronicle': '<div class="views-field-title cufon">(.|\s)*?<a href=".*?">.*?<\/a>(.|\s)*?<\/div>'}

	def __init__(self, url, source):
		self.url = url
		self.source = source
		self.location = 'halifax'
		allLocations = ['halifax', 'calgary', 'edmonton', 'ottawa', 'toronto', 'vancouver', 'winnipeg']
		for each in allLocations:
			if each in self.url:
				self.location = each
				break

	def process(self, headlines = True, normal = True):
		self.data = self.__webInfo()
		if headlines == True:
			headlines = self.__headlines()
		if normal == True:
			normal = self.__normalNews()
		if headlines == False:
			return self.__jsonHanlder(info = normal)
		if normal == False:
			return self.__jsonHanlder(info = headlines)
		return {'headlines': self.__jsonHanlder(info = headlines), 'normal': self.__jsonHanlder(info = normal)}

	def __jsonHanlder(self, info):
		ids = set()
		result = []
		for news in info:
			if news.url in ids:
				continue
			ids.add(news.url)
			result.append(news.toDict())
		return result

	def __webInfo(self):
		return urllib.request.urlopen(self.url).read().decode('UTF-8')

	def __searchInfo(self, patternGroup):
		pattern = patternGroup[self.source]
		pattern = re.compile(pattern)
		info = re.search(pattern, self.data)
		if info is None:
			raise ValueError
		else:
			return info.group()

	def __findAllInfo(self, patternGroup):
		pattern = patternGroup[self.source]
		pattern = re.compile(pattern)
		return re.finditer(pattern, self.data)

	def __headlines(self):
		if self.url is None or self.source is None:
			raise ValueError
		if self.source == 'metro':
			headline = self.__searchInfo(patternGroup = self.headlinePatterns)
			soup = BeautifulSoup(headline, 'html.parser')
			url = soup.a['href']
			img = soup.img['data-original']
			title = soup.h1.a.text
			try:
				subtitle = soup.h2.text.strip()
			except AttributeError:
				subtitle = ""
			subHeadlines = self.__processMetroSubHeadlines()
			if self.__urlChecker(url = url):
				subHeadlines.insert(0, News(title = title, url = url, source = self.source, content = subtitle, img = img, location = self.location))
			return subHeadlines
		elif self.source == 'chronicle':
			headlinePattern = re.compile(self.headlinePatterns[self.source])
			result = re.finditer(headlinePattern, self.data)
			titles = []
			for each in result:# Find all titles
				soup = BeautifulSoup(each.group(), 'html.parser')
				titles.append(soup.h2.text)
			imgs = []
			urls = []
			contents = []
			for index in range(len(titles)):
				headlineIntro = self.__processChronicleHeadline(index = index)
				soup = BeautifulSoup(headlineIntro, 'html.parser')
				imgs.append(soup.a.img['src'])
				url = soup.a['href']
				if self.__urlChecker(url = url) == False:
					continue
				urls.append('http://thechronicleherald.ca' + url)
				contents.append(soup.a.img['title'])
			headlines = []
			for index in range(len(titles)):
				headlines.append(News(title = titles[index], url = urls[index], source = self.source, content = contents[index], location = self.location, img = imgs[index] if len(imgs) > index else ''))
			return headlines

	def __normalNews(self):
		if self.url is None or self.source is None:
			raise ValueError
		normal = self.__findAllInfo(patternGroup = self.normalPatterns)
		normal = filter(lambda x: len(x.group()) < 4000, normal)
		news = []
		for each in normal:
			soup = BeautifulSoup(each.group(), 'html.parser')
			if self.source == 'metro':
				try:
					img = soup.li['data-thumbnail']
				except KeyError:
					try:
						img = soup.li.img['data-original']
					except:
						img = ''
				url = soup.li.a['href']
				if self.__urlChecker(url = url) == False:
					continue
				title = soup.li.p.a.text if len(soup.li.a.text.strip()) == 0 else soup.li.a.text
				content = ''
				try:
					content = soup.li.img['alt']
				except: 
					pass
				news.append(News(title = title, img = img, url = url, location = self.location, source = self.source))
			elif self.source == 'chronicle':
				url = soup.div.span.a['href']
				if self.__urlChecker(url = url) == False:
					continue
				imgLink, content = self.__moreInfoForChronicle(url)
				if not ('http://' in url or 'https://' in url):
					url = 'http://thechronicleherald.ca' + url
				title = soup.div.span.a.text
				news.append(News(title = title, url = url, source = self.source, content = content, location = self.location, img = imgLink))
		return news

	def __moreInfoForChronicle(self, url):
		imgURL = ''
		for character in url:
			if character == '/':
				imgURL += '\/'
			else:
				imgURL += character
		imgPattern = re.compile('<span.*' + imgURL + '(\s|.).*?<img.*<\/span>')
		imgPart = re.search(imgPattern, self.data)
		if not imgPart is None:
			soup = BeautifulSoup(imgPart.group(), 'html.parser')
			return soup.span.a.img['src'], soup.span.a.img['title']
		return '',''


	def __processChronicleHeadline(self, index):
		introPattern = re.compile('<div id="tab-' + str(index) + '" class="ui-tabs-panel (ui-tabs-hide)?">(.|\s)*?<\/div>')
		return re.search(introPattern, self.data).group()

	def __processMetroSubHeadlines(self):
		subPattern = re.compile('<li data-vr-contentbox="">(\s|.)*?<\/li>')
		result = re.finditer(subPattern, self.data)
		news = []
		for each in result:
			soup = BeautifulSoup(each.group(), 'html.parser')
			url = soup.a['href']
			if self.__urlChecker(url = url) == False:
				continue
			img = soup.img['data-original']
			content = soup.img['alt']
			title = soup.li.contents[len(soup.li.contents) - 2].text
			news.append(News(title = title, url = url, img = img, location = self.location, content = content, source = self.source))
		return news

	def __urlChecker(self, url):
		try:
			urlCopy = '%s' % url
			urlCopy.encode('UTF-8')
			return True
		except:
			return False