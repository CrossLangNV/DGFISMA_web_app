# -*- coding: UTF-8 -*-
import logging
import re
from datetime import datetime, MAXYEAR
from enum import Enum
from urllib.parse import urlparse, quote

import scrapy

ALLOWED_MISC_TYPES = [
    "additional_information",
    "addressee",
    "author",
    "department_responsible",
    "depositary",
    "form",
    "internal_comment",
    "internal_reference",
    "parliamentary_term",
    "rapporteur",
    "session",
]
ALLOWED_PROCEDURE_TYPES = ["co author"]


class EurLexType(Enum):
    DECISIONS = "https://eur-lex.europa.eu/search.html?wh0=andCOMPOSE%3DENG,orEMBEDDED_MANIFESTATION-TYPE%3Dpdf;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa1a;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa1b;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa2a;EMBEDDED_MANIFESTATION-TYPE%3Dpdfx;EMBEDDED_MANIFESTATION-TYPE%3Dpdf1x;EMBEDDED_MANIFESTATION-TYPE%3Dhtml;EMBEDDED_MANIFESTATION-TYPE%3Dxhtml;EMBEDDED_MANIFESTATION-TYPE%3Ddoc;EMBEDDED_MANIFESTATION-TYPE%3Ddocx&qid=1600765281210&DB_TYPE_OF_ACT=decision&DTS_DOM=ALL&excConsLeg=true&typeOfActStatus=DECISION&type=advanced&lang=en&SUBDOM_INIT=ALL_ALL&DTS_SUBDOM=ALL_ALL"
    DIRECTIVES = "https://eur-lex.europa.eu/search.html?wh0=andCOMPOSE%3DENG,orEMBEDDED_MANIFESTATION-TYPE%3Dpdf;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa1a;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa1b;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa2a;EMBEDDED_MANIFESTATION-TYPE%3Dpdfx;EMBEDDED_MANIFESTATION-TYPE%3Dpdf1x;EMBEDDED_MANIFESTATION-TYPE%3Dhtml;EMBEDDED_MANIFESTATION-TYPE%3Dxhtml;EMBEDDED_MANIFESTATION-TYPE%3Ddoc;EMBEDDED_MANIFESTATION-TYPE%3Ddocx&qid=1600765362488&DB_TYPE_OF_ACT=directive&DTS_DOM=ALL&excConsLeg=true&typeOfActStatus=DIRECTIVE&type=advanced&lang=en&SUBDOM_INIT=ALL_ALL&DTS_SUBDOM=ALL_ALL"
    REGULATIONS = "https://eur-lex.europa.eu/search.html?wh0=andCOMPOSE%3DENG,orEMBEDDED_MANIFESTATION-TYPE%3Dpdf;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa1a;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa1b;EMBEDDED_MANIFESTATION-TYPE%3Dpdfa2a;EMBEDDED_MANIFESTATION-TYPE%3Dpdfx;EMBEDDED_MANIFESTATION-TYPE%3Dpdf1x;EMBEDDED_MANIFESTATION-TYPE%3Dhtml;EMBEDDED_MANIFESTATION-TYPE%3Dxhtml;EMBEDDED_MANIFESTATION-TYPE%3Ddoc;EMBEDDED_MANIFESTATION-TYPE%3Ddocx&qid=1600765406005&DB_TYPE_OF_ACT=regulation&DTS_DOM=ALL&excConsLeg=true&typeOfActStatus=REGULATION&type=advanced&lang=en&SUBDOM_INIT=ALL_ALL&DTS_SUBDOM=ALL_ALL"


class EurLexSpider(scrapy.Spider):
    download_delay = 0.1
    name = "eurlex"
    date_format = "%d/%m/%Y"
    year = None

    def __init__(self, spider_type=None, spider_date_start=None, spider_date_end=None, year=None, *args, **kwargs):
        super(EurLexSpider, self).__init__(*args, **kwargs)
        logging.log(logging.INFO, "spider_date_start: %s", spider_date_start)
        logging.log(logging.INFO, "spider_date_end: %s", spider_date_end)
        logging.log(logging.INFO, "year: %s", year)
        if not spider_type:
            logging.log(logging.WARNING, "EurLex spider_type not given, default to DECISIONS")
            spider_type = EurLexType.DECISIONS
        else:
            spider_type_arg = spider_type.upper()
            # this can throw a KeyError if spider_type_arg is not known in the enum
            spider_type = EurLexType[spider_type_arg]
            logging.log(logging.INFO, "EurLex spider_type: " + spider_type.name)

        if (not spider_date_start or not spider_date_end) and not year:
            logging.log(logging.WARNING, "No date range given, fetching all")
            start_url = spider_type.value
        elif year:
            logging.log(logging.INFO, "Fetching year: %s", year)
            self.year = year
            start_url = spider_type.value + "&DD_YEAR=" + year
        else:
            # Date format: DDMMYYYY
            logging.log(logging.INFO, "Fetching from: %s, to: %s", spider_date_start, spider_date_end)
            start_url = spider_type.value + "&date0=DD:" + spider_date_start + "|" + spider_date_end

        self.start_urls = [start_url]

    def date_safe(self, date_string):
        try:
            return datetime.strptime(date_string, self.date_format)
        except:
            return "n/a"

    def parse(self, response):
        for h2 in response.css("div.EurlexContent div.SearchResult"):
            doc_link = h2.css("::attr(name)").extract_first().replace("/AUTO/", "/EN/ALL/")
            yield scrapy.Request(doc_link, callback=self.parse_document)

        next_page_url = response.css("a[title='Next Page']::attr(href)").extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))

    def parse_document(self, response):
        parsed_uri = urlparse(response.url)
        base_url = "{uri.scheme}://{uri.netloc}/".format(uri=parsed_uri)
        result_dict = {}

        celex = response.url.split(":")[-1]
        result_dict["celex"] = celex

        body = response.css("div.panel-body")
        if body:
            title = body.xpath('.//p[@id="englishTitle"]')
            if title:
                title_raw_text = title.xpath(".//text()").get()
                # englishTitle element can still be empty
                if title_raw_text:
                    title = title_raw_text.replace("\n", " ").strip()
                    result_dict["title"] = title

            status = body.css("p.forceIndicator")
            if status:
                status = "".join(status.xpath(".//text()").getall()).replace("\n", " ").strip().split(":")[0]
                result_dict["status"] = status

            various = body.xpath(".//p[not(@*)]")
            if various:
                links = various.xpath(".//a/@href").getall()
                for link in links:
                    if "eli" in link:
                        result_dict["eli"] = link
                        break

                various_text = "".join(various.xpath(".//em//text()").getall()).replace("\n", " ").strip()
                result_dict["various"] = various_text

        self.parse_dates(response, result_dict)
        self.parse_classifications(response, result_dict)
        self.parse_misc(response, result_dict)
        self.parse_procedures(response, result_dict)
        self.parse_relationships(response, result_dict)
        self.parse_consolidated_versions(response, result_dict)
        self.parse_content(response, result_dict)

        result_dict.update(
            {"html_docs": ["http://publications.europa.eu/resource/celex/" + quote(result_dict["celex"])]}
        )

        result_dict.update({"url": response.url})

        summary_link = response.xpath("//li[@class='legissumTab']/a/@href").get()
        if summary_link:
            summary_link_abs = summary_link.replace("./../../../", base_url)
            yield scrapy.Request(summary_link_abs, callback=self.parse_document_summary)
        yield result_dict

    def parse_document_summary(self, response):
        base_url = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(response.url))

        # check if multiple summaries are listed, follow links if so
        if response.xpath("//div[@id='documentView']//table//tr/th[text()='Summary reference']").get():
            summary_links = response.xpath("//tbody//td//a/@href").getall()
            # preserve celex of document
            meta = {"celex": response.url.split(":")[-1]}
            for link in summary_links:
                link_abs = link.replace("./../../../", base_url)
                yield scrapy.Request(link_abs, callback=self.parse_document_summary_single, meta=meta)
        else:
            yield self.parse_document_summary_single(response)

    def parse_document_summary_single(self, response):
        result_dict = {}
        result_dict["doc_summary"] = True
        result_dict["url"] = response.url
        # use received celex if available
        celex = response.meta.get("celex", response.url.split(":")[-1])
        result_dict["celex"] = celex
        title = response.xpath('//div[@id="PP1Contents"]//p/text()').get()
        result_dict["title"] = title
        self.parse_classifications(response, result_dict)
        self.parse_dates(response, result_dict)
        self.parse_misc(response, result_dict)
        result_dict["html_content"] = response.xpath('//div[@id="text"]').get()
        return result_dict

    def parse_dates(self, response, result_dict):
        dates = response.xpath('//div[@id="PPDates_Contents"]')
        if dates:
            all_dates = []
            all_dates_type = []
            all_dates_info = []
            date_types = dates.xpath(".//dt")
            date_texts = dates.xpath(".//dd")
            for (t, d) in zip(date_types, date_texts):
                date_type = t.xpath(".//text()").get().split(":")[0].lower()
                date_value_all = "".join(d.xpath(".//text()").getall()).split(";")
                if "/" in date_value_all[0]:
                    date_value = datetime.strptime(date_value_all[0], self.date_format)
                else:
                    date_value = datetime(MAXYEAR, 1, 1)
                date_info = date_value_all[1].replace("\n", " ").strip() if len(date_value_all) > 1 else "n/a"
                # date of document is our main "date"
                if date_type == "date of document":
                    result_dict["date"] = date_value
                # handle other date_types to be appended to "dates"
                all_dates_type.append(date_type)
                all_dates.append(date_value)
                all_dates_info.append(date_info)
            result_dict.update({"dates": all_dates})
            result_dict.update({"dates_type": all_dates_type})
            result_dict.update({"dates_info": all_dates_info})

    def parse_classifications(self, response, result_dict):
        base_url = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(response.url))
        classifications = response.xpath('//div[@id="PPClass_Contents"]')
        if classifications:
            classifications_types = classifications.xpath(".//dt")
            classifications_data = classifications.xpath(".//dd")
            all_classifications_type = []
            all_classifications_label = []
            all_classifications_code = []
            for (t, d) in zip(classifications_types, classifications_data):
                ref_codes = d.xpath(".//a")
                for ref_code in ref_codes:
                    all_classifications_type.append(t.xpath(".//text()").get().split(":")[0].lower())
                    element_name = "".join(ref_code.xpath(".//text()").getall()).replace("\n", " ").strip()
                    ref_code = str(ref_code.xpath(".//@href").get()).replace("./../../../", base_url)
                    element_code = re.search("CODED=(.*)&", ref_code)
                    element_code = element_code.group(1)
                    all_classifications_label.append(element_name)
                    all_classifications_code.append(element_code if element_code else "n/a")

            result_dict.update({"classifications_label": all_classifications_label})
            result_dict.update({"classifications_type": all_classifications_type})
            result_dict.update({"classifications_code": all_classifications_code})

    def parse_misc(self, response, result_dict):
        misc = response.xpath('//div[@id="PPMisc_Contents"]')
        if misc:
            misc_types = misc.xpath(".//dt")
            misc_data = misc.xpath(".//dd")
            for (t, d) in zip(misc_types, misc_data):
                misc_type = t.xpath(".//text()").get().split(":")[0].lower().replace(" ", "_")
                misc_value = "".join(d.xpath(".//text()").getall()).replace("\n", " ").strip()
                # save 'form' value also as general document type value
                if misc_type == "form" and not result_dict.get("doc_summary"):
                    result_dict["type"] = misc_value
                if misc_type in ALLOWED_MISC_TYPES:
                    result_dict["misc_" + misc_type] = misc_value

    def parse_procedures(self, response, result_dict):
        procedures = response.xpath('//div[@id="PPProc_Contents"]')
        if procedures:
            all_procedures_links_url = []
            all_procedures_links_name = []
            all_procedures_number = []
            procedure_types = procedures.xpath(".//dt")
            procedure_data = procedures.xpath(".//dd")
            for (t, d) in zip(procedure_types, procedure_data):
                procedure_type = (
                    "".join(t.xpath(".//text()").getall()).replace("\n", " ").strip().split(":")[0].lower()
                )
                if procedure_type == "procedure number":
                    for number in d.xpath(".//a/text()").getall():
                        all_procedures_number.append(number)

                elif procedure_type == "link":
                    procedure_link = d.xpath(".//a")
                    if procedure_link:
                        name = procedure_link.xpath("./b/text()").get().replace("\n", " ").strip()
                        link = procedure_link.xpath("./@href").get()
                        all_procedures_links_name.append(name)
                        all_procedures_links_url.append(link)
                else:
                    proc_misc_value = "".join(d.xpath(".//text()").getall()).replace("\n", " ").strip()
                    if procedure_type in ALLOWED_PROCEDURE_TYPES:
                        result_dict.update({"procedure_" + procedure_type.replace(" ", "_"): proc_misc_value})

            result_dict.update({"procedures_number": all_procedures_number})
            result_dict.update({"procedures_links_name": all_procedures_links_name})
            result_dict.update({"procedures_links_url": all_procedures_links_url})

    def parse_relationships(self, response, result_dict):
        base_url = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(response.url))
        relationships = response.xpath('//div[@id="PPLinked_Contents"]')
        if relationships:
            rel_types = relationships.xpath(".//dt[not(@class)]")
            rel_texts = relationships.xpath(".//dd[not(@class)]")
            all_relationships_legal_basis = []
            all_relationships_proposal = []
            redirect_link_value = ""
            # treaty is always the first
            result_dict.update(
                {"relationships_treaty": "".join(rel_texts[0].xpath(".//text()").getall()).replace("\n", " ").strip()}
            )
            # iterate over next relationships
            for rel_text in rel_texts[1:]:
                common_index = rel_texts.index(rel_text)
                rel_category = rel_types[common_index].xpath(".//text()").get().split(":")[0].replace("\n", "").lower()
                redirect_link_value = ""
                redirect_links = rel_text.xpath(".//a")
                for redirect_link in redirect_links:
                    redirect_link_text = redirect_link.xpath(".//text()").get()
                    redirect_link_url = redirect_link.xpath("./@href").get().replace("./../../../", base_url)
                    if "CELEX" in redirect_link_url:
                        redirect_link_value = redirect_link_text
                    else:
                        redirect_link_value = redirect_link_url
                    if rel_category == "legal basis":
                        all_relationships_legal_basis.append(redirect_link_value)
                    elif rel_category == "proposal":
                        all_relationships_proposal.append(redirect_link_value)
            # oj link is always the last
            result_dict.update({"relationships_oj_link": redirect_link_value})
            result_dict.update({"relationships_legal_basis": all_relationships_legal_basis})
            result_dict.update({"relationships_proposal": all_relationships_proposal})

            amendments = relationships.xpath(".//tbody")
            all_amendments_relation = []
            all_amendments_act = []
            all_amendments_comment = []
            all_amendments_subdivision = []
            all_amendments_from = []
            all_amendments_to = []
            if amendments:
                rows = amendments.xpath(".//tr")
                if rows:
                    n = 0
                    for tr in rows:
                        td = tr.xpath(".//td")
                        relation = td[0].xpath(".//text()").get(default="").replace("\n", " ").strip()
                        act = td[1].xpath(".//a//text()").get(default="").replace("\n", " ").strip()
                        comment = td[2].xpath(".//text()").get(default="").replace("\n", " ").strip()
                        subdivision_concerned = td[3].xpath(".//text()").get(default="").replace("\n", " ").strip()
                        as_from = td[4].xpath(".//text()").get(default="").replace("\n", " ").strip()
                        to = td[5].xpath(".//text()").get(default="").replace("\n", " ").strip()
                        n += 1
                        all_amendments_relation.append(relation if relation else "n/a")
                        all_amendments_act.append(act if act else "n/a")
                        all_amendments_comment.append(comment if comment else "n/a")
                        all_amendments_subdivision.append(subdivision_concerned if subdivision_concerned else "n/a")
                        all_amendments_from.append(self.date_safe(as_from) if as_from else "n/a")
                        all_amendments_to.append(self.date_safe(to) if to else "n/a")
                    result_dict.update({"amendments_relation": all_amendments_relation})
                    result_dict.update({"amendments_act": all_amendments_act})
                    result_dict.update({"amendments_comment": all_amendments_comment})
                    result_dict.update({"amendments_subdivision": all_amendments_subdivision})
                    result_dict.update({"amendments_from": all_amendments_from})
                    result_dict.update({"amendments_to": all_amendments_to})

    def parse_consolidated_versions(self, response, result_dict):
        consolidated_links = response.xpath(
            '//dt[contains(text(), "consolidated versions:")]/following-sibling::dd[1]//a'
        )
        if consolidated_links:
            consolidated_celex_ids = []
            for link_sel in consolidated_links:
                link = link_sel.xpath("./@href").get()
                celex = link.split(":")[-1]
                consolidated_celex_ids.append(celex)
            result_dict["consolidated_versions"] = consolidated_celex_ids

    def parse_content(self, response, result_dict):
        # get html content first, if available
        content = response.xpath('//div[@id="text"]').get()
        if content:
            result_dict["content_html"] = content
        else:
            # Check for pdfs
            base_url = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(response.url))
            oj = response.xpath('//div[@id="PP2Contents"]')
            # only store english pdf doc url(s)
            if oj is not None:
                pdf_docs = []
                pdfs = oj.xpath(".//li")
                for pdf in pdfs:
                    if len(pdf.xpath('a[@class!="disabled"]')):
                        pdf = pdf.xpath(".//a/@href").get().replace("./../../../", base_url)
                        if "EN/TXT/PDF/" in pdf:
                            pdf_docs.append(pdf)
                        result_dict.update({"pdf_docs": pdf_docs})
