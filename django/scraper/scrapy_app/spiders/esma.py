# -*- coding: UTF-8 -*-

from datetime import datetime

import bs4
import scrapy
from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException
from tika import parser


class EsmaScraperSpider(scrapy.Spider):
    download_delay = 0.1
    name = "esma"
    start_urls = [
        "https://www.esma.europa.eu/databases-library/esma-library/?f%5B0%5D=im_field_document_type%3A45",
    ]

    def get_metadata(self, element):
        newdict = {}
        publication_date = element.find("td", {"class": "esma_library-date"})
        reference_number = element.find("td", {"class": "esma_library-ref"})
        publication_title = element.find("td", {"class": "esma_library-title"})
        publication_type = element.find("td", {"class": "esma_library-type"})
        publication_section = element.find("td", {"class": "esma_library-section"})
        if publication_date is not None:
            date = publication_date.getText()
            newdict.update({"date": datetime.strptime(date, "%d/%m/%Y")})
        if reference_number is not None:
            reference = reference_number.getText()
            newdict.update({"reference": reference})
        if publication_title is not None:
            title = publication_title.getText()
            newdict.update({"title": title})
        if publication_type is not None:
            type = publication_type.getText()
            newdict.update({"type": type})
        if publication_section is not None:
            section = publication_section.getText()
            newdict.update({"section": section})
        document_link = element.find("a")
        if document_link is not None:
            document_link = document_link.get("href")
            output = parser.from_file(document_link)
            content = output.get("content")
            metadata = output.get("metadata")
            content_type = metadata.get("Content-Type")
            if content is not None and content_type is not None:
                if self.is_document_english(content):
                    if isinstance(content_type, list):
                        if (
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in content_type
                            or "application/vnd.ms-excel" in content_type
                        ):
                            newdict.update({"other_docs": [document_link]})
                            newdict.update({"url": document_link})

                    if metadata.get("Content-Type") == "application/pdf" and self.is_document_english(content):
                        if not document_link.startswith("/databases-library"):
                            newdict.update({"pdf_docs": [document_link]})
                            # doc url == pdf url for esma
                            newdict.update({"url": document_link})

        if "url" in newdict:
            return newdict

    def parse(self, response):
        soup = bs4.BeautifulSoup(response.text, features="html.parser")
        publications_body = soup.find("tbody")
        all_publications_on_a_page = publications_body.findAll("tr")
        for element in all_publications_on_a_page:
            yield self.parse_single(element)
        next_page_url = response.css("li.pager-next > a::attr(href)").extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))

    def parse_single(self, element):
        data = self.get_metadata(element)
        return data

    def is_document_english(self, plain_text):
        english = False
        detect_threshold = 0.4
        try:
            langs = detect_langs(plain_text)
            number_langs = len(langs)
            # trivial case for 1 language detected
            if number_langs == 1:
                if langs[0].lang == "en":
                    english = True
            # if 2 or more languages are detected, consider detect probability
            else:
                for detected in langs:
                    if detected.lang == "en" and detected.prob >= detect_threshold:
                        english = True
                        break
        except LangDetectException:
            pass
        return english
