# -*- coding: UTF-8 -*-
from urllib.parse import urlparse

import logging
import bs4
import scrapy
from bs4 import BeautifulSoup

from datetime import datetime


class BISSpider(scrapy.Spider):
    download_delay = 0.1
    name = "bis"
    start_urls = [
        "https://www.bis.org/bcbs/publications.htm",
    ]

    def get_metadata(self, response):
        soup = BeautifulSoup(response.text, features="html.parser")
        metas = soup.find_all("meta")
        parsed_uri = urlparse(response.url)
        base_url = "{uri.scheme}://{uri.netloc}".format(uri=parsed_uri)

        newdict = {}
        newdict.update(({"url": response.url}))

        for meta in metas:
            if "property" in meta.attrs and meta.attrs["property"] == "og:title":
                title = meta.attrs["content"]
                newdict.update({"title": title.strip()})
            if "name" in meta.attrs and meta.attrs["name"] == "keywords":
                keywords = meta.attrs["content"]
                newdict.update({"keywords": keywords})
            if "property" in meta.attrs and meta.attrs["property"] == "og:url":
                url = meta.attrs["content"]
                newdict.update({"url": url})
            if "name" in meta.attrs and meta.attrs["name"] == "DC.date":
                # "1995-04-29"
                datum = meta.attrs["content"]
                datum = datetime.strptime(datum, "%Y-%m-%d")
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
                link_to_pdf = link.get("href")
                if link_to_pdf is not None and link_to_pdf.endswith("pdf"):
                    if not link_to_pdf.startswith(base_url):
                        link_to_pdf = str(base_url) + str(link_to_pdf)
                    newdict.update({"pdf_docs": [link_to_pdf]})
                    break

        description = soup.find("div", {"id": "cmsContent"})
        if description is not None:
            description = description.getText().replace("\xa0\n", "").replace("\n", "")
            newdict.update({"summary": description})

        docinfo = soup.find("div", {"class": "docinfoline"})

        if docinfo is not None:
            status = docinfo.find("div", {"class": "bcbs_publication_status"})
            if status is not None:
                status = status.getText()
                status = status.split()
                status = status[1]
                newdict.update({"status": status})

            doc_type = docinfo.find("span", {"class": "bcbs_type"}).getText()
            if doc_type is not None:
                newdict.update({"type": doc_type})
        return newdict

    def parse(self, response):
        # type 1, 2, 7: Standards, Guidelines and Sound practices
        return scrapy.FormRequest(
            "https://www.bis.org/doclist/bcbspubls.htm",
            formdata={
                "bcbspubltypes": {"1", "2", "7"},
                "paging_length": "25",
                "page": "1",
                "sort_list": "date_desc",
                "theme": "bcbspubls",
            },
            callback=self.find_number_of_pages,
        )

    def find_number_of_pages(self, response):
        soup = bs4.BeautifulSoup(response.text, features="html.parser")
        range_limit = soup.find("div", {"class": "pageof"}).getText()[-1]
        for x in range(1, int(range_limit)):
            yield scrapy.FormRequest(
                "https://www.bis.org/doclist/bcbspubls.htm",
                formdata={
                    "bcbspubltypes": {"1", "2", "7"},
                    "paging_length": "25",
                    "page": str(x),
                    "sort_list": "date_desc",
                    "theme": "bcbspubls",
                },
                callback=self.parse_single,
            )

    def parse_single(self, response):
        soup = bs4.BeautifulSoup(response.text, features="html.parser")
        parsed_uri = urlparse(response.url)
        base_url = "{uri.scheme}://{uri.netloc}/".format(uri=parsed_uri)
        all_publications_on_a_page = soup.findAll("a")
        for element in all_publications_on_a_page:
            new_url = base_url + element["href"]
            yield scrapy.Request(new_url, callback=self.get_metadata)
