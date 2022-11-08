import abc
import logging
import warnings
from typing import Iterable, List, Tuple, Dict, Union

import rdflib
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Literal, BNode, URIRef

from obligations import build_rdf

B_LOG_QUERIES = False

CONTAINS = 'contains'
STARTS_WITH = 'starts with'

VALUE = 'value_ent'
SUB = 'subject'
PRED = 'pred'
COUNT = 'count'
QUERY = 'query'
URIS = 'uris'


class GraphWrapper(abc.ABC):
    """
    Abstract method for accessing RDF's for querying.
    """

    @abc.abstractmethod
    def query(self, q: str) -> Iterable[Dict[str, Dict[str, str]]]:
        """
        Args:
            q: SPARQL query string
        Returns:
            Iterable with tuples of query results.
        """
        pass

    def get_column(self, l, k: str) -> List[str]:
        """Convert results to simpler format
        Args:
            l:
            k: key
        Returns:
        """

        def get_val(row_k):
            return row_k["value"] if row_k else None

        return [get_val(row[k]) for row in l]


class RDFLibGraphWrapper(GraphWrapper):
    def __init__(self, path_rdf):
        super(RDFLibGraphWrapper, self).__init__()
        g = rdflib.Graph()
        g.parse(path_rdf)

        self.g = g

    def query(self, q) -> List[Dict[str, Union[Literal, URIRef, BNode]]]:

        # TODO Order by not working when using group
        if ("group by" in q.lower()) or ("groupby" in q.lower()):
            # This removes the sorting part, hacky fix, but it works.
            i_order_by = max(q.lower().find("order by"), q.lower().find("orderby"))
            if i_order_by > 0:
                q = q[:i_order_by]

        def get_identifier_dict(v):

            t = (
                "literal"
                if isinstance(v, Literal)
                else ("bnode" if isinstance(v, BNode) else ("uri" if isinstance(v, URIRef) else None))
            )

            d = {"type": t, "value": v.toPython()}

            try:
                lang = v.language
            except AttributeError as e:
                pass
            else:
                d_i["xml:lang"] = lang

            return d

        qres = self.g.query(q)

        l = []
        for l_i in qres:
            d_i = {}
            for k, v in zip(qres.vars, l_i):
                d_i[str(k)] = get_identifier_dict(v) if v else None

            l.append(d_i)

        return l


class SPARQLGraphWrapper(GraphWrapper):
    def __init__(self, endpoint):
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)

    def query(self, q: str) -> Iterable[Dict[str, Dict[str, str]]]:
        self.sparql.setQuery(q)
        ret = self.sparql.query()
        results = ret.convert()

        vars = results["head"]["vars"]

        l = []
        for binding_i in results["results"]["bindings"]:
            # l.append({k: v['value'] for k, v in binding_i.items()})
            # list(binding_i.keys())

            # l_i = tuple(binding_i[k]['value'] for k in list(binding_i.keys()))

            # Also add variables without results as None.
            l_i = {k_j: binding_i.get(k_j, None) for k_j in vars}
            l.append(l_i)

        return l


class SPARQLReportingObligationProvider:
    def __init__(self, graph_wrapper: GraphWrapper):
        self.graph_wrapper = graph_wrapper

    def get_different_entity_types(self):
        q = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dgfro: <{build_rdf.RO_BASE}>

            SELECT DISTINCT ?pred # ?entClass
            WHERE {{
                ?pred rdfs:domain dgfro:ReportingObligation ;
                    rdfs:range ?entClass .

            FILTER ( EXISTS {{ ?entClass rdfs:subClassOf skos:Concept . }} ||
                ?entClass = skos:Concept
            )
            }}
        """

        l = list(self.graph_wrapper.query(q))

        if len(l) == 0:
            raise ValueError(
                "No entity types were found.\n"
                "RDF has not been initialized yet.\n"
                "See technical documentation for more information"
            )

        l_entity_predicates = self.graph_wrapper.get_column(l, "pred")

        return l_entity_predicates

    def get_all_from_type(self, type_uri, distinct=True) -> List[str]:
        """
        Args:
            type_uri:
            distinct: Returning distinct elements is base behaviour
        Returns:
        """
        warnings.warn(f"Use {self.get_filter_entities_from_type_lazy_loading} instead", DeprecationWarning)

        VALUE = "value_ent"

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT {'DISTINCT' if distinct else ''} ?{VALUE}
            WHERE {{
                ?ro a {build_rdf.ROGraph.class_rep_obl.n3()} ;
                    {URIRef(type_uri).n3()} ?ent .
                ?ent skos:prefLabel ?{VALUE}

                BIND (LCASE(?{VALUE}) AS ?value_ent_lower)
                BIND (REPLACE(REPLACE(?value_ent_lower,'[^a-zA-Z\\\\s]+', ''), '^[ \\t]+|[ \\t]+$','') AS ?special_sort)
            }}

            ORDER BY
            ASC(str(?special_sort) = '')
            (?special_sort)
            ASC(?value_ent_lower)
            ASC(?{VALUE})
        """
        #                 FILTER (lang(?value) = 'en')
        l = list(self.graph_wrapper.query(q))

        l_values = self.graph_wrapper.get_column(l, VALUE)

        return l_values

    def get_all_doc_uri(self) -> List[str]:
        """
        There was a demand to retrieve all documents from fuseki
        :return:
        """

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?{SUB}
            WHERE {{
                ?{SUB} a {build_rdf.ROGraph.class_cat_doc.n3()} .
            }}
            """

        l = self.graph_wrapper.query(q)

        l_uri = self.graph_wrapper.get_column(l, SUB)

        return l_uri

    def get_all_ro_uri(self) -> List[str]:
        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?ro_id
            WHERE {{
                ?ro_id rdf:type {build_rdf.ROGraph.class_rep_obl.n3()} .
            }}
            """

        l = self.graph_wrapper.query(q)

        l_uri = self.graph_wrapper.get_column(l, "ro_id")

        return l_uri

    def get_all_ro_str(self):
        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?value ?ro_id
            WHERE {{
                ?ro_id rdf:type {build_rdf.ROGraph.class_rep_obl.n3()} ;
                    rdf:value ?value
            }}
        """
        l = self.graph_wrapper.query(q)

        l_ro = self.graph_wrapper.get_column(l, "value")

        return l_ro

    def get_filter_single(self, pred, value) -> List[str]:
        """Retrieve reporting obligations with a matching value for certain predicate
        Args:
            pred: predicate URI
            value: string to match
        Returns:
            List of reporting obligations with matching content.
        """
        warnings.warn(f"Use {self.get_filter_ro_id_multiple} instead", DeprecationWarning)

        return self.get_filter_multiple([(pred, value)])

    def get_filter_multiple(self, list_pred_value: List[Tuple[str]] = [], exact_match=False) -> List[str]:
        """Retrieve reporting obligations with a matching value for certain predicate
        Args:
            list_pred_value: List[(pred:str, value:str)]
            e.g. [ ("<pred 1>", "<value 1>"),
                    ...
                    ("<pred n>", "<value n>") ]
        Returns:
        """
        warnings.warn(f"Use {self.get_filter_ro_id_multiple} instead", DeprecationWarning)

        q_filter = self._get_q_filter(list_pred_value, exact_match=exact_match)

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?value ?ro_id ?p
            WHERE {{
                ?ro_id rdf:type {build_rdf.ROGraph.class_rep_obl.n3()} ;
                    rdf:value ?value .

                {q_filter}
            }}
        """

        if B_LOG_QUERIES:
            logging.info(q)

        l = self.graph_wrapper.query(q)

        l_ro = self.graph_wrapper.get_column(l, "value")

        return l_ro

    def get_filter_ro_id_multiple(
        self,
        list_pred_value: List[Tuple[str]] = [],
        l_doc_uri: List[str] = None,
        doc_src: str = None,
        limit=None,
        offset=0,
        exact_match: bool = False,
    ) -> List[str]:
        """Retrieve reporting obligations UID's with a matching value for certain predicate
        Args:
            list_pred_value: List[(pred:str, value:str)]
            e.g. [ ("<pred 1>", "<value 1>"),
                    ...
                    ("<pred n>", "<value n>") ]
            doc_src: uri/url to document source/website.
            limit: number of id's to return
            offset: what index to start from (counting from 0)
            exact_match: (boolean) if exact matches or contains in matches should be retrieved
        Returns:
            List with URI's of the Reporting obligations.
        """

        q_doc_uri_filter = (
            ""
            if l_doc_uri is None
            else self._get_filter_doc_uri(
                l_doc_uri,
                ro_var="ro_id",
            )
        )

        q_doc_src_filter = (
            ""
            if doc_src is None
            else self._get_filter_doc_src(
                doc_src,
                ro_var="ro_id",
            )
        )

        q_filter = self._get_q_filter(list_pred_value, ro="ro_id", exact_match=exact_match)

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT DISTINCT ?ro_id
            WHERE {{
                {q_doc_uri_filter}
                {q_doc_src_filter}
                ?ro_id rdf:type {build_rdf.ROGraph.class_rep_obl.n3()} ;
                   rdf:value ?{VALUE} .

            {q_filter}
        }}

        ORDER BY ASC(LCASE(?{VALUE})) ASC(?{VALUE}) ?ro_id
        """

        if limit is not None:
            q += f"""LIMIT {limit}"""

        if offset:
            q += f"""OFFSET {offset}"""

        if B_LOG_QUERIES:
            logging.info(q)

        l = self.graph_wrapper.query(q)

        l_ro_id = self.graph_wrapper.get_column(l, "ro_id")

        r = {QUERY: q, URIS: l_ro_id}

        return r

    def get_entities(self, distinct=True):
        """Trying to speed up get_filter_entities without filters.
        Returns:
        """

        l_has = [has_i for has_i, type_i in build_rdf.D_ENTITIES.values()]

        q_values = f"""
        VALUES ?{PRED} {{{' '.join(map(lambda x: x.n3(), l_has))}}}
        """

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT {'DISTINCT' if distinct else ''} ?{PRED} ?{VALUE} (count(?ro_id) as ?{COUNT})
            WHERE {{

                {q_values}

                ?ro_id a {build_rdf.ROGraph.class_rep_obl.n3()} ;
                    ?{PRED} ?ent .
                ?ent skos:prefLabel ?{VALUE} .
            }}
            GROUP BY ?{PRED} ?{VALUE}
            ORDER BY (LCASE(?{PRED})) (LCASE(?{VALUE})) ASC(?{VALUE})
        """

        l = list(self.graph_wrapper.query(q))

        d_filtered_ents = {}
        for l_i in l:
            has_type_i = l_i.get(PRED).get("value")

            d_filtered_ents.setdefault(has_type_i, []).append(
                {VALUE: l_i.get(VALUE).get("value"), COUNT: l_i.get(COUNT).get("value")}
            )

        return d_filtered_ents

    def get_filter_entities(self, list_pred_value: List[Tuple[str]] = [], distinct=True, exact_match: bool = False):
        """Return all entities per type based on filters
        Args:
            list_pred_value: Filters to apply similar to get_filter_ro_id_multiple.
            distinct:
        Returns:
        """

        VALUE = "value_ent"
        PRED = "pred"
        COUNT = "count"

        l_has = [has_i for has_i, type_i in build_rdf.D_ENTITIES.values()]

        q_values = f"""
        VALUES ?{PRED} {{{' '.join(map(lambda x: x.n3(), l_has))}}}
        """

        q_filter = self._get_q_filter(list_pred_value, exact_match=exact_match)

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT {'DISTINCT' if distinct else ''} ?{PRED} ?{VALUE} (count(?ro_id) as ?{COUNT})
            WHERE {{
                {q_values}

                ?ro_id rdf:type {build_rdf.ROGraph.class_rep_obl.n3()} ;
                    ?{PRED} ?ent .
                ?ent skos:prefLabel ?{VALUE} .

                {q_filter}
            }}

            GROUP BY ?{PRED} ?{VALUE}

            ORDER BY (LCASE(?{PRED})) (LCASE(?{VALUE})) (?{VALUE})
        """

        l = list(self.graph_wrapper.query(q))

        d_filtered_ents = {}
        for l_i in l:
            ent_i = l_i.get(PRED).get("value")

            d_filtered_ents.setdefault(ent_i, []).append(
                {VALUE: l_i.get(VALUE).get("value"), COUNT: l_i.get(COUNT).get("value")}
            )

        return d_filtered_ents

    def get_filter_entities_from_type(
        self, type_uri, list_pred_value: List[Tuple[str]] = [], distinct=True, exact_match: bool = False
    ):
        """
        Args:
            type_uri: from which type of entity to return entities of.
            list_pred_value: Filters to apply similar to get_filter_ro_id_multiple.
            distinct:
        Returns:
        """

        VALUE = "value_ent"

        q_filter = self._get_q_filter(list_pred_value, exact_match=exact_match)

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: {build_rdf.RO_BASE[None].n3()}
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            # SELECT DISTINCT ?ro_id
            SELECT {'DISTINCT' if distinct else ''} ?{VALUE}
            WHERE {{
                ?ro_id rdf:type {build_rdf.ROGraph.class_rep_obl.n3()} ;
                    rdf:value ?value ;
                    {URIRef(type_uri).n3()} ?ent .
                ?ent skos:prefLabel ?{VALUE} .

                {q_filter}
          }}
          ORDER BY (LCASE(?{VALUE})) (?{VALUE})
          """

        l = list(self.graph_wrapper.query(q))
        l_values = self.graph_wrapper.get_column(l, VALUE)

        return l_values

    def get_filter_entities_from_type_lazy_loading(
        self,
        uri_type_has,
        str_match: str = "",
        type_match=CONTAINS,
        list_pred_value: List[Tuple[str]] = [],
        l_doc_uri: List[str] = None,
        doc_src: str = None,
        exact_match=False,
        limit: int = 0,
    ):

        """Filter the entities for a certain entity type.
        Args:
            uri_type_has: The URI of the <hasEntity> predicate type.
            str_match: (str) the string to match to.
            type_match: rdf_parser.CONTAINS or rdf_parser.STARTS_WITH
            doc_src: uri/url to document source/website.
        Returns:
            List of strings with the labels of the entities.
        """

        VALUE = "value_ent"
        RO = "RO"

        starts_with_options = [CONTAINS, STARTS_WITH]
        if type_match not in starts_with_options:
            warnings.warn(f"Unknown value for type_match: {type_match}", UserWarning)

        q_doc_uri_filter = (
            ""
            if l_doc_uri is None
            else self._get_filter_doc_uri(
                l_doc_uri,
                ro_var=RO,
            )
        )

        q_doc_src_filter = (
            ""
            if doc_src is None
            else self._get_filter_doc_src(
                doc_src,
                ro_var=RO,
            )
        )

        q_filter = self._get_q_filter(list_pred_value, ro=RO, exact_match=exact_match) if list_pred_value else ""

        str_match = str_match.strip()

        if str_match == "":
            q_filter_entity = ""
        elif type_match == CONTAINS:
            q_filter_entity = f"""
                FILTER CONTAINS(LCASE(?value_ent), LCASE({Literal(str_match).n3()}))
            """
        elif type_match == STARTS_WITH:
            q_filter_entity = f"""
                FILTER STRSTARTS(LCASE(?value_ent), LCASE({Literal(str_match).n3()}))
            """
        else:
            raise ValueError(f"Unknown value for {type_match}. Expected a value from {starts_with_options}).")

        q_sort_str_match = f"DESC(strStarts(?value_ent_lower, LCASE({Literal(str_match).n3()})))" if str_match else ""

        q = f"""

        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX dgfro: {URIRef(build_rdf.RO_BASE).n3()}

        SELECT DISTINCT ?{VALUE}

        WHERE {{
            {q_doc_uri_filter}
            {q_doc_src_filter}

            ?{RO} a dgfro:ReportingObligation ;
                {URIRef(uri_type_has).n3()} ?ent .
            ?ent skos:prefLabel ?{VALUE} .

            BIND (LCASE(?{VALUE}) AS ?value_ent_lower)
            BIND (REPLACE(REPLACE(?value_ent_lower,'[^a-zA-Z\\\\s]+', ''), '^[ \\t]+|[ \\t]+$','') AS ?special_sort)
            {q_filter}

            {q_filter_entity}
        }}

        ORDER BY
        {q_sort_str_match}
        ASC(str(?special_sort) = '')
        (?special_sort)
        ASC(?value_ent_lower)
        ASC(?{VALUE})
        {f"LIMIT {limit}" if limit else ''}

        """

        if 0:
            print(q)

        l = list(self.graph_wrapper.query(q))
        l_values = self.graph_wrapper.get_column(l, VALUE)

        return l_values

    def get_document_and_source_pairs(self) -> List[Tuple[str, str]]:
        """
        Retrieves a list of document ID's with it's respective document source (if available).
        :return:
        """

        DOC = "doc_id"
        SRC = "src_id"

        q = f"""
        PREFIX dgfro: {build_rdf.RO_BASE[''].n3()}
        SELECT DISTINCT ?{DOC} ?{SRC}
        {{
            ?{DOC} a {build_rdf.ROGraph.class_cat_doc.n3()} .
            OPTIONAL {{
                ?{DOC} {build_rdf.ROGraph.prop_has_doc_src.n3()} ?{SRC} .
                ?{SRC} a {build_rdf.ROGraph.class_doc_src.n3()} .
            }}
        }}
        """

        l = list(self.graph_wrapper.query(q))
        l_doc = self.graph_wrapper.get_column(l, DOC)
        l_src = self.graph_wrapper.get_column(l, SRC)

        return list(zip(l_doc, l_src))

    @staticmethod
    def _get_q_filter(list_pred_value: List[Tuple[str]] = [], ro="ro_id", exact_match: bool = False):
        """
        values of the filters are stripped from leading and trailing spaces.
        Args:
            list_pred_value: e.g. [("dgfisma.com/hasReporter", "The highest authority")]
            exact_match: (boolean) True means exact matches, although case insensitive, are retrieved
                False means we look for substrings.
        Returns:
        """
        q_total = ""

        def get_q_filter_i(i, value_i, exact_match=True):

            if exact_match:
                q_filter_i = f"""
                    lcase(str(?p{i})) = lcase({Literal(value_i.strip()).n3()})
                """
            else:
                q_filter_i = f"""
                    CONTAINS(
                        lcase(str(?p{i})), lcase({Literal(value_i.strip()).n3()})
                    )
                """

            return q_filter_i

        for i, (pred, value) in enumerate(list_pred_value):

            if isinstance(value, (list, tuple)):
                q_filter_i = "||".join(
                    map(lambda value_i_j: get_q_filter_i(i, value_i_j, exact_match=exact_match), value)
                )

            else:
                q_filter_i = get_q_filter_i(i, value, exact_match=exact_match)

            q_i = f"""
                ?{ro} {URIRef(pred).n3()} ?ent{i} .
                ?ent{i} skos:prefLabel ?p{i} .
                FILTER({q_filter_i})
            """

            q_total += q_i

        return q_total

    @staticmethod
    def _get_filter_doc_uri(
        list_doc_uri: List[str],
        ro_var: str = "ro_id",
        doc_var: str = "doc_id",
    ):

        # dgfro:hasReportingObligation
        q = f"""
        values ?{doc_var} {{ {' '.join(map(lambda s: URIRef(s).n3(), list_doc_uri))} }}
        ?{doc_var} {build_rdf.RO_BASE.hasReportingObligation.n3()} ?{ro_var} .
        """

        return q

    @staticmethod
    def _get_filter_doc_src(
        doc_src: str, ro_var: str = "ro_id", doc_var: str = "doc_id", doc_src_var: str = "doc_src_id"
    ):

        # dgfro:hasDocumentSource
        q = f"""
        bind ({URIRef(doc_src).n3()} as ?{doc_src_var})
        ?{doc_var} {build_rdf.ROGraph.prop_has_doc_src.n3()} ?{doc_src_var} ;
            {build_rdf.ROGraph.prop_has_rep_obl.n3()} ?{ro_var} .
        """

        return q

    def info_doc_source(self):
        """
        Retrieves a summary # documents and # reporting obligations per source.
        :return:
        """

        SRC = "doc_src_id"
        SRC_NAME = "src_name"
        N_DOC = "n_DOC"
        N_RO = "n_RO"

        q = f"""
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX dgfro: <http://dgfisma.com/reporting_obligations/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            SELECT ?{SRC} ?{SRC_NAME} (count(DISTINCT ?ro_id) as ?{N_RO}) (count(DISTINCT ?doc_id) as ?{N_DOC})
            WHERE {{

              ?doc_id <http://dgfisma.com/reporting_obligations/hasDocumentSource> ?{SRC} .
              ?{SRC} rdf:value ?{SRC_NAME} .

                ?doc_id <http://dgfisma.com/reporting_obligations/hasReportingObligation> ?ro_id .
                ?ro_id a <http://dgfisma.com/reporting_obligations/ReportingObligation> .

            }}

            GROUP BY ?{SRC} ?{SRC_NAME}
            ORDER BY ?{SRC} ?{SRC_NAME}
        """

        l = list(self.graph_wrapper.query(q))
        l_src = self.graph_wrapper.get_column(l, SRC)
        l_src_name = self.graph_wrapper.get_column(l, SRC_NAME)
        l_n_doc = self.graph_wrapper.get_column(l, N_DOC)
        l_n_ro = self.graph_wrapper.get_column(l, N_RO)

        return list(zip(l_src, l_src_name, l_n_doc, l_n_ro))
