# -*- coding: utf-8 -*-
import time
import arrow
import random
import decimal
import requests
import rfc822
import calendar
from bs4 import BeautifulSoup
from meya import Component
from meya.cards import Card, Cards


CACHE_REFRESH = 60 * 60  # 1 hour


class PollContent(Component):

    def start(self):
        # refresh cache first
        url = self.properties.get("url")
        assert url, "Feed url is required."
        self.refresh_cache(url)

        # get the user's latest read story
        latest_read_ts = self.db.user.get('latest_read_ts') or 0

        # get the latest, unread story (ts needs to be Decimal)
        content_list = self.db.table('content').filter(
            ts__gt=decimal.Decimal(latest_read_ts),
            content_id__exists=True,
            order_by=["-ts"]
        )[:3]

        if content_list:
            # reverse to dispaly in ASC order
            content_list.reverse()
            elements = []
            for content in content_list:
                # set the user's latest unread story
                self.db.user.set('latest_read_ts', content["ts"])
                print content
                element = Card(
                    title=content["title"],
                    text=content["description"],
                    item_url=content["link"],
                    image_url=content["image_url"]
                )
                elements.append(element)

            card = Cards(elements=elements)
            message = self.create_message(card=card)
            action = "yes_content"

        else:
            # [default] no content
            message = None
            action = "no_content"

        return self.respond(message=message, action=action)

    def refresh_cache(self, url):
        last_cache_ts = self.db.bot.get('content_refresh_ts') or 0
        now_ts = arrow.utcnow().timestamp

        if (now_ts - last_cache_ts) > CACHE_REFRESH:
            # update cache ts first BEFORE polling
            self.db.bot.set('content_refresh_ts', now_ts)
            self.poll_content(url)

    def poll_content(self, url):
        # simulate slow request
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.find_all("item"):
            try:
                content_id = item.guid.text
                title = item.title.text.strip()
                description = item.description.text.strip()
                image_url = item.find('media:content')['url']
                link = item.link.text
                pub_date = calendar.timegm(rfc822.parsedate_tz(item.pubdate.text))
            except:
                # don't get hung up on errors
                continue
    
            # dedupe based on the content_id
            content = self.db.table('content').filter(content_id=content_id)[:1]
            if content:
                # don't add duplicate content
                return
    
            # add any new stories
            ts = arrow.utcnow().timestamp
            content = {
                "content_id": content_id,
                "ts": ts,
                "title": title,
                "description": description,
                "image_url": image_url,
                "link": link,
                "pub_date": pub_date
            }
            self.db.table('content').add(content)
