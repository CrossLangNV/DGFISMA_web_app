# -*- coding: UTF-8 -*-

import bs4
import scrapy
from urllib.parse import urlparse
from scrapy.http.response.text import TextResponse

from datetime import datetime


class FSBScraperSpider(scrapy.Spider):
    download_delay = 0.1
    name = "fsb"
    start_urls = [
        "https://www.fsb.org/publications/policy-documents/",
    ]

    def get_metadata(self, response):
        if not isinstance(response, TextResponse):
            pass
        else:
            soup = bs4.BeautifulSoup(response.text, features="html.parser")
            metas = soup.find_all("meta")
            parsed_uri = urlparse(response.url)
            base_url = "{uri.scheme}://{uri.netloc}/".format(uri=parsed_uri)

            newdict = {}
            for meta in metas:
                if "property" in meta.attrs and meta.attrs["property"] == "og:title":
                    title = meta.attrs["content"]
                    newdict.update({"title": title})
                if "name" in meta.attrs and meta.attrs["name"] == "keywords":
                    keywords = meta.attrs["content"]
                    newdict.update({"keywords": keywords})
                if "property" in meta.attrs and meta.attrs["property"] == "og:url":
                    url = meta.attrs["content"]
                    newdict.update({"url": url})
                if "name" in meta.attrs and meta.attrs["name"] == "DC.date":
                    datum = meta.attrs["content"]
                    datum = datum.split("+")[0]
                    datum = datetime.strptime(datum, "%Y-%m-%d")
                    newdict.update({"date": datum})
                if "content" in meta.attrs and meta.attrs["content"].endswith("pdf"):
                    link_to_pdf = meta.attrs["content"]
                    if not link_to_pdf.startswith(base_url):
                        link_to_pdf = str(base_url) + link_to_pdf
                    newdict.update({"pdf_docs": [link_to_pdf]})

            if "pdf_docs" not in newdict:
                for link in soup.find_all("a"):
                    pdf_link = link.get("href")
                    if pdf_link is not None and pdf_link.endswith("pdf"):
                        if not pdf_link.startswith(base_url):
                            pdf_link = str(base_url) + pdf_link
                        newdict.update({"pdf_docs": [pdf_link]})
                        break

            description = soup.find("span", {"class": "post-content"})
            if description is not None:
                description = description.getText().replace("\n", " ")
                newdict.update({"summary": description.strip()})

            return newdict

    def parse(self, response):
        for div in response.css("div.mtt-results div.media-body"):
            meta = {"doc_link": div.css("a::attr(href)").extract_first()}
            yield scrapy.Request(meta["doc_link"], callback=self.parse_single, meta=meta)
        next_page_url = response.css("li > a.next::attr(href)").extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))

    def parse_single(self, response):
        data = self.get_metadata(response)
        return data
