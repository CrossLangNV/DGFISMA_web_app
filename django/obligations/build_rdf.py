import os
import warnings

from SPARQLWrapper import SPARQLWrapper, JSON, GET
from rdflib import BNode, Namespace, Graph
from rdflib.namespace import SKOS, RDF, RDFS, OWL, DC
from rdflib.term import _serial_number_generator, _is_valid_uri, URIRef, Literal
from obligations.cas_parser import CasContent, KEY_CHILDREN, KEY_SENTENCE_FRAG_CLASS, KEY_VALUE

NS_BASE = Namespace("http://dgfisma.com/")
RO_BASE = Namespace(NS_BASE + "reporting_obligations/")

# FROM https://github.com/CrossLangNV/DGFISMA_reporting_obligations
D_ENTITIES = {
    "ARG0": (RO_BASE["hasReporter"], RO_BASE["Reporter"]),
    "ARG1": (RO_BASE["hasReport"], RO_BASE["Report"]),
    "ARG2": (RO_BASE["hasRegulatoryBody"], RO_BASE["RegulatoryBody"]),
    "ARG3": (RO_BASE["hasDetails"], RO_BASE["Details"]),
    "V": (RO_BASE["hasVerb"], RO_BASE["Verb"]),  # Pivot verb
    # http://clear.colorado.edu/compsem/documents/propbank_guidelines.pdf
    "ARGM-TMP": (RO_BASE["hasPropTmp"], RO_BASE["PropTmp"]),
    "ARGM-LOC": (RO_BASE["hasPropLoc"], RO_BASE["PropLoc"]),  # Locatives
    "ARGM-CAU": (RO_BASE["hasPropCau"], RO_BASE["PropCau"]),
    "ARGM-EXT": (RO_BASE["hasPropExt"], RO_BASE["PropExt"]),
    "ARGM-MNR": (RO_BASE["hasPropMnr"], RO_BASE["PropMnr"]),
    "ARGM-PNC": (RO_BASE["hasPropPnc"], RO_BASE["PropPnc"]),
    "ARGM-ADV": (RO_BASE["hasPropAdv"], RO_BASE["PropAdv"]),
    "ARGM-DIR": (RO_BASE["hasPropDir"], RO_BASE["PropDir"]),  # Directional
    "ARGM-NEG": (RO_BASE["hasPropNeg"], RO_BASE["PropNeg"]),
    "ARGM-MOD": (RO_BASE["hasPropMod"], RO_BASE["PropMod"]),  # Modals
    "ARGM-DIS": (RO_BASE["hasPropDis"], RO_BASE["PropDis"]),  # Discourse
    "ARGM-PRP": (RO_BASE["hasPropPrp"], RO_BASE["PropPrp"]),  # Purpose
    "ARGM-PRD": (RO_BASE["hasPropPrd"], RO_BASE["PropPrd"]),  # Secondary Predication
    # Unused until proven, added for completeness
    "ARGM-COM": (RO_BASE["hasPropCom"], RO_BASE["PropCom"]),  # Comitatives
    "ARGM-GOL": (RO_BASE["hasPropGol"], RO_BASE["PropGol"]),  # Goal
    "ARGM-REC": (RO_BASE["hasPropRec"], RO_BASE["PropRec"]),  # Reciprocals
    "ARGM-DSP": (RO_BASE["hasPropDsp"], RO_BASE["PropDsp"]),  # Direct Speech
    "ARGM-LVB": (RO_BASE["hasPropLVB"], RO_BASE["PropLvb"]),  # Light Verb
}

PROP_HAS_ENTITY = RO_BASE.hasEntity


class ROGraph(Graph):
    """
    Reporting Obligation Graph
    """

    # Final
    # Init classes & connections
    # Classes
    class_cat_doc = RO_BASE.CatalogueDocument
    class_rep_obl = RO_BASE.ReportingObligation
    class_doc_src = RO_BASE.DocumentSource
    # Connections
    prop_has_rep_obl = RO_BASE.hasReportingObligation
    prop_has_doc_src = RO_BASE.hasDocumentSource

    def __init__(self, *args, include_schema=False, **kwargs):
        """Looks quite clean if implemented with RDFLib https://github.com/RDFLib/rdflib
        Ontology can be visualised with http://www.visualdataweb.de/webvowl/
        Args:
            *args:
            **kwargs:
        """

        super(ROGraph, self).__init__(*args, **kwargs)

        self.bind("rdf", RDF)
        self.bind("rdfs", RDFS)
        self.bind("skos", SKOS)
        self.bind("owl", OWL)
        self.bind("dgf", NS_BASE)
        self.bind("dgfro", RO_BASE)
        self.bind("dc", DC)

        if include_schema:
            self._init_schema()

    def _init_schema(self):

        """
        describe ontology
        """
        # header info
        ont = OWL.Ontology
        self.add((RO_BASE[""], RDF.type, ont))
        self.add((RO_BASE[""], DC.title, Literal("Reporting obligations (RO) vocabulary")))

        self._add_owl_class(self.class_cat_doc)
        self._add_owl_class(self.class_rep_obl)
        self._add_owl_class(self.class_doc_src)

        # OWL properties
        self._add_property(self.prop_has_rep_obl, self.class_cat_doc, self.class_rep_obl)
        self._add_property(self.prop_has_doc_src, self.class_cat_doc, self.class_doc_src)

        self._add_property(RDF.value, self.class_rep_obl, RDFS.Literal)
        self._add_property(RDF.value, self.class_doc_src, RDFS.Literal)

        self._add_property(PROP_HAS_ENTITY, self.class_rep_obl, SKOS.Concept)

        for prop, cls in D_ENTITIES.values():
            self._add_property(prop, self.class_rep_obl, cls)
            # Sub property
            self.add((prop, RDFS.subPropertyOf, PROP_HAS_ENTITY))
            self._add_sub_class(cls, SKOS.Concept)

    # OWL classes
    def _add_owl_class(self, cls):
        self.add((cls, RDF.type, RDFS.Class))
        self.add((cls, RDF.type, OWL.Class))

    def add_cas_content(self, cas_content: CasContent, doc_id: str, query_endpoint=None):
        """Build the RDF from cas content.
        Args:
            cas_content:
            doc_id:
            query_endpoint: (Optional) is used to check if RO already exist. If so, the ID is re-used.
                If an endpoint is provided, all previous RO's will be removed!
        Returns:
        """

        # Only add (and remove) triples at the end to enable auto-commit/transactions to work.
        l_add = []
        l_remove = []

        if query_endpoint:
            ro_update = ROUpdate(query_endpoint)

        # add a document
        cat_doc = self._get_cat_doc_uri(doc_id)

        cas_content["id"] = cat_doc.toPython()  # adding ID to cas

        # iterate over reporting obligations (RO's)
        list_ro = cas_content[KEY_CHILDREN]

        if len(list_ro) == 0:  # No reporting obligations, no need to add to fuseki
            return

        l_add.append((cat_doc, RDF.type, self.class_cat_doc))

        for i, ro_i in enumerate(list_ro):

            value_i = ro_i[KEY_VALUE]

            if query_endpoint:
                l_ro_uri = ro_update.get_l_ro(value_i, doc_uri=cat_doc)

                if len(l_ro_uri):  # At least one RO's found, keep 1 and remove the rest
                    rep_obl_i = URIRef(l_ro_uri[0])
                else:  # RO not found, just make a new one
                    rep_obl_i = get_UID_node(info="rep_obl_")

                for i_ro_uri, ro_uri_i in enumerate(l_ro_uri):
                    l_remove.extend(
                        self._get_triples_remove_reporting_obligation(
                            ro_uri_i,
                            keep_value=i_ro_uri == 0,
                        )
                    )

            else:
                rep_obl_i = get_UID_node(info="rep_obl_")

            l_add.append((rep_obl_i, RDF.type, self.class_rep_obl))
            # link to catalog document + ontology
            l_add.append((cat_doc, self.prop_has_rep_obl, rep_obl_i))
            # add whole reporting obligation
            l_add.append((rep_obl_i, RDF.value, Literal(value_i)))
            cas_content[KEY_CHILDREN][i]["id"] = rep_obl_i.toPython()  # adding ID to cas

            # iterate over different entities of RO
            for j, ent_j in enumerate(ro_i[KEY_CHILDREN]):

                concept_j = get_UID_node(info="entity_")

                t_pred_cls = D_ENTITIES.get(ent_j[KEY_SENTENCE_FRAG_CLASS])
                if t_pred_cls is None:
                    # Unknown property/entity class
                    # TODO how to handle unknown entities?

                    print(f"Unknown sentence entity class: {ent_j[KEY_SENTENCE_FRAG_CLASS]}")

                    pred_i = PROP_HAS_ENTITY
                    cls = SKOS.Concept

                else:
                    pred_i, cls = t_pred_cls

                # type definition
                l_add.append((concept_j, RDF.type, cls))
                # Add the string representation
                value_j = Literal(ent_j[KEY_VALUE], lang="en")
                l_add.append((concept_j, SKOS.prefLabel, value_j))

                # connect entity with RO
                l_add.append((rep_obl_i, pred_i, concept_j))

                cas_content[KEY_CHILDREN][i][KEY_CHILDREN][j]["id"] = concept_j.toPython()  # adding ID to cas

        for triple in l_remove:
            self.remove(triple)

        for triple in l_add:
            self.add(triple)

        return cas_content

    def get_doc_source(self, doc_id: str):
        # TODO
        return

    def add_doc_source(
        self,
        doc_id: str,
        source_id: str,
        source_name: str = None,
    ) -> None:
        """
        :param doc_id: id that refers to the document (From Django)
        :param source_id: document/website source id, ideally the URL
        :param source_name: (Optional) label of the document source
        :return: None
        """

        l_add = []

        cat_doc = self._get_cat_doc_uri(doc_id)

        # Check if uri like, else convert to one.

        def _get_source_uri(source_id):

            if _is_valid_uri(source_id):
                return URIRef(source_id)
            else:
                return RO_BASE["doc_src/" + source_id.strip().replace(" ", "_")]

        source_uri = _get_source_uri(source_id)

        l_add.append((cat_doc, self.prop_has_doc_src, source_uri))
        l_add.append((source_uri, RDF.type, self.class_doc_src))

        if source_name:
            l_add.append((source_uri, RDF.value, Literal(source_name, lang="en")))

        for triple in l_add:
            self.add(triple)

    def remove_doc_source(self, doc_id: str, b_link_only: bool = True) -> None:
        """
        Removes all document source information from a document.
        :param doc_id:
        :param b_link_only: (Optional) By default, only the link between the document and the source is broken.
            When False, the doc_source element is deleted as well.
        :return:
        """

        cat_doc = self._get_cat_doc_uri(doc_id)

        # Same doc sources are shared, so you probably don't want to remove it's value
        q_delete_doc_src = (
            ""
            if b_link_only
            else f"""
            BIND (rdf:value as ?val)

            OPTIONAL {{
                ?doc_src_id a ?doc_src .
            }}

            OPTIONAL {{ # Not every doc source has a name associated with it.
               ?doc_src_id ?val ?src_name .
            }}
        """
        )

        q_construct_delete_doc_src = (
            ""
            if b_link_only
            else f"""
        	?doc_src_id a ?doc_src .
        """
        )

        q_construct = f"""
            PREFIX dgfisma: {RO_BASE[''].n3()}
            PREFIX rdf: {RDF.uri.n3()}
            # For testing, replace DELETE with SELECT
            CONSTRUCT {{
                ?doc_id ?hasdocsrc ?doc_src_id .
                ?doc_src_id  ?val ?src_name .
                {q_construct_delete_doc_src}

            }}
            WHERE {{
                BIND ({cat_doc.n3()} as ?doc_id)
                BIND (dgfisma:hasDocumentSource as ?hasdocsrc)
                ?doc_id ?hasdocsrc ?doc_src_id .

                {q_delete_doc_src}
            }}
        """

        a = self.query(q_construct)

        l_remove = []
        l_remove.extend(a)
        for triple in l_remove:
            self.remove(triple)

        return

    def _add_property(self, prop: URIRef, domain: URIRef, ran: URIRef) -> None:
        """shared function to build all necessary triples for a property in the ontology.
        Args:
            prop:
            domain:
            ran:
        Returns:
            None
        """
        self.add((prop, RDF.type, RDF.Property))
        self.add((prop, RDFS.domain, domain))
        self.add((prop, RDFS.range, ran))

    def _add_sub_class(self, child_cls: URIRef, parent_cls: URIRef) -> None:
        self.add((child_cls, RDFS.subClassOf, parent_cls))

    def _get_triples_remove_reporting_obligation(self, ro_i: URIRef, keep_value=True):
        """
        The reporting obligation (with it's entities should be deleted)
        Args:
            ro_i:
            keep_value: Boolean, if keep_value, then a single triple stays with (RO URI, value, string)
        Returns:
        """

        q_ent_construct = f"""
        PREFIX dgfisma: <http://dgfisma.com/reporting_obligations/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        # For testing, replace DELETE with SELECT
        CONSTRUCT {{
            ?ent ?p ?o .
        }}
        WHERE {{
        VALUES ?ro_uri {{ {URIRef(ro_i).n3()} }}
        ?ro_uri a dgfisma:ReportingObligation ;
            ?hasEnt ?ent .
        ?ent ?p ?o
        FILTER (?hasEnt != rdf:type)
        }}
        """

        q_ro_construct = f"""
        PREFIX dgfisma: <http://dgfisma.com/reporting_obligations/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        # For testing, replace DELETE with SELECT
        CONSTRUCT {{
            ?s_ro ?p_ro2 ?ro_uri.
            ?ro_uri ?p_ro ?o_ro .
        }}
        WHERE {{
        VALUES ?ro_uri {{ {URIRef(ro_i).n3()} }}
            ?ro_uri ?p_ro ?o_ro .
            ?s_ro ?p_ro2 ?ro_uri .
        {
        "FILTER(?p_ro2 != rdf:value)" if keep_value else ""
        }
        }}
        """

        l_remove = []

        # CONSTRUCT
        a = self.query(q_ent_construct)
        l_remove.extend(a)

        a = self.query(q_ro_construct)
        l_remove.extend(a)

        return l_remove

    @staticmethod
    def _get_cat_doc_uri(doc_id):
        return RO_BASE["cat_doc/" + doc_id.strip().replace(" ", "_")]


def get_UID_node(base=RO_BASE, info=None):
    """Shared function to generate nodes that need a unique ID.
    ID is randomly generated.
    Args:
        base: used namespace
        info: info to add to the ID.
    Returns:
        a URI or BNode
    """
    if 1:
        node = base[info + _serial_number_generator()()]
    elif 0:  # blank nodes
        node = BNode()
    else:  # https://github.com/RDFLib/rdflib/pull/512#issuecomment-133857982
        node = BNode().skolemize()

    return node


class ROUpdate:
    def __init__(
        self,
        endpoint,
    ):
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)

    def get_l_ro(self, value: str, doc_uri=None):
        RO_URI = "ro_uri"
        q = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX dgfisma: <http://dgfisma.com/reporting_obligations/>
            SELECT ?{RO_URI}
            WHERE {{
                {URIRef(doc_uri).n3() if doc_uri else "?cat_doc_uri"} dgfisma:hasReportingObligation ?{RO_URI} .
                ?{RO_URI} a dgfisma:ReportingObligation ;
                rdf:value ?o
            FILTER(?o = {Literal(value).n3()})
            }}
        """
        self.sparql.setQuery(q)
        self.sparql.setMethod(GET)

        results = self.sparql.query().convert()["results"]["bindings"]
        l_ro_uri = [res[RO_URI]["value"] for res in results]

        return l_ro_uri
