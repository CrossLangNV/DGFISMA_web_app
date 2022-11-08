from obligations.models import ReportingObligation


def rdf_get_reporters_mock():
    # TODO Mock
    reporters = ReportingObligation.objects.all()
    result = []

    for reporter in reporters:
        result.append(reporter.name)

    return result


def rdf_get_verbs_mock():
    # TODO Mock
    verbs = ["shall", "must"]
    return verbs


def rdf_get_reports_mock():
    # TODO Mock
    reports = ["report", "submit", "reviewed", "review"]
    return reports


def rdf_get_regulatory_body_mock():
    # TODO Mock
    regulatory_body = [
        "to the Commission",
        "to the competent authorities",
        "to the board",
        "to the council",
        "to the president",
        "to the management",
    ]
    return regulatory_body


def rdf_get_propmod_mock():
    # TODO Mock
    prop_mod = [
        "in accordance with the reporting requirements set out in Article 415(1 ) and the uniform reporting formats referred to in Article 415(3 )",
        "in accordance with requirements",
    ]
    return prop_mod


def rdf_get_entity_mock():
    # TODO Mock
    entity = [
        "those draft regulatory technical standards",
        "inflows from any of the liquid assets reported in accordance with Article 416 other than payments due on the assets that are not reflected in the market value of the asset",
        "inflows from any new obligations entered into",
        "about the result of the process referred to in Article 20(1)(b )",
        "Fulfilment of the conditions for such higher inflows",
    ]
    return entity


def rdf_get_frequency_mock():
    # TODO Mock
    frequency = [
        "regularly",
        "by 1 January 2015",
        "daily",
        "monthly",
        "yearly",
        "upon request",
        "within a deadline set by the board",
        "in the previous financial year",
    ]
    return frequency
