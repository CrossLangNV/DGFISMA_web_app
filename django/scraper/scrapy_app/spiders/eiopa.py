from datetime import datetime

import scrapy
from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException
from tika import parser


class EiopaSpider(scrapy.Spider):
    download_delay = 0.1
    name = "eiopa"
    start_urls = [
        "https://www.eiopa.europa.eu/document-library_en?field_term_document_type_tid%5B0%5D=654&field_term_document_type_tid%5B1%5D=502",
    ]

    def parse(self, response):
        for div in response.css("div.view-content div.grid-list-item"):
            meta = {
                "title_prefix": div.css("div.title-prefix::text").extract_first(),
                "title": div.css("div.title::text").extract_first(),
                "date": div.css("span.date::text").extract_first(),
                "type": div.css("span.type::text").extract_first(),
                "doc_link": div.css("a::attr(href)").extract_first(),
            }
            yield scrapy.Request(meta["doc_link"], callback=self.parse_single, meta=meta)

        next_page_url = response.css("li.next:not([class^='disabled']) > a::attr(href)").extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))

    def parse_single(self, response):
        english_pdfs = response.xpath("//a[contains(@download, 'EN.pdf')]").css("a::attr(href)").extract()
        verified_english_pdfs = []
        # Parse each pdf using tika to make sure the type is pdf and check whether the content is English
        for pdf in english_pdfs:
            output = parser.from_file(pdf)
            content = output.get("content")
            metadata = output.get("metadata")
            content_type = metadata.get("Content-Type")
            if content is not None and content_type == "application/pdf":
                if is_document_english(content):
                    verified_english_pdfs.append(pdf)
        data = {
            "title_prefix": response.meta["title_prefix"],
            "title": response.meta["title"],
            "date": datetime.strptime(response.meta["date"], "%d %b %Y"),
            "type": response.meta["type"],
            "url": response.url,
            "summary": response.css("div[id='main-content'] ::text").extract(),
            "pdf_docs": verified_english_pdfs,
        }
        return data


def is_document_english(plain_text):
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
