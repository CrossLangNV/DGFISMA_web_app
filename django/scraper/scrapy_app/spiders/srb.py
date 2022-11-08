# -*- coding: UTF-8 -*-
from urllib.parse import urlparse

import bs4
import re
import scrapy
import logging

from datetime import datetime


class SRBScraperSpider(scrapy.Spider):
    download_delay = 0.1
    name = "srb"
    start_urls = [
        "https://srb.europa.eu/en/news/policies",
    ]

    def get_metadata(self, response):
        soup = bs4.BeautifulSoup(response.text, features="html.parser")
        metas = soup.find_all("meta")
        parsed_uri = urlparse(response.url)
        base_url = "{uri.scheme}://{uri.netloc}/".format(uri=parsed_uri)
        newdict = {}
        for meta in metas:
            if "property" in meta.attrs and meta.attrs["property"] == "og:title":
                title = meta.attrs["content"]
                newdict.update({"title": title})
            if "property" in meta.attrs and meta.attrs["property"] == "og:url":
                url_link = meta.attrs["content"]
                newdict.update({"url": url_link})
            if "name" in meta.attrs and meta.attrs["name"] == "dcterms.date":
                datum = meta.attrs["content"]
                datum = datum.split("+")[0]
                datum = datetime.strptime(datum, "%Y-%m-%dT%H:%M")
                newdict.update({"date": datum})
            if "content" in meta.attrs and meta.attrs["content"].endswith("pdf"):
                link_to_pdf = meta.attrs["content"]
                if not link_to_pdf.startswith(base_url):
                    link_to_pdf = str(base_url) + str(link_to_pdf)
                    newdict.update({"pdf_docs": [link_to_pdf]})
                else:
                    newdict.update({"pdf_docs": [link_to_pdf]})

        if "pdf_docs" not in newdict:
            for link in soup.find_all("a"):
                pdf_link = link.get("href")
                if pdf_link is not None and pdf_link.endswith("pdf"):
                    newdict.update({"pdf_docs": [pdf_link]})
                    break

        description = soup.find("div", {"class": "post__body"})
        if description is not None:
            description = description.getText()
            newdict.update({"summary": description})
        return newdict

    def parse(self, response):
        parsed_uri = urlparse(response.url)
        base_url = "{uri.scheme}://{uri.netloc}/".format(uri=parsed_uri)

        for div in response.css("section.block div.ds-1col"):
            meta = {"doc_link": base_url + str(div.css("::attr(about)").extract_first())}
            yield scrapy.Request(meta["doc_link"], callback=self.parse_single, meta=meta)

        """
        there is currently no next page available
        next_page_url = response.css("li.pager-next > a::attr(href)").extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))

        """

    def parse_single(self, element):
        data = self.get_metadata(element)
        return data
