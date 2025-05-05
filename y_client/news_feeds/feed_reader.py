import feedparser
import numpy as np
import json
import requests, re
from bs4 import BeautifulSoup
try:
    from .client_modals import Websites, Articles, Images, session
except:
    from y_client.clients.client_web import session
    from .client_modals import Websites, Articles, Images
import datetime


class News(object):
    def __init__(self, title, summary, link, published, image_url=None):
        """
        This class represents a news article.

        :param title: the title of the article
        :param summary: the summary of the article
        :param link: the link to the article
        :param published: the date the article was published
        :param image_url: the url of the image in the article
        """
        self.title = title
        self.summary = summary
        self.link = link
        self.published = published
        self.image_url = image_url

    def __str__(self):
        """
        String representation of the news article.
        :return: a string representation of the news article
        """
        return f"Title: {self.title}\nSummary: {self.summary}\nLink: {self.link}\nPublished: {self.published}"

    def __repr__(self):
        """
        Representation of the news article.
        :return: the string representation of the news article
        """
        return self.__str__()

    def to_dict(self):
        """
        Convert the news article to a dictionary.

        :return: the dictionary representation of the news article
        """
        return {
            "title": self.title,
            "summary": self.summary,
            "link": self.link,
            "published": self.published,
        }

    def to_json(self):
        """
        Convert the news article to a json string.

        :return: a json string representation of the news article
        """
        return json.dumps(self.to_dict())

    def save(self, name, rss):
        """
        Save the news article to the database.

        :param name: the name of the website
        :param rss: the rss feed of the website
        """
        website_id = (
            session.query(Websites)
            .filter(Websites.name == name, Websites.rss == rss)
            .first()
            .id
        )
        # check if article exists
        if session.query(Articles).filter(Articles.link == self.link).first() is None:
            art = Articles(
                title=self.title,
                summary=self.summary,
                website_id=website_id,
                fetched_on=self.published,
                link=self.link,
            )
            session.add(art)
            session.commit()

        # get the article id
        article_id = (
            session.query(Articles).filter(Articles.link == self.link).first().id
        )

        if self.image_url is not None:
            img = Images(url=self.image_url, article_id=article_id)
            session.add(img)
            session.commit()


class NewsFeed(object):
    def __init__(
        self,
        name,
        feed_url,
        url_site=None,
        category=None,
        language=None,
        leaning=None,
        country=None,
    ):
        """
        This class represents a news feed.

        :param name: the name of the website
        :param feed_url: the rss feed url
        :param url_site: the website url
        :param category: the category of the website
        :param language: the language of the website
        :param leaning: the political leaning of the website
        :param country: the country of the website
        """
        self.feed_url = feed_url
        self.name = name
        self.url_site = url_site
        self.category = category
        self.language = language
        self.leaning = leaning
        self.country = country
        self.news = []

    def read_feed(self):
        """
        Read the feed and store the news articles.
        """
        today = datetime.datetime.now()
        timestamp = int(today.strftime("%Y%m%d"))

        # Track statistics
        stats = {
            "total_entries": 0,
            "processed": 0,
            "errors": 0,
            "images_added": 0
        }

        try:
            # get website id
            website = session.query(Websites).filter(Websites.name == self.name, Websites.rss == self.feed_url).first()
            if not website:
                print(f"Error: Website {self.name} with RSS {self.feed_url} not found in database")
                return

            website_id = website.id

            print(f"Processing feed: {self.name} ({self.feed_url})")

            # Fetch the feed
            try:
                feed = feedparser.parse(self.feed_url)
                if hasattr(feed, 'status') and feed.status != 200:
                    print(f"Error fetching feed {self.feed_url}: HTTP status {feed.status}")
                    if hasattr(feed, 'bozo_exception'):
                        print(f"Exception: {feed.bozo_exception}")
                    return
            except Exception as e:
                print(f"Error parsing feed {self.feed_url}: {str(e)}")
                return

            # Process all entries in the feed
            stats["total_entries"] = len(feed.entries)
            print(f"Found {stats['total_entries']} entries in the feed")

            for entry in feed.entries:
                try:
                    # Create news article
                    art = News(entry.title, entry.summary, entry.link, timestamp)
                    art.save(name=self.name, rss=self.feed_url)

                    # get article id to save image
                    article_record = session.query(Articles).filter(Articles.link == entry.link).first()
                    if not article_record:
                        print(f"Warning: Article {entry.title} not found in database after save")
                        continue

                    article_id = article_record.id

                    # check if there is an image in the article
                    if "media_content" in entry:
                        img = entry.media_content[0]["url"].split("?")[0]
                        if img is not None:
                            # check if image is already in the database
                            if session.query(Images).filter(Images.url == img).first() is None:
                                img_record = Images(url=img, article_id=article_id)
                                session.add(img_record)
                                session.commit()
                                stats["images_added"] += 1

                    self.news.append(art)
                    stats["processed"] += 1
                except Exception as e:
                    stats["errors"] += 1
                    print(f"Error processing article '{entry.title if hasattr(entry, 'title') else 'Unknown'}': {str(e)}")

            # If no new articles were processed, load existing ones from database
            if stats["processed"] == 0:
                # Get recent articles from this website (not just today)
                articles = session.query(Articles).filter(Articles.website_id == website_id).order_by(Articles.id.desc()).limit(10).all()

                if articles:
                    print(f"Loading {len(articles)} existing articles from database")
                    for art in articles:
                        self.news.append(News(art.title, art.summary, art.link, art.fetched_on))

            # Print summary
            print(f"Feed processing summary for {self.name}:")
            print(f"  - Total entries found: {stats['total_entries']}")
            print(f"  - Successfully processed: {stats['processed']}")
            print(f"  - Errors encountered: {stats['errors']}")
            print(f"  - Images added: {stats['images_added']}")
            print(f"  - Total articles in memory: {len(self.news)}")

        except Exception as e:
            print(f"Critical error processing feed {self.name}: {str(e)}")
            import traceback
            traceback.print_exc()

    def __extract_image_url(self, art):
        """
        Extract the image url from the article.

        :param art:
        :return: img url
        """
        if "media_content" in art:
            image = art.media_content[0]["url"].split("?")[0]
            return image
        return None

    def get_random_news(self):
        """
        Get a random news article from the feed.

        :return: a random news article or error message if none available
        """
        if len(self.news) == 0:
            # Try to load from database first
            self.get_all_news()

        # Check again after potential database load
        if len(self.news) == 0:
            return "No news available"

        return np.random.choice(self.news)

    def get_news(self):
        """
        Get all the news articles from the feed.
        :return: a list of news articles
        """
        return self.news

    def get_all_news(self):
        """
        Get all the news articles from the feed.
        If no news is available in memory, try to fetch from database.
        :return: a list of news articles
        """
        if len(self.news) == 0:
            # Try to get articles from database
            try:
                # Get website id
                website = session.query(Websites).filter(Websites.name == self.name, Websites.rss == self.feed_url).first()
                if website:
                    website_id = website.id
                    # Get articles from this website
                    articles = session.query(Articles).filter(Articles.website_id == website_id).order_by(Articles.id.desc()).limit(10).all()

                    if articles:
                        for art in articles:
                            self.news.append(News(art.title, art.summary, art.link, art.fetched_on))
            except Exception as e:
                print(f"Error fetching articles from database: {str(e)}")

        return self.news

    def to_dict(self):
        """
        Convert the news feed to a dictionary.

        :return: the dictionary representation of the news feed
        """
        return {
            "name": self.name,
            "feed_url": self.feed_url,
            "url_site": self.url_site,
            "category": self.category,
            "language": self.language,
            "leaning": self.leaning,
            "country": self.country,
            "news": [n.to_dict() for n in self.news],
        }

    def to_json(self):
        """
        Convert the news feed to a json string.

        :return: a json string representation of the news feed
        """
        return json.dumps(self.to_dict())


class Feeds(object):
    def __init__(self):
        """
        This class represents a collection of news feeds.
        """
        self.feeds = []

    @staticmethod
    def __not_in_db(name: str, url: str) -> object:
        """
        Check if the feed is not in the database.

        :param name: the name of the website
        :param url: the rss feed url
        :return: whether the feed is not in the database
        """
        res = (
            session.query(Websites)
            .filter(Websites.name == name, Websites.rss == url)
            .first()
        )
        return res is None

    def add_feed(
        self,
        name,
        url_site=None,
        url_feed=None,
        category=None,
        language=None,
        leaning=None,
        country=None,
    ):
        """
        Add a feed to the collection.

        :param name: the name of the website
        :param url_site: the website url
        :param url_feed: the rss feed url
        :param category: the category of the website
        :param language: the language of the website
        :param leaning: the political leaning of the website
        :param country: the country of the website
        """
        today = datetime.datetime.now()
        timestamp = int(today.strftime("%Y%m%d"))

        if url_feed is not None:
            if self.__not_in_db(name, url_feed):
                if self.__validate_feed(url_feed):
                    print(f"Adding feed: {name} ({url_feed})")
                    self.feeds.append(
                        NewsFeed(
                            name,
                            url_feed,
                            url_site,
                            category,
                            language,
                            leaning,
                            country,
                        )
                    )

                    # check if website exists
                    web = Websites(
                        name=name,
                        rss=url_feed,
                        country=country or "Unknown",
                        language=language or "en",
                        leaning=leaning or "center",
                        category=category or "general",
                        last_fetched=timestamp,
                    )
                    session.add(web)
                    session.commit()
                else:
                    print(f"Feed validation failed: {name} ({url_feed})")
                    try:
                        website = session.query(Websites).filter(Websites.name == name, Websites.rss == url_feed).first()
                        if website:
                            last_fetched = website.last_fetched
                            if timestamp > last_fetched:
                                session.query(Websites).filter(
                                    Websites.name == name, Websites.rss == url_feed
                                ).update({"last_fetched": timestamp})
                                session.commit()
                    except Exception as e:
                        print(f"Error updating last_fetched time: {str(e)}")
            else:
                print(f"Feed already in database: {name} ({url_feed})")
                try:
                    website = session.query(Websites).filter(Websites.name == name, Websites.rss == url_feed).first()
                    if website:
                        # Add to current feed collection even if it's already in the database
                        self.feeds.append(
                            NewsFeed(
                                name,
                                url_feed,
                                url_site,
                                website.category,
                                website.language,
                                website.leaning,
                                website.country,
                            )
                        )
                except Exception as e:
                    print(f"Error retrieving website from database: {str(e)}")

        elif url_site is not None:
            print(f"Extracting RSS feeds from site: {url_site}")
            fex = FeedLinkExtractor(url_site)
            fex.extract_rss_url()
            rss_urls = fex.get_rss_urls()

            if not rss_urls:
                print(f"No RSS feeds found on site: {url_site}")

            for rss in rss_urls:
                if self.__not_in_db(name, rss):  # Fixed bug: was using url_feed here
                    if self.__validate_feed(rss):
                        print(f"Adding extracted feed: {name} ({rss})")
                        self.feeds.append(
                            NewsFeed(
                                name,
                                rss,
                                url_site,
                                category,
                                language,
                                leaning,
                                country,
                            )
                        )

                        web = Websites(
                            name=name,
                            rss=rss,  # Fixed bug: was using url_feed here
                            country=country or "Unknown",
                            language=language or "en",
                            leaning=leaning or "center",
                            category=category or "general",
                            last_fetched=timestamp,
                        )
                        session.add(web)
                        session.commit()
                    else:
                        print(f"Extracted feed validation failed: {name} ({rss})")
                else:
                    print(f"Extracted feed already in database: {name} ({rss})")
        else:
            print("Please provide a feed url or a site url")

    def get_feeds(self):
        """
        Get all the feeds in the collection.

        :return: a list of feeds
        """
        return self.feeds

    @staticmethod
    def __validate_feed(url):
        """
        Validate the rss feed.

        :param url: the rss feed url
        :return: whether the feed is valid
        """
        try:
            feed = feedparser.parse(url)

            # Check if the feed was successfully parsed
            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"Warning: Feed {url} might be malformed. Error: {feed.bozo_exception if hasattr(feed, 'bozo_exception') else 'Unknown'}")

            # Check if the feed has entries
            if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                print(f"Warning: Feed {url} has no entries")
                # Still return True as it might be a valid feed with no current entries
                return True

            return True
        except Exception as e:
            print(f"Error validating feed {url}: {str(e)}")
            return False


class FeedLinkExtractor(object):
    def __init__(self, url):
        """
        This class extracts rss feed urls from a website.

        :param url: the website url
        """
        self.url = url
        self.rss_urls = []

    def extract_rss_url(self):
        """
        Extract (or at least tries to) the rss feed urls from the website.
        """
        try:
            page = requests.get(self.url, timeout=5).text
            soup = BeautifulSoup(page, features="html.parser")

            for e in soup.select(
                'a[href*="rss"],a[href*="/feed"],a:-soup-contains-own("RSS")'
            ):
                if e.get("href").startswith("/"):
                    url = self.url.strip("/") + e.get("href")
                else:
                    url = e.get("href")

                base_url = re.search(
                    "^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/\n]+)", url
                ).group(0)
                r = requests.get(url)
                soup = BeautifulSoup(r.text, features="html.parser")

                for e1 in soup.select(
                    '[type="application/rss+xml"],a[href*=".rss"],a[href$="feed"]'
                ):
                    if e1.get("href").startswith("/"):
                        rss = base_url + e1.get("href")
                    else:
                        rss = e1.get("href")
                    if "xml" in requests.get(rss).headers.get("content-type"):
                        self.rss_urls.append(rss)
        except:
            pass

    def get_rss_urls(self):
        """
        Get the extracted rss feed urls.

        :return: the extracted rss feed urls
        """
        return self.rss_urls

    def to_dict(self):
        """
        Convert the rss feed urls to a dictionary.

        :return: the dictionary representation of the rss feed urls
        """
        return {"rss_urls": self.rss_urls}

    def to_json(self):
        """
        Convert the rss feed urls to a json string.

        :return: the json string representation of the rss feed urls
        """
        return json.dumps(self.to_dict())
